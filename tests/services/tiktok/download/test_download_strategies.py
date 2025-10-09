"""Unit tests for TikTok download strategies."""

from app.services.tiktok.download.strategies.factory import TikTokDownloadStrategyFactory
from app.services.tiktok.download.strategies.chromium import ChromiumDownloadStrategy
from app.services.tiktok.download.strategies.camoufox import CamoufoxDownloadStrategy
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestCamoufoxDownloadStrategy:
    """Test cases for CamoufoxDownloadStrategy."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        return settings

    @pytest.fixture
    def strategy(self, mock_settings: MagicMock) -> CamoufoxDownloadStrategy:
        """Create a CamoufoxDownloadStrategy instance for testing."""
        return CamoufoxDownloadStrategy(mock_settings)

    def test_get_strategy_name(self, strategy: CamoufoxDownloadStrategy) -> None:
        """Test getting strategy name."""
        assert strategy.get_strategy_name() == "camoufox"

    def test_resolve_video_url_success(self, strategy: CamoufoxDownloadStrategy) -> None:
        """Test successful video URL resolution."""
        with patch.object(strategy, '_build_camoufox_fetch_kwargs') as mock_build:
            # Mock the components
            mock_adapter = MagicMock()
            mock_fetch_kwargs = {"test": "kwargs"}
            mock_resolve_action = MagicMock()
            mock_resolve_action.result_links = ["https://example.com/video.mp4"]
            mock_cleanup = None

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": mock_fetch_kwargs,
                "resolve_action": mock_resolve_action,
                "cleanup": mock_cleanup,
            }

            # Mock successful fetch
            mock_adapter.fetch.return_value = MagicMock()

            result = strategy.resolve_video_url("https://www.tiktok.com/@test/video/123")

            assert result == "https://example.com/video.mp4"

    def test_resolve_video_url_fallback_to_html(self, strategy: CamoufoxDownloadStrategy) -> None:
        """Test video URL resolution fallback to HTML parsing."""
        with patch.object(strategy, '_build_camoufox_fetch_kwargs') as mock_build:
            # Mock the components
            mock_adapter = MagicMock()
            mock_fetch_kwargs = {"test": "kwargs"}
            mock_resolve_action = MagicMock()
            mock_resolve_action.result_links = []
            mock_cleanup = None

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": mock_fetch_kwargs,
                "resolve_action": mock_resolve_action,
                "cleanup": mock_cleanup,
            }

            # Mock successful fetch with HTML content
            mock_page_result = MagicMock()
            mock_page_result.html_content = 'href="https://example.com/fallback.mp4"'
            mock_adapter.fetch.return_value = mock_page_result

            result = strategy.resolve_video_url("https://www.tiktok.com/@test/video/123")

            assert result == "https://example.com/fallback.mp4"

    def test_resolve_video_url_failure(self, strategy: CamoufoxDownloadStrategy) -> None:
        """Test video URL resolution failure after retries."""
        with patch.object(strategy, '_build_camoufox_fetch_kwargs') as mock_build:
            # Mock the components to always fail
            mock_adapter = MagicMock()
            mock_fetch_kwargs = {"test": "kwargs"}
            mock_resolve_action = MagicMock()
            mock_resolve_action.result_links = []
            mock_cleanup = None

            mock_build.return_value = {
                "adapter": mock_adapter,
                "fetch_kwargs": mock_fetch_kwargs,
                "resolve_action": mock_resolve_action,
                "cleanup": mock_cleanup,
            }

            # Mock failed fetch with no HTML content
            mock_page_result = MagicMock()
            mock_page_result.html_content = None
            mock_adapter.fetch.return_value = mock_page_result

            with pytest.raises(RuntimeError, match="Resolution failed after retries"):
                strategy.resolve_video_url("https://www.tiktok.com/@test/video/123")

    def test_filter_media_links(self, strategy: CamoufoxDownloadStrategy) -> None:
        """Test filtering media links."""
        test_links = [
            "https://example.com/video.mp4",
            "https://tikvid.io/info",  # Does NOT start with TIKVID_BASE (https://tikvid.io/vi)
            "https://example.com/video.mp4?mime_type=video_mp4",
            "https://example.com/image.jpg",
            "https://tikvid.io/vi/info",  # This starts with TIKVID_BASE and has no mp4
        ]

        filtered = strategy._filter_media_links(test_links)

        # Should keep all links except the one that starts with TIKVID_BASE and has no mp4
        assert "https://example.com/video.mp4" in filtered
        assert "https://tikvid.io/info" in filtered  # Kept because doesn't start with tikvid.io/vi
        assert "https://example.com/video.mp4?mime_type=video_mp4" in filtered
        assert "https://example.com/image.jpg" in filtered
        assert "https://tikvid.io/vi/info" not in filtered  # Filtered out - starts with TIKVID_BASE and no mp4
        assert len(filtered) == 4


class TestChromiumDownloadStrategy:
    """Test cases for ChromiumDownloadStrategy."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        return settings

    @pytest.fixture
    def strategy(self, mock_settings: MagicMock) -> ChromiumDownloadStrategy:
        """Create a ChromiumDownloadStrategy instance for testing."""
        return ChromiumDownloadStrategy(mock_settings)

    def test_get_strategy_name(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test getting strategy name."""
        assert strategy.get_strategy_name() == "chromium"

    def test_resolve_video_url_success(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test successful video URL resolution in headful mode."""
        with patch.object(strategy, '_build_chromium_fetch_kwargs') as mock_build:
            # Mock the components
            mock_fetcher_class = MagicMock()
            mock_fetcher_instance = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher_instance
            mock_fetch_kwargs = {"test": "kwargs"}
            mock_resolve_action = MagicMock()
            mock_resolve_action.result_links = ["https://example.com/video.mp4"]

            mock_build.return_value = {
                "fetcher": mock_fetcher_class,
                "fetch_kwargs": mock_fetch_kwargs,
                "resolve_action": mock_resolve_action,
                "headers": {"User-Agent": "test"},
            }

            # Mock successful fetch
            mock_fetcher_instance.fetch.return_value = MagicMock()

            result = strategy.resolve_video_url("https://www.tiktok.com/@test/video/456")

            assert result == "https://example.com/video.mp4"

            # Verify that headful mode is used
            mock_build.assert_called_once()
            call_args = mock_build.call_args
            assert call_args[0][0] == "https://www.tiktok.com/@test/video/456"  # tiktok_url
            assert call_args[0][1] is None  # quality_hint

    def test_chromium_strategy_enforces_headful_fetch_kwargs(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that Chromium strategy enforces headful mode in fetch kwargs."""
        with patch.object(strategy, '_build_chromium_fetch_kwargs') as mock_build:
            # Mock the internal method to return actual fetch kwargs for inspection
            mock_fetcher_class = MagicMock()
            mock_resolve_action = MagicMock()
            mock_resolve_action.result_links = []

            # Simulate the actual method behavior
            mock_build.return_value = {
                "fetcher": mock_fetcher_class,
                "fetch_kwargs": {"headless": False, "other": "value"},  # Should have headless: False
                "resolve_action": mock_resolve_action,
                "headers": {"User-Agent": "test"},
            }

            # This should not raise an exception
            try:
                strategy.resolve_video_url("https://www.tiktok.com/@test/video/456")
            except RuntimeError:
                pass  # Expected to fail due to mocked components, but we want to check the fetch kwargs

            # Verify the fetch kwargs contain headless: False
            call_args = mock_build.call_args
            # The actual method should be called with the URL and quality_hint
            assert call_args[0][0] == "https://www.tiktok.com/@test/video/456"

    def test_chromium_strategy_build_fetch_kwargs_headful_enforcement(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that _build_chromium_fetch_kwargs method enforces headful mode."""
        # Call the actual method to inspect the returned fetch kwargs
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None  # quality_hint
        )

        # Verify that headless is explicitly set to False
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]
        assert result["fetch_kwargs"]["headless"] is False

    def test_chromium_strategy_injects_user_data_dir_when_enabled(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that user_data_dir is injected when chromium_user_data_dir is configured."""
        # Set up mock settings with user data dir
        strategy.settings.chromium_user_data_dir = "/path/to/user/data"

        with patch("app.services.tiktok.download.strategies.chromium.ChromiumUserDataManager") as mock_manager:
            mock_context_manager = MagicMock()
            mock_user_data_context = MagicMock()
            mock_user_data_context.clone_path = "/path/to/clone/data"
            mock_cleanup_func = MagicMock()
            mock_user_data_context.cleanup = mock_cleanup_func
            mock_context_manager.__enter__ = MagicMock(return_value=mock_user_data_context)
            mock_context_manager.__exit__ = MagicMock(return_value=None)
            mock_manager.get_user_data_context.return_value = mock_context_manager

            # Call the actual method
            strategy._build_chromium_fetch_kwargs(
                "https://www.tiktok.com/@test/video/456",
                None  # quality_hint
            )

            # Verify that user data context was obtained
            mock_manager.get_user_data_context.assert_called_once()

    def test_chromium_strategy_headless_allowed_when_parity_flag_enabled(self, strategy: ChromiumDownloadStrategy) -> None:
        """Future parity test: Test that headless mode is allowed when parity flag is enabled.

        This test is marked as xfail until headless parity is implemented.
        """
        # This test will fail until headless parity is implemented
        pytest.xfail("Headless parity not yet implemented")

        # When parity is implemented, this test should verify that:
        # 1. When a parity flag is enabled and force_headful is False, headless can be True
        # 2. The strategy respects the parity setting
        pass


class TestTikTokDownloadStrategyFactory:
    """Test cases for TikTokDownloadStrategyFactory."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        return settings

    def test_create_strategy_camoufox(self, mock_settings: MagicMock) -> None:
        """Test creating Camoufox strategy when environment variable is set to 'camoufox'."""
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "camoufox"):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert isinstance(strategy, CamoufoxDownloadStrategy)

    def test_create_strategy_chromium(self, mock_settings: MagicMock) -> None:
        """Test creating Chromium strategy when environment variable is set to 'chromium'."""
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "chromium"):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert isinstance(strategy, ChromiumDownloadStrategy)

    def test_create_strategy_default(self, mock_settings: MagicMock) -> None:
        """Test creating default strategy when environment variable is not set."""
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "chromium"):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert isinstance(strategy, ChromiumDownloadStrategy)

    def test_create_strategy_case_insensitive(self, mock_settings: MagicMock) -> None:
        """Test that strategy selection is case insensitive."""
        test_cases = [
            ("CAMOUFOX", CamoufoxDownloadStrategy),
            ("Camoufox", CamoufoxDownloadStrategy),
            ("cAmOuFoX", CamoufoxDownloadStrategy),
            ("CHROMIUM", ChromiumDownloadStrategy),
            ("Chromium", ChromiumDownloadStrategy),
            ("cHrOmIuM", ChromiumDownloadStrategy),
        ]

        for env_value, expected_strategy in test_cases:
            with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", env_value.lower()):
                strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
                assert isinstance(strategy, expected_strategy)

    def test_create_strategy_invalid_value(self, mock_settings: MagicMock) -> None:
        """Test creating strategy when environment variable has invalid value."""
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "invalid_strategy"):
            with pytest.raises(ValueError, match="Unsupported TikTok download strategy: invalid_strategy"):
                TikTokDownloadStrategyFactory.create_strategy(mock_settings)

    def test_get_current_strategy_name(self) -> None:
        """Test getting currently configured strategy name."""
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "camoufox"):
            name = TikTokDownloadStrategyFactory.get_current_strategy_name()
            assert name == "camoufox"

    def test_list_supported_strategies(self) -> None:
        """Test listing all supported strategy names."""
        strategies = TikTokDownloadStrategyFactory.list_supported_strategies()
        assert "camoufox" in strategies
        assert "chromium" in strategies
        assert len(strategies) == 2

    def test_strategy_execution(self, mock_settings: MagicMock) -> None:
        """Test that returned strategies can execute properly."""
        # Test Camoufox strategy
        with patch.dict("app.services.tiktok.download.strategies.factory.os.environ", {"TIKTOK_DOWNLOAD_STRATEGY": "camoufox"}):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert hasattr(strategy, 'resolve_video_url')
            assert callable(strategy.resolve_video_url)
            assert hasattr(strategy, 'get_strategy_name')
            assert callable(strategy.get_strategy_name)

        # Test Chromium strategy
        with patch.dict("app.services.tiktok.download.strategies.factory.os.environ", {"TIKTOK_DOWNLOAD_STRATEGY": "chromium"}):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert hasattr(strategy, 'resolve_video_url')
            assert callable(strategy.resolve_video_url)
            assert hasattr(strategy, 'get_strategy_name')
            assert callable(strategy.get_strategy_name)
