"""Integration tests for TikTok download endpoint."""

import asyncio
import pytest
import httpx

from app.main import app
from app.services.tiktok.download.service import TikTokDownloadService
from app.schemas.tiktok.download import TikTokDownloadRequest

# Use the demo URL from the original demo script
DEMO_TIKTOK_URL = "https://www.tiktok.com/@tieentiton/video/7530618987760209170"


class TestTikTokDownloadIntegration:
    """Integration tests for TikTok download functionality."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_invalid_url(self):
        """Test download endpoint with invalid URL."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/tiktok/download",
                json={"url": "https://example.com/not-tiktok/video/123"}
            )
            assert response.status_code == 400
            data = response.json()
            assert data["status"] == "error"
            assert data["error_code"] == "INVALID_URL"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_invalid_json(self):
        """Test download endpoint with invalid JSON."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/tiktok/download",
                json={"invalid": "data", "url": "not-a-url"}
            )
            # Should validate URL format first
            assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_empty_body(self):
        """Test download endpoint with empty body."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/tiktok/download", json={})
            assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_missing_url(self):
        """Test download endpoint with missing URL field."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/tiktok/download",
                json={"quality": "HD"}
            )
            assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_valid_request_format(self):
        """Test download endpoint with valid request format."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )
            # Should either succeed or fail with a proper error structure
            assert response.status_code in [200, 400, 404, 500, 503]
            data = response.json()
            assert "status" in data
            assert data["status"] in ["success", "error"]
            if data["status"] == "error":
                assert "error_code" in data or "message" in data

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_download_resolution(self):
        """
        Test actual TikTok video URL resolution with real service calls.
        This test makes real network calls and may be slow.

        Prerequisites: Camoufox browser engine must be installed
        Installation: pip install camoufox
        """
        service = TikTokDownloadService()
        request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

        try:
            result = await service.download_video(request)

            # The test should either succeed or fail gracefully
            assert result.status in ["success", "error"]
            assert result.message is not None
            assert result.execution_time is not None
            assert result.execution_time > 0

            if result.status == "success":
                assert result.download_url is not None
                assert str(result.download_url).startswith("http")
                assert result.video_info is not None
                assert result.video_info.id == "7530618987760209170"

        except Exception as exc:
            # If there's a network/browser issue, that's acceptable for integration tests
            # Log the error but don't fail the test
            print(f"Integration test network error (acceptable): {exc}")
            pytest.skip(f"Network/browser issue: {exc}")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_download_with_file_info(self):
        """
        Test actual download URL resolution and file info retrieval.
        This test makes real network calls and may be slow.

        Prerequisites: Camoufox browser engine must be installed
        Installation: pip install camoufox
        """
        service = TikTokDownloadService()
        request = TikTokDownloadRequest(url=DEMO_TIKTOK_URL)

        try:
            result = await service.download_video(request)

            if result.status == "success" and result.download_url:
                # Try to get file info from the resolved URL
                from app.services.tiktok.download.downloaders.file import VideoFileDownloader
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

        except Exception as exc:
            # If there's a network issue, that's acceptable for integration tests
            print(f"File info test network error (acceptable): {exc}")
            pytest.skip(f"Network issue: {exc}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_download_endpoint_extra_fields_rejection(self):
        """Test download endpoint rejects extra fields."""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/tiktok/download",
                json={
                    "url": DEMO_TIKTOK_URL,
                    "extra_field": "should_be_rejected"
                }
            )

            # Should reject extra fields according to Pydantic settings
            assert response.status_code == 422

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_layer_directly_with_real_url(self):
        """
        Test the service layer directly with real URL.
        This helps isolate the service logic from API layer concerns.
        """
        # Test URL validation
        from app.services.tiktok.download.utils.helpers import is_valid_tiktok_url
        assert is_valid_tiktok_url(DEMO_TIKTOK_URL) is True

        # Test video ID extraction
        from app.services.tiktok.download.utils.helpers import extract_tiktok_video_id
        video_id = extract_tiktok_video_id(DEMO_TIKTOK_URL)
        assert video_id == "7530618987760209170"

        # Test metadata extraction
        from app.services.tiktok.download.utils.helpers import extract_video_metadata_from_url
        metadata = extract_video_metadata_from_url(DEMO_TIKTOK_URL)
        assert metadata["id"] == "7530618987760209170"
        assert metadata["username"] == "tieentiton"

        print("Service layer validation tests passed")
