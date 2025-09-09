import asyncio
import logging
import random
import sys
import time
from typing import Any, Dict, List, Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction, IBackoffPolicy, IAttemptPlanner, IProxyHealthTracker
from app.services.common.types import FetchCapabilities
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
from app.services.crawler.executors.backoff import BackoffPolicy
from app.services.browser.options.resolver import OptionsResolver
from app.services.browser.options.camoufox import CamoufoxArgsBuilder
from app.services.crawler.proxy.plan import AttemptPlanner
from app.services.crawler.proxy.health import get_health_tracker

logger = logging.getLogger(__name__)


class RetryingExecutor(IExecutor):
    """Crawl executor that performs multiple attempts with retry logic."""
    
    def __init__(self, 
                 fetch_client: Optional[ScraplingFetcherAdapter] = None,
                 options_resolver: Optional[OptionsResolver] = None,
                 arg_composer: Optional[FetchArgComposer] = None,
                 camoufox_builder: Optional[CamoufoxArgsBuilder] = None,
                 backoff_policy: Optional[IBackoffPolicy] = None,
                 attempt_planner: Optional[IAttemptPlanner] = None,
                 health_tracker: Optional[IProxyHealthTracker] = None):
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()
        self.options_resolver = options_resolver or OptionsResolver()
        self.arg_composer = arg_composer or FetchArgComposer()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()
        self.backoff_policy = backoff_policy or BackoffPolicy.from_settings(app_config.get_settings())
        self.attempt_planner = attempt_planner or AttemptPlanner()
        self.health_tracker = health_tracker or get_health_tracker()
    
    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute crawl with retry and proxy strategy."""
        # Windows event loop policy fix
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        settings = app_config.get_settings()
        public_proxies = self._load_public_proxies(settings.proxy_list_file_path)
        candidates = public_proxies.copy()
        if getattr(settings, "private_proxy_url", None):
            candidates.append(settings.private_proxy_url)

        last_error = None

        user_data_cleanup = None
        try:
            caps = self.fetch_client.detect_capabilities()

            options = self.options_resolver.resolve(request, settings)
            additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps)
            # Capture optional cleanup callback from user-data context (read/write modes)
            try:
                user_data_cleanup = additional_args.get('_user_data_cleanup') if additional_args else None
            except Exception:
                user_data_cleanup = None
            if not caps.supports_proxy:
                logger.warning(
                    "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
                )

            attempt_count = 0
            last_used_proxy: Optional[str] = None
            attempt_plan = self.attempt_planner.build_plan(settings, public_proxies)

            while attempt_count < settings.max_retries:
                selected_proxy: Optional[str] = None
                mode = "direct"

                if getattr(settings, "proxy_rotation_mode", "sequential") != "random" or not candidates:
                    found_healthy_attempt = False
                    while attempt_count < settings.max_retries:
                        attempt_config = attempt_plan[attempt_count]
                        candidate_proxy = attempt_config["proxy"]
                        candidate_mode = attempt_config["mode"]

                        if candidate_proxy and self.health_tracker.is_unhealthy(candidate_proxy):
                            logger.info(
                                f"Attempt {attempt_count+1} skipped - {candidate_mode} proxy {self._redact_proxy(candidate_proxy)} is unhealthy"
                            )
                            attempt_count += 1
                            continue

                        selected_proxy = candidate_proxy
                        mode = candidate_mode
                        found_healthy_attempt = True
                        break

                    if not found_healthy_attempt:
                        break
                else:
                    # Random rotation: prefer public proxies; reserve private for the last attempt
                    private = getattr(settings, "private_proxy_url", None)
                    healthy_public = [
                        p for p in public_proxies if not self.health_tracker.is_unhealthy(p)
                    ]
                    if healthy_public:
                        # Stable ordering by value to ensure deterministic behavior
                        healthy_public = sorted(healthy_public)[:2]
                        base_order = healthy_public
                        if (attempt_count >= settings.max_retries - 1) and private:
                            selected_proxy = private
                            mode = "private"
                        elif attempt_count == 0:
                            # First attempt: first healthy public
                            selected_proxy = (healthy_public[0] if healthy_public else (private if private else None))
                            mode = "public"
                        elif attempt_count == 1:
                            # Second attempt: next healthy public different from last
                            choice_list = [p for p in healthy_public if p != last_used_proxy] or healthy_public
                            selected_proxy = (choice_list[0] if choice_list else (private if private else None))
                            mode = "public"
                        elif attempt_count == 2:
                            # Third attempt: cycle back to first healthy
                            selected_proxy = (healthy_public[0] if healthy_public else (private if private else None))
                            mode = "public"
                        elif attempt_count == 3 and private:
                            selected_proxy = private
                            mode = "private"
                        else:
                            # Fallback: first healthy or private if none
                            if healthy_public:
                                selected_proxy = healthy_public[0]
                                mode = "public"
                            elif private and not self.health_tracker.is_unhealthy(private):
                                selected_proxy = private
                                mode = "private"
                    else:
                        if private and not self.health_tracker.is_unhealthy(private):
                            selected_proxy = private
                            mode = "private"
                        else:
                            selected_proxy = None
                            mode = "direct"

                redacted_proxy = self._redact_proxy(selected_proxy)
                logger.debug(f"Attempt {attempt_count+1} using {mode} connection, proxy: {redacted_proxy}")

                try:
                    fetch_kwargs = self.arg_composer.compose(
                        options=options,
                        caps=caps,
                        selected_proxy=selected_proxy,
                        additional_args=additional_args,
                        extra_headers=extra_headers,
                        settings=settings,
                        page_action=page_action,
                    )

                    logger.info(f"Attempt {attempt_count+1} - calling fetch")
                    page = self.fetch_client.fetch(str(request.url), fetch_kwargs)

                    status = getattr(page, "status", None)
                    html = getattr(page, "html_content", None)
                    html_len = len(html or "")
                    logger.info(
                        f"Attempt {attempt_count+1} - page status: {status}, html length: {html_len}"
                    )

                    # Success only when HTTP 200 AND sufficiently complete HTML (length-based)
                    min_len = int(getattr(settings, "min_html_content_length", 500) or 0)
                    html_has_doc = bool(html and "<html" in (html.lower() if isinstance(html, str) else ""))
                    if status == 200 and html and html_len >= min_len:
                        if selected_proxy:
                            self.health_tracker.mark_success(selected_proxy)
                            logger.debug(f"Proxy {redacted_proxy} recovered")
                        logger.info(f"Attempt {attempt_count+1} outcome: success (html-ok)")
                        return CrawlResponse(status="success", url=request.url, html=html)

                    # Non-200 status is a failure and should retry; otherwise, HTML too short is failure
                    if status != 200:
                        last_error = f"Non-200 status: {status}"
                        if selected_proxy:
                            self._mark_proxy_failure(selected_proxy, settings)
                        logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")
                    else:
                        # Failure path (status 200 but unacceptable HTML)
                        if not html:
                            last_error = "HTML content is None or empty"
                        else:
                            last_error = (
                                f"HTML not acceptable (len={html_len}, has_html_tag={html_has_doc}, status={status})"
                            )
                        if selected_proxy:
                            self._mark_proxy_failure(selected_proxy, settings)
                        logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        
                        

                    
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                    if selected_proxy:
                        self._mark_proxy_failure(selected_proxy, settings)
                    logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")

                attempt_count += 1
                last_used_proxy = selected_proxy

                if attempt_count < settings.max_retries:
                    delay = self.backoff_policy.delay_for_attempt(attempt_count - 1)
                    time.sleep(delay)

            return CrawlResponse(status="failure", url=request.url, html=None, message=last_error or "exhausted retries")
        except ImportError:
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message="Scrapling library not available",
            )
        finally:
            # Cleanup any user-data clone directory or release write-mode lock
            if user_data_cleanup:
                try:
                    user_data_cleanup()
                except Exception as e:
                    logger.warning(f"Failed to cleanup user data context: {e}")
    
    def _load_public_proxies(self, file_path: Optional[str]) -> List[str]:
        """Load public proxies from a file."""
        if not file_path:
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                proxies = []
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if not line.startswith(("http://", "https://", "socks5://", "socks4://")):
                        line = f"socks5://{line}"
                    proxies.append(line)
                return proxies
        except Exception:
            return []
    
    def _mark_proxy_failure(self, proxy: str, settings) -> None:
        """Mark a proxy as failed and potentially mark it as unhealthy."""
        self.health_tracker.mark_failure(proxy)
        if self.health_tracker.get_failure_count(proxy) >= settings.proxy_health_failure_threshold:
            self.health_tracker.set_unhealthy(proxy, settings.proxy_unhealthy_cooldown_minute)
    
    def _redact_proxy(self, proxy: Optional[str]) -> str:
        """Redact proxy URL for logging."""
        from app.services.crawler.proxy.redact import redact_proxy
        return redact_proxy(proxy)
