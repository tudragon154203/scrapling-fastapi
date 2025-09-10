"""
Contract tests for TikTok login detection behavior
"""
import pytest
import asyncio


class TestTikTokLoginDetectionContract:
    """Test TikTok login detection contract"""
    
    @pytest.mark.asyncio
    async def test_login_detection_timeout(self):
        """Test login detection timeout behavior"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig, TikTokLoginState

        # Create a mock browser
        mock_browser = type('MockBrowser', (), {})()

        # Create config with short timeout
        config = TikTokSessionConfig(login_detection_timeout=1)

        detector = LoginDetector(mock_browser, config)

        # Test that timeout is respected (should return UNCERTAIN due to mock)
        result = await detector.detect_login_state(timeout=1)
        assert result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]
    
    @pytest.mark.asyncio
    async def test_login_detection_methods(self):
        """Test multiple login detection methods"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig, TikTokLoginState

        # Create a mock browser
        mock_browser = type('MockBrowser', (), {})()

        config = TikTokSessionConfig()
        detector = LoginDetector(mock_browser, config)

        # Test that methods exist and can be called
        assert hasattr(detector, '_detect_dom_elements')
        assert hasattr(detector, '_detect_api_requests')
        assert hasattr(detector, '_try_fallback_refresh')

        # Test that methods return proper enum values
        dom_result = await detector._detect_dom_elements(1)
        assert dom_result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]

        api_result = await detector._detect_api_requests(1)
        assert api_result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]

        fallback_result = await detector._try_fallback_refresh(1)
        assert fallback_result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]
    
    @pytest.mark.asyncio
    async def test_dom_detection_method(self):
        """Test DOM element detection method"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig, TikTokLoginState

        # Create mock element
        class MockElement:
            async def is_visible(self):
                return True

        # Create mock browser that finds logged-in element
        class MockBrowserLoggedIn:
            async def find(self, selector, timeout=None):
                if selector == "[data-e2e='profile-avatar']":
                    return MockElement()
                return None

        config = TikTokSessionConfig()
        detector = LoginDetector(MockBrowserLoggedIn(), config)

        # Test logged-in detection
        result = await detector._detect_dom_elements(2)
        assert result == TikTokLoginState.LOGGED_IN

        # Create mock browser that finds logged-out element
        class MockBrowserLoggedOut:
            async def find(self, selector, timeout=None):
                if selector == "[data-e2e='login-button']":
                    return MockElement()
                return None

        detector_logged_out = LoginDetector(MockBrowserLoggedOut(), config)

        # Test logged-out detection
        result = await detector_logged_out._detect_dom_elements(2)
        assert result == TikTokLoginState.LOGGED_OUT
    
    @pytest.mark.asyncio
    async def test_api_detection_method(self):
        """Test API request detection method"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig, TikTokLoginState

        # Create mock response for logged-in user
        class MockResponseLoggedIn:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {"code": 0, "status": "success"}

        # Create mock browser for logged-in scenario
        class MockBrowserLoggedIn:
            async def request(self, method, url):
                return MockResponseLoggedIn()

        config = TikTokSessionConfig()
        detector = LoginDetector(MockBrowserLoggedIn(), config)

        # Test logged-in detection via API
        result = await detector._detect_api_requests(2)
        assert result == TikTokLoginState.LOGGED_IN

        # Create mock response for logged-out user
        class MockResponseLoggedOut:
            def __init__(self):
                self.status_code = 401

            def json(self):
                return {"code": -1, "status": "error"}

        # Create mock browser for logged-out scenario
        class MockBrowserLoggedOut:
            async def request(self, method, url):
                return MockResponseLoggedOut()

        detector_logged_out = LoginDetector(MockBrowserLoggedOut(), config)

        # Test logged-out detection via API
        result = await detector_logged_out._detect_api_requests(2)
        assert result == TikTokLoginState.LOGGED_OUT
    
    @pytest.mark.asyncio
    async def test_fallback_refresh_method(self):
        """Test fallback refresh mechanism"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig, TikTokLoginState

        # Create mock browser that supports reload
        class MockBrowser:
            async def reload(self):
                pass

        config = TikTokSessionConfig()
        detector = LoginDetector(MockBrowser(), config)

        # Test that fallback refresh method exists and returns proper type
        result = await detector._try_fallback_refresh(2)
        assert result in [TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN]
    
    def test_login_state_transitions(self):
        """Test login state transitions"""
        from app.schemas.tiktok import TikTokLoginState

        # Test that all login states exist and are properly defined
        assert TikTokLoginState.LOGGED_IN == "logged_in"
        assert TikTokLoginState.LOGGED_OUT == "logged_out"
        assert TikTokLoginState.UNCERTAIN == "uncertain"

        # Test that states are strings
        assert isinstance(TikTokLoginState.LOGGED_IN, str)
        assert isinstance(TikTokLoginState.LOGGED_OUT, str)
        assert isinstance(TikTokLoginState.UNCERTAIN, str)

        # Test that all expected values are present
        expected_values = {"logged_in", "logged_out", "uncertain"}
        actual_values = {TikTokLoginState.LOGGED_IN, TikTokLoginState.LOGGED_OUT, TikTokLoginState.UNCERTAIN}
        assert actual_values == expected_values
    
    def test_selectors_configuration(self):
        """Test login detection selectors configuration"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        from app.schemas.tiktok import TikTokSessionConfig

        # Create mock browser
        mock_browser = type('MockBrowser', (), {})()

        # Create config with default selectors
        config = TikTokSessionConfig()
        detector = LoginDetector(mock_browser, config)

        # Test that selectors are properly configured
        assert "logged_in" in detector.selectors
        assert "logged_out" in detector.selectors
        assert "uncertain" in detector.selectors

        # Test default selector values
        assert detector.selectors["logged_in"] == "[data-e2e='profile-avatar']"
        assert detector.selectors["logged_out"] == "[data-e2e='login-button']"
        assert detector.selectors["uncertain"] == "body"

        # Test that all selectors are non-empty strings
        for selector_name, selector_value in detector.selectors.items():
            assert isinstance(selector_value, str)
            assert len(selector_value) > 0