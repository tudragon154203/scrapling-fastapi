"""Chromium-based TikTok download strategy using DynamicFetcher."""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from typing import Any, Dict, Optional

# Import DynamicFetcher for Chromium support
try:
    from scrapling.fetchers import DynamicFetcher
except ImportError:
    print("Error: DynamicFetcher not available. Please install scrapling with: pip install scrapling")
    sys.exit(1)

from app.services.tiktok.download.actions.resolver import TikVidResolveAction
from app.services.tiktok.download.strategies.base import TikTokDownloadStrategy

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
            nonlocal last_exc, result_holder
            for attempt in range(1, 4):
                components = self._build_chromium_fetch_kwargs(tiktok_url, quality_hint)
                fetcher_class = components["fetcher"]
                fetch_kwargs: Dict[str, Any] = components["fetch_kwargs"]
                resolve_action: TikVidResolveAction = components["resolve_action"]

                try:
                    # Use DynamicFetcher directly
                    fetcher = fetcher_class()
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
        Compose DynamicFetcher keyword arguments for Chromium-based resolution.

        This encapsulates the Chromium configuration for stealth and anti-detection.
        """
        resolve_action = TikVidResolveAction(tiktok_url, quality_hint)

        # Chromium-specific configuration for stealth and anti-detection
        additional_args = {
            # Browser arguments for stealth
            "browser_args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
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
                "--disable-javascript",  # Enable only when needed
                "--disable-default-apps",
                "--disable-sync",
                "--disable-translate",
                "--hide-scrollbars",
                "--metrics-recording-only",
                "--mute-audio",
                "--no-first-run",
                "--safebrowsing-disable-auto-update",
                "--disable-infobars",
                "--window-position=0,0",
                "--window-size=1920,1080",
            ],
            # User preferences for stealth
            "user_prefs": {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2,
            },
        }

        # Create fetch kwargs for DynamicFetcher
        # Note: DynamicFetcher uses Playwright's Chromium by default
        fetch_kwargs = {
            "headless": False,  # keep the browser visible for debugging
            "page_action": resolve_action,
            "timeout": 90000,  # 90 seconds in milliseconds
            "extra_headers": {"User-Agent": USER_AGENT},
            "network_idle": True,  # Wait for network to be idle
            "wait": 5000,  # Wait 5 seconds after page loads
        }

        # Apply additional args if DynamicFetcher supports them
        if hasattr(DynamicFetcher, 'fetch'):
            try:
                import inspect
                sig = inspect.signature(DynamicFetcher.fetch)
                if 'additional_args' in sig.parameters:
                    fetch_kwargs["additional_args"] = additional_args
            except Exception:
                logger.debug("Could not inspect DynamicFetcher signature, skipping additional_args")

        return {
            "fetcher": DynamicFetcher,
            "fetch_kwargs": fetch_kwargs,
            "resolve_action": resolve_action,
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
