"""
Comprehensive tests for TikTok login detection to achieve 80%+ coverage.
"""

from unittest.mock import MagicMock

import pytest

from app.schemas.tiktok.session import TikTokLoginState, TikTokSessionConfig
from app.services.tiktok.utils.login_detection import LoginDetector, LoginDetectionMethod


@pytest.fixture
def mock_config():
    """Mock TikTok session config."""
    return TikTokSessionConfig(
        user_data_master_dir="/tmp/master",
        user_data_clones_dir="/tmp/clones",
        write_mode_enabled=False,
        acquire_lock_timeout=30,
        login_detection_timeout=30,
        max_session_duration=3600,
        tiktok_url="https://www.tiktok.com",
        headless=True,
        selectors={"logged_in": ".profile-avatar", "logged_out": ".login-button"},
        api_endpoints={"/api/user/profile", "/api/auth/status"},
        login_detection_refresh=True,
    )


@pytest.fixture
def mock_browser():
    """Mock browser."""
    browser = MagicMock()
    return browser


@pytest.fixture
def login_detector(mock_browser, mock_config):
    """Login detector fixture."""
    return LoginDetector(mock_browser, mock_config)


class TestLoginDetectionMethod:
    """Test LoginDetectionMethod enum."""

    def test_login_detection_method_values(self):
        """Test LoginDetectionMethod enum values."""
        assert LoginDetectionMethod.DOM_ELEMENT == "dom_element"
        assert LoginDetectionMethod.API_REQUEST == "api_request"
        assert LoginDetectionMethod.FALLBACK_REFRESH == "fallback_refresh"
        assert LoginDetectionMethod.COMBO == "combo"


class TestLoginDetectorInitialization:
    """Test LoginDetector initialization."""

    def test_login_detector_init(self, mock_browser, mock_config):
        """Test LoginDetector initialization."""
        detector = LoginDetector(mock_browser, mock_config)

        assert detector.browser is mock_browser
        assert detector.config is mock_config
        assert detector.selectors is mock_config.selectors
        assert detector.api_endpoints is mock_config.api_endpoints


class TestLoginDetectorStateDetection:
    """Test login state detection methods."""

    @pytest.mark.asyncio
    async def test_detect_login_state_logged_in(self, login_detector, mock_browser):
        """Test detection when logged in."""
        # Setup browser with logged-in HTML content
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
                <button class="sign-out">Sign Out</button>
                <div class="account">Account Settings</div>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.LOGGED_IN

    @pytest.mark.asyncio
    async def test_detect_login_state_logged_out(self, login_detector, mock_browser):
        """Test detection when logged out."""
        # Setup browser with logged-out HTML content
        mock_browser.html_content = """
        <html>
            <body>
                <button class="login-button">Login</button>
                <a class="sign-in">Sign In</a>
                <button class="register">Register</button>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.LOGGED_OUT

    @pytest.mark.asyncio
    async def test_detect_login_state_uncertain_equal_matches(self, login_detector, mock_browser):
        """Test detection when indicators are balanced."""
        # Setup browser with mixed HTML content
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
                <button class="login-button">Login</button>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_uncertain_no_html(self, login_detector, mock_browser):
        """Test detection when no HTML content available."""
        # Setup browser without HTML content
        delattr(mock_browser, 'html_content')

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_uncertain_empty_html(self, login_detector, mock_browser):
        """Test detection when HTML content is empty."""
        # Setup browser with empty HTML content
        mock_browser.html_content = ""

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_exception_handling(self, login_detector, mock_browser):
        """Test detection with exception during processing."""
        # Setup browser to raise exception when accessing html_content
        type(mock_browser).html_content = property(
            lambda self: exec('raise Exception("HTML access failed")')
        )

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_case_insensitive(self, login_detector, mock_browser):
        """Test detection is case insensitive."""
        # Setup browser with mixed case HTML content
        mock_browser.html_content = """
        <html>
            <body>
                <div class="PROFILE-AVATAR">User Avatar</div>
                <button class="SIGN-OUT">Sign Out</button>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.LOGGED_IN

    @pytest.mark.asyncio
    async def test_detect_login_state_multiple_indicators(self, login_detector, mock_browser):
        """Test detection with multiple indicators."""
        # Setup browser with many logged-in indicators
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
                <div class="user-avatar">Another Avatar</div>
                <button class="sign-out">Sign Out</button>
                <div class="account">Account</div>
                <div class="notification">Notifications</div>
                <div class="message">Messages</div>
                <div class="inbox">Inbox</div>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.LOGGED_IN

    @pytest.mark.asyncio
    async def test_detect_login_state_custom_timeout(self, login_detector, mock_browser):
        """Test detection with custom timeout."""
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state(timeout=15)

        assert result == TikTokLoginState.LOGGED_IN


