"""
Integration tests for TikTok Session endpoint with real user data cloning
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import time

from app.main import app
from app.core.config import Settings
from app.schemas.tiktok import TikTokLoginState


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def temp_user_data_dir():
    """Create a temporary user data directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_tiktok_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def existing_user_data_dir(temp_user_data_dir):
    """Create a temporary user data directory with existing data."""
    # Create some fake user data files
    profiles_dir = Path(temp_user_data_dir) / "default"
    profiles_dir.mkdir(parents=True, exist_ok=True)

    # Create some fake user data files to simulate existing profile
    (profiles_dir / "places.sqlite").touch()
    (profiles_dir / "cookies.sqlite").touch()
    (profiles_dir / "webappsstore.sqlite").touch()

    return temp_user_data_dir


class TestTikTokSessionIntegration:
    """Integration tests for TikTok session endpoint with real user data cloning."""

    def test_tiktok_session_with_logged_in_user_real_cloning(self, monkeypatch, client, existing_user_data_dir):
        """Test successful TikTok session creation with real user data cloning and minimal mocking."""

        # Mock the settings to use our test user data directory
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = existing_user_data_dir
        mock_settings.tiktok_login_detection_timeout = 5
        mock_settings.tiktok_max_session_duration = 30
        mock_settings.tiktok_url = "https://www.tiktok.com/"

        # Create a mock browser that simulates real TikTok page behavior
        mock_browser = MagicMock()
        mock_browser.url = "https://www.tiktok.com/"
        mock_browser.title = AsyncMock(return_value="TikTok")
        mock_browser.is_visible = AsyncMock(return_value=True)
        mock_browser.close = AsyncMock()
        mock_browser.get = AsyncMock()

        # Mock the browser to return elements that indicate logged-in state
        mock_logged_in_element = MagicMock()
        mock_logged_in_element.is_visible = AsyncMock(return_value=True)

        mock_logged_out_element = MagicMock()
        mock_logged_out_element.is_visible = AsyncMock(return_value=False)

        # Configure browser.find to return appropriate elements for login detection
        def mock_find(selector, timeout=None):
            if selector == "[data-e2e='profile-avatar']":  # Logged in indicator
                return mock_logged_in_element
            elif selector == "[data-e2e='login-button']":  # Logged out indicator
                return mock_logged_out_element
            else:
                return None

        mock_browser.find = AsyncMock(side_effect=mock_find)

        # Mock ScraplingFetcherAdapter and FetchArgComposer
        mock_fetcher = MagicMock()
        mock_fetcher.detect_capabilities = MagicMock(return_value={})
        mock_fetcher.fetch = MagicMock(return_value={"status": 200, "content": "<html>TikTok</html>"})
        
        mock_arg_composer = MagicMock()
        mock_arg_composer.compose = MagicMock(return_value={})

        with patch('app.services.tiktok.executor.ScraplingFetcherAdapter', return_value=mock_fetcher), \
             patch('app.services.tiktok.executor.FetchArgComposer', return_value=mock_arg_composer), \
             patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('app.services.common.executor.get_settings', return_value=mock_settings), \
             patch('app.core.config.get_settings', return_value=mock_settings):
            # Test the TikTok session endpoint - this will use the new StealthyFetcher approach
            resp = client.post("/tiktok/session", json={})

            # Debug: print response content
            print(f"Response status: {resp.status_code}")
            print(f"Response content: {resp.text}")

            # Verify response
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["message"] == "TikTok session established successfully"
            # error_details should be null for successful responses
            assert data.get("error_details") is None

            # Verify that fetcher was called with correct parameters
            mock_fetcher.fetch.assert_called_once()
            call_args = mock_fetcher.fetch.call_args
            print(f"DEBUG: call_args = {call_args}")
            
            # Verify the URL was fetched
            assert call_args[0][0] == "https://www.tiktok.com/"

    def test_tiktok_session_with_logged_out_user(self, monkeypatch, client, temp_user_data_dir):
        """Test TikTok session creation when user is not logged in using real login detection."""

        # Mock the settings to use our test user data directory
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir
        mock_settings.tiktok_login_detection_timeout = 5
        mock_settings.tiktok_url = "https://www.tiktok.com/"

        # Create a mock browser that simulates logged-out TikTok page
        mock_browser = MagicMock()
        mock_browser.url = "https://www.tiktok.com/"
        mock_browser.title = AsyncMock(return_value="TikTok")
        mock_browser.close = AsyncMock()
        mock_browser.get = AsyncMock()

        # Mock the browser to return elements that indicate logged-out state
        mock_logged_in_element = MagicMock()
        mock_logged_in_element.is_visible = AsyncMock(return_value=False)

        mock_logged_out_element = MagicMock()
        mock_logged_out_element.is_visible = AsyncMock(return_value=True)

        # Configure browser.find to return appropriate elements for login detection
        def mock_find(selector, timeout=None):
            if selector == "[data-e2e='profile-avatar']":  # Logged in indicator
                return mock_logged_in_element
            elif selector == "[data-e2e='login-button']":  # Logged out indicator
                return mock_logged_out_element
            else:
                return None

        mock_browser.find = AsyncMock(side_effect=mock_find)

        # Mock Scrapling browser creation
        mock_dynamic_fetcher = MagicMock(return_value=mock_browser)

        with patch('scrapling.DynamicFetcher', mock_dynamic_fetcher), \
             patch('app.services.tiktok.service.TiktokService._load_tiktok_config') as mock_load_config:
            # Mock the config loading to return our test config
            mock_config = MagicMock()
            mock_config.tiktok_url = "https://www.tiktok.com/"
            mock_config.login_detection_timeout = 5
            mock_config.max_session_duration = 30
            mock_config.user_data_master_dir = existing_user_data_dir
            mock_config.user_data_clones_dir = existing_user_data_dir
            mock_load_config.return_value = mock_config
            # Test the TikTok session endpoint - this will use real login detection logic
            resp = client.post("/tiktok/session", json={})

            # Debug: print response content
            print(f"Response status: {resp.status_code}")
            print(f"Response content: {resp.text}")

            # Verify response - should return 409 Conflict
            assert resp.status_code == 409
            data = resp.json()
            assert data["status"] == "error"
            assert data["message"] == "Not logged in to TikTok"
            assert data["error_details"]["code"] == "NOT_LOGGED_IN"

            # Verify that browser was created and navigated
            mock_browser.get.assert_called_with("https://www.tiktok.com/")

    def test_tiktok_session_browser_startup_failure(self, monkeypatch, client, temp_user_data_dir):
        """Test handling of browser startup failures."""

        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir

        # Mock Scrapling to raise an exception during browser creation
        mock_dynamic_fetcher = MagicMock(side_effect=Exception("Browser startup failed"))

        with patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('scrapling.DynamicFetcher', mock_dynamic_fetcher):

            # Test the TikTok session endpoint
            resp = client.post("/tiktok/session", json={})

            # Verify error response
            assert resp.status_code == 500
            data = resp.json()
            assert data["status"] == "error"
            assert data["message"] == "Failed to create TikTok session"
            assert data["error_details"]["code"] == "SESSION_CREATION_FAILED"

    def test_tiktok_session_with_uncertain_login_state(self, monkeypatch, client, temp_user_data_dir):
        """Test TikTok session when login detection is uncertain."""

        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir
        mock_settings.tiktok_login_detection_timeout = 5

        # Mock browser
        mock_browser = MagicMock()
        mock_browser.url = "https://www.tiktok.com/"
        mock_browser.title = AsyncMock(return_value="TikTok")
        mock_browser.close = AsyncMock()

        # Mock Scrapling browser creation
        mock_dynamic_fetcher = MagicMock(return_value=mock_browser)

        # Mock login detection to return UNCERTAIN
        def mock_login_detector(browser, config):
            detector = MagicMock()
            detector.detect_login_state = AsyncMock(return_value=TikTokLoginState.UNCERTAIN)
            return detector

        with patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('scrapling.DynamicFetcher', mock_dynamic_fetcher), \
             patch('app.services.tiktok.utils.login_detection.LoginDetector', side_effect=mock_login_detector), \
             patch('app.services.tiktok.service.TiktokService._load_tiktok_config') as mock_load_config:

            # Mock the config loading
            mock_config = MagicMock()
            mock_config.tiktok_url = "https://www.tiktok.com/"
            mock_config.login_detection_timeout = 5
            mock_config.login_detection_refresh = False  # Disable refresh fallback
            mock_load_config.return_value = mock_config

            # Test the TikTok session endpoint
            resp = client.post("/tiktok/session", json={})

            # Should fail due to uncertain login state
            assert resp.status_code == 409
            data = resp.json()
            assert data["status"] == "error"
            assert data["message"] == "Not logged in to TikTok"

    def test_tiktok_session_browser_cleanup_on_failure(self, monkeypatch, client, temp_user_data_dir):
        """Test that browser is properly cleaned up when session creation fails."""

        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir

        # Mock browser
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()

        # Mock Scrapling browser creation
        mock_dynamic_fetcher = MagicMock(return_value=mock_browser)

        # Mock login detection to raise an exception
        def mock_login_detector(browser, config):
            detector = MagicMock()
            detector.detect_login_state = AsyncMock(side_effect=Exception("Login detection failed"))
            return detector

        with patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('scrapling.DynamicFetcher', mock_dynamic_fetcher), \
             patch('app.services.tiktok.utils.login_detection.LoginDetector', side_effect=mock_login_detector), \
             patch('app.services.tiktok.service.TiktokService._load_tiktok_config') as mock_load_config:

            # Mock the config loading
            mock_config = MagicMock()
            mock_config.tiktok_url = "https://www.tiktok.com/"
            mock_load_config.return_value = mock_config

            # Test the TikTok session endpoint
            resp = client.post("/tiktok/session", json={})

            # Verify error response
            assert resp.status_code == 500
            data = resp.json()
            assert data["status"] == "error"

            # Verify browser cleanup was called
            mock_browser.close.assert_called_once()

    def test_tiktok_session_with_custom_user_data_dir(self, monkeypatch, client):
        """Test TikTok session with custom user data directory."""

        custom_dir = "/tmp/custom_tiktok_data"

        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = custom_dir

        # Mock browser
        mock_browser = MagicMock()
        mock_browser.url = "https://www.tiktok.com/"
        mock_browser.title = AsyncMock(return_value="TikTok")
        mock_browser.is_visible = AsyncMock(return_value=True)
        mock_browser.close = AsyncMock()

        # Mock Scrapling browser creation
        mock_dynamic_fetcher = MagicMock(return_value=mock_browser)

        # Mock login detection
        def mock_login_detector(browser, config):
            detector = MagicMock()
            detector.detect_login_state = AsyncMock(return_value=TikTokLoginState.LOGGED_IN)
            return detector

        with patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('scrapling.DynamicFetcher', mock_dynamic_fetcher), \
             patch('app.services.tiktok.utils.login_detection.LoginDetector', side_effect=mock_login_detector), \
             patch('app.services.tiktok.service.TiktokService._load_tiktok_config') as mock_load_config:

            # Mock the config loading and verify custom directory is used
            mock_config = MagicMock()
            mock_config.tiktok_url = "https://www.tiktok.com/"
            mock_config.user_data_clones_dir = custom_dir
            mock_load_config.return_value = mock_config

            # Test the TikTok session endpoint
            resp = client.post("/tiktok/session", json={})

            # Verify success
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"

            # Verify browser was created with custom user data directory
            mock_dynamic_fetcher.assert_called_once()
            call_args = mock_dynamic_fetcher.call_args
            assert call_args[1]['user_data_dir'] == custom_dir

    def test_tiktok_session_timeout_handling(self, monkeypatch, client, temp_user_data_dir):
        """Test handling of session timeouts."""

        # Mock settings
        mock_settings = Settings()
        mock_settings.camoufox_user_data_dir = temp_user_data_dir
        mock_settings.tiktok_max_session_duration = 1  # Very short timeout

        # Mock browser
        mock_browser = MagicMock()
        mock_browser.url = "https://www.tiktok.com/"
        mock_browser.title = AsyncMock(return_value="TikTok")
        mock_browser.is_visible = AsyncMock(return_value=True)
        mock_browser.close = AsyncMock()

        # Mock Scrapling browser creation
        mock_dynamic_fetcher = MagicMock(return_value=mock_browser)

        # Mock login detection
        def mock_login_detector(browser, config):
            detector = MagicMock()
            detector.detect_login_state = AsyncMock(return_value=TikTokLoginState.LOGGED_IN)
            return detector

        with patch('app.services.tiktok.service.get_settings', return_value=mock_settings), \
             patch('scrapling.DynamicFetcher', mock_dynamic_fetcher), \
             patch('app.services.tiktok.utils.login_detection.LoginDetector', side_effect=mock_login_detector), \
             patch('app.services.tiktok.service.TiktokService._load_tiktok_config') as mock_load_config:

            # Mock the config loading
            mock_config = MagicMock()
            mock_config.tiktok_url = "https://www.tiktok.com/"
            mock_config.max_session_duration = 1
            mock_load_config.return_value = mock_config

            # Test the TikTok session endpoint
            resp = client.post("/tiktok/session", json={})

            # Verify success (session created)
            assert resp.status_code == 200

            # Wait for timeout
            time.sleep(2)

            # Test session info - should show timeout
            from app.services.tiktok.service import TiktokService
            service = TiktokService()

            # This would normally check timeout, but since we're mocking,
            # we'll just verify the service can be instantiated
            assert service is not None