import os
import sys
import tempfile
import pytest
import shutil
from unittest.mock import Mock, patch
from pathlib import Path

from app.services.crawler.options.user_data import user_data_context
from app.schemas.crawl import CrawlRequest
from app.services.crawler.options.camoufox import CamoufoxArgsBuilder


class TestUserDataContext:
    """Test suite for user_data_context functionality."""

    @pytest.fixture
    def temp_base_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock()
        settings.camoufox_user_data_dir = "/test/user_data_dir"
        settings.camoufox_window = None
        settings.camoufox_disable_coop = False
        settings.camoufox_locale = None
        settings.camoufox_virtual_display = None
        settings.camoufox_window = None
        return settings

    @pytest.fixture
    def mock_caps_with_user_data(self):
        """Create mock capabilities with user data support."""
        caps = Mock()
        caps.user_data_dir = True
        caps.profile_dir = False
        caps.profile_path = False
        caps.user_data = False
        return caps

    @pytest.fixture
    def mock_caps_without_user_data(self):
        """Create mock capabilities without user data support."""
        caps = Mock()
        caps.user_data_dir = False
        caps.profile_dir = False
        caps.profile_path = False
        caps.user_data = False
        return caps

    def test_user_data_context_invalid_mode(self, temp_base_dir):
        """Test that invalid user_data_mode raises ValueError."""
        with pytest.raises(ValueError, match="user_data_mode must be 'read' or 'write'"):
            with user_data_context(temp_base_dir, "invalid_mode"):
                pass

    def test_write_mode_creates_master_directory(self, temp_base_dir):
        """Test that write mode creates and uses master directory."""
        with user_data_context(temp_base_dir, "write") as (effective_dir, cleanup):
            expected_dir = os.path.join(temp_base_dir, "master")
            assert effective_dir == expected_dir
            assert os.path.exists(expected_dir)
            assert os.path.exists(os.path.join(temp_base_dir, "master.lock"))

        # Cleanup should clean up resources
        assert os.path.exists(os.path.join(temp_base_dir, "master.lock"))

    def test_read_mode_with_no_master(self, temp_base_dir):
        """Test that read mode creates empty clone when no master exists."""
        effective_dir = None
        cleanup_func = None
        
        with user_data_context(temp_base_dir, "read") as (dir_path, cleanup):
            effective_dir = dir_path
            cleanup_func = cleanup
            assert os.path.exists(effective_dir)
            assert "clones" in effective_dir

        # After cleanup, clone directory should be removed
        assert cleanup_func is not None
        cleanup_func()  # Manually call cleanup
        assert not os.path.exists(effective_dir)

    def test_read_mode_with_master(self, temp_base_dir):
        """Test that read mode clones from existing master."""
        # Create master with some content
        master_dir = os.path.join(temp_base_dir, "master")
        os.makedirs(master_dir)
        with open(os.path.join(master_dir, "test_file.txt"), "w") as f:
            f.write("test content")

        effective_dir = None
        cleanup_func = None
        
        with user_data_context(temp_base_dir, "read") as (dir_path, cleanup):
            effective_dir = dir_path
            cleanup_func = cleanup
            assert os.path.exists(effective_dir)
            assert "clones" in effective_dir
            assert os.path.exists(os.path.join(effective_dir, "test_file.txt"))

        # After cleanup, clone directory should be removed
        assert cleanup_func is not None
        cleanup_func()  # Manually call cleanup
        assert not os.path.exists(effective_dir)

    def test_request_validation_invalid_mode(self):
        """Test that request schema validation rejects invalid user_data_mode."""
        with pytest.raises(ValueError, match="user_data_mode must be either 'read' or 'write'"):
            CrawlRequest(
                url="https://example.com",
                force_user_data=True,
                user_data_mode="invalid_mode"
            )

    def test_request_validation_valid_modes(self):
        """Test that request schema validation accepts valid user_data_mode values."""
        # Test read mode
        request_read = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="read"
        )
        assert request_read.user_data_mode == "read"

        # Test write mode
        request_write = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="write"
        )
        assert request_write.user_data_mode == "write"

        # Test default (read)
        request_default = CrawlRequest(
            url="https://example.com",
            force_user_data=True
        )
        assert request_default.user_data_mode == "read"

    @pytest.mark.skipif(sys.platform == "win32", reason="fcntl not available on Windows")
    @patch('fcntl.flock')
    @patch('os.open')
    def test_write_mode_lock_timeout(self, mock_open, mock_fcntl, temp_base_dir):
        """Test that write mode handles lock acquisition timeout."""
        # Mock open to succeed
        mock_open.return_value = 1
        
        # Mock fcntl.flock to raise BlockingIOError
        mock_fcntl.side_effect = BlockingIOError("Resource temporarily unavailable")
        
        with pytest.raises(RuntimeError, match="Timeout waiting for exclusive user-data lock"):
            with user_data_context(temp_base_dir, "write"):
                pass

    def test_camoufox_builder_integration_with_force_user_data_true(
        self, mock_settings, mock_caps_with_user_data, temp_base_dir
    ):
        """Test CamoufoxArgsBuilder integration with force_user_data=True."""
        mock_settings.camoufox_user_data_dir = temp_base_dir
        
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="read"
        )
        
        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_with_user_data
        )
        
        # Should contain user_data_dir parameter
        assert "user_data_dir" in additional_args
        # In read mode, should use a clone directory
        assert "clones" in additional_args["user_data_dir"]
        assert additional_args["user_data_dir"].startswith(temp_base_dir)

    def test_camoufox_builder_integration_with_force_user_data_false(
        self, mock_settings, mock_caps_with_user_data
    ):
        """Test CamoufoxArgsBuilder integration with force_user_data=False."""
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=False,
            user_data_mode="read"
        )
        
        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_with_user_data
        )
        
        # Should not contain user data parameters
        assert "user_data_dir" not in additional_args

    def test_camoufox_builder_integration_without_capabilities(
        self, mock_settings, mock_caps_without_user_data, temp_base_dir
    ):
        """Test CamoufoxArgsBuilder integration without user data capabilities."""
        mock_settings.camoufox_user_data_dir = temp_base_dir
        
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="read"
        )
        
        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_without_user_data
        )
        
        # Should not contain user data parameters when not supported
        assert "user_data_dir" not in additional_args

    def test_camoufox_builder_integration_no_settings(self, mock_caps_with_user_data):
        """Test CamoufoxArgsBuilder integration without user data settings."""
        mock_settings = Mock()
        mock_settings.camoufox_user_data_dir = None
        mock_settings.camoufox_window = None
        mock_settings.camoufox_disable_coop = False
        mock_settings.camoufox_locale = None
        mock_settings.camoufox_virtual_display = None
        
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="read"
        )
        
        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_with_user_data
        )
        
        # Should not contain user data parameters when settings not configured
        assert "user_data_dir" not in additional_args

    def test_camoufox_builder_write_mode(self, temp_base_dir):
        """Test CamoufoxArgsBuilder integration with write mode."""
        mock_settings = Mock()
        mock_settings.camoufox_user_data_dir = temp_base_dir
        mock_settings.camoufox_window = None
        mock_settings.camoufox_disable_coop = False
        mock_settings.camoufox_locale = None
        mock_settings.camoufox_virtual_display = None
        
        mock_caps = Mock()
        mock_caps.user_data_dir = True
        mock_caps.profile_dir = False
        mock_caps.profile_path = False
        mock_caps.user_data = False
        
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_mode="write"
        )
        
        with patch('app.services.crawler.options.user_data.user_data_context') as mock_context:
            mock_context.return_value.__enter__ = Mock(return_value=(temp_base_dir, Mock()))
            mock_context.return_value.__exit__ = Mock(return_value=None)
            
            additional_args, extra_headers = CamoufoxArgsBuilder.build(
                request, mock_settings, mock_caps
            )
            
            # Verify context was called with write mode
            mock_context.assert_called_once_with(temp_base_dir, "write")
            assert "user_data_dir" in additional_args