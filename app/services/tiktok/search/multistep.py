"""Placeholder TikTok multi-step search service."""

from __future__ import annotations

from typing import Any, Dict, List, Union

from app.services.tiktok.abstract_search_service import AbstractTikTokSearchService


class TiktokMultistepSearchService(AbstractTikTokSearchService):
    """Placeholder service inheriting from the abstract TikTok search base."""

    def __init__(self, service: Any) -> None:
        super().__init__(service)

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int,
        sort_type: str,
        recency_days: str,
    ) -> Dict[str, Any]:
        """Placeholder search implementation to be provided in the future."""
        raise NotImplementedError("TikTok multi-step search service not implemented yet.")
