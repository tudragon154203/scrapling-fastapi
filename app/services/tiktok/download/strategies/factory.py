"""Factory for creating TikTok download strategies based on configuration."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.services.tiktok.download.strategies.base import TikTokDownloadStrategy
from app.services.tiktok.download.strategies.camoufox import CamoufoxDownloadStrategy
from app.services.tiktok.download.strategies.chromium import ChromiumDownloadStrategy

logger = logging.getLogger(__name__)

# Environment variable for strategy selection
settings = get_settings()
TIKTOK_DOWNLOAD_STRATEGY = settings.tiktok_download_strategy.lower()


class TikTokDownloadStrategyFactory:
    """Factory for creating TikTok download strategies."""

    @staticmethod
    def create_strategy(settings: Any) -> TikTokDownloadStrategy:
        """
        Create a TikTok download strategy based on environment configuration.

        Args:
            settings: Application settings

        Returns:
            TikTokDownloadStrategy instance

        Raises:
            ValueError: If the strategy name is not supported
        """
        strategy_name = TIKTOK_DOWNLOAD_STRATEGY.lower()

        logger.info(f"Creating TikTok download strategy: {strategy_name}")

        if strategy_name == "camoufox":
            return CamoufoxDownloadStrategy(settings)
        elif strategy_name == "chromium":
            return ChromiumDownloadStrategy(settings)
        else:
            supported_strategies = ["camoufox", "chromium"]
            raise ValueError(
                f"Unsupported TikTok download strategy: {strategy_name}. "
                f"Supported strategies: {', '.join(supported_strategies)}"
            )

    @staticmethod
    def get_current_strategy_name() -> str:
        """Get the currently configured strategy name."""
        return TIKTOK_DOWNLOAD_STRATEGY

    @staticmethod
    def list_supported_strategies() -> list[str]:
        """List all supported strategy names."""
        return ["camoufox", "chromium"]
