import logging
import sys
import os
import inspect
import asyncio
from typing import Optional

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.common.interfaces import IExecutor, PageAction
from app.services.browser.options.resolver import OptionsResolver

logger = logging.getLogger(__name__)

# Try to import fetchers for Chromium support
try:
    from scrapling.fetchers import DynamicFetcher
    DYNAMIC_FETCHER_AVAILABLE = True
except ImportError:
    DynamicFetcher = None
    DYNAMIC_FETCHER_AVAILABLE = False
    logger.warning("DynamicFetcher not available for Chromium support")

try:
    from app.services.browser.fetchers.persistent_chromium import PersistentChromiumFetcher
    PERSISTENT_CHROMIUM_AVAILABLE = True
except ImportError:
    PersistentChromiumFetcher = None
    PERSISTENT_CHROMIUM_AVAILABLE = False
    logger.warning("PersistentChromiumFetcher not available")


class ChromiumBrowseExecutor(IExecutor):
    """Chromium-based browse executor for interactive browsing sessions.

    This executor uses DynamicFetcher with Chromium for browser automation
    while maintaining the same interface as the Camoufox executor.
    """

    def __init__(self, options_resolver: Optional[OptionsResolver] = None):
        if not DYNAMIC_FETCHER_AVAILABLE and not PERSISTENT_CHROMIUM_AVAILABLE:
            raise ImportError("Either DynamicFetcher or PersistentChromiumFetcher is required for Chromium support")

        self.options_resolver = options_resolver or OptionsResolver()
        self.fetcher = None  # Will be initialized based on user_data_dir availability

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
            fetch_kwargs, user_data_dir = self._build_chromium_kwargs(request, settings, page_action)

            # Choose appropriate fetcher based on user_data_dir availability
            # Enforce persistent context when a user_data_dir is provided to ensure master profile population
            if user_data_dir:
                if PERSISTENT_CHROMIUM_AVAILABLE:
                    # Use persistent fetcher for profile persistence
                    self.fetcher = PersistentChromiumFetcher(user_data_dir=user_data_dir)
                    logger.debug(f"Using PersistentChromiumFetcher with user_data_dir: {user_data_dir}")
                else:
                    # Do not fall back to ephemeral sessions when persistence is requested
                    raise ImportError(
                        "PersistentChromiumFetcher is required for Chromium browse sessions with user_data_dir. "
                        "Install Playwright and Chromium: pip install 'playwright' && playwright install chromium"
                    )
            elif DYNAMIC_FETCHER_AVAILABLE:
                # Ephemeral session only when no user_data_dir is requested
                self.fetcher = DynamicFetcher()
                logger.debug("Using DynamicFetcher (ephemeral profile)")
            else:
                raise ImportError("No suitable Chromium fetcher available")

            # Execute the fetch
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
                message="Browser session failed to initialize - DynamicFetcher returned None"
            )

        except ImportError as e:
            logger.error(f"ImportError in Chromium browse: {e}")
            return CrawlResponse(
                status="failure",
                url=request.url,
                html=None,
                message=f"ImportError: {e} - install with: pip install 'scrapling[chromium]'",
            )
        except Exception as e:
            # For browse operations, we should NOT retry on user close or similar errors
            # The user explicitly closed the browser, so we should respect that
            logger.info(f"Chromium browse session ended with exception: {type(e).__name__}: {e}")

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
                logger.info("Chromium browser was closed by user - session completed successfully")
                return CrawlResponse(
                    status="success",
                    url=request.url,
                    html=None,
                    message="Browser session completed successfully (user closed)"
                )

            # For other exceptions, return failure but don't retry
            logger.error(f"Chromium browse session failed with unexpected error: {e}")
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

    def _build_chromium_kwargs(self, request: CrawlRequest, settings, page_action: Optional[PageAction] = None) -> tuple:
        """Build Chromium-specific fetch kwargs.
    
        Returns:
            Tuple of (fetch_kwargs, user_data_dir)
        """
    
        # Chromium-specific configuration for browsing
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
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
            "--safebrowsing-disable-auto-update",
            "--disable-infobars",
            "--window-position=0,0",
            "--window-size=1920,1080",
        ]
    
        # Only add headless flag if explicitly requested (not for browse sessions)
        if not request.force_headful:
            browser_args.append("--headless")
    
        # Resolve user_data_dir to absolute path if provided via runtime settings
        user_data_dir = getattr(settings, 'chromium_runtime_effective_user_data_dir', None)
        if user_data_dir:
            user_data_dir = os.path.abspath(user_data_dir)
            logger.debug(f"Using Chromium user data directory (absolute): {user_data_dir}")
    
        # Create page action callable for fetchers
        def page_action_callable(page):
            if page_action:
                return page_action._execute(page)
            return None
    
        # Base fetch kwargs
        # IMPORTANT: DynamicFetcher.fetch does not accept 'browser_args' directly.
        # Only PersistentChromiumFetcher supports passing Chromium launch args.
        fetch_kwargs = {
            "headless": not request.force_headful,
            "page_action": page_action_callable,
            "timeout": 300000,  # 5 minutes for browsing sessions
            "network_idle": True,
        }

        # Inject browser args only when using PersistentChromiumFetcher (i.e., user_data_dir present)
        if user_data_dir:
            fetch_kwargs["browser_args"] = browser_args
    
        # Conditionally pass user_data_dir based on DynamicFetcher.fetch signature
        # and ensure additional_args["user_data_dir"] is set if supported.
        try:
            supports_user_data_dir = False
            supports_additional_args = False
    
            if DYNAMIC_FETCHER_AVAILABLE and DynamicFetcher is not None:
                try:
                    sig = inspect.signature(DynamicFetcher.fetch)
                    params = sig.parameters
                    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
                    supports_user_data_dir = ("user_data_dir" in params) or has_varkw
                    supports_additional_args = ("additional_args" in params) or has_varkw
                except Exception as e:
                    logger.debug(f"Failed to introspect DynamicFetcher.fetch signature: {e}")
                    supports_user_data_dir = False
                    supports_additional_args = False
    
            if user_data_dir:
                # Top-level user_data_dir if supported
                if supports_user_data_dir:
                    fetch_kwargs["user_data_dir"] = user_data_dir
    
                # Ensure additional_args carries user_data_dir when supported
                if supports_additional_args:
                    safe_additional_args = dict(fetch_kwargs.get("additional_args", {}))
                    safe_additional_args["user_data_dir"] = user_data_dir
                    fetch_kwargs["additional_args"] = safe_additional_args
        except Exception as e:
            logger.debug(f"Skipping user_data_dir injection due to error: {e}")
    
        # Log browser mode for visibility
        if request.force_headful:
            logger.info("Starting Chromium in HEADFUL mode for browsing session")
            logger.info(f"URL: {request.url}")
        else:
            logger.info("Starting Chromium in HEADLESS mode")
    
        return fetch_kwargs, user_data_dir