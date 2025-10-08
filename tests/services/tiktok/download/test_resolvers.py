"""Unit tests for TikTok download resolvers."""

import pytest
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.unit]


from app.services.tiktok.download.resolvers.video_url import TikVidVideoResolver
from app.services.tiktok.download.actions.resolver import TikVidResolveAction


class TestTikVidVideoResolver:
    """Test cases for TikVidVideoResolver."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        return settings

    @pytest.fixture
    def resolver(self, mock_settings):
        """Create a TikVidVideoResolver instance."""
        return TikVidVideoResolver(mock_settings)

    def test_init(self, resolver, mock_settings):
        """Test resolver initialization."""
        assert resolver.settings == mock_settings

    def test_resolve_video_url_success(self, resolver):
        """Test successful video URL resolution."""
        tiktok_url = "https://www.tiktok.com/@username/video/1234567890"
        expected_mp4_url = "https://example.com/video.mp4"

        # Mock the adapter and components
        mock_adapter = Mock()
        mock_action = Mock(spec=TikVidResolveAction)
        mock_action.result_links = [expected_mp4_url, "https://example.com/info.html"]

        with patch('app.services.tiktok.download.resolvers.video_url.ScraplingFetcherAdapter', return_value=mock_adapter), \
                patch.object(resolver, '_build_camoufox_fetch_kwargs') as mock_build:

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": {"test": "kwargs"},
                "resolve_action": mock_action,
                "cleanup": None
            }

            mock_adapter.fetch.return_value = Mock()

            result = resolver.resolve_video_url(tiktok_url)

        assert result == expected_mp4_url
        mock_adapter.fetch.assert_called_once()

    def test_resolve_video_url_fallback_to_html_extraction(self, resolver):
        """Test URL resolution with HTML extraction fallback."""
        tiktok_url = "https://www.tiktok.com/@username/video/1234567890"
        expected_mp4_url = "https://example.com/fallback.mp4"

        # Mock the adapter and components
        mock_adapter = Mock()
        mock_action = Mock(spec=TikVidResolveAction)
        mock_action.result_links = []  # No direct links

        mock_page_result = Mock()
        mock_page_result.html_content = 'href="https://example.com/fallback.mp4"'

        with patch('app.services.tiktok.download.resolvers.video_url.ScraplingFetcherAdapter', return_value=mock_adapter), \
                patch.object(resolver, '_build_camoufox_fetch_kwargs') as mock_build:

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": {"test": "kwargs"},
                "resolve_action": mock_action,
                "cleanup": None
            }

            mock_adapter.fetch.return_value = mock_page_result

            result = resolver.resolve_video_url(tiktok_url)

        assert result == expected_mp4_url

    def test_resolve_video_url_retry_logic(self, resolver):
        """Test retry logic when resolution fails."""
        tiktok_url = "https://www.tiktok.com/@username/video/1234567890"

        # Mock the adapter to fail on first two attempts, succeed on third
        mock_adapter = Mock()
        mock_action = Mock(spec=TikVidResolveAction)

        call_count = 0

        def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            mock_action.result_links = ["https://example.com/retry.mp4"]
            return Mock()

        with patch('app.services.tiktok.download.resolvers.video_url.ScraplingFetcherAdapter', return_value=mock_adapter), \
                patch.object(resolver, '_build_camoufox_fetch_kwargs') as mock_build:

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": {"test": "kwargs"},
                "resolve_action": mock_action,
                "cleanup": None
            }

            mock_adapter.fetch.side_effect = mock_fetch

            result = resolver.resolve_video_url(tiktok_url)

        assert result == "https://example.com/retry.mp4"
        assert call_count == 3

    def test_resolve_video_url_max_retries_exceeded(self, resolver):
        """Test failure when max retries are exceeded."""
        tiktok_url = "https://www.tiktok.com/@username/video/1234567890"

        # Mock the adapter to always fail
        mock_adapter = Mock()
        mock_adapter.fetch.side_effect = Exception("Persistent failure")

        with patch('app.services.tiktok.download.resolvers.video_url.ScraplingFetcherAdapter', return_value=mock_adapter), \
                patch.object(resolver, '_build_camoufox_fetch_kwargs') as mock_build:

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": {"test": "kwargs"},
                "resolve_action": Mock(spec=TikVidResolveAction),
                "cleanup": None
            }

            with pytest.raises(RuntimeError, match="Resolution failed after retries"):
                resolver.resolve_video_url(tiktok_url)

        assert mock_adapter.fetch.call_count == 3

    def test_filter_media_links(self, resolver):
        """Test media link filtering."""
        links = [
            "https://tikvid.io/vi/info",
            "https://example.com/video.mp4",
            "https://cdn.example.com/content?mime_type=video_mp4",
            "https://another.com/video.MP4",
            "https://tikvid.io/vi/download",
        ]

        filtered = resolver._filter_media_links(links)

        # Should only include actual media links
        assert len(filtered) == 3
        assert "https://example.com/video.mp4" in filtered
        assert "https://cdn.example.com/content?mime_type=video_mp4" in filtered
        assert "https://another.com/video.MP4" in filtered

    def test_build_camoufox_fetch_kwargs(self, resolver):
        """Test building Camoufox fetch kwargs."""
        tiktok_url = "https://www.tiktok.com/@username/video/1234567890"
        quality_hint = "HD"

        # Mock dependencies
        mock_adapter = Mock()

        # Create a simple object with the required __dict__ attribute
        class MockCaps:
            def __init__(self):
                self.supports_proxy = True

        mock_caps_obj = MockCaps()
        mock_adapter.detect_capabilities.return_value = mock_caps_obj

        mock_action = Mock(spec=TikVidResolveAction)
        mock_action.result_links = []

        mock_additional_args = {"user_data_dir": "/tmp/data"}
        mock_extra_headers = {"User-Agent": "test"}
        mock_fetch_kwargs = {"headless": False}

        with patch('app.services.tiktok.download.resolvers.video_url.ScraplingFetcherAdapter', return_value=mock_adapter), \
                patch('app.services.tiktok.download.resolvers.video_url.TikVidResolveAction', return_value=mock_action), \
                patch('app.services.tiktok.download.resolvers.video_url.CamoufoxArgsBuilder') as mock_builder, \
                patch('app.services.tiktok.download.resolvers.video_url.FetchArgComposer') as mock_composer:

            mock_builder.build.return_value = (mock_additional_args, mock_extra_headers)
            mock_composer.compose.return_value = mock_fetch_kwargs

            result = resolver._build_camoufox_fetch_kwargs(tiktok_url, quality_hint)

        assert "adapter" in result
        assert "fetch_kwargs" in result
        assert "resolve_action" in result
        assert "cleanup" in result
        assert result["adapter"] == mock_adapter
        assert result["resolve_action"] == mock_action
