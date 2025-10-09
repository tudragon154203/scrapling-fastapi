"""Main TikTok download service orchestrating video URL resolution."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from app.core.config import get_settings
from app.schemas.tiktok.download import (
    TikTokDownloadRequest,
    TikTokDownloadResponse,
    TikTokVideoInfo,
)
from app.services.tiktok.download.strategies.factory import TikTokDownloadStrategyFactory
from app.services.tiktok.download.utils.helpers import (
    extract_video_metadata_from_url,
    is_valid_tiktok_url,
)
import app.services.tiktok.download.downloaders.file as downloaders_module
import app.services.tiktok.download.resolvers.video_url as resolvers_module

if TYPE_CHECKING:
    from app.services.tiktok.download.downloaders.file import VideoFileDownloader
    from app.services.tiktok.download.strategies.base import TikTokDownloadStrategy


logger = logging.getLogger(__name__)
_DEFAULT_TIKVID_RESOLVER = resolvers_module.TikVidVideoResolver


class TikTokDownloadService:
    """Service for downloading TikTok videos by resolving direct URLs."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.strategy_factory = TikTokDownloadStrategyFactory()
        try:
            self.download_strategy: Optional["TikTokDownloadStrategy"] = (
                self.strategy_factory.create_strategy(self.settings)
            )
        except ValueError:
            # Surface configuration issues later while still allowing unit tests to mock resolvers.
            self.download_strategy = None

    async def download_video(self, request: TikTokDownloadRequest) -> TikTokDownloadResponse:
        """
        Download a TikTok video by resolving its direct download URL.

        Args:
            request: Download request containing TikTok URL and options

        Returns:
            Download response with direct URL or error information
        """
        start_time = time.perf_counter()

        try:
            # Validate the TikTok URL
            url_str = str(request.url)
            if not is_valid_tiktok_url(url_str):
                return self._error_response(
                    message="Invalid TikTok URL provided",
                    code="INVALID_URL",
                    details={"url": url_str},
                    execution_time=time.perf_counter() - start_time,
                )

            # Extract video metadata from URL
            metadata = extract_video_metadata_from_url(url_str)
            video_id = metadata.get('id')

            if not video_id:
                return self._error_response(
                    message="Could not extract video ID from URL",
                    code="INVALID_VIDEO_ID",
                    details={"url": url_str},
                    execution_time=time.perf_counter() - start_time,
                )

            resolver_cls = resolvers_module.TikVidVideoResolver
            resolver_overridden = resolver_cls is not _DEFAULT_TIKVID_RESOLVER
            strategy_name = str(self.settings.tiktok_download_strategy).lower()
            use_strategy = (
                self.download_strategy is not None
                and strategy_name != "camoufox"
                and not resolver_overridden
            )
            resolver_label = getattr(resolver_cls, "__name__", resolver_cls.__class__.__name__)
            strategy_label = (
                self.download_strategy.get_strategy_name()  # type: ignore[attr-defined]
                if use_strategy and hasattr(self.download_strategy, "get_strategy_name")
                else resolver_label
            )
            self.logger.info(
                "[TikTokDownloadService] Resolving video ID %s via %s",
                video_id,
                strategy_label,
            )

            # Resolve the direct download URL using either the configured strategy or the (possibly mocked) resolver.
            if use_strategy:
                download_url = await asyncio.to_thread(
                    self.download_strategy.resolve_video_url,
                    url_str,
                    None,  # quality_hint - not currently used
                    request.force_headful,
                )
            else:
                resolver = resolver_cls(self.settings)
                download_url = await asyncio.to_thread(
                    resolver.resolve_video_url,
                    url_str,
                )

            self.logger.info(f"[TikTokDownloadService] Resolved download URL: {download_url}")

            # Get file information
            downloader_cls = downloaders_module.VideoFileDownloader
            downloader: "VideoFileDownloader" = downloader_cls()
            try:
                file_info = await downloader.get_file_info(
                    download_url,
                    referer="https://tikvid.io"
                )
            except Exception as exc:
                self.logger.warning(f"[TikTokDownloadService] Failed to get file info: {exc}")
                file_info = {"file_size": None, "filename": None}

            # Create video info object
            video_info = TikTokVideoInfo(
                id=video_id,
                title=f"TikTok Video {video_id}",
                author=metadata.get('username'),
                file_size=file_info.get("file_size"),
            )

            # Build successful response
            execution_time = time.perf_counter() - start_time
            return TikTokDownloadResponse(
                status="success",
                message="Video download URL resolved successfully",
                download_url=download_url,
                video_info=video_info,
                file_size=file_info.get("file_size"),
                execution_time=execution_time,
            )

        except Exception as exc:
            self.logger.error(f"[TikTokDownloadService] Download failed: {exc}", exc_info=True)
            execution_time = time.perf_counter() - start_time

            # Determine error code based on exception type
            error_code = "DOWNLOAD_FAILED"
            error_message = "Failed to resolve video download URL"

            if "navigation" in str(exc).lower() or "timeout" in str(exc).lower():
                error_code = "NAVIGATION_FAILED"
                error_message = "Failed to navigate to TikVid service"
            elif "no MP4 link found" in str(exc).lower():
                error_code = "NO_DOWNLOAD_LINK"
                error_message = "No download link found for the video"
            elif "invalid" in str(exc).lower():
                error_code = "INVALID_VIDEO"
                error_message = "Invalid or inaccessible TikTok video"

            return self._error_response(
                message=error_message,
                code=error_code,
                details={
                    "original_url": str(request.url),
                    "exception": str(exc),
                },
                execution_time=execution_time,
            )

    def _error_response(
        self,
        *,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
    ) -> TikTokDownloadResponse:
        """Create a standardized error response."""
        return TikTokDownloadResponse(
            status="error",
            message=message,
            error_code=code,
            error_details=details,
            execution_time=execution_time,
        )
