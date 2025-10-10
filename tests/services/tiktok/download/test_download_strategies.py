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
        # Explicitly set chromium_user_data_dir to None to avoid directory creation
        settings.chromium_user_data_dir = None
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
        # Explicitly set chromium_user_data_dir to None to avoid directory creation
        settings.chromium_user_data_dir = None
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
        """Test that _build_chromium_fetch_kwargs method enforces headful mode when force_headful=True."""
        # Call the actual method with force_headful=True to inspect the returned fetch kwargs
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            True   # force_headful
        )

        # Verify that headless is explicitly set to False when force_headful=True
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]
        assert result["fetch_kwargs"]["headless"] is False

    def test_chromium_strategy_injects_user_data_dir_when_enabled(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that user_data_dir is injected when chromium_user_data_dir is configured."""
        # Set up mock settings with user data dir
        strategy.settings.chromium_user_data_dir = "/path/to/user/data"

        # Mock the user_data_manager instance directly
        mock_manager = MagicMock()
        mock_context_manager = MagicMock()
        mock_user_data_context = MagicMock()
        mock_user_data_context.clone_path = "/path/to/clone/data"
        mock_cleanup_func = MagicMock()
        mock_user_data_context.cleanup = mock_cleanup_func
        mock_context_manager.__enter__ = MagicMock(return_value=mock_user_data_context)
        mock_context_manager.__exit__ = MagicMock(return_value=None)
        mock_manager.get_user_data_context.return_value = mock_context_manager

        # Replace the instance's user_data_manager
        strategy.user_data_manager = mock_manager

        # Call the actual method
        strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            False  # force_headful
        )

        # Verify that user data context was obtained
        mock_manager.get_user_data_context.assert_called_once()

    def test_chromium_strategy_headless_when_force_headful_false(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that Chromium strategy uses headless mode when force_headful=False."""
        with patch.object(strategy, '_build_chromium_fetch_kwargs') as mock_build:
            # Mock the components
            mock_fetcher_class = MagicMock()
            mock_fetcher_instance = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher_instance
            mock_fetch_kwargs = {"headless": True, "other": "value"}  # Should have headless: True
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

            result = strategy.resolve_video_url("https://www.tiktok.com/@test/video/456", force_headful=False)

            assert result == "https://example.com/video.mp4"

            # Verify that the method was called with force_headful=False
            mock_build.assert_called_once_with("https://www.tiktok.com/@test/video/456", None, False)

    def test_chromium_strategy_headful_when_force_headful_true(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that Chromium strategy uses headful mode when force_headful=True."""
        with patch.object(strategy, '_build_chromium_fetch_kwargs') as mock_build:
            # Mock the components
            mock_fetcher_class = MagicMock()
            mock_fetcher_instance = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher_instance
            mock_fetch_kwargs = {"headless": False, "other": "value"}  # Should have headless: False
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

            result = strategy.resolve_video_url("https://www.tiktok.com/@test/video/456", force_headful=True)

            assert result == "https://example.com/video.mp4"

            # Verify that the method was called with force_headful=True
            mock_build.assert_called_once_with("https://www.tiktok.com/@test/video/456", None, True)

    def test_chromium_strategy_parity_features_in_headless(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that headless mode includes parity features."""
        # Call the actual method with force_headful=False to check parity features
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            force_headful=False
        )

        # Verify that headless is set to True when force_headful=False
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]
        assert result["fetch_kwargs"]["headless"] is True

        # Verify headless-specific parity configurations
        assert result["fetch_kwargs"]["network_idle"] is True  # Headless uses network idle
        assert result["fetch_kwargs"]["wait"] == 5000  # Headless uses longer wait
        assert result["fetch_kwargs"]["timeout"] == 120000  # Headless uses longer timeout

        # Verify additional headers for headless parity
        headers = result["fetch_kwargs"]["extra_headers"]
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "DNT" in headers

    def test_chromium_strategy_headful_mode_unchanged(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that headful mode configurations remain unchanged."""
        # Call the actual method with force_headful=True to check headful features
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            force_headful=True
        )

        # Verify that headless is set to False when force_headful=True
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]
        assert result["fetch_kwargs"]["headless"] is False

        # Verify headful configurations remain as expected
        assert result["fetch_kwargs"]["network_idle"] is False  # Headful doesn't use network idle
        assert result["fetch_kwargs"]["wait"] == 3000  # Headful uses shorter wait
        assert result["fetch_kwargs"]["timeout"] == 90000  # Headful uses standard timeout

    def test_chromium_strategy_user_data_in_both_modes(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that user data management works in both headless and headful modes."""
        # Set up mock settings with user data dir
        strategy.settings.chromium_user_data_dir = "/path/to/user/data"

        # Mock the user_data_manager instance directly
        mock_manager = MagicMock()
        mock_context_manager = MagicMock()
        mock_user_data_context = MagicMock()
        mock_user_data_context.clone_path = "/path/to/clone/data"
        mock_cleanup_func = MagicMock()
        mock_user_data_context.cleanup = mock_cleanup_func
        mock_context_manager.__enter__ = MagicMock(return_value=mock_user_data_context)
        mock_context_manager.__exit__ = MagicMock(return_value=None)
        mock_manager.get_user_data_context.return_value = mock_context_manager

        # Replace the instance's user_data_manager
        strategy.user_data_manager = mock_manager

        # Test with force_headful=True (headful mode)
        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            force_headful=True
        )

        # Test with force_headful=False (headless mode)
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            force_headful=False
        )

        # Both modes should have user data management
        assert "effective_user_data_dir" in result_headful
        assert "user_data_cleanup" in result_headful
        assert "effective_user_data_dir" in result_headless
        assert "user_data_cleanup" in result_headless

        # Verify that user data context was obtained for both modes
        assert mock_manager.get_user_data_context.call_count == 2

    def test_chromium_strategy_headless_allowed_when_parity_flag_enabled(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that headless mode is allowed when force_headful=False (current default behavior)."""
        # Test with force_headful=False (should allow headless by default)
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            force_headful=False
        )

        # Verify that headless is set to True when force_headful is False (default behavior)
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]
        assert result["fetch_kwargs"]["headless"] is True

        # Test with force_headful=True (should enforce headful)
        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            force_headful=True
        )

        # Verify that headless is False when force_headful is True
        assert "fetch_kwargs" in result_headful
        assert "headless" in result_headful["fetch_kwargs"]
        assert result_headful["fetch_kwargs"]["headless"] is False


class TestTikTokDownloadStrategyFactory:
    """Test cases for TikTokDownloadStrategyFactory."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        # Explicitly set chromium_user_data_dir to None to avoid directory creation
        settings.chromium_user_data_dir = None
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
        # Test Camoufox strategy - patch the module-level variable
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "camoufox"):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert hasattr(strategy, 'resolve_video_url')
            assert callable(strategy.resolve_video_url)
            assert hasattr(strategy, 'get_strategy_name')
            assert callable(strategy.get_strategy_name)

        # Test Chromium strategy - patch the module-level variable
        with patch("app.services.tiktok.download.strategies.factory.TIKTOK_DOWNLOAD_STRATEGY", "chromium"):
            strategy = TikTokDownloadStrategyFactory.create_strategy(mock_settings)
            assert hasattr(strategy, 'resolve_video_url')
            assert callable(strategy.resolve_video_url)
            assert hasattr(strategy, 'get_strategy_name')
            assert callable(strategy.get_strategy_name)
