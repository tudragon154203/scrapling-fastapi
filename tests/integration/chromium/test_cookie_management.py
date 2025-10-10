"""Integration tests for Chromium cookie management functionality."""

import json
import time
from pathlib import Path

import pytest

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


class TestChromiumCookieManagement:
    """Test comprehensive cookie import/export functionality."""

    @pytest.fixture
    def temp_user_data_dir(self, tmp_path):
        """Create a temporary user data directory for testing."""
        return tmp_path / "chromium_cookies_test"

    @pytest.fixture
    def user_data_manager(self, temp_user_data_dir):
        """Create a ChromiumUserDataManager instance for testing."""
        return ChromiumUserDataManager(str(temp_user_data_dir))

    @pytest.fixture
    def sample_cookies(self):
        """Sample cookie data for testing."""
        return {
            "format": "json",
            "cookies": [
                {
                    "name": "session_token",
                    "value": "abc123xyz789",
                    "domain": ".tiktok.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                },
                {
                    "name": "user_preferences",
                    "value": json.dumps({"theme": "dark", "language": "en"}),
                    "domain": "www.tiktok.com",
                    "path": "/",
                    "expires": int(time.time()) + 86400 * 30,  # 30 days
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                },
                {
                    "name": "analytics_id",
                    "value": "ga_123456789",
                    "domain": ".tiktokcdn.com",
                    "path": "/analytics",
                    "expires": int(time.time()) + 86400 * 7,  # 7 days
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Strict"
                }
            ]
        }

    @pytest.fixture
    def storage_state_cookies(self):
        """Sample Playwright storage_state format cookies."""
        return {
            "cookies": [
                {
                    "name": "playwright_session",
                    "value": "pw_session_abc",
                    "domain": "tiktok.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                },
                {
                    "name": "csrf_token",
                    "value": "csrf_xyz123",
                    "domain": ".tiktok.com",
                    "path": "/api",
                    "expires": int(time.time()) + 3600,  # 1 hour
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Strict"
                }
            ],
            "origins": []
        }

    def test_export_empty_profile(self, user_data_manager):
        """Test exporting cookies from an empty profile."""
        # Initialize the master profile first to ensure it exists
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            # Just create the profile structure
            cleanup()

        result = user_data_manager.export_cookies()

        assert result is not None
        assert result["format"] == "json"
        assert result["cookies"] == []
        assert result["cookies_available"] is False
        assert "master_profile_path" in result

    def test_create_and_export_cookies(self, user_data_manager, sample_cookies):
        """Test creating cookies and then exporting them."""
        # Import sample cookies first
        success = user_data_manager.import_cookies(sample_cookies)
        assert success is True

        # Export cookies
        result = user_data_manager.export_cookies()

        assert result is not None
        assert result["format"] == "json"
        assert result["cookies_available"] is True
        assert len(result["cookies"]) == len(sample_cookies["cookies"])

        # Verify cookie data integrity
        exported_cookies = result["cookies"]
        for i, expected_cookie in enumerate(sample_cookies["cookies"]):
            exported_cookie = exported_cookies[i]
            assert exported_cookie["name"] == expected_cookie["name"]
            assert exported_cookie["value"] == expected_cookie["value"]
            assert exported_cookie["domain"] == expected_cookie["domain"]

    def test_export_storage_state_format(self, user_data_manager, sample_cookies):
        """Test exporting cookies in storage_state format."""
        # Import sample cookies
        success = user_data_manager.import_cookies(sample_cookies)
        assert success is True

        # Export in storage_state format
        result = user_data_manager.export_cookies("storage_state")

        assert result is not None
        assert "cookies" in result
        assert "origins" in result
        assert len(result["cookies"]) == len(sample_cookies["cookies"])

        # Verify format matches Playwright storage_state
        for cookie in result["cookies"]:
            assert "name" in cookie
            assert "value" in cookie
            assert "domain" in cookie
            assert "path" in cookie
            assert "expires" in cookie
            assert "httpOnly" in cookie
            assert "secure" in cookie
            assert "sameSite" in cookie

    def test_import_storage_state_format(self, user_data_manager, storage_state_cookies):
        """Test importing cookies in storage_state format."""
        # Initialize the master profile first
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        # Add format indicator for storage_state format
        formatted_cookies = storage_state_cookies.copy()
        formatted_cookies["format"] = "storage_state"

        success = user_data_manager.import_cookies(formatted_cookies)
        assert success is True

        # Verify cookies were imported
        result = user_data_manager.export_cookies()
        assert len(result["cookies"]) == len(storage_state_cookies["cookies"])

        # Check specific cookies
        cookie_names = [cookie["name"] for cookie in result["cookies"]]
        assert "playwright_session" in cookie_names
        assert "csrf_token" in cookie_names

    def test_cookie_persistence_across_sessions(self, user_data_manager, sample_cookies):
        """Test that cookies persist across manager sessions."""
        # Import cookies in first session
        success1 = user_data_manager.import_cookies(sample_cookies)
        assert success1 is True

        # Create new manager instance (simulating restart)
        new_manager = ChromiumUserDataManager(str(user_data_manager.base_path))

        # Export cookies in new session
        result = new_manager.export_cookies()
        assert len(result["cookies"]) == len(sample_cookies["cookies"])

        # Verify metadata was updated
        metadata = new_manager.get_metadata()
        assert metadata is not None
        assert "last_cookie_import" in metadata
        assert metadata.get("cookie_import_count") == len(sample_cookies["cookies"])

    def test_cookie_update_and_replacement(self, user_data_manager, sample_cookies):
        """Test updating existing cookies."""
        # Import initial cookies
        success1 = user_data_manager.import_cookies(sample_cookies)
        assert success1 is True

        # Modify one cookie and re-import
        updated_cookies = sample_cookies.copy()
        updated_cookies["cookies"][0]["value"] = "updated_session_token_456"

        success2 = user_data_manager.import_cookies(updated_cookies)
        assert success2 is True

        # Verify the cookie was updated
        result = user_data_manager.export_cookies()
        session_cookie = next(
            (c for c in result["cookies"] if c["name"] == "session_token"),
            None
        )
        assert session_cookie is not None
        assert session_cookie["value"] == "updated_session_token_456"

    def test_cookie_deletion_by_expiration(self, user_data_manager, sample_cookies):
        """Test handling of expired cookies."""
        # Create cookies with some expired ones
        expired_cookies = sample_cookies.copy()
        expired_time = int(time.time()) - 3600  # 1 hour ago

        expired_cookies["cookies"].append({
            "name": "expired_cookie",
            "value": "should_be_gone",
            "domain": ".tiktok.com",
            "path": "/",
            "expires": expired_time,
            "httpOnly": False,
            "secure": True,
            "sameSite": "None"
        })

        # Import cookies
        success = user_data_manager.import_cookies(expired_cookies)
        assert success is True

        # Export and verify expired cookie handling
        result = user_data_manager.export_cookies()

        # Should include all cookies (let the application decide on expired ones)
        cookie_names = [c["name"] for c in result["cookies"]]
        assert "expired_cookie" in cookie_names

        # Verify the expiration time is preserved
        expired_cookie = next(
            (c for c in result["cookies"] if c["name"] == "expired_cookie"),
            None
        )
        assert expired_cookie is not None
        assert expired_cookie["expires"] == expired_time

    def test_samesite_attribute_handling(self, user_data_manager):
        """Test proper handling of SameSite attribute."""
        cookies_with_samesite = {
            "format": "json",
            "cookies": [
                {
                    "name": "strict_cookie",
                    "value": "strict_value",
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Strict"
                },
                {
                    "name": "lax_cookie",
                    "value": "lax_value",
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax"
                },
                {
                    "name": "none_cookie",
                    "value": "none_value",
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None"
                }
            ]
        }

        # Import cookies
        success = user_data_manager.import_cookies(cookies_with_samesite)
        assert success is True

        # Export and verify SameSite handling
        result = user_data_manager.export_cookies()

        for cookie in result["cookies"]:
            original_cookie = next(
                c for c in cookies_with_samesite["cookies"] if c["name"] == cookie["name"]
            )
            assert cookie["sameSite"] == original_cookie["sameSite"]

    def test_domain_and_path_matching(self, user_data_manager):
        """Test proper handling of domain and path matching."""
        cookies_with_domains = {
            "format": "json",
            "cookies": [
                {
                    "name": "domain_cookie",
                    "value": "domain_value",
                    "domain": ".example.com",  # Subdomain cookie
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                },
                {
                    "name": "host_cookie",
                    "value": "host_value",
                    "domain": "example.com",  # Host-only cookie
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                },
                {
                    "name": "path_cookie",
                    "value": "path_value",
                    "domain": "example.com",
                    "path": "/specific/path",  # Specific path
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                }
            ]
        }

        # Import cookies
        success = user_data_manager.import_cookies(cookies_with_domains)
        assert success is True

        # Export and verify domain/path handling
        result = user_data_manager.export_cookies()

        for cookie in result["cookies"]:
            original_cookie = next(
                c for c in cookies_with_domains["cookies"] if c["name"] == cookie["name"]
            )
            assert cookie["domain"] == original_cookie["domain"]
            assert cookie["path"] == original_cookie["path"]

    def test_large_cookie_value_handling(self, user_data_manager):
        """Test handling of large cookie values."""
        large_value = "x" * 4000  # 4KB cookie value

        large_cookies = {
            "format": "json",
            "cookies": [
                {
                    "name": "large_cookie",
                    "value": large_value,
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                }
            ]
        }

        # Import large cookie
        success = user_data_manager.import_cookies(large_cookies)
        assert success is True

        # Export and verify large value preservation
        result = user_data_manager.export_cookies()
        assert len(result["cookies"]) == 1

        exported_cookie = result["cookies"][0]
        assert exported_cookie["value"] == large_value

    def test_special_characters_in_cookies(self, user_data_manager):
        """Test handling of special characters in cookie names and values."""
        special_cookies = {
            "format": "json",
            "cookies": [
                {
                    "name": "special_chars_!@#$%^&*()",
                    "value": "value_with_special_chars_🚀🌟✨",
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                },
                {
                    "name": "unicode_cookie_üñíçøðé",
                    "value": "unicode_value_测试中文",
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                },
                {
                    "name": "json_cookie",
                    "value": json.dumps({"key": "value", "nested": {"data": [1, 2, 3]}}),
                    "domain": "example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "None"
                }
            ]
        }

        # Import special character cookies
        success = user_data_manager.import_cookies(special_cookies)
        assert success is True

        # Export and verify character preservation
        result = user_data_manager.export_cookies()
        assert len(result["cookies"]) == 3

        for cookie in result["cookies"]:
            original_cookie = next(
                c for c in special_cookies["cookies"] if c["name"] == cookie["name"]
            )
            assert cookie["value"] == original_cookie["value"]
