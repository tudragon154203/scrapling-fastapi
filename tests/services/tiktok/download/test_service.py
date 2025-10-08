"""Unit tests for TikTok download service."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.tiktok.download.service import TikTokDownloadService
from app.services.tiktok.download.resolvers.video_url import TikVidVideoResolver
from app.services.tiktok.download.downloaders.file import VideoFileDownloader
from app.schemas.tiktok.download import TikTokDownloadRequest


class TestTikTokDownloadService:
    """Test cases for TikTokDownloadService."""

    @pytest.fixture
    def service(self):
        """Create a TikTokDownloadService instance."""
        return TikTokDownloadService()

    @pytest.fixture
    def valid_request(self):
        """Create a valid download request."""
        return TikTokDownloadRequest(
            url="https://www.tiktok.com/@username/video/1234567890"
        )

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        return settings

    @pytest.mark.asyncio
    async def test_download_video_success(self, service, valid_request):
        """Test successful video download."""
        mock_resolver = Mock(spec=TikVidVideoResolver)
        mock_downloader = Mock(spec=VideoFileDownloader)

        expected_url = "https://example.com/video.mp4"
        mock_resolver.resolve_video_url.return_value = expected_url
        mock_downloader.get_file_info = AsyncMock(return_value={
            "file_size": 1024000,
            "content_type": "video/mp4",
            "filename": "video.mp4"
        })

        with patch('app.services.tiktok.download.service.TikVidVideoResolver', return_value=mock_resolver), \
                patch('app.services.tiktok.download.service.VideoFileDownloader', return_value=mock_downloader):

            result = await service.download_video(valid_request)

        assert result.status == "success"
        assert result.message == "Video download URL resolved successfully"
        assert str(result.download_url) == expected_url
        assert result.file_size == 1024000
        assert result.video_info.id == "1234567890"
        assert result.video_info.author == "username"

    @pytest.mark.asyncio
    async def test_download_video_invalid_url(self, service):
        """Test download with invalid URL."""
        invalid_request = TikTokDownloadRequest(
            url="https://example.com/not-tiktok/video/123"
        )

        result = await service.download_video(invalid_request)

        assert result.status == "error"
        assert result.error_code == "INVALID_URL"
        assert "Invalid TikTok URL" in result.message

    @pytest.mark.asyncio
    async def test_download_video_no_video_id(self, service):
        """Test download with URL that has no extractable video ID."""
        invalid_request = TikTokDownloadRequest(
            url="https://www.tiktok.com/@username"  # No video ID
        )

        result = await service.download_video(invalid_request)

        assert result.status == "error"
        assert result.error_code == "INVALID_URL"
        assert "Invalid TikTok URL" in result.message

    @pytest.mark.asyncio
    async def test_download_video_resolution_failure(self, service, valid_request):
        """Test download when URL resolution fails."""
        mock_resolver = Mock(spec=TikVidVideoResolver)
        mock_resolver.resolve_video_url.side_effect = Exception("Navigation failed")

        with patch('app.services.tiktok.download.service.TikVidVideoResolver', return_value=mock_resolver):
            result = await service.download_video(valid_request)

        assert result.status == "error"
        assert result.error_code == "NAVIGATION_FAILED"
        assert "Failed to navigate" in result.message

    @pytest.mark.asyncio
    async def test_download_video_file_info_failure(self, service, valid_request):
        """Test download when file info retrieval fails but URL resolution succeeds."""
        mock_resolver = Mock(spec=TikVidVideoResolver)
        mock_downloader = Mock(spec=VideoFileDownloader)

        expected_url = "https://example.com/video.mp4"
        mock_resolver.resolve_video_url.return_value = expected_url
        mock_downloader.get_file_info = AsyncMock(side_effect=Exception("Network error"))

        with patch('app.services.tiktok.download.service.TikVidVideoResolver', return_value=mock_resolver), \
                patch('app.services.tiktok.download.service.VideoFileDownloader', return_value=mock_downloader):

            result = await service.download_video(valid_request)

        assert result.status == "success"  # Should still succeed even if file info fails
        assert str(result.download_url) == expected_url
        assert result.file_size is None

    @pytest.mark.asyncio
    async def test_download_video_navigation_error(self, service, valid_request):
        """Test download with navigation timeout error."""
        mock_resolver = Mock(spec=TikVidVideoResolver)
        mock_resolver.resolve_video_url.side_effect = Exception("navigation timeout")

        with patch('app.services.tiktok.download.service.TikVidVideoResolver', return_value=mock_resolver):
            result = await service.download_video(valid_request)

        assert result.status == "error"
        assert result.error_code == "NAVIGATION_FAILED"

    @pytest.mark.asyncio
    async def test_download_video_no_download_link_error(self, service, valid_request):
        """Test download when no MP4 link is found."""
        mock_resolver = Mock(spec=TikVidVideoResolver)
        mock_resolver.resolve_video_url.side_effect = Exception("no MP4 link found")

        with patch('app.services.tiktok.download.service.TikVidVideoResolver', return_value=mock_resolver):
            result = await service.download_video(valid_request)

        assert result.status == "error"
        assert result.error_code == "DOWNLOAD_FAILED"

    def test_error_response_creation(self, service):
        """Test error response creation."""
        result = service._error_response(
            message="Test error",
            code="TEST_ERROR",
            details={"test": "detail"},
            execution_time=1.5
        )

        assert result.status == "error"
        assert result.message == "Test error"
        assert result.error_code == "TEST_ERROR"
        assert result.error_details == {"test": "detail"}
        assert result.execution_time == 1.5