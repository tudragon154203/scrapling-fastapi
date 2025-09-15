import logging
import sys
import asyncio
from typing import Any, Callable, Dict, Optional, Tuple

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
from app.services.browser.options.resolver import OptionsResolver
from app.services.common.browser.camoufox import CamoufoxArgsBuilder

logger = logging.getLogger(__name__)


class BrowseExecutor(IExecutor):
    """Browse-specific executor that respects user close actions and never retries.

    This executor is designed for interactive browsing sessions where users
    manually close the browser. It never retries when the browser is closed
    by the user, avoiding the problematic relaunch behavior.
    """

    def __init__(self, fetch_client: Optional[ScraplingFetcherAdapter] = None,
                 options_resolver: Optional[OptionsResolver] = None,
                 arg_composer: Optional[FetchArgComposer] = None,
                 camoufox_builder: Optional[CamoufoxArgsBuilder] = None):
        self.fetch_client = fetch_client or ScraplingFetcherAdapter()
        self.options_resolver = options_resolver or OptionsResolver()
        self.arg_composer = arg_composer or FetchArgComposer()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()

    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute a browse operation with special handling for user close actions."""
        settings = app_config.get_settings()

        # Ensure proper event loop policy on Windows for Playwright
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        user_data_cleanup: Optional[Callable[[], None]] = None

        try:
            fetch_kwargs, user_data_cleanup = self._prepare_fetch(request, page_action, settings)
            self._apply_browse_timeout(fetch_kwargs, request, settings)

            logger.info(f"Starting browse session for URL: {request.url}")
            page = self.fetch_client.fetch(str(request.url), fetch_kwargs)

            # The page_action (WaitForUserCloseAction) should have completed successfully
            # at this point since the fetch only returns after the user closes the browser
            if page is not None:
                return CrawlResponse(
                    status="success",
                    url=request.url,
                    html=None,  # Browse operations don't return HTML
                    message="Browser session completed successfully",
                )

            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message="Browser session failed to initialize",
            )

        except Exception as e:
            # For browse operations, we should NOT retry on user close or similar errors
            # The user explicitly closed the browser, so we should respect that
            logger.info(f"Browse session ended normally: {type(e).__name__}: {e}")

            if isinstance(e, ImportError):
                return CrawlResponse(
                    status="failure",
                    url=request.url,
                    html=None,
                    message="Scrapling library not available",
                )

            close_response = self._handle_close_errors(e, request)
            if close_response is not None:
                return close_response

            # For other exceptions, return failure but don't retry
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=f"Browse session failed: {type(e).__name__}: {e}",
            )

        finally:
            self._cleanup_user_data(user_data_cleanup)

    def _prepare_fetch(
        self,
        request: CrawlRequest,
        page_action: Optional[PageAction],
        settings: Any,
    ) -> Tuple[Dict[str, Any], Optional[Callable[[], None]]]:
        """Resolve capabilities, arguments, and compose fetch kwargs."""
        options = self.options_resolver.resolve(request, settings)
        additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps={})

        user_data_cleanup = self._extract_user_data_cleanup(additional_args)

        caps = self.fetch_client.detect_capabilities()
        logger.debug(f"Detected capabilities: {caps}")

        additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps)
        user_data_cleanup = self._extract_user_data_cleanup(additional_args, user_data_cleanup)

        if not caps.supports_proxy:
            logger.warning(
                "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
            )

        selected_proxy = getattr(settings, "private_proxy_url", None) or None

        fetch_kwargs = self.arg_composer.compose(
            options=options,
            caps=caps,
            selected_proxy=selected_proxy,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=settings,
            page_action=page_action,
        )

        return fetch_kwargs, user_data_cleanup

    def _apply_browse_timeout(
        self,
        fetch_kwargs: Dict[str, Any],
        request: CrawlRequest,
        settings: Any,
    ) -> None:
        """Ensure interactive browse sessions use an extended timeout."""
        if request.timeout_seconds is None:
            browse_timeout_ms = getattr(settings, "default_timeout_ms", 20000) * 10
            existing = fetch_kwargs.get("timeout")
            if existing is None or int(existing) < int(browse_timeout_ms):
                fetch_kwargs["timeout"] = browse_timeout_ms

    def _handle_close_errors(self, error: Exception, request: CrawlRequest) -> Optional[CrawlResponse]:
        """Convert expected close-related errors into successful responses."""
        close_errors = [
            "TargetClosedError",
            "TargetClosed",
            "SessionClosed",
            "BrowserClosed",
            "ConnectionClosed",
            "Target page, context or browser has been closed",
        ]

        error_name = type(error).__name__
        error_str = str(error).lower()

        if any(close_err.lower() in error_str or close_err in error_name for close_err in close_errors):
            logger.info("Browser was closed by user - session completed successfully")
            return CrawlResponse(
                status="success",
                url=request.url,
                html=None,
                message="Browser session completed successfully (user closed)",
            )

        return None

    def _extract_user_data_cleanup(
        self,
        additional_args: Optional[Dict[str, Any]],
        current_cleanup: Optional[Callable[[], None]] = None,
    ) -> Optional[Callable[[], None]]:
        """Safely extract the user data cleanup callback if present."""
        if not isinstance(additional_args, dict):
            return current_cleanup

        candidate = additional_args.get("_user_data_cleanup")
        if callable(candidate):
            return candidate

        return current_cleanup

    def _cleanup_user_data(self, cleanup: Optional[Callable[[], None]]) -> None:
        """Invoke the user data cleanup callback if it exists."""
        if cleanup is None:
            return

        try:
            cleanup()
        except Exception as exc:
            logger.warning(f"Failed to cleanup user data context: {exc}")

    def should_retry(self, request: CrawlResponse) -> bool:
        """Browse operations should never retry - respect user's close action."""
        return False

    def get_retry_delay(self, request: CrawlResponse, attempt: int) -> float:
        """Browse operations should never retry."""
        return 0.0
