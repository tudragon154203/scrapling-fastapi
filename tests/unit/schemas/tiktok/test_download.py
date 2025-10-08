"""Unit tests for TikTok download schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.tiktok.download import TikTokDownloadRequest, TikTokDownloadResponse, TikTokVideoInfo


class TestTikTokDownloadRequest:
    """Test cases for TikTokDownloadRequest schema."""

    def test_valid_request(self):
        """Test creating a valid request."""
        request = TikTokDownloadRequest(
            url="https://www.tiktok.com/@username/video/1234567890"
        )
        assert str(request.url) == "https://www.tiktok.com/@username/video/1234567890"

    def test_invalid_url_type(self):
        """Test validation error for invalid URL type."""
        with pytest.raises(ValidationError):
            TikTokDownloadRequest(url="not-a-url")

    def test_empty_url(self):
        """Test validation error for empty URL."""
        with pytest.raises(ValidationError):
            TikTokDownloadRequest(url="")

    def test_request_serialization(self):
        """Test request serialization."""
        request = TikTokDownloadRequest(
            url="https://www.tiktok.com/@username/video/1234567890"
        )
        data = request.model_dump()
        assert data["url"] == "https://www.tiktok.com/@username/video/1234567890"
        assert "quality" not in data  # quality field should not exist


class TestTikTokVideoInfo:
    """Test cases for TikTokVideoInfo schema."""

    def test_complete_video_info(self):
        """Test creating complete video info."""
        info = TikTokVideoInfo(
            id="1234567890",
            title="Test Video",
            author="testuser",
            duration=30.5,
            thumbnail_url="https://example.com/thumb.jpg"
        )
        assert info.id == "1234567890"
        assert info.title == "Test Video"
        assert info.author == "testuser"
        assert info.duration == 30.5
        assert str(info.thumbnail_url) == "https://example.com/thumb.jpg"

    def test_minimal_video_info(self):
        """Test creating minimal video info."""
        info = TikTokVideoInfo(id="1234567890")
        assert info.id == "1234567890"
        assert info.title is None
        assert info.author is None
        assert info.duration is None
        assert info.thumbnail_url is None

    def test_video_info_serialization(self):
        """Test video info serialization."""
        info = TikTokVideoInfo(
            id="1234567890",
            title="Test Video",
            author="testuser"
        )
        data = info.model_dump()
        assert data["id"] == "1234567890"
        assert data["title"] == "Test Video"
        assert data["author"] == "testuser"
        assert "duration" not in data  # None values should be excluded

    def test_invalid_thumbnail_url(self):
        """Test validation error for invalid thumbnail URL."""
        with pytest.raises(ValidationError):
            TikTokVideoInfo(
                id="1234567890",
                thumbnail_url="not-a-url"
            )


class TestTikTokDownloadResponse:
    """Test cases for TikTokDownloadResponse schema."""

    def test_success_response(self):
        """Test creating a success response."""
        video_info = TikTokVideoInfo(
            id="1234567890",
            title="Test Video",
            author="testuser"
        )
        response = TikTokDownloadResponse(
            status="success",
            message="Video downloaded successfully",
            download_url="https://example.com/video.mp4",
            video_info=video_info,
            file_size=1024000,
            execution_time=5.5
        )
        assert response.status == "success"
        assert response.message == "Video downloaded successfully"
        assert str(response.download_url) == "https://example.com/video.mp4"
        assert response.video_info.id == "1234567890"
        assert response.file_size == 1024000
        assert response.execution_time == 5.5
        assert response.error_code is None
        assert response.error_details is None

    def test_error_response(self):
        """Test creating an error response."""
        response = TikTokDownloadResponse(
            status="error",
            message="Download failed",
            error_code="DOWNLOAD_FAILED",
            error_details={"reason": "Network error"},
            execution_time=2.3
        )
        assert response.status == "error"
        assert response.message == "Download failed"
        assert response.error_code == "DOWNLOAD_FAILED"
        assert response.error_details == {"reason": "Network error"}
        assert response.execution_time == 2.3
        assert response.download_url is None
        assert response.video_info is None
        assert response.file_size is None

    def test_minimal_response(self):
        """Test creating a minimal response."""
        response = TikTokDownloadResponse(
            status="success",
            message="OK"
        )
        assert response.status == "success"
        assert response.message == "OK"
        assert response.download_url is None
        assert response.video_info is None
        assert response.file_size is None
        assert response.error_code is None
        assert response.error_details is None
        assert response.execution_time is None

    def test_response_serialization_success(self):
        """Test success response serialization."""
        video_info = TikTokVideoInfo(id="1234567890")
        response = TikTokDownloadResponse(
            status="success",
            message="OK",
            download_url="https://example.com/video.mp4",
            video_info=video_info
        )
        data = response.model_dump()
        assert data["status"] == "success"
        assert data["message"] == "OK"
        assert data["download_url"] == "https://example.com/video.mp4"
        assert data["video_info"]["id"] == "1234567890"
        assert "error_code" not in data  # None values should be excluded

    def test_response_serialization_error(self):
        """Test error response serialization."""
        response = TikTokDownloadResponse(
            status="error",
            message="Failed",
            error_code="ERROR",
            error_details={"detail": "test"}
        )
        data = response.model_dump()
        assert data["status"] == "error"
        assert data["message"] == "Failed"
        assert data["error_code"] == "ERROR"
        assert data["error_details"] == {"detail": "test"}
        assert "download_url" not in data  # None values should be excluded

    def test_invalid_status_value(self):
        """Test validation error for invalid status."""
        with pytest.raises(ValidationError):
            TikTokDownloadResponse(
                status="invalid_status",
                message="Test"
            )

    def test_response_with_partial_success_data(self):
        """Test response with partial success data."""
        response = TikTokDownloadResponse(
            status="success",
            message="Partial success",
            download_url="https://example.com/video.mp4",
            file_size=1024000
            # video_info is None
        )
        assert response.status == "success"
        assert response.download_url is not None
        assert response.file_size is not None
        assert response.video_info is None