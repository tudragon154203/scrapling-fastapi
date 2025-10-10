"""Integration tests for Chromium cookie management functionality."""

import json
import time

import pytest

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


class TestChromiumCookieManagement:
    """Test essential cookie import/export functionality."""

    @pytest.fixture
    def temp_user_data_dir(self, tmp_path):
        """Create a temporary user data directory for testing."""
        return tmp_path / "chromium_cookies_test"

    @pytest.fixture
    def user_data_manager(self, temp_user_data_dir):
        """Create a ChromiumUserDataManager instance for testing."""
        return ChromiumUserDataManager(str(temp_user_data_dir))

    def test_export_empty_profile(self, user_data_manager):
        """Test exporting cookies from an empty profile."""
        # Initialize the master profile
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        result = user_data_manager.export_cookies()

        assert result is not None
        assert result["format"] == "json"
        assert result["cookies"] == []
        assert result["cookies_available"] is False

    def test_export_formats(self, user_data_manager):
        """Test different export formats for cookies."""
        # Initialize master profile
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        # Test JSON export
        json_result = user_data_manager.export_cookies("json")
        assert json_result is not None
        assert json_result["format"] == "json"
        assert "cookies" in json_result

        # Test storage_state export
        storage_result = user_data_manager.export_cookies("storage_state")
        assert storage_result is not None
        assert "cookies" in storage_result
        assert "origins" in storage_result


    def test_metadata_operations(self, user_data_manager):
        """Test metadata read/write operations."""
        # Initialize master profile
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        # Test metadata update
        user_data_manager.update_metadata({
            "test_field": "test_value",
            "test_number": 123
        })

        # Test metadata read
        metadata = user_data_manager.get_metadata()
        assert metadata is not None
        assert metadata.get("test_field") == "test_value"
        assert metadata.get("test_number") == 123

    def test_profile_persistence(self, user_data_manager):
        """Test that profile data persists across manager instances."""
        # Initialize master profile and set metadata
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        user_data_manager.update_metadata({
            "test_persistence": True,
            "test_timestamp": time.time()
        })

        # Create new manager instance
        new_manager = ChromiumUserDataManager(str(user_data_manager.base_path))

        # Verify metadata persists
        metadata = new_manager.get_metadata()
        assert metadata is not None
        assert metadata.get("test_persistence") is True
        assert "test_timestamp" in metadata