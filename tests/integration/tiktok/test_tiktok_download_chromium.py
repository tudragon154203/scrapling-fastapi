"""Integration tests for TikTok download endpoint using Chromium browser."""

from pathlib import Path
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


def _file_contains_video_track(path: Path) -> bool:
    """Return True if the downloaded media file contains a video track marker."""
    marker = b"vide"
    buffer = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 14):
            buffer += chunk
            if marker in buffer:
                return True
            buffer = buffer[-(len(marker) - 1):]
    return False


class TestTikTokDownloadChromiumIntegration:
    """Integration tests that exercise TikTok download flows using Chromium browser."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_download_resolution_with_chromium(self) -> None:
        """Resolve a real TikTok URL via the download service using Chromium strategy.

        Note: This test requires actual browser automation and may be slow or flaky.
        It tests the real integration with TikVid service in headful mode.
        """
        # Force the use of Chromium strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            # Ensure we're using Chromium strategy
            assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

            request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

            result = await service.download_video(request)

            # Note: This test may fail due to external dependencies
            assert result.status == "success"
            assert result.message is not None
            assert result.execution_time is not None
            assert result.execution_time > 0
            assert result.download_url is not None
            assert str(result.download_url).startswith("http")
            assert result.video_info is not None
            assert result.video_info.id == "7530618987760209170"
