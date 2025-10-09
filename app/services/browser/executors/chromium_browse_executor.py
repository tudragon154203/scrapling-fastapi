import logging
import sys
import asyncio
from typing import Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction
from app.services.browser.options.resolver import OptionsResolver

logger = logging.getLogger(__name__)

# Try to import DynamicFetcher for Chromium support
try:
    from scrapling.fetchers import DynamicFetcher
    DYNAMIC_FETCHER_AVAILABLE = True
except ImportError:
    DynamicFetcher = None
    DYNAMIC_FETCHER_AVAILABLE = False
    logger.warning("DynamicFetcher not available for Chromium support")


class ChromiumBrowseExecutor(IExecutor):
    """Chromium-based browse executor for interactive browsing sessions.

    This executor uses DynamicFetcher with Chromium for browser automation
    while maintaining the same interface as the Camoufox executor.
    """

    def __init__(self, options_resolver: Optional[OptionsResolver] = None):
        if not DYNAMIC_FETCHER_AVAILABLE:
            raise ImportError("DynamicFetcher is required for Chromium support")

        self.options_resolver = options_resolver or OptionsResolver()
        self.fetcher = DynamicFetcher()

    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute a browse operation using Chromium."""
        # Ensure proper event loop policy on Windows for Playwright
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        settings = app_config.get_settings()

        try:
            # Build Chromium-specific configuration
            fetch_kwargs = self._build_chromium_kwargs(request, settings, page_action)

            logger.debug(f"Starting Chromium browse session for URL: {request.url}")

            # Use DynamicFetcher for Chromium browsing
            page = self.fetcher.fetch(str(request.url), **fetch_kwargs)

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
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message="Browser session failed to initialize"
            )

        except ImportError:
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message="DynamicFetcher library not available for Chromium support",
            )
        except Exception as e:
            # For browse operations, we should NOT retry on user close or similar errors
            # The user explicitly closed the browser, so we should respect that
            logger.debug(f"Chromium browse session ended normally: {type(e).__name__}: {e}")

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
                logger.debug("Chromium browser was closed by user - session completed successfully")
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
                message=f"Chromium browse session failed: {type(e).__name__}: {e}",
            )

    def should_retry(self, request: CrawlResponse) -> bool:
        """Browse operations should never retry - respect user's close action."""
        return False

    def get_retry_delay(self, request: CrawlResponse, attempt: int) -> float:
        """Browse operations should never retry."""
        return 0.0

    def _build_chromium_kwargs(self, request: CrawlRequest, settings, page_action: Optional[PageAction] = None) -> dict:
        """Build Chromium-specific fetch kwargs for DynamicFetcher."""

        # Chromium-specific configuration for browsing
        additional_args = {
            # Browser arguments for headful browsing
            "browser_args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--disable-gpu" if request.force_headful else "--headless",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-default-apps",
                "--disable-sync",
                "--disable-translate",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--disable-infobars",
                "--window-position=0,0",
                "--window-size=1920,1080",
            ],
            # User preferences for browsing
            "user_prefs": {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
            },
        }

        # Override for headful mode if requested
        if request.force_headful:
            additional_args["browser_args"] = [
                arg for arg in additional_args["browser_args"] if "--headless" not in arg
            ]

        # Check if user data directory is provided via runtime settings
        user_data_dir = getattr(settings, 'chromium_runtime_effective_user_data_dir', None)
        if user_data_dir:
            additional_args["user_data_dir"] = user_data_dir
            logger.debug(f"Using Chromium user data directory: {user_data_dir}")

        # Create page action callable for DynamicFetcher
        def page_action_callable(page):
            if page_action:
                return page_action._execute(page)
            return None

        # Basic fetch kwargs for DynamicFetcher
        fetch_kwargs = {
            "headless": not request.force_headful,
            "page_action": page_action_callable,
            "timeout": 300000,  # 5 minutes in milliseconds for browsing sessions
            "network_idle": True,  # Wait for network to be idle
        }

        # Apply additional args if DynamicFetcher supports them
        try:
            import inspect
            sig = inspect.signature(DynamicFetcher.fetch)
            if 'additional_args' in sig.parameters:
                fetch_kwargs["additional_args"] = additional_args
        except Exception:
            logger.debug("Could not inspect DynamicFetcher signature, skipping additional_args")

        return fetch_kwargs