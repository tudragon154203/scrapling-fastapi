"""Service for handling TikTok search operations."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Union
from pathlib import Path

from app.services.tiktok.search.interfaces import TikTokSearchInterface
from app.services.tiktok.search.multistep import TikTokMultiStepSearchService
from app.services.tiktok.search.url_param import TikTokURLParamSearchService
from specify_src.models.browser_mode import BrowserMode


class TikTokSearchService(TikTokSearchInterface):
    """Main TikTok search service that orchestrates different search strategies."""

    def __init__(
        self,
        strategy: str = "multistep",
        force_headful: bool = False,
        browser_mode: BrowserMode | None = None,
    ) -> None:
        from app.core.config import get_settings
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self._requested_strategy = strategy
        self._browser_mode = browser_mode
        self._force_headful = force_headful
        self.strategy = self._resolve_strategy(strategy)

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

    def _resolve_strategy(self, requested_strategy: str) -> str:
        """Resolve the effective strategy based on browser mode constraints."""
        # The multistep flow requires a visible browser window for TikTok login and
        # human-verification interstitials. When the resolved browser mode is
        # headless we immediately downgrade to the direct strategy rather than
        # attempting a flow that is guaranteed to fail without those UI
        # capabilities.
        if (
            self._browser_mode is not None
            and self._browser_mode == BrowserMode.HEADLESS
            and requested_strategy == "multistep"
        ):
            self.logger.info(
                "[TikTokSearchService] Overriding multistep strategy with direct strategy for headless mode"
            )
            return "direct"
        return requested_strategy

    def _build_search_implementation(self) -> TikTokSearchInterface:
        """Instantiate the configured search implementation."""
        if self.strategy == "direct":
            return TikTokURLParamSearchService()

        user_data_dir = getattr(self.settings, "camoufox_user_data_dir", None)
        if not user_data_dir:
            self.logger.warning(
                "[TikTokSearchService] camoufox_user_data_dir not configured; running without persistent user data"
            )

        else:
            master_dir = Path(user_data_dir) / "master"
            master_ready = False
            try:
                master_ready = master_dir.exists() and any(master_dir.iterdir())
            except Exception:
                master_ready = False
            if not master_ready:
                self.logger.warning(
                    "[TikTokSearchService] camoufox master profile missing or empty; running with ephemeral user data"
                )

        return TikTokMultiStepSearchService(force_headful=getattr(self, '_force_headful', False))
