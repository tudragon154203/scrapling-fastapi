"""Chromium-based TikTok download strategy using DynamicFetcher."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import inspect
from typing import Any, Dict, Optional

# Set proper event loop policy for Windows
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

# Import fetchers for Chromium support
try:
    from scrapling.fetchers import DynamicFetcher
except ImportError:
    print("Error: DynamicFetcher not available. Please install scrapling with: pip install scrapling")
    sys.exit(1)

try:
    from app.services.browser.fetchers.persistent_chromium import PersistentChromiumFetcher
except ImportError:
    PersistentChromiumFetcher = None
    print("Warning: PersistentChromiumFetcher not available, falling back to DynamicFetcher")

from app.services.tiktok.download.actions.resolver import TikVidResolveAction
from app.services.tiktok.download.strategies.base import TikTokDownloadStrategy
from app.services.common.browser.user_data_chromium import ChromiumUserDataManager
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Get configuration values
settings = get_settings()
TIKVID_BASE = settings.tikvid_base
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _format_exception(exc: BaseException) -> str:
    """Render exceptions so that Windows consoles do not crash on Unicode."""
    try:
        text = str(exc)
    except Exception:
        text = repr(exc)
    try:
        return text.encode("ascii", "backslashreplace").decode()
    except Exception:
        return repr(exc)


class ChromiumDownloadStrategy(TikTokDownloadStrategy):
    """TikTok download strategy using Chromium with DynamicFetcher."""

    def __init__(self, settings: Any):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        # Initialize Chromium user data manager
        self.user_data_manager = ChromiumUserDataManager(
            user_data_dir=getattr(settings, 'chromium_user_data_dir', None)
        )

    def resolve_video_url(self, tiktok_url: str, quality_hint: Optional[str] = None, force_headful: bool = False) -> str:
        """
        Resolve the direct MP4 URL for a TikTok video using TikVid with Chromium.

        Args:
            tiktok_url: The TikTok video URL to resolve
            quality_hint: Optional quality preference (HD, SD, etc.)
            force_headful: Whether to force headful mode (True=headful, False=allow headless with parity)

        Returns:
            Direct MP4 URL for the video

        Raises:
            RuntimeError: If resolution fails after retries
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, 4):
            components = self._build_chromium_fetch_kwargs(tiktok_url, quality_hint, force_headful)
            fetcher_class = components["fetcher"]
            fetch_kwargs: Dict[str, Any] = components["fetch_kwargs"]
            resolve_action: TikVidResolveAction = components["resolve_action"]
            user_data_cleanup = components.get("user_data_cleanup")

            try:
                # Create fetcher based on type
                if fetcher_class == PersistentChromiumFetcher:
                    # Use persistent fetcher with user data directory
                    effective_user_data_dir = components.get("effective_user_data_dir")
                    fetcher = fetcher_class(user_data_dir=effective_user_data_dir)
                else:
                    # Use DynamicFetcher for ephemeral sessions
                    fetcher = fetcher_class()

                try:
                    # Let the fetcher handle async/sync conflicts internally
                    page_result = fetcher.fetch(TIKVID_BASE, **fetch_kwargs)

                    direct_url = None
                    if resolve_action.result_links:
                        logger.debug(f"Found {len(resolve_action.result_links)} download links")
                        media_links = self._filter_media_links(resolve_action.result_links)
                        logger.debug(f"Filtered media links: {media_links}")
                        if media_links:
                            direct_url = media_links[0]
                        else:
                            logger.warning("Resolver warning: TikVid returned only info links, retrying...")
                    elif getattr(page_result, "html_content", None):
                        mp4_urls = re.findall(r'href=["\']([^"\']*\.mp4[^"\']*)["\']', page_result.html_content)
                        if mp4_urls:
                            direct_url = mp4_urls[0]
                            logger.info(f"Found MP4 URL in HTML: {direct_url}")

                    if direct_url:
                        logger.info(f"Direct MP4 URL resolved: {direct_url}")
                        return direct_url

                    logger.warning("Resolver warning: no MP4 link found, retrying...")
                    last_exc = RuntimeError("TikVid resolver returned no download URL")

                finally:
                    # Ensure proper cleanup of fetcher resources and user data context
                    if hasattr(fetcher, 'close'):
                        try:
                            fetcher.close()
                        except Exception as e:
                            logger.warning(f"Error closing fetcher: {e}")
                    # Clean up user data context if provided
                    if callable(user_data_cleanup):
                        try:
                            user_data_cleanup()
                        except Exception as e:
                            logger.warning(f"Error cleaning up user data context: {e}")

            except Exception as exc:
                last_exc = exc
                logger.warning(f"Chromium attempt {attempt} failed: {_format_exception(exc)}")
                continue

        raise RuntimeError(
            f"Resolution failed after retries: {_format_exception(last_exc or RuntimeError('unknown error'))}")

    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return "chromium"

    def _build_chromium_fetch_kwargs(
        self,
        tiktok_url: str,
        quality_hint: Optional[str] = None,
        force_headful: bool = False,
    ) -> Dict[str, Any]:
        """
        Compose Chromium fetcher keyword arguments for TikTok video resolution.

        This encapsulates the Chromium configuration for stealth and anti-detection,
        supporting both DynamicFetcher and PersistentChromiumFetcher.

        Args:
            tiktok_url: The TikTok video URL to resolve
            quality_hint: Optional quality preference (HD, SD, etc.)
            force_headful: Whether to force headful mode (True=headful, False=allow headless with parity)
        """
        resolve_action = TikVidResolveAction(tiktok_url, quality_hint)

        # Get user data context for read mode (clone master profile) ONLY when enabled
        user_data_cleanup = None
        effective_user_data_dir = None
        abs_dir: Optional[str] = None
        if self.user_data_manager.is_enabled():
            try:
                user_data_context = self.user_data_manager.context_manager.get_user_data_context('read')
                effective_user_data_dir, user_data_cleanup = user_data_context.__enter__()
                # Ensure absolute path for profile persistence
                if effective_user_data_dir:
                    abs_dir = os.path.abspath(effective_user_data_dir)
                    effective_user_data_dir = abs_dir
                logger.debug(f"Using Chromium user data directory (absolute): {effective_user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to get Chromium user data context, falling back to temporary profile: {e}")
                effective_user_data_dir = None
                user_data_cleanup = None
                abs_dir = None
        else:
            # When disabled, do not inject user_data_dir into fetch kwargs or additional args
            logger.debug("Chromium user data management disabled; not injecting user_data_dir")

        # Choose fetcher: prefer DynamicFetcher for strategy tests and compatibility.
        # Persistent profile is handled by browse flows; downloads use read-mode clones.
        fetcher_class = DynamicFetcher
        logger.debug("Using DynamicFetcher (ephemeral profile)")

        # Determine headless mode based on force_headful flag
        # When force_headful=False, enable headless mode with full parity features
        # When force_headful=True, enforce headful mode
        headless_mode = not force_headful

        # Browser arguments for stealth and anti-detection
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-images",  # Faster loading
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            "--safebrowsing-disable-auto-update",
            "--disable-infobars",
            "--window-position=0,0",
            "--window-size=1920,1080",
            "--blink-settings=imagesEnabled=false",  # Force disable images
            "--disable-javascript-harmony-shipping",  # Faster JS execution
            "--disable-features=IsolateOrigins,site-per-process",  # Reduce process overhead
        ]

        # Add headless-specific parity arguments when in headless mode
        if headless_mode:
            headless_args = [
                "--disable-background-networking",  # Prevent background requests interfering
                "--no-default-browser-check",  # Prevent browser check dialogs
                "--disable-features=TranslateUI,BlinkGenPropertyTrees",  # Reduce headless overhead
                "--enable-automation",  # Enable automation mode for better headless support
                "--password-store=basic",  # Use basic password store in headless
                "--use-mock-keychain",  # Mock keychain for headless environments
                "--disable-ipc-flooding-protection",  # Enhanced protection for headless
                "--disable-component-update",  # Prevent component updates in headless
                "--disable-domain-reliability",  # Disable domain reliability reporting
                "--disable-features=AudioServiceOutOfProcess",  # Reduce process overhead
            ]
            browser_args.extend(headless_args)
            logger.debug("Added headless-specific parity arguments for enhanced headless compatibility")

        # Create page action callable for fetchers
        def page_action_callable(page):
            return resolve_action._execute(page)

        # Base fetch kwargs compatible with both fetchers
        # IMPORTANT: DynamicFetcher.fetch does not accept 'browser_args' directly.
        # Only PersistentChromiumFetcher supports passing Chromium launch args.
        fetch_kwargs = {
            "headless": headless_mode,  # Conditional headless/headful mode
            "page_action": page_action_callable,
            "timeout": 90000,  # 90 seconds in milliseconds
            "extra_headers": {"User-Agent": USER_AGENT},
            "network_idle": False,  # Use domcontentloaded instead for faster loading
            "wait": 3000,  # Reduced wait time to 3 seconds
        }

        # Add headless-specific parity configurations
        if headless_mode:
            # Enhanced waiting strategy for headless mode
            fetch_kwargs.update({
                "network_idle": True,  # Wait for network to be idle in headless mode
                "wait": 5000,  # Slightly longer wait for headless stability
                "timeout": 120000,  # Longer timeout for headless processing
            })

            # Additional headers for headless mode parity
            fetch_kwargs["extra_headers"].update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })

            logger.debug("Applied headless parity configurations for enhanced web interaction")

        # Inject browser args only for PersistentChromiumFetcher
        if fetcher_class == PersistentChromiumFetcher:
            fetch_kwargs["browser_args"] = browser_args

        # Conditionally pass user-data parameters to DynamicFetcher if supported
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

        if abs_dir and fetcher_class == DynamicFetcher:
            if supports_user_data_dir:
                fetch_kwargs["user_data_dir"] = abs_dir
            if supports_additional_args:
                additional_args = fetch_kwargs.get("additional_args", {})
                if not isinstance(additional_args, dict):
                    additional_args = {}
                additional_args["user_data_dir"] = abs_dir
                fetch_kwargs["additional_args"] = additional_args

        return {
            "fetcher": fetcher_class,
            "fetch_kwargs": fetch_kwargs,
            "resolve_action": resolve_action,
            "effective_user_data_dir": effective_user_data_dir,
            "user_data_cleanup": user_data_cleanup,
            "headers": {"User-Agent": USER_AGENT},
        }

    def _filter_media_links(self, links: list) -> list:
        """Filter download links to find actual media files."""
        def _looks_like_media(link: str) -> bool:
            lowered = link.lower()
            if ".mp4" in lowered:
                return True
            if "mime_type=video_mp4" in lowered or "video_mp4" in lowered:
                return True
            return not lowered.startswith(TIKVID_BASE.lower())

        return [link for link in links if link and _looks_like_media(link)]
