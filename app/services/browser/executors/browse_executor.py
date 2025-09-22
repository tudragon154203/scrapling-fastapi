import logging
import sys
import asyncio
from typing import Optional

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

        # Resolve options and potential lightweight headers early so we can fallback if needed
        options = self.options_resolver.resolve(request, settings)
        additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps={})
        # Capture optional user-data cleanup callback early
        user_data_cleanup = None
        try:
            user_data_cleanup = additional_args.get('_user_data_cleanup') if additional_args else None
        except Exception:
            user_data_cleanup = None

        try:
            caps = self.fetch_client.detect_capabilities()
            logger.debug(f"Detected capabilities: {caps}")
            additional_args, extra_headers = self.camoufox_builder.build(request, settings, caps)
            # Refresh cleanup callback in case caps-dependent build altered args
            try:
                user_data_cleanup = additional_args.get('_user_data_cleanup') if additional_args else user_data_cleanup
            except Exception:
                pass

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

            # Set up browse-specific timeout: ensure a long timeout for interactive sessions
            # Use at least 10x the default timeout when no explicit seconds were requested
            if request.timeout_seconds is None:
                browse_timeout_ms = getattr(settings, "default_timeout_ms", 20000) * 10
                # If compose already set a timeout, ensure ours is not shorter
                existing = fetch_kwargs.get("timeout")
                if existing is None or int(existing) < int(browse_timeout_ms):
                    fetch_kwargs["timeout"] = browse_timeout_ms

            logger.debug(f"Starting browse session for URL: {request.url}")
            page = self.fetch_client.fetch(str(request.url), fetch_kwargs)

            # The page_action (WaitForUserCloseAction) should have completed successfully
            # at this point since the fetch only returns after the user closes the browser

            # Cleanup user data context after fetch if cleanup function was stored
            if user_data_cleanup:
                try:
                    user_data_cleanup()
                except Exception as e:
                    logger.warning(f"Failed to cleanup user data context: {e}")

            # For browse operations, we consider success if:
            # 1. The fetch completed (meaning user closed the browser)
            # 2. We got a valid page object (not None)
            if page is not None:
                return CrawlResponse(
                    status="success",
                    url=request.url,
                    html=None,  # Browse operations don't return HTML
                    message="Browser session completed successfully"
                )
            else:
                return CrawlResponse(
                    status="failure",
                    url=request.url,
                    html=None,
                    message="Browser session failed to initialize"
                )

        except Exception as e:
            # For browse operations, we should NOT retry on user close or similar errors
            # The user explicitly closed the browser, so we should respect that
            logger.debug(f"Browse session ended normally: {type(e).__name__}: {e}")

            if isinstance(e, ImportError):
                return CrawlResponse(
                    status="failure",
                    url=request.url,
                    html=None,
                    message="Scrapling library not available",
                )

            # Convert common browser close errors to success responses
            # These are expected when users manually close the browser
            close_errors = [
                "TargetClosedError",
                "TargetClosed",
                "SessionClosed",
                "BrowserClosed",
                "ConnectionClosed",
                "Target page, context or browser has been closed",
            ]

            error_name = type(e).__name__
            error_str = str(e).lower()

            if any(close_err.lower() in error_str or close_err in error_name for close_err in close_errors):
                logger.debug("Browser was closed by user - session completed successfully")
                return CrawlResponse(
                    status="success",
                    url=request.url,
                    html=None,
                    message="Browser session completed successfully (user closed)"
                )

            # For other exceptions, return failure but don't retry
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=f"Browse session failed: {type(e).__name__}: {e}",
            )

    def should_retry(self, request: CrawlResponse) -> bool:
        """Browse operations should never retry - respect user's close action."""
        return False

    def get_retry_delay(self, request: CrawlResponse, attempt: int) -> float:
        """Browse operations should never retry."""
        return 0.0
