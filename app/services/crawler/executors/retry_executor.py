import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from typing import List, Optional
import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction, IBackoffPolicy, IAttemptPlanner, IProxyHealthTracker
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
from app.services.crawler.executors.backoff import BackoffPolicy
from app.services.browser.options.resolver import OptionsResolver
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.services.crawler.proxy.plan import AttemptPlanner
from app.services.crawler.proxy.health import get_health_tracker
from app.services.crawler.proxy.redact import redact_proxy

logger = logging.getLogger(__name__)


@dataclass
class ProxySelection:
    """Represents the proxy to use for a given attempt."""

    proxy: Optional[str]
    mode: str
    attempt_index: int
    aborted: bool = False

    def __post_init__(self) -> None:
        valid_modes = {"public", "private", "direct"}
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid proxy mode '{self.mode}'. Expected one of {valid_modes}.")
        if self.attempt_index < 0:
            raise ValueError("attempt_index must be non-negative")
        if self.mode == "direct":
            if self.proxy:
                raise ValueError("Direct mode selections must not include a proxy URL")
        else:
            if not self.proxy:
                raise ValueError(f"Proxy URL required when mode is '{self.mode}'")
        if self.aborted and self.mode != "direct":
            raise ValueError("Aborted selections must use direct mode")


@dataclass
class AttemptResult:
    """Return payload from a single fetch attempt."""

    response: Optional[CrawlResponse]
    error: Optional[str]

    def __post_init__(self) -> None:
        if (self.response is None) == (self.error is None):
            raise ValueError("AttemptResult requires exactly one of response or error")


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
                selection = self._select_proxy(
                    attempt_index=attempt_count,
                    settings=settings,
                    attempt_plan=attempt_plan,
                    public_proxies=public_proxies,
                    last_used_proxy=last_used_proxy,
                )
                if selection.aborted:
                    break
                attempt_number = selection.attempt_index + 1
                result = self._run_attempt(
                    attempt_number=attempt_number,
                    request=request,
                    page_action=page_action,
                    selection=selection,
                    caps=caps,
                    options=options,
                    additional_args=additional_args,
                    extra_headers=extra_headers,
                    settings=settings,
                )
                self._record_outcome(selection, result, settings)
                if result.response:
                    return result.response
                last_error = result.error
                attempt_count = selection.attempt_index + 1
                last_used_proxy = selection.proxy
                if not self._should_continue(attempt_count, settings):
                    break
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=last_error or "exhausted retries"
            )
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

    def _select_proxy(self,
                      attempt_index: int,
                      settings,
                      attempt_plan: List[dict],
                      public_proxies: List[str],
                      last_used_proxy: Optional[str]) -> ProxySelection:
        rotation_mode = getattr(settings, "proxy_rotation_mode", "sequential")
        private_proxy = getattr(settings, "private_proxy_url", None)
        has_candidates = bool(public_proxies or private_proxy)
        if rotation_mode != "random" or not has_candidates:
            index = attempt_index
            while index < settings.max_retries:
                attempt_config = attempt_plan[index]
                candidate_proxy = attempt_config["proxy"]
                candidate_mode = attempt_config["mode"]
                if candidate_proxy and self.health_tracker.is_unhealthy(candidate_proxy):
                    logger.debug(
                        f"Attempt {index+1} skipped - {candidate_mode} proxy "
                        f"{self._redact_proxy(candidate_proxy)} is unhealthy"
                    )
                    index += 1
                    continue
                return ProxySelection(candidate_proxy, candidate_mode, index)
            return ProxySelection(None, "direct", index, aborted=True)

        healthy_public = [
            proxy for proxy in public_proxies if not self.health_tracker.is_unhealthy(proxy)
        ]
        if healthy_public:
            healthy_public = sorted(healthy_public)[:2]
            if private_proxy and (
                attempt_index >= settings.max_retries - 1 or attempt_index == 3
            ):
                return ProxySelection(private_proxy, "private", attempt_index)
            if attempt_index == 1:
                choice_list = [p for p in healthy_public if p != last_used_proxy] or healthy_public
                return ProxySelection(choice_list[0], "public", attempt_index)
            return ProxySelection(healthy_public[0], "public", attempt_index)
        if private_proxy and not self.health_tracker.is_unhealthy(private_proxy):
            return ProxySelection(private_proxy, "private", attempt_index)
        return ProxySelection(None, "direct", attempt_index)

    def _run_attempt(self,
                     attempt_number: int,
                     request: CrawlRequest,
                     page_action: Optional[PageAction],
                     selection: ProxySelection,
                     caps,
                     options,
                     additional_args,
                     extra_headers,
                     settings) -> AttemptResult:
        last_error = "Unknown error"
        selected_proxy = selection.proxy
        redacted_proxy = self._redact_proxy(selected_proxy)
        logger.debug(
            f"Attempt {attempt_number} using {selection.mode} connection, proxy: {redacted_proxy}"
        )
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
            logger.debug(f"Attempt {attempt_number} - calling fetch")
            page = self.fetch_client.fetch(str(request.url), fetch_kwargs)
            status = getattr(page, "status", None)
            html = getattr(page, "html_content", None)
            html_len = len(html or "")
            logger.debug(
                f"Attempt {attempt_number} - page status: {status}, html length: {html_len}"
            )
            min_len = int(getattr(settings, "min_html_content_length", 500) or 0)
            html_has_doc = bool(html and "<html" in (html.lower() if isinstance(html, str) else ""))
            if status == 200 and html and html_len >= min_len:
                logger.debug(f"Attempt {attempt_number} outcome: success (html-ok)")
                return AttemptResult(CrawlResponse(status="success", url=request.url, html=html), None)
            if status != 200:
                last_error = f"Non-200 status: {status}"
            else:
                if not html:
                    last_error = "HTML content is None or empty"
                else:
                    last_error = (
                        f"HTML not acceptable (len={html_len}, "
                        f"has_html_tag={html_has_doc}, status={status})"
                    )
            logger.debug(f"Attempt {attempt_number} outcome: failure - {last_error}")
            return AttemptResult(None, last_error)
        except Exception:
            logger.debug(f"Attempt {attempt_number} outcome: failure - {last_error}")
            return AttemptResult(None, last_error)

    def _record_outcome(self, selection: ProxySelection, result: AttemptResult, settings) -> None:
        if not selection.proxy:
            return
        selected_proxy = selection.proxy
        if result.response:
            redacted_proxy = self._redact_proxy(selected_proxy)
            self.health_tracker.mark_success(selected_proxy)
            logger.debug(f"Proxy {redacted_proxy} recovered")
        else:
            self._mark_proxy_failure(selected_proxy, settings)

    def _should_continue(self, attempt_count: int, settings) -> bool:
        if attempt_count >= settings.max_retries:
            return False
        delay = self.backoff_policy.delay_for_attempt(attempt_count - 1)
        time.sleep(delay)
        return True

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
        return redact_proxy(proxy)
