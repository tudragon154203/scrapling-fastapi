"""Tests for headless parity features in TikTok download strategy."""

import pytest
from unittest.mock import MagicMock, patch
from app.services.tiktok.download.strategies.chromium import ChromiumDownloadStrategy

pytestmark = [pytest.mark.unit]


class TestHeadlessParity:
    """Test cases for headless parity features."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings for testing."""
        settings = MagicMock()
        return settings

    @pytest.fixture
    def strategy(self, mock_settings: MagicMock) -> ChromiumDownloadStrategy:
        """Create a ChromiumDownloadStrategy instance for testing."""
        return ChromiumDownloadStrategy(mock_settings)

    def test_navigation_parity_headless_vs_headful(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test navigation parity between headless and headful modes."""
        # Test that both modes have proper navigation configurations
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            False  # force_headful
        )

        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Both modes should have valid navigation configurations
        assert result_headless["fetch_kwargs"]["headless"] == True
        assert result_headful["fetch_kwargs"]["headless"] == False

        # Headless mode should have enhanced waiting for navigation parity
        assert result_headless["fetch_kwargs"]["network_idle"] == True
        assert result_headless["fetch_kwargs"]["wait"] == 5000

        # Headful mode maintains original timing
        assert result_headful["fetch_kwargs"]["network_idle"] == False
        assert result_headful["fetch_kwargs"]["wait"] == 3000

    def test_form_interaction_parity(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test form interaction parity between headless and headful modes."""
        # Test that both modes have proper configurations for form interaction
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            False  # force_headful
        )

        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Headless mode should have enhanced headers for form interactions
        assert "Accept" in result_headless["fetch_kwargs"]["extra_headers"]
        assert "Accept-Language" in result_headless["fetch_kwargs"]["extra_headers"]

        # Headful mode has basic headers (User-Agent is always there)
        assert "User-Agent" in result_headful["fetch_kwargs"]["extra_headers"]
        # Additional headers are only added in headless mode for parity

        # Headless mode has enhanced automation support
        assert result_headless["fetch_kwargs"]["headless"] == True
        assert result_headful["fetch_kwargs"]["headless"] == False

    def test_click_interaction_parity(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test click interaction parity between headless and headful modes."""
        # Test that both modes have proper timeouts for click interactions
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            False  # force_headful
        )

        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Headless mode should have longer timeout for click reliability
        assert result_headless["fetch_kwargs"]["timeout"] == 120000
        assert result_headless["fetch_kwargs"]["headless"] == True

        # Headful mode maintains standard timeout
        assert result_headful["fetch_kwargs"]["timeout"] == 90000
        assert result_headful["fetch_kwargs"]["headless"] == False

    def test_waiting_strategy_parity(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test waiting strategy parity between headless and headful modes."""
        # Test that both modes have appropriate waiting strategies
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            False  # force_headful
        )

        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Headless mode uses network idle detection and longer waits
        assert result_headless["fetch_kwargs"]["network_idle"] == True
        assert result_headless["fetch_kwargs"]["wait"] == 5000
        assert result_headless["fetch_kwargs"]["timeout"] == 120000

        # Headful mode uses faster waiting strategy
        assert result_headful["fetch_kwargs"]["network_idle"] == False
        assert result_headful["fetch_kwargs"]["wait"] == 3000
        assert result_headful["fetch_kwargs"]["timeout"] == 90000

    def test_content_extraction_parity(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test content extraction parity between headless and headful modes."""
        # Test that both modes have proper configurations for content extraction
        result_headless = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            False  # force_headful
        )

        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Both modes should have basic headers that support content extraction
        assert "User-Agent" in result_headless["fetch_kwargs"]["extra_headers"]
        assert "User-Agent" in result_headful["fetch_kwargs"]["extra_headers"]

        # Headless mode has enhanced headers for better content extraction
        assert "Accept-Encoding" in result_headless["fetch_kwargs"]["extra_headers"]
        assert "Accept" in result_headless["fetch_kwargs"]["extra_headers"]

        # Both modes should have proper timeouts for content extraction
        assert result_headless["fetch_kwargs"]["timeout"] == 120000
        assert result_headful["fetch_kwargs"]["timeout"] == 90000

    def test_headless_parity_flag_structure(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that the structure for headless parity flag is in place."""
        # Call the method with force_headful=False
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            False  # force_headful
        )

        # Verify the structure is in place
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]

        # Currently should be False until parity is implemented
        # This verifies the conditional logic structure exists
        assert isinstance(result["fetch_kwargs"]["headless"], bool)

    def test_force_headful_true_ignores_parity(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that force_headful=True always uses headful mode regardless of parity flag."""
        # Mock the _build_chromium_fetch_kwargs method
        with patch.object(strategy, '_build_chromium_fetch_kwargs') as mock_build:
            # Mock the components to prevent actual network calls
            mock_fetcher_class = MagicMock()
            mock_fetcher_instance = MagicMock()
            mock_fetcher_class.return_value = mock_fetcher_instance
            mock_fetch_kwargs = {"headless": False, "other": "value"}
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

            # Call with force_headful=True
            strategy.resolve_video_url("https://www.tiktok.com/@test/video/456", force_headful=True)

            # Verify the call
            mock_build.assert_called_once_with("https://www.tiktok.com/@test/video/456", None, True)

    def test_parity_flag_placeholder_exists(self, strategy: ChromiumDownloadStrategy) -> None:
        """Test that the parity flag placeholder exists in the code."""
        # This test verifies that the structure for future parity implementation exists
        # The actual parity flag is hardcoded to False for now

        # Call the method and inspect the returned structure
        result = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,  # quality_hint
            False  # force_headful
        )

        # The structure should support future parity implementation
        assert "fetch_kwargs" in result
        assert "headless" in result["fetch_kwargs"]

        # Parity is now implemented! Test both modes
        result_headful = strategy._build_chromium_fetch_kwargs(
            "https://www.tiktok.com/@test/video/456",
            None,
            True  # force_headful
        )

        # Headless mode should be True when force_headful=False
        assert result["fetch_kwargs"]["headless"] == True
        # Headful mode should be False when force_headful=True
        assert result_headful["fetch_kwargs"]["headless"] == False

        # Verify parity features are applied in headless mode
        assert result["fetch_kwargs"]["network_idle"] == True
        assert result["fetch_kwargs"]["wait"] == 5000
        assert result["fetch_kwargs"]["timeout"] == 120000