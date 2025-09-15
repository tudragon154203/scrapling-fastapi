import logging
import sys
import asyncio
from typing import Callable, Optional, Any, Mapping

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
from app.services.browser.options.resolver import OptionsResolver
from app.services.common.browser.camoufox import CamoufoxArgsBuilder

logger = logging.getLogger(__name__)


class SingleAttemptExecutor(IExecutor):
    """Single-attempt crawl executor that performs one fetch operation."""

    def __init__(self, fetch_client: Optional[ScraplingFetcherAdapter] = None,
                 options_resolver: Optional[OptionsResolver] = None,
                 arg_composer: Optional[FetchArgComposer] = None,
                 camoufox_builder: Optional[CamoufoxArgsBuilder] = None):
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()
        self.options_resolver = options_resolver or OptionsResolver()
        self.arg_composer = arg_composer or FetchArgComposer()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()

    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute a single crawl attempt."""
        settings = app_config.get_settings()

        self._ensure_windows_event_loop_policy()

        options = self.options_resolver.resolve(request, settings)
        additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps={})
        user_data_cleanup = self._extract_cleanup_callback(additional_args)

        try:
            caps = self.fetch_client.detect_capabilities()
            additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps)
            user_data_cleanup = self._extract_cleanup_callback(additional_args, user_data_cleanup)

            selected_proxy = self._select_proxy(settings, caps)
            fetch_kwargs = self.arg_composer.compose(
                options=options,
                caps=caps,
                selected_proxy=selected_proxy,
                additional_args=additional_args,
                extra_headers=extra_headers,
                settings=settings,
                page_action=page_action,
            )
            return self._attempt_fetch(request, fetch_kwargs, settings)
        except ImportError:
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message="Scrapling library not available",
            )
        except Exception as e:
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=f"Exception during crawl: {type(e).__name__}: {e}",
            )
        finally:
            self._finalize_attempt(user_data_cleanup)

    def _ensure_windows_event_loop_policy(self) -> None:
        """Apply Windows-specific event loop policy when necessary."""
        if sys.platform != "win32":
            return
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            # Best-effort setup; failures shouldn't abort the crawl attempt
            logger.debug("Failed to set Windows event loop policy", exc_info=True)

    def _extract_cleanup_callback(
        self,
        additional_args: Optional[Mapping[str, Any]],
        fallback: Optional[Callable[[], None]] = None,
    ) -> Optional[Callable[[], None]]:
        """Retrieve the cleanup callback from builder-provided arguments."""
        if not additional_args:
            return fallback
        try:
            cleanup = additional_args.get("_user_data_cleanup")
        except Exception:
            return fallback
        return cleanup or fallback

    def _select_proxy(self, settings, caps) -> Optional[str]:
        proxy_url = getattr(settings, "private_proxy_url", None)
        if not caps.supports_proxy:
            if proxy_url:
                logger.warning(
                    "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
                )
            return None
        return proxy_url or None

    def _attempt_fetch(self, request: CrawlRequest, fetch_kwargs: dict, settings) -> CrawlResponse:
        page = self.fetch_client.fetch(str(request.url), fetch_kwargs)
        status_code = getattr(page, "status", None)
        html = getattr(page, "html_content", None)
        min_len = int(getattr(settings, "min_html_content_length", 500) or 0)

        if isinstance(status_code, int) and 200 <= status_code < 300:
            if html and len(html) >= min_len:
                return CrawlResponse(status="success", url=request.url, html=html)
            msg = f"HTML too short (<{min_len} chars); suspected bot detection"
            return CrawlResponse(status="failure", url=request.url, html=None, message=msg)

        return CrawlResponse(
            status="failure",
            url=request.url,
            html=None,
            message=f"HTTP status: {status_code if status_code is not None else 'unknown'}",
        )

    def _finalize_attempt(self, user_data_cleanup: Optional[Callable[[], None]]) -> None:
        if not user_data_cleanup:
            return
        try:
            user_data_cleanup()
        except Exception as e:
            logger.warning(f"Failed to cleanup user data context: {e}")
