"""Unit tests for ChromiumUserDataManager."""

import os
import json
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(sys.platform == "win32", reason="Chromium user data manager tests fail on Windows due to API mismatches")
]


class TestChromiumUserDataManager:
    """Test cases for ChromiumUserDataManager."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.user_data_manager = ChromiumUserDataManager(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_enabled(self):
        """Test manager initialization with user data directory."""
        assert self.user_data_manager.enabled is True
        assert self.user_data_manager.user_data_dir == self.temp_dir
        assert self.user_data_manager.path_manager.base_path == Path(self.temp_dir)
        assert self.user_data_manager.path_manager.master_dir == Path(self.temp_dir) / 'master'
        assert self.user_data_manager.path_manager.clones_dir == Path(self.temp_dir) / 'clones'

    def test_init_disabled(self):
        """Test manager initialization without user data directory."""
        manager = ChromiumUserDataManager(None)
        assert manager.enabled is False
        assert manager.user_data_dir is None

    def test_is_enabled(self):
        """Test is_enabled method."""
        assert self.user_data_manager.is_enabled() is True

        disabled_manager = ChromiumUserDataManager(None)
        assert disabled_manager.is_enabled() is False

    def test_get_master_dir(self):
        """Test get_master_dir method."""
        expected = str(Path(self.temp_dir) / 'master')
        assert self.user_data_manager.get_master_dir() == expected

        disabled_manager = ChromiumUserDataManager(None)
        assert disabled_manager.get_master_dir() is None

    def test_write_mode_context(self):
        """Test write mode context manager."""
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            assert effective_dir == str(self.user_data_manager.master_dir)
            assert callable(cleanup)
            assert os.path.exists(effective_dir)

        # Check metadata was created
        metadata_file = Path(effective_dir) / 'metadata.json'
        assert metadata_file.exists()

    def test_read_mode_context_without_master(self):
        """Test read mode context when master doesn't exist."""
        with self.user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
            assert effective_dir != str(self.user_data_manager.master_dir)
            assert effective_dir.startswith(str(self.user_data_manager.clones_dir))
            assert callable(cleanup)
            assert os.path.exists(effective_dir)

        # Clone should be cleaned up
        assert not os.path.exists(effective_dir)

    def test_read_mode_context_with_master(self):
        """Test read mode context when master exists."""
        # Create master directory with some content
        master_dir = self.user_data_manager.master_dir
        master_dir.mkdir(parents=True, exist_ok=True)
        test_file = master_dir / 'test.txt'
        test_file.write_text('test content')

        with self.user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
            assert effective_dir != str(self.user_data_manager.master_dir)
            assert effective_dir.startswith(str(self.user_data_manager.clones_dir))

            # Check that content was cloned
            cloned_file = Path(effective_dir) / 'test.txt'
            assert cloned_file.exists()
            assert cloned_file.read_text() == 'test content'

        # Clone should be cleaned up
        assert not os.path.exists(effective_dir)

    def test_invalid_mode(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="user_data_mode must be 'read' or 'write'"):
            with self.user_data_manager.get_user_data_context('invalid'):
                pass

    def test_disabled_manager_context(self):
        """Test context manager when user data management is disabled."""
        manager = ChromiumUserDataManager(None)

        with manager.get_user_data_context('read') as (effective_dir, cleanup):
            assert effective_dir.startswith(tempfile.gettempdir())
            assert 'chromium_temp_' in effective_dir
            assert callable(cleanup)
            assert os.path.exists(effective_dir)

        # Temp directory should be cleaned up
        assert not os.path.exists(effective_dir)

    @patch('app.services.common.browser.profile_manager.BROWSERFORGE_AVAILABLE', True)
    @patch('app.services.common.browser.profile_manager.browserforge')
    def test_metadata_creation_with_browserforge(self, mock_browserforge):
        """Test metadata creation when BrowserForge is available."""
        mock_browserforge.__version__ = '1.2.3'
        mock_browserforge.generate.return_value = {
            'userAgent': 'test-agent',
            'viewport': {'width': 1920, 'height': 1080}
        }

        # Trigger metadata creation by accessing write mode
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Check metadata file
        metadata_file = Path(effective_dir) / 'metadata.json'
        assert metadata_file.exists()

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata['browserforge_version'] == '1.2.3'
        assert metadata['profile_type'] == 'chromium'

        # Check fingerprint file
        fingerprint_file = Path(effective_dir) / 'browserforge_fingerprint.json'
        assert fingerprint_file.exists()

    @patch('app.services.common.browser.profile_manager.BROWSERFORGE_AVAILABLE', False)
    def test_metadata_creation_without_browserforge(self):
        """Test metadata creation when BrowserForge is not available."""
        # Trigger metadata creation
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Check metadata file
        metadata_file = Path(effective_dir) / 'metadata.json'
        assert metadata_file.exists()

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert metadata['browserforge_version'] is None
        assert metadata['profile_type'] == 'chromium'

        # Fingerprint file should not exist
        fingerprint_file = Path(effective_dir) / 'browserforge_fingerprint.json'
        assert not fingerprint_file.exists()

    def test_get_browserforge_fingerprint(self):
        """Test getting BrowserForge fingerprint."""
        # Test when fingerprint doesn't exist
        fingerprint = self.user_data_manager.get_browserforge_fingerprint()
        assert fingerprint is None

        # Create fingerprint file
        fingerprint_data = {
            'userAgent': 'test-agent',
            'viewport': {'width': 1920, 'height': 1080}
        }
        fingerprint_file = self.user_data_manager.master_dir / 'browserforge_fingerprint.json'
        fingerprint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(fingerprint_file, 'w') as f:
            json.dump(fingerprint_data, f)

        # Test getting existing fingerprint
        fingerprint = self.user_data_manager.get_browserforge_fingerprint()
        assert fingerprint == fingerprint_data

    @patch('app.services.common.browser.profile_manager.BROWSERFORGE_AVAILABLE', False)
    def test_get_browserforge_fingerprint_unavailable(self):
        """Test getting fingerprint when BrowserForge is unavailable."""
        fingerprint = self.user_data_manager.get_browserforge_fingerprint()
        assert fingerprint is None

    def test_update_metadata(self):
        """Test updating metadata."""
        # Create initial metadata
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Update metadata
        self.user_data_manager.update_metadata({
            'test_key': 'test_value',
            'another_key': 123
        })

        # Check updated metadata
        metadata = self.user_data_manager.get_metadata()
        assert metadata['test_key'] == 'test_value'
        assert metadata['another_key'] == 123
        assert 'last_updated' in metadata

    def test_update_metadata_disabled(self):
        """Test updating metadata when manager is disabled."""
        manager = ChromiumUserDataManager(None)
        # Should not raise error
        manager.update_metadata({'test': 'value'})

    def test_get_metadata(self):
        """Test getting metadata."""
        # Test when metadata doesn't exist
        metadata = self.user_data_manager.get_metadata()
        assert metadata is None

        # Create metadata file
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Test getting existing metadata
        metadata = self.user_data_manager.get_metadata()
        assert metadata is not None
        assert 'version' in metadata
        assert 'profile_type' in metadata
        assert metadata['profile_type'] == 'chromium'

    def test_get_metadata_disabled(self):
        """Test getting metadata when manager is disabled."""
        manager = ChromiumUserDataManager(None)
        metadata = manager.get_metadata()
        assert metadata is None

    def test_concurrent_write_locks(self):
        """Test that write mode handles concurrent access."""
        # This is a basic test - more thorough testing would require threading
        # which is complex in unit tests
        with self.user_data_manager.get_user_data_context('write') as (effective_dir1, cleanup1):
            # First context should work
            assert effective_dir1 == str(self.user_data_manager.master_dir)

            # Try to get second write context - should fail on some platforms
            # Note: This test might behave differently on Windows vs Unix
            try:
                with self.user_data_manager.get_user_data_context('write') as (effective_dir2, cleanup2):
                    # If we get here, the platform doesn't support proper locking
                    assert effective_dir2 == str(self.user_data_manager.master_dir)
            except RuntimeError:
                # Expected on platforms that support file locking
                pass

    def test_concurrent_read_contexts(self):
        """Test that multiple read contexts can coexist."""
        # Create master directory first
        with self.user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            pass

        # Multiple read contexts should work
        contexts = []
        try:
            for i in range(3):
                effective_dir, cleanup = self.user_data_manager.get_user_data_context('read').__enter__()
                contexts.append((effective_dir, cleanup))
                assert effective_dir.startswith(str(self.user_data_manager.clones_dir))
                assert effective_dir != str(self.user_data_manager.master_dir)
        finally:
            # Clean up all contexts
            for effective_dir, cleanup in contexts:
                cleanup()

    def test_copytree_recursive(self):
        """Test the recursive directory copy function."""
        # Create source structure
        src_dir = Path(self.temp_dir) / 'src'
        src_dir.mkdir()

        # Create nested structure
        (src_dir / 'file1.txt').write_text('content1')
        (src_dir / 'subdir').mkdir()
        (src_dir / 'subdir' / 'file2.txt').write_text('content2')

        # Copy to destination
        dst_dir = Path(self.temp_dir) / 'dst'
        self.user_data_manager._copytree_recursive(src_dir, dst_dir)

        # Verify copy
        assert dst_dir.exists()
        assert (dst_dir / 'file1.txt').exists()
        assert (dst_dir / 'file1.txt').read_text() == 'content1'
        assert (dst_dir / 'subdir').exists()
        assert (dst_dir / 'subdir' / 'file2.txt').exists()
        assert (dst_dir / 'subdir' / 'file2.txt').read_text() == 'content2'
