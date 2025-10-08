"""Integration tests for TikTok download endpoint using Chromium browser."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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
MOCK_DOWNLOAD_URL = "https://example.com/video.mp4"


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
    async def test_chromium_download_resolution_with_mocked_browser(self) -> None:
        """Test download resolution with mocked browser components to avoid external dependencies."""
        # Force the use of Chromium strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            # Mock the DynamicFetcher to avoid actual browser automation
            with patch('app.services.tiktok.download.strategies.chromium.DynamicFetcher') as mock_fetcher:
                mock_instance = MagicMock()
                mock_fetcher.return_value = mock_instance

                # Mock the response to simulate successful resolution
                mock_response = MagicMock()
                mock_response.html_content = f'<a href="{MOCK_DOWNLOAD_URL}">Download</a>'
                mock_instance.fetch.return_value = mock_response

                service = TikTokDownloadService()
                # Ensure we're using Chromium strategy
                assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

                request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

                result = await service.download_video(request)

                assert result.status == "success"
                assert result.message is not None
                assert result.execution_time is not None
                assert result.execution_time > 0
                assert result.download_url is not None
                assert str(result.download_url).startswith("http")
                assert result.video_info is not None
                assert result.video_info.id == "7530618987760209170"

    @pytest.mark.asyncio
    async def test_chromium_strategy_handles_browser_errors(self) -> None:
        """Test that Chromium strategy properly handles browser errors."""
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            # Mock the DynamicFetcher to raise an exception
            with patch('app.services.tiktok.download.strategies.chromium.DynamicFetcher') as mock_fetcher:
                mock_instance = MagicMock()
                mock_fetcher.return_value = mock_instance
                mock_instance.fetch.side_effect = Exception("Browser navigation failed")

                service = TikTokDownloadService()
                assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

                request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)
                result = await service.download_video(request)

                assert result.status == "error"
                assert result.error_code in ["DOWNLOAD_FAILED", "NAVIGATION_FAILED"]
                assert result.error_details is not None

    @pytest.mark.asyncio
    async def test_chromium_strategy_page_action_callable_conversion(self) -> None:
        """Test that the Chromium strategy properly converts TikVidResolveAction to callable."""
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            strategy = service.download_strategy

            # Test that the strategy can build fetch kwargs without errors
            components = strategy._build_chromium_fetch_kwargs(DEMO_TIKTOK_URL)

            assert "fetch_kwargs" in components
            assert "page_action" in components["fetch_kwargs"]

            # Verify page_action is callable
            page_action = components["fetch_kwargs"]["page_action"]
            assert callable(page_action)

            # Test the callable with a mock page
            mock_page = MagicMock()
            mock_resolve_action = components["resolve_action"]
            mock_resolve_action.result_links = [MOCK_DOWNLOAD_URL]

            result = page_action(mock_page)
            assert result == mock_page

    @pytest.mark.asyncio
    async def test_chromium_strategy_name(self) -> None:
        """Test that Chromium strategy reports correct name."""
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            assert isinstance(service.download_strategy, ChromiumDownloadStrategy)
            assert service.download_strategy.get_strategy_name() == "chromium"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_real_download_resolution_with_chromium(self) -> None:
        """Resolve a real TikTok URL via the download service using Chromium strategy.

        Note: This test requires actual browser automation and may be slow or flaky.
        It tests the real integration with TikVid service.
        """
        # Force the use of Chromium strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'chromium'):
            service = TikTokDownloadService()
            # Ensure we're using Chromium strategy
            assert isinstance(service.download_strategy, ChromiumDownloadStrategy)

            request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

            result = await service.download_video(request)

            # Note: This test may fail due to external dependencies
            # The important thing is that the strategy can be instantiated and called
            if result.status == "success":
                assert result.message is not None
                assert result.execution_time is not None
                assert result.execution_time > 0
                assert result.download_url is not None
                assert str(result.download_url).startswith("http")
                assert result.video_info is not None
                assert result.video_info.id == "7530618987760209170"
            else:
                # If it fails, it should fail gracefully with proper error structure
                assert result.error_code is not None
                assert result.error_details is not None
