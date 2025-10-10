"""Unit tests for TikTok download downloaders."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx

from app.services.tiktok.download.downloaders.file import VideoFileDownloader

pytestmark = [pytest.mark.unit]


class TestVideoFileDownloader:
    """Test cases for VideoFileDownloader."""

    @pytest.fixture
    def downloader(self):
        """Create a VideoFileDownloader instance."""
        return VideoFileDownloader(timeout=30.0)

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.headers = {
            "content-length": "1024000",
            "content-type": "video/mp4",
            "content-disposition": 'attachment; filename="video.mp4"'
        }
        response.raise_for_status = Mock()
        return response

    @pytest.mark.asyncio
    async def test_get_file_info_success(self, downloader, mock_response):
        """Test successful file info retrieval."""
        url = "https://example.com/video.mp4"

        with patch('app.services.tiktok.download.downloaders.file.httpx') as mock_httpx:
            mock_client = AsyncMock()

            # Mock the AsyncClient context manager properly
            mock_client_manager = AsyncMock()
            mock_client_manager.__aenter__.return_value = mock_client
            mock_client_manager.__aexit__ = AsyncMock()
            mock_httpx.AsyncClient.return_value = mock_client_manager

            mock_client.head.return_value = mock_response

            result = await downloader.get_file_info(url)

        assert result["file_size"] == 1024000
        assert result["content_type"] == "video/mp4"
        assert result["filename"] == "video.mp4"
        assert "headers" in result

    @pytest.mark.asyncio
    async def test_get_file_info_with_referer(self, downloader, mock_response):
        """Test file info retrieval with referer header."""
        url = "https://example.com/video.mp4"
        referer = "https://tikvid.io"

        with patch('app.services.tiktok.download.downloaders.file.httpx') as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
            mock_client.head.return_value = mock_response

            await downloader.get_file_info(url, referer)

            # Check that referer was included in headers
            call_kwargs = mock_client.head.call_args[1]
            assert "Referer" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Referer"] == referer

    @pytest.mark.asyncio
    async def test_get_file_info_no_content_length(self, downloader):
        """Test file info retrieval when content-length is missing."""
        url = "https://example.com/video.mp4"

        mock_response = Mock()
        mock_response.headers = {
            "content-type": "video/mp4",
        }
        mock_response.raise_for_status = Mock()

        with patch('app.services.tiktok.download.downloaders.file.httpx') as mock_httpx:
            mock_client = AsyncMock()

            # Mock the AsyncClient context manager properly
            mock_client_manager = AsyncMock()
            mock_client_manager.__aenter__.return_value = mock_client
            mock_client_manager.__aexit__ = AsyncMock()
            mock_httpx.AsyncClient.return_value = mock_client_manager

            mock_client.head.return_value = mock_response

            result = await downloader.get_file_info(url)

        assert result["file_size"] is None
        assert result["content_type"] == "video/mp4"

    @pytest.mark.asyncio
    async def test_get_file_info_httpx_not_available(self, downloader):
        """Test file info retrieval when httpx is not available."""
        url = "https://example.com/video.mp4"

        with patch('app.services.tiktok.download.downloaders.file.httpx', None):
            with pytest.raises(RuntimeError, match="httpx library is not available"):
                await downloader.get_file_info(url)

    @pytest.mark.asyncio
    async def test_get_file_info_request_failure(self, downloader):
        """Test file info retrieval when request fails."""
        url = "https://example.com/video.mp4"

        with patch('app.services.tiktok.download.downloaders.file.httpx') as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
            mock_client.head.side_effect = httpx.RequestError("Network error")

            with pytest.raises(RuntimeError, match="Failed to get file info"):
                await downloader.get_file_info(url)

    @pytest.mark.asyncio
    async def test_stream_to_memory_success(self, downloader):
        """Test successful streaming to memory."""
        url = "https://example.com/video.mp4"
        expected_content = b"video content data"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        # Mock async iteration
        async def mock_aiter_bytes(chunk_size):
            yield expected_content[:chunk_size // 2]
            yield expected_content[chunk_size // 2:]

        mock_response.aiter_bytes = mock_aiter_bytes

        # Create custom mock for proper async context manager behavior
        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def stream(self, method, url, headers=None):
                return MockAsyncResponse()

        class MockAsyncResponse:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch('app.services.tiktok.download.downloaders.file.httpx.AsyncClient', MockAsyncClient):
            result = await downloader.stream_to_memory(url)

        assert result == expected_content

    @pytest.mark.asyncio
    async def test_stream_to_file_success(self, downloader, tmp_path):
        """Test successful streaming to file."""
        url = "https://example.com/video.mp4"
        expected_content = b"video content data"
        output_dir = tmp_path

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-disposition": 'attachment; filename="video.mp4"'}

        # Mock async iteration
        async def mock_aiter_bytes(chunk_size):
            yield expected_content[:chunk_size // 2]
            yield expected_content[chunk_size // 2:]

        mock_response.aiter_bytes = mock_aiter_bytes

        # Create custom mock for proper async context manager behavior
        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def stream(self, method, url, headers=None):
                return MockAsyncResponse()

        class MockAsyncResponse:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch('app.services.tiktok.download.downloaders.file.httpx.AsyncClient', MockAsyncClient):
            result = await downloader.stream_to_file(url, output_dir)

        expected_path = output_dir / "video.mp4"
        assert result == expected_path
        assert expected_path.exists()
        assert expected_path.read_bytes() == expected_content

    @pytest.mark.asyncio
    async def test_stream_to_file_directory_path(self, downloader, tmp_path):
        """Test streaming to file when output_path is a directory."""
        url = "https://example.com/video.mp4"
        expected_content = b"video content data"
        output_dir = tmp_path

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-disposition": 'attachment; filename="test_video.mp4"'}

        async def mock_aiter_bytes(chunk_size):
            yield expected_content

        mock_response.aiter_bytes = mock_aiter_bytes

        # Create custom mock for proper async context manager behavior
        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

            def stream(self, method, url, headers=None):
                return MockAsyncResponse()

        class MockAsyncResponse:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        with patch('app.services.tiktok.download.downloaders.file.httpx.AsyncClient', MockAsyncClient):
            result = await downloader.stream_to_file(url, output_dir)

        expected_path = output_dir / "test_video.mp4"
        assert result == expected_path
        assert expected_path.exists()

    def test_extract_filename_from_url_or_headers_content_disposition(self, downloader):
        """Test filename extraction from Content-Disposition header."""
        url = "https://example.com/video.mp4"
        headers = {"content-disposition": 'attachment; filename="custom_name.mp4"'}

        filename = downloader._extract_filename_from_url_or_headers(url, headers)

        assert filename == "custom_name.mp4"

    def test_extract_filename_from_url_or_headers_utf8(self, downloader):
        """Test filename extraction from UTF-8 encoded Content-Disposition."""
        url = "https://example.com/video.mp4"
        headers = {"content-disposition": "attachment; filename*=UTF-8''café.mp4"}

        filename = downloader._extract_filename_from_url_or_headers(url, headers)

        assert filename == "café.mp4"

    def test_extract_filename_from_url_or_headers_query_param(self, downloader):
        """Test filename extraction from URL query parameters."""
        url = "https://example.com/download?filename=query_name.mp4&id=123"
        headers = {}

        filename = downloader._extract_filename_from_url_or_headers(url, headers)

        assert filename == "query_name.mp4"

    def test_extract_filename_from_url_or_headers_path(self, downloader):
        """Test filename extraction from URL path."""
        url = "https://example.com/videos/path_name.mp4"
        headers = {}

        filename = downloader._extract_filename_from_url_or_headers(url, headers)

        assert filename == "path_name.mp4"

    def test_extract_filename_from_url_or_headers_fallback(self, downloader):
        """Test filename extraction fallback to default."""
        url = "https://example.com/"
        headers = {}

        filename = downloader._extract_filename_from_url_or_headers(url, headers, "fallback.mp4")

        assert filename == "fallback.mp4"
