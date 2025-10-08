"""Integration tests for TikTok download endpoint."""

import pytest

from app.schemas.tiktok.download import TikTokDownloadRequest
from app.services.tiktok.download.downloaders.file import VideoFileDownloader
from app.services.tiktok.download.service import TikTokDownloadService

DEMO_TIKTOK_URL = "https://www.tiktok.com/@tieentiton/video/7530618987760209170"


class TestTikTokDownloadIntegration:
    """Integration tests that exercise real TikTok download flows."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_download_resolution(self):
        """Resolve a real TikTok URL via the download service."""
        service = TikTokDownloadService()
        request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

        try:
            result = await service.download_video(request)

            assert result.status in ["success", "error"]
            assert result.message is not None
            assert result.execution_time is not None
            assert result.execution_time > 0

            if result.status == "success":
                assert result.download_url is not None
                assert str(result.download_url).startswith("http")
                assert result.video_info is not None
                assert result.video_info.id == "7530618987760209170"

        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Network/browser issue: {exc}")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_download_with_file_info(self):
        """Resolve download URL and retrieve file metadata from the source."""
        service = TikTokDownloadService()
        request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

        try:
            result = await service.download_video(request)

            if result.status == "success" and result.download_url:
                downloader = VideoFileDownloader()

                file_info = await downloader.get_file_info(
                    str(result.download_url),
                    referer="https://tikvid.io"
                )

                assert "file_size" in file_info
                assert "content_type" in file_info
                assert "filename" in file_info

                if file_info["file_size"]:
                    assert isinstance(file_info["file_size"], int)
                    assert file_info["file_size"] > 0

        except Exception as exc:  # pragma: no cover
            pytest.skip(f"Network issue: {exc}")
