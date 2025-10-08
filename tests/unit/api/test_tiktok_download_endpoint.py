"""Unit tests for TikTok download endpoint."""

import pytest
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.tiktok.download import TikTokDownloadResponse, TikTokVideoInfo

# Use the demo URL from the original demo script
DEMO_TIKTOK_URL = "https://www.tiktok.com/@tieentiton/video/7530618987760209170"

client = TestClient(app)


class TestTikTokDownloadEndpointUnit:
    """Unit tests for TikTok download endpoint functionality."""

    @pytest.mark.unit
    def test_download_endpoint_success_routing(self):
        """Test successful download endpoint routing and response mapping."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="success",
                message="Video download URL resolved successfully",
                download_url="https://example.com/video.mp4",
                video_info=TikTokVideoInfo(
                    id="7530618987760209170",
                    title="TikTok Video",
                    author="tieentiton"
                ),
                file_size=1024000,
                execution_time=12.5
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["download_url"] == "https://example.com/video.mp4"
            assert data["video_info"]["id"] == "7530618987760209170"
            assert data["video_info"]["author"] == "tieentiton"
            assert data["file_size"] == 1024000
            assert data["execution_time"] == 12.5

    @pytest.mark.unit
    def test_download_endpoint_invalid_url_error_routing(self):
        """Test download endpoint error mapping for invalid URLs."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="error",
                message="Invalid TikTok URL provided",
                error_code="INVALID_URL",
                error_details={"url": "https://example.com/invalid"},
                execution_time=0.1
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": "https://example.com/invalid"}
            )

            assert response.status_code == 400  # Maps to HTTP_400_BAD_REQUEST
            data = response.json()
            assert data["status"] == "error"
            assert data["error_code"] == "INVALID_URL"
            assert data["message"] == "Invalid TikTok URL provided"

    @pytest.mark.unit
    def test_download_endpoint_navigation_failed_error_routing(self):
        """Test download endpoint error mapping for navigation failures."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="error",
                message="Failed to navigate to TikVid service",
                error_code="NAVIGATION_FAILED",
                error_details={"original_url": DEMO_TIKTOK_URL},
                execution_time=30.0
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )

            assert response.status_code == 503  # Maps to HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "error"
            assert data["error_code"] == "NAVIGATION_FAILED"

    @pytest.mark.unit
    def test_download_endpoint_no_download_link_error_routing(self):
        """Test download endpoint error mapping for missing download links."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="error",
                message="No download link found for the video",
                error_code="NO_DOWNLOAD_LINK",
                execution_time=15.0
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )

            assert response.status_code == 404  # Maps to HTTP_404_NOT_FOUND
            data = response.json()
            assert data["status"] == "error"
            assert data["error_code"] == "NO_DOWNLOAD_LINK"

    @pytest.mark.unit
    def test_download_endpoint_unknown_error_routing(self):
        """Test download endpoint error mapping for unknown errors."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="error",
                message="Unknown error occurred",
                error_code="UNKNOWN_ERROR",
                execution_time=5.0
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )

            assert response.status_code == 500  # Maps to HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["status"] == "error"
            assert data["error_code"] == "UNKNOWN_ERROR"

    @pytest.mark.unit
    def test_download_endpoint_request_validation_invalid_url_format(self):
        """Test request validation for invalid URL format."""
        response = client.post(
            "/tiktok/download",
            json={"url": "not-a-valid-url"}
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_download_endpoint_request_validation_missing_url(self):
        """Test request validation for missing URL field."""
        response = client.post(
            "/tiktok/download",
            json={}
        )

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_download_endpoint_request_validation_extra_fields(self):
        """Test request validation rejects extra fields."""
        response = client.post(
            "/tiktok/download",
            json={
                "url": DEMO_TIKTOK_URL,
                "extra_field": "should_be_rejected"
            }
        )

        assert response.status_code == 422  # Validation error for extra fields
        data = response.json()
        assert "detail" in data

    @pytest.mark.unit
    def test_download_endpoint_service_call_without_quality(self):
        """Test that service is called without quality parameter."""
        with patch('app.api.tiktok.tiktok_download_service') as mock_service:
            mock_service.download_video = AsyncMock(return_value=TikTokDownloadResponse(
                status="success",
                message="Video download URL resolved successfully",
                download_url="https://example.com/video.mp4",
                video_info=TikTokVideoInfo(id="7530618987760209170"),
                execution_time=10.0
            ))

            response = client.post(
                "/tiktok/download",
                json={"url": DEMO_TIKTOK_URL}
            )

            assert response.status_code == 200

            # Verify the service was called
            mock_service.download_video.assert_called_once()

            # Verify the request object does not have quality field
            call_args = mock_service.download_video.call_args[0][0]
            assert not hasattr(call_args, 'quality') or call_args.quality is None