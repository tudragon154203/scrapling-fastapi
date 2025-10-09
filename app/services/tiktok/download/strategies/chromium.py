"""Chromium-based TikTok download strategy using DynamicFetcher."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
import threading
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

logger = logging.getLogger(__name__)

# TikVid serves regional variants; default to Vietnamese because it currently
# avoids the heavy advertisement overlays seen on the English page.
TIKVID_BASE = os.environ.get("TIKVID_BASE", "https://tikvid.io/vi")
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

    def resolve_video_url(self, tiktok_url: str, quality_hint: Optional[str] = None) -> str:
        """
        Resolve the direct MP4 URL for a TikTok video using TikVid with Chromium.

        Args:
            tiktok_url: The TikTok video URL to resolve
            quality_hint: Optional quality preference (HD, SD, etc.)

        Returns:
            Direct MP4 URL for the video

        Raises:
            RuntimeError: If resolution fails after retries
        """
        last_exc: Optional[Exception] = None
        result_holder = {}

        def _run_in_thread():
            nonlocal last_exc
            for attempt in range(1, 4):
                components = self._build_chromium_fetch_kwargs(tiktok_url, quality_hint)
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
                            result_holder["url"] = direct_url
                            return

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

            result_holder["error"] = RuntimeError(
                f"Resolution failed after retries: {_format_exception(last_exc or RuntimeError('unknown error'))}")

        # Run in a separate thread to avoid asyncio issues
        thread = threading.Thread(target=_run_in_thread)
        thread.start()
        thread.join()

        if "url" in result_holder:
            return result_holder["url"]
        elif "error" in result_holder:
            raise result_holder["error"]
        else:
            raise RuntimeError("Unknown error occurred during resolution")

    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        return "chromium"

    def _build_chromium_fetch_kwargs(
        self,
        tiktok_url: str,
        quality_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compose Chromium fetcher keyword arguments for TikTok video resolution.

        This encapsulates the Chromium configuration for stealth and anti-detection,
        supporting both DynamicFetcher and PersistentChromiumFetcher.
        """
        resolve_action = TikVidResolveAction(tiktok_url, quality_hint)

        # Get user data context for read mode (clone master profile)
        user_data_cleanup = None
        effective_user_data_dir = None
        abs_dir: Optional[str] = None
        try:
            user_data_context = self.user_data_manager.get_user_data_context('read')
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

        # Choose fetcher: prefer DynamicFetcher for strategy tests and compatibility.
        # Persistent profile is handled by browse flows; downloads use read-mode clones.
        fetcher_class = DynamicFetcher
        logger.debug("Using DynamicFetcher (ephemeral profile)")

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
        ]

        # Create page action callable for fetchers
        def page_action_callable(page):
            return resolve_action._execute(page)

        # Base fetch kwargs compatible with both fetchers
        # IMPORTANT: DynamicFetcher.fetch does not accept 'browser_args' directly.
        # Only PersistentChromiumFetcher supports passing Chromium launch args.
        fetch_kwargs = {
            "headless": True,  # Use headless mode for downloads
            "page_action": page_action_callable,
            "timeout": 90000,  # 90 seconds in milliseconds
            "extra_headers": {"User-Agent": USER_AGENT},
            "network_idle": True,  # Wait for network to be idle
            "wait": 5000,  # Wait 5 seconds after page loads
        }

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
