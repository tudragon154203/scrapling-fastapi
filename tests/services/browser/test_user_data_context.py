import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from unittest.mock import Mock, patch

from app.services.common.browser import user_data as user_data_module
from app.services.common.browser.user_data import user_data_context
from app.schemas.crawl import CrawlRequest
from app.services.common.browser.camoufox import CamoufoxArgsBuilder

pytestmark = pytest.mark.integration


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

    def test_write_mode_windows_fallback(self, temp_base_dir, monkeypatch, caplog):
        """Simulate Windows fallback when fcntl is unavailable."""
        monkeypatch.setattr(user_data_module, "FCNTL_AVAILABLE", False)
        lock_file = Path(temp_base_dir) / "master.lock"
        cleanup_fn = None

        caplog.clear()
        with caplog.at_level("WARNING"):
            with user_data_context(temp_base_dir, "write") as (effective_dir, cleanup):
                cleanup_fn = cleanup
                assert Path(effective_dir) == Path(temp_base_dir) / "master"
                assert lock_file.exists()

        assert cleanup_fn is not None
        cleanup_fn()
        assert not lock_file.exists()
        assert "fcntl not available on this platform, using exclusive fallback" in caplog.text

    def test_read_mode_with_no_master(self, temp_base_dir, caplog):
        """Test that read mode creates empty clone when no master exists."""
        clone_path = None

        caplog.clear()
        with caplog.at_level("DEBUG"):
            with user_data_context(temp_base_dir, "read") as (dir_path, cleanup):
                clone_path = Path(dir_path)
                assert clone_path.exists()
                assert "clones" in dir_path
                cleanup()

        assert clone_path is not None
        assert not clone_path.exists()
        assert f"Created empty clone directory: {clone_path}" in caplog.text
        assert f"Cleaned up clone directory: {clone_path}" in caplog.text

    def test_read_mode_with_master(self, temp_base_dir, caplog):
        """Test that read mode clones from existing master."""
        master_dir = Path(temp_base_dir) / "master"
        master_dir.mkdir(parents=True, exist_ok=True)
        (master_dir / "test_file.txt").write_text("test content")

        clone_path = None

        caplog.clear()
        with caplog.at_level("DEBUG"):
            with user_data_context(temp_base_dir, "read") as (dir_path, cleanup):
                clone_path = Path(dir_path)
                assert clone_path.exists()
                assert "clones" in dir_path
                assert (clone_path / "test_file.txt").exists()
                cleanup()

        assert clone_path is not None
        assert not clone_path.exists()
        assert f"Created clone directory: {clone_path}" in caplog.text
        assert f"Cleaned up clone directory: {clone_path}" in caplog.text

    def test_read_mode_clone_failure_logs_and_raises(self, temp_base_dir, monkeypatch, caplog):
        """Ensure clone failures are logged and raised to the caller."""
        master_dir = Path(temp_base_dir) / "master"
        master_dir.mkdir(parents=True, exist_ok=True)
        (master_dir / "data.txt").write_text("payload")

        monkeypatch.setattr(
            user_data_module,
            "_copytree_recursive",
            Mock(side_effect=RuntimeError("copy explosion")),
        )

        caplog.clear()
        with caplog.at_level("ERROR"):
            with pytest.raises(RuntimeError, match="Failed to create clone"):
                with user_data_context(temp_base_dir, "read"):
                    pass

        assert "Error in user_data_context mode=read: Failed to create clone" in caplog.text
        clones_root = Path(temp_base_dir) / "clones"
        if clones_root.exists():
            assert not any(clones_root.iterdir())

    def test_cleanup_logs_warning_preserves_errors(
        self, temp_base_dir, monkeypatch, caplog
    ):
        """Cleanup warnings should not mask the original exception."""
        original_rmtree = shutil.rmtree
        monkeypatch.setattr(
            user_data_module.shutil,
            "rmtree",
            Mock(side_effect=OSError("cannot remove")),
        )

        clone_holder = {}

        caplog.clear()
        with caplog.at_level("WARNING"):
            with pytest.raises(RuntimeError, match="boom"):
                with user_data_context(temp_base_dir, "read") as (dir_path, cleanup):
                    clone_holder["path"] = Path(dir_path)
                    try:
                        raise RuntimeError("boom")
                    finally:
                        cleanup()

        assert "Failed to cleanup clone directory" in caplog.text
        clone_path = clone_holder["path"]
        assert clone_path.exists()
        monkeypatch.setattr(user_data_module.shutil, "rmtree", original_rmtree)
        shutil.rmtree(clone_path, ignore_errors=True)

    # Removed schema-level user_data_mode validation in new model

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
        )

        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_with_user_data
        )

        # Should contain user_data_dir parameter
        assert "user_data_dir" in additional_args
        # In read mode, should use a clone directory
        assert "clones" in additional_args["user_data_dir"]
        # On Windows, TemporaryDirectory may yield a short (8.3) path while
        # Path.resolve() returns the long form. Compare using resolved paths.
        assert Path(additional_args["user_data_dir"]).resolve().is_relative_to(
            Path(temp_base_dir).resolve()
        )

    def test_camoufox_builder_integration_with_force_user_data_false(
        self, mock_settings, mock_caps_with_user_data
    ):
        """Test CamoufoxArgsBuilder integration with force_user_data=False."""
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=False,
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
        )

        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_without_user_data
        )

        # Should contain user_data_dir parameter regardless of capabilities
        # (force profile_dir regardless of capability detection)
        assert "user_data_dir" in additional_args
        # In read mode, should use a clone directory
        assert "clones" in additional_args["user_data_dir"]
        assert Path(additional_args["user_data_dir"]).resolve().is_relative_to(
            Path(temp_base_dir).resolve()
        )

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
        )

        additional_args, extra_headers = CamoufoxArgsBuilder.build(
            request, mock_settings, mock_caps_with_user_data
        )

        # Should not contain user data parameters when settings not configured
        assert "user_data_dir" not in additional_args

    # Write-mode handling is now covered by browse flow; builder uses read-mode only