class TestLoginDetectorDetectionMethods:
    """Test individual detection methods."""

    @pytest.mark.asyncio
    async def test_try_combo_detection(self, login_detector, mock_browser):
        """Test combo detection method."""
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
            </body>
        </html>
        """

        result = await login_detector._try_combo_detection(10)

        assert result == TikTokLoginState.LOGGED_IN

    @pytest.mark.asyncio
    async def test_detect_dom_elements(self, login_detector, mock_browser):
        """Test DOM elements detection method."""
        mock_browser.html_content = """
        <html>
            <body>
                <button class="login-button">Login</button>
            </body>
        </html>
        """

        result = await login_detector._detect_dom_elements(10)

        assert result == TikTokLoginState.LOGGED_OUT

    @pytest.mark.asyncio
    async def test_detect_api_requests(self, login_detector):
        """Test API requests detection method (not available)."""
        result = await login_detector._detect_api_requests(10)

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_try_fallback_refresh(self, login_detector):
        """Test fallback refresh method (not available)."""
        result = await login_detector._try_fallback_refresh(10)

        assert result == TikTokLoginState.UNCERTAIN


class TestLoginDetectorConfiguration:
    """Test detector configuration and validation methods."""

    @pytest.mark.asyncio
    async def test_get_detection_details(self, login_detector):
        """Test getting detection details."""
        # Setup browser
        login_detector.browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
            </body>
        </html>
        """

        result = await login_detector.get_detection_details()

        assert "selectors_used" in result
        assert "api_endpoints_checked" in result
        assert "login_detection_enabled" in result
        assert "detection_timeout" in result
        assert "detected_state" in result

        assert result["selectors_used"] is login_detector.selectors
        assert result["api_endpoints_checked"] is login_detector.api_endpoints
        assert result["login_detection_enabled"] is True
        assert result["detection_timeout"] == 30
        assert result["detected_state"] == "LOGGED_IN"

    @pytest.mark.asyncio
    async def test_get_detection_details_uncertain(self, login_detector):
        """Test getting detection details when uncertain."""
        login_detector.browser.html_content = ""

        result = await login_detector.get_detection_details()

        assert result["detected_state"] == "UNCERTAIN"

    @pytest.mark.asyncio
    async def test_update_selectors(self, login_detector):
        """Test updating selectors."""
        new_selectors = {"new_selector": ".new-element"}
        original_selectors = login_detector.selectors.copy()

        await login_detector.update_selectors(new_selectors)

        assert login_detector.selectors != original_selectors
        assert login_detector.selectors["new_selector"] == ".new-element"

    @pytest.mark.asyncio
    async def test_validate_selectors_all_valid(self, login_detector):
        """Test selector validation when all are valid."""
        login_detector.selectors = {
            "logged_in": ".profile-avatar",
            "logged_out": ".login-button",
            "uncertain": ".uncertain-element"
        }

        result = await login_detector.validate_selectors()

        assert result["logged_in"] is True
        assert result["logged_out"] is True
        assert result["uncertain"] is True

    @pytest.mark.asyncio
    async def test_validate_selectors_missing_values(self, login_detector):
        """Test selector validation with missing values."""
        login_detector.selectors = {
            "logged_in": ".profile-avatar",
            "logged_out": "",  # Empty
            # "uncertain" missing
        }

        result = await login_detector.validate_selectors()

        assert result["logged_in"] is True
        assert result["logged_out"] is False
        assert result["uncertain"] is False

    @pytest.mark.asyncio
    async def test_validate_selectors_none_values(self, login_detector):
        """Test selector validation with None values."""
        login_detector.selectors = {
            "logged_in": None,
            "logged_out": ".login-button",
            "uncertain": ""
        }

        result = await login_detector.validate_selectors()

        assert result["logged_in"] is False
        assert result["logged_out"] is True
        assert result["uncertain"] is False

    @pytest.mark.asyncio
    async def test_test_selector_exists(self, login_detector):
        """Test testing an existing selector."""
        login_detector.selectors = {"test_selector": ".test-element"}

        result = await login_detector.test_selector("test_selector")

        assert result is True

    @pytest.mark.asyncio
    async def test_test_selector_missing(self, login_detector):
        """Test testing a missing selector."""
        result = await login_detector.test_selector("missing_selector")

        assert result is False

    @pytest.mark.asyncio
    async def test_test_selector_empty(self, login_detector):
        """Test testing an empty selector."""
        login_detector.selectors = {"empty_selector": ""}

        result = await login_detector.test_selector("empty_selector")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_login_state_details(self, login_detector, mock_browser):
        """Test getting comprehensive login state details."""
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
            </body>
        </html>
        """
        mock_browser.url = "https://www.tiktok.com"

        result = await login_detector.get_login_state_details()

        assert "dom_detection" in result
        assert "api_detection" in result
        assert "browser_url" in result
        assert "page_title" in result
        assert "detection_method" in result
        assert "html_available" in result

        assert result["dom_detection"] == TikTokLoginState.LOGGED_IN
        assert result["api_detection"] == TikTokLoginState.UNCERTAIN
        assert result["browser_url"] == "https://www.tiktok.com"
        assert result["page_title"] is None
        assert result["detection_method"] == "html_content_analysis"
        assert result["html_available"] is True

    @pytest.mark.asyncio
    async def test_get_login_state_details_no_html(self, login_detector, mock_browser):
        """Test login state details when no HTML available."""
        delattr(mock_browser, 'html_content')
        mock_browser.url = "https://www.tiktok.com"

        result = await login_detector.get_login_state_details()

        assert result["dom_detection"] == TikTokLoginState.UNCERTAIN
        assert result["html_available"] is False

    @pytest.mark.asyncio
    async def test_get_login_state_details_no_url(self, login_detector, mock_browser):
        """Test login state details when no URL available."""
        mock_browser.html_content = "<html><body>Test</body></html>"
        delattr(mock_browser, 'url')

        result = await login_detector.get_login_state_details()

        assert result["browser_url"] is None


class TestLoginDetectorEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_detect_login_state_html_content_attribute_error(self, login_detector, mock_browser):
        """Test detection when html_content access raises AttributeError."""
        # Setup browser to raise AttributeError
        def raise_error():
            raise AttributeError("html_content not found")

        type(mock_browser).html_content = property(lambda self: raise_error())

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_with_none_html_content(self, login_detector, mock_browser):
        """Test detection when html_content is None."""
        mock_browser.html_content = None

        result = await login_detector.detect_login_state()

        assert result == TikTokLoginState.UNCERTAIN

    @pytest.mark.asyncio
    async def test_detect_login_state_regex_error_handling(self, login_detector, mock_browser):
        """Test detection handles regex errors gracefully."""
        # This would test if any regex pattern could fail, but since we use
        # simple patterns this is unlikely to fail in practice
        mock_browser.html_content = "Normal content"

        result = await login_detector.detect_login_state()

        # Should not raise exception
        assert result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]

    @pytest.mark.asyncio
    async def test_detector_without_config_attributes(self, mock_browser):
        """Test detector with minimal config."""
        minimal_config = TikTokSessionConfig(
            user_data_master_dir="/tmp/master",
            user_data_clones_dir="/tmp/clones",
            write_mode_enabled=False,
            acquire_lock_timeout=30,
            login_detection_timeout=30,
            max_session_duration=3600,
            tiktok_url="https://www.tiktok.com",
            headless=True,
            # No selectors or api_endpoints
        )

        detector = LoginDetector(mock_browser, minimal_config)

        # Should work with empty selectors/endpoints
        result = await detector.get_detection_details()
        assert result["selectors_used"] == {}
        assert result["api_endpoints_checked"] == {}

    @pytest.mark.asyncio
    async def test_login_state_value_attribute(self, login_detector, mock_browser):
        """Test login state value attribute handling."""
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">User Avatar</div>
            </body>
        </html>
        """

        # Test with enum that has value attribute
        result = await login_detector.get_detection_details()
        assert result["detected_state"] == "LOGGED_IN"

    @pytest.mark.asyncio
    async def test_large_html_content_performance(self, login_detector, mock_browser):
        """Test detection performance with large HTML content."""
        # Create large HTML content
        large_html = "<html><body>" + "Content " * 10000 + "<div class='profile-avatar'>Avatar</div></body></html>"
        mock_browser.html_content = large_html

        # Should complete without timeout issues
        result = await login_detector.detect_login_state()
        assert result == TikTokLoginState.LOGGED_IN

    @pytest.mark.asyncio
    async def test_unicode_html_content(self, login_detector, mock_browser):
        """Test detection with Unicode HTML content."""
        mock_browser.html_content = """
        <html>
            <body>
                <div class="profile-avatar">👤 User Avatar</div>
                <div class="account">Account 📊</div>
            </body>
        </html>
        """

        result = await login_detector.detect_login_state()
        assert result == TikTokLoginState.LOGGED_IN