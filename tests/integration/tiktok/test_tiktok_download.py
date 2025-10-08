"""Integration tests for TikTok download endpoint."""

from pathlib import Path

import pytest

from app.schemas.tiktok.download import TikTokDownloadRequest
from app.services.tiktok.download.downloaders.file import VideoFileDownloader
from app.services.tiktok.download.service import TikTokDownloadService

pytestmark = [pytest.mark.integration, pytest.mark.slow]

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


class TestTikTokDownloadIntegration:
    """Integration tests that exercise real TikTok download flows."""

    @pytest.mark.asyncio
    async def test_real_download_resolution(self) -> None:
        """Resolve a real TikTok URL via the download service."""
        service = TikTokDownloadService()
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
    async def test_real_download_end_to_end(self, tmp_path: Path) -> None:
        """Resolve, inspect, and download the media ensuring the file includes video."""
        service = TikTokDownloadService()
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
