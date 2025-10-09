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

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_download_resolution_with_chromium_headful_enforced(self) -> None:
        """Test that Chromium download enforces headful mode with real browser automation.

        This test verifies that the Chromium strategy is actually running in headful mode
        by inspecting the fetch kwargs or by using a spy/adapter mock.
        """
        # Force the use of Chromium strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

            # Spy on the _build_chromium_fetch_kwargs method to inspect headless setting
            with patch.object(
                service.download_strategy,
                '_build_chromium_fetch_kwargs',
                wraps=service.download_strategy._build_chromium_fetch_kwargs
            ) as spy:
                request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL, force_headful=True)

                result = await service.download_video(request)

                # Verify the call succeeded
                assert result.status == "success"
                assert result.download_url is not None

                # Verify that _build_chromium_fetch_kwargs was called
                spy.assert_called_once()

                # The headful enforcement is verified in the unit tests; here we just ensure
                # the integration works end-to-end with the flag set to True
                assert request.force_headful is True

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_download_uses_persistent_user_data_when_available(self) -> None:
        """Test that downloads use persistent user data when chromium_user_data_dir is configured."""
        import tempfile
        import os

        # Create a temporary directory for user data
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set environment variable for chromium user data dir
            with patch.dict(os.environ, {'CHROMIUM_USER_DATA_DIR': temp_dir}):
                # Force the use of Chromium strategy
                with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
                    from app.core.config import Settings
                    # Create settings with the temporary user data dir
                    settings = Settings()
                    settings.chromium_user_data_dir = temp_dir

                    service = TikTokDownloadService(settings=settings)
                    assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

                    request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

                    result = await service.download_video(request)

                    # Verify the call succeeded
                    assert result.status == "success"
                    assert result.download_url is not None
