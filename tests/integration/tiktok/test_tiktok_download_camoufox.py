"""Integration tests for TikTok download endpoint using Camoufox browser."""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.schemas.tiktok.download import TikTokDownloadRequest
from app.services.tiktok.download.downloaders.file import VideoFileDownloader
from app.services.tiktok.download.service import TikTokDownloadService
from app.services.tiktok.download.strategies.camoufox import CamoufoxDownloadStrategy

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


class TestTikTokDownloadCamoufoxIntegration:
    """Integration tests that exercise real TikTok download flows using Camoufox browser."""

    @pytest.mark.asyncio
    async def test_real_download_resolution_with_camoufox(self) -> None:
        """Resolve a real TikTok URL via the download service using Camoufox strategy."""
        # Force the use of Camoufox strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'camoufox'):
            service = TikTokDownloadService()
            # Ensure we're using Camoufox strategy
            assert isinstance(service.download_strategy, CamoufoxDownloadStrategy)

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
    async def test_real_download_end_to_end_with_camoufox(self, tmp_path: Path) -> None:
        """Resolve, inspect, and download the media ensuring the file includes video using Camoufox."""
        # Force the use of Camoufox strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'camoufox'):
            service = TikTokDownloadService()
            # Ensure we're using Camoufox strategy
            assert isinstance(service.download_strategy, CamoufoxDownloadStrategy)

            request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

            result = await service.download_video(request)

            assert result.status == "success"
            assert result.download_url is not None

            downloader = VideoFileDownloader()

            file_info = await downloader.get_file_info(
                str(result.download_url),
                referer="https://tikvid.io",
            )

            assert file_info["content_type"]
            assert "video" in file_info["content_type"].lower()

            download_dir = tmp_path / "downloads"
            downloaded_path = await downloader.stream_to_file(
                str(result.download_url),
                download_dir,
                referer="https://tikvid.io",
            )

            assert downloaded_path.exists()
            assert downloaded_path.stat().st_size > 0
            assert _file_contains_video_track(downloaded_path)

    @pytest.mark.asyncio
    async def test_camoufox_unaffected_by_force_headful_field(self) -> None:
        """Test that Camoufox strategy is unaffected by force_headful field in schema."""
        # Force the use of Camoufox strategy
        with patch('app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY', 'camoufox'):
            service = TikTokDownloadService()
            assert isinstance(service.download_strategy, CamoufoxDownloadStrategy)

            # Test with force_headful=True (should be ignored by Camoufox strategy)
            request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL, force_headful=True)

            result = await service.download_video(request)

            # Verify success - force_headful should not interfere with Camoufox
            assert result.status == "success"
            assert result.download_url is not None
            assert result.video_info is not None

            # Test with force_headful=False (default)
            request_default = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

            result_default = await service.download_video(request_default)

            # Verify success
            assert result_default.status == "success"
            assert result_default.download_url is not None
