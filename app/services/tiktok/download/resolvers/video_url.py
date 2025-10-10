"""Video URL resolver using TikVid and browser automation."""

from __future__ import annotations

import logging
import re
from types import SimpleNamespace
from typing import Any, Dict, Optional

from app.services.common.adapters.scrapling_fetcher import FetchArgComposer, ScraplingFetcherAdapter
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.services.tiktok.download.actions.resolver import TikVidResolveAction
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


class TikVidVideoResolver:
    """Resolver for TikTok video URLs using TikVid and browser automation."""

    def __init__(self, settings: Any):
        self.settings = settings
        self.logger = logging.getLogger(__name__)

    def resolve_video_url(self, tiktok_url: str, quality_hint: Optional[str] = None) -> str:
        """
        Resolve the direct MP4 URL for a TikTok video using TikVid.

        Args:
            tiktok_url: The TikTok video URL to resolve
            quality_hint: Optional quality preference (HD, SD, etc.)

        Returns:
            Direct MP4 URL for the video

        Raises:
            RuntimeError: If resolution fails after retries
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            components = self._build_camoufox_fetch_kwargs(tiktok_url, quality_hint)
            adapter: ScraplingFetcherAdapter = components["adapter"]
            fetch_kwargs: Dict[str, Any] = components["fetch_kwargs"]
            resolve_action: TikVidResolveAction = components["resolve_action"]
            cleanup = components["cleanup"]

            try:
                page_result = adapter.fetch(TIKVID_BASE, fetch_kwargs)
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Camoufox attempt {attempt} failed: {_format_exception(exc)}")
                continue
            finally:
                if cleanup:
                    try:
                        cleanup()
                    except Exception as exc:
                        logger.warning(f"User data cleanup warning: {_format_exception(exc)}")

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

        raise RuntimeError(f"Resolution failed after retries: {_format_exception(last_exc or RuntimeError('unknown error'))}")

    def _build_camoufox_fetch_kwargs(
        self,
        tiktok_url: str,
        quality_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compose StealthyFetcher keyword arguments for a single TikVid resolution pass.

        This encapsulates the Camoufox user-data handling that other services will need
        to replicate when they want TikVid (or other sites) to load with persistent
        session data.
        """
        adapter = ScraplingFetcherAdapter()
        caps = adapter.detect_capabilities()
        resolve_action = TikVidResolveAction(tiktok_url, quality_hint)

        payload = SimpleNamespace(force_user_data=True)
        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, self.settings, caps.__dict__)

        cleanup = None
        if additional_args and "_user_data_cleanup" in additional_args:
            cleanup = additional_args.pop("_user_data_cleanup")

        headers = {"User-Agent": USER_AGENT}
        if extra_headers:
            headers.update(extra_headers)

        fetch_kwargs = FetchArgComposer.compose(
            options={
                "headless": False,  # keep the browser visible for debugging
                "wait_ms": 5000,
                "timeout_seconds": 90,
                "network_idle": True,
                "prefer_domcontentloaded": True,
            },
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args or {},
            extra_headers=headers,
            settings=self.settings,
            page_action=resolve_action,
        )

        return {
            "adapter": adapter,
            "fetch_kwargs": fetch_kwargs,
            "resolve_action": resolve_action,
            "cleanup": cleanup,
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
