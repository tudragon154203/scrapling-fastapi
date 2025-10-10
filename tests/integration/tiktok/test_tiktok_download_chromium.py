"""Integration tests for TikTok download endpoint using Chromium browser."""

from unittest.mock import patch

import pytest

from app.schemas.tiktok.download import TikTokDownloadRequest
from app.services.tiktok.download.service import TikTokDownloadService
from app.services.tiktok.download.strategies.chromium import ChromiumDownloadStrategy

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.usefixtures("require_scrapling"),
]

DEMO_TIKTOK_URL = "https://www.tiktok.com/@tieentiton/video/7530618987760209170"


class TestTikTokDownloadChromiumIntegration:
    """Integration coverage for the Chromium TikTok download strategy."""

    @pytest.mark.asyncio
    async def test_real_download_resolution_with_chromium(self) -> None:
        """Resolve a real TikTok URL using the Chromium strategy end-to-end."""
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

            request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

            result = await service.download_video(request)

            assert result.status == "success"
            assert result.message is not None
            assert result.execution_time is not None and result.execution_time > 0
            assert result.download_url is not None
            assert str(result.download_url).startswith("http")
            assert result.video_info is not None
            assert result.video_info.id == "7530618987760209170"

    @pytest.mark.asyncio
    async def test_download_uses_persistent_user_data_when_available(self) -> None:
        """Ensure persistent user data is honoured when configured."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {'CHROMIUM_USER_DATA_DIR': temp_dir}):
                from app.core.config import Settings

                settings = Settings()
                settings.chromium_user_data_dir = temp_dir

                with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
                    service = TikTokDownloadService(settings=settings)
                    assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

                    request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)
                    result = await service.download_video(request)

                    assert result.status == "success"
                    assert result.download_url is not None
