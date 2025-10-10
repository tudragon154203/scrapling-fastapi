"""Base strategy interface for TikTok video download implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TikTokDownloadStrategy(ABC):
    """Abstract base class for TikTok download strategies."""

    @abstractmethod
    def resolve_video_url(self, tiktok_url: str, quality_hint: Optional[str] = None, force_headful: Optional[bool] = None) -> str:
        """
        Resolve the direct MP4 URL for a TikTok video.

        Args:
            tiktok_url: The TikTok video URL to resolve
            quality_hint: Optional quality preference (HD, SD, etc.)
            force_headful: Optional flag to force headful browser mode

        Returns:
            Direct MP4 URL for the video

        Raises:
            RuntimeError: If resolution fails
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this strategy."""
        pass
