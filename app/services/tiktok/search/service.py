"""Service for handling TikTok search operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from app.core.config import get_settings

from app.services.tiktok.search.interfaces import TikTokSearchInterface
from app.services.tiktok.search.multistep import TikTokMultiStepSearchService
from app.services.tiktok.search.url_param import TikTokURLParamSearchService


class TikTokSearchService(TikTokSearchInterface):
    """Main TikTok search service that orchestrates different search strategies."""

    def __init__(
        self,
        strategy: str = "multistep",
    ) -> None:
        from app.core.config import get_settings
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.strategy = strategy

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int = 50,
        sort_type: str = "RELEVANCE",
        recency_days: str = "ALL",
    ) -> Dict[str, Any]:
        """Execute a TikTok search using the configured strategy."""
        self.logger.debug(
            "[TikTokSearchService] search called - query: %s, num_videos: %s, sort_type: %s, recency_days: %s",
            query,
            num_videos,
            sort_type,
            recency_days,
        )

        try:
            search_impl = self._build_search_implementation()
            result = await search_impl.search(
                query,
                num_videos=num_videos,
                sort_type=sort_type,
                recency_days=recency_days,
            )
            self.logger.debug(
                "[TikTokSearchService] Search completed successfully - total results: %s",
                len(result.get("results", [])),
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("[TikTokSearchService] Exception in search: %s", exc, exc_info=True)
            return {"error": f"Search failed: {exc}"}

    def _build_search_implementation(self) -> TikTokSearchInterface:
        """Instantiate the configured search implementation."""
        if self.strategy == "direct":
            return TikTokURLParamSearchService()
        else:  # multistep or any other value
            return TikTokMultiStepSearchService()
