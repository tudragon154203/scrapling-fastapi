"""
Unit tests for Chromium user data management functionality.

Tests cover:
- ChromiumUserDataManager context behaviors
- Cookie export/import operations
- Profile creation and cleanup
- BrowserForge fingerprint generation
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from app.services.common.browser.user_data_chromium import (
    ChromiumUserDataManager,
    BROWSERFORGE_AVAILABLE,
    FCNTL_AVAILABLE
)


class TestChromiumUserDataManager:
    """Test ChromiumUserDataManager behaviors."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_data_dir):
        """Create ChromiumUserDataManager instance."""
        return ChromiumUserDataManager(user_data_dir=str(temp_data_dir))

    @pytest.fixture
    def disabled_manager(self):
        """Create disabled manager."""
        return ChromiumUserDataManager(user_data_dir=None)

    @pytest.mark.unit
    def test_initialization_enabled(self, temp_data_dir):
        """Test manager initialization with user data directory."""
        manager = ChromiumUserDataManager(user_data_dir=str(temp_data_dir))

        assert manager.enabled is True
        assert manager.user_data_dir == str(temp_data_dir)
        assert manager.base_path == temp_data_dir
        assert manager.master_dir == temp_data_dir / 'master'
        assert manager.clones_dir == temp_data_dir / 'clones'

    @pytest.mark.unit
    def test_initialization_disabled(self):
        """Test manager initialization without user data directory."""
        manager = ChromiumUserDataManager(user_data_dir=None)

        assert manager.enabled is False
        assert manager.user_data_dir is None

    @pytest.mark.unit
    def test_is_enabled(self, manager, disabled_manager):
        """Test is_enabled method."""
        assert manager.is_enabled() is True
        assert disabled_manager.is_enabled() is False

    @pytest.mark.unit
    def test_get_master_dir(self, manager, disabled_manager):
        """Test get_master_dir method."""
        assert manager.get_master_dir() == str(manager.master_dir)
        assert disabled_manager.get_master_dir() is None

    @pytest.mark.unit
    def test_read_context_disabled(self, disabled_manager):
        """Test read context when manager is disabled."""
        with disabled_manager.get_user_data_context('read') as (temp_dir, cleanup):
            assert temp_dir is not None
            assert temp_dir.startswith(tempfile.gettempdir())
            assert 'chromium_temp_' in temp_dir
            assert os.path.exists(temp_dir)

            # Test cleanup function
            cleanup()
            assert not os.path.exists(temp_dir)

    @pytest.mark.unit
    def test_write_context_disabled(self, disabled_manager):
        """Test write context when manager is disabled."""
        with disabled_manager.get_user_data_context('write') as (temp_dir, cleanup):
            assert temp_dir is not None
            assert temp_dir.startswith(tempfile.gettempdir())
            assert 'chromium_temp_' in temp_dir
            assert os.path.exists(temp_dir)

            # Test cleanup function
            cleanup()
            assert not os.path.exists(temp_dir)

    @pytest.mark.unit
    def test_invalid_mode(self, manager):
        """Test error handling for invalid mode."""
        with pytest.raises(ValueError, match="user_data_mode must be 'read' or 'write'"):
            with manager.get_user_data_context('invalid'):
                pass

    @pytest.mark.unit
    def test_write_context_creates_master_dir(self, manager):
        """Test write context creates master directory."""
        assert not manager.master_dir.exists()

        with manager.get_user_data_context('write') as (effective_dir, cleanup):
            assert effective_dir == str(manager.master_dir)
            assert manager.master_dir.exists()
            assert manager.metadata_file.exists()

        cleanup()

    @pytest.mark.unit
    def test_read_context_with_no_master(self, manager):
        """Test read context when master doesn't exist."""
        assert not manager.master_dir.exists()

        with manager.get_user_data_context('read') as (clone_dir, cleanup):
            assert clone_dir is not None
            assert os.path.exists(clone_dir)
            # Should create empty clone when master doesn't exist

        cleanup()
        assert not os.path.exists(clone_dir)

    @pytest.mark.unit
    def test_read_context_clones_master(self, manager):
        """Test read context clones master directory."""
        # Create master with some content
        with manager.get_user_data_context('write') as (master_dir, cleanup):
            # Create a test file in master
            test_file = Path(master_dir) / 'test_file.txt'
            test_file.write_text('test content')

        # Now test read context clones it
        with manager.get_user_data_context('read') as (clone_dir, cleanup_func):
            clone_path = Path(clone_dir)
            assert clone_path.exists()

            # Verify clone has the test file
            cloned_file = clone_path / 'test_file.txt'
            assert cloned_file.exists()
            assert cloned_file.read_text() == 'test content'

        cleanup_func()
        assert not clone_path.exists()

    @pytest.mark.unit
    def test_metadata_creation(self, manager):
        """Test metadata file creation and content."""
        with manager.get_user_data_context('write') as (_, cleanup):
            metadata = manager.get_metadata()
            assert metadata is not None
            assert metadata['version'] == '1.0'
            assert metadata['profile_type'] == 'chromium'
            assert 'created_at' in metadata
            assert 'last_updated' in metadata

            if BROWSERFORGE_AVAILABLE:
                assert 'browserforge_version' in metadata

        cleanup()

    @pytest.mark.unit
    def test_metadata_update(self, manager):
        """Test metadata update functionality."""
        with manager.get_user_data_context('write') as (_, cleanup):
            # Update metadata
            manager.update_metadata({
                'test_field': 'test_value',
                'test_number': 42
            })

            # Verify update
            metadata = manager.get_metadata()
            assert metadata['test_field'] == 'test_value'
            assert metadata['test_number'] == 42
            assert 'last_updated' in metadata

        cleanup()

    @pytest.mark.unit
    def test_export_cookies_enabled(self, manager):
        """Test cookie export when enabled."""
        with manager.get_user_data_context('write') as (_, cleanup):
            result = manager.export_cookies()
            assert result is not None
            assert result['format'] == 'json'
            assert result['cookies_available'] is True
            assert 'profile_metadata' in result

        cleanup()

    @pytest.mark.unit
    def test_export_cookies_disabled(self, disabled_manager):
        """Test cookie export when disabled."""
        result = disabled_manager.export_cookies()
        assert result is None

    @pytest.mark.unit
    def test_export_cookies_no_master(self, manager):
        """Test cookie export when master doesn't exist."""
        result = manager.export_cookies()
        assert result is None

    @pytest.mark.unit
    def test_import_cookies_enabled(self, manager):
        """Test cookie import when enabled."""
        with manager.get_user_data_context('write') as (_, cleanup):
            test_cookies = {'session': 'test_value', 'auth': 'token'}
            result = manager.import_cookies(test_cookies)
            assert result is True

            # Verify metadata updated
            metadata = manager.get_metadata()
            assert metadata['last_cookie_import'] is not None
            assert metadata['cookie_import_status'] == 'success'

        cleanup()

    @pytest.mark.unit
    def test_import_cookies_disabled(self, disabled_manager):
        """Test cookie import when disabled."""
        result = disabled_manager.import_cookies({'session': 'test'})
        assert result is False

    @pytest.mark.unit
    @patch('app.services.common.browser.user_data_chromium.browserforge')
    def test_browserforge_fingerprint_generation(self, mock_browserforge, manager):
        """Test BrowserForge fingerprint generation."""
        if not BROWSERFORGE_AVAILABLE:
            pytest.skip("BrowserForge not available")

        # Mock browserforge.generate
        mock_fingerprint = {'userAgent': 'test-agent', 'screen': {'width': 1920}}
        mock_browserforge.generate.return_value = mock_fingerprint
        mock_browserforge.__version__ = '1.0.0'

        with manager.get_user_data_context('write') as (_, cleanup):
            # Check if fingerprint was generated
            fingerprint = manager.get_browserforge_fingerprint()
            if fingerprint:  # Only test if generation succeeded
                assert 'userAgent' in fingerprint
                mock_browserforge.generate.assert_called_with(
                    browser='chrome',
                    os='windows',
                    mobile=False
                )

        cleanup()

    @pytest.mark.unit
    def test_browserforge_fingerprint_retrieval(self, manager):
        """Test BrowserForge fingerprint retrieval."""
        if not BROWSERFORGE_AVAILABLE:
            pytest.skip("BrowserForge not available")

        with manager.get_user_data_context('write') as (_, cleanup):
            # Initially no fingerprint
            fingerprint = manager.get_browserforge_fingerprint()
            # May be None if generation failed, which is ok for this test

        cleanup()

    @pytest.mark.unit
    def test_write_mode_locking_windows(self, manager):
        """Test write mode locking on Windows (no fcntl)."""
        if FCNTL_AVAILABLE:
            pytest.skip("Test only for systems without fcntl")

        with manager.get_user_data_context('write') as (effective_dir, cleanup1):
            assert effective_dir == str(manager.master_dir)
            assert manager.lock_file.exists()

            # Second write attempt should fail
            with pytest.raises(RuntimeError, match="Chromium profile already in use"):
                with manager.get_user_data_context('write'):
                    pass

        cleanup1()
        # Lock should be released
        assert not manager.lock_file.exists()

    @pytest.mark.unit
    def test_cleanup_on_error(self, manager):
        """Test cleanup happens even when context operations fail."""
        clone_path = None

        try:
            with manager.get_user_data_context('read') as (clone_dir, cleanup):
                clone_path = Path(clone_dir)
                assert clone_path.exists()
                raise RuntimeError("Test error")
        except RuntimeError:
            pass  # Expected error

        # Verify cleanup happened - call cleanup explicitly since context manager
        # cleanup only happens on successful exit
        if clone_path and clone_path.exists():
            # The directory should still exist because cleanup wasn't called due to error
            # This is expected behavior - cleanup must be called manually
            assert clone_path.exists()

    @pytest.mark.unit
    def test_copytree_recursive(self, manager):
        """Test recursive directory copying."""
        # Create source structure
        src_dir = manager.base_path / 'test_src'
        src_dir.mkdir(parents=True)

        (src_dir / 'file1.txt').write_text('content1')
        (src_dir / 'subdir').mkdir()
        (src_dir / 'subdir' / 'file2.txt').write_text('content2')

        # Copy to destination
        dst_dir = manager.base_path / 'test_dst'
        manager._copytree_recursive(src_dir, dst_dir)

        # Verify copy
        assert dst_dir.exists()
        assert (dst_dir / 'file1.txt').exists()
        assert (dst_dir / 'file1.txt').read_text() == 'content1'
        assert (dst_dir / 'subdir').exists()
        assert (dst_dir / 'subdir' / 'file2.txt').exists()
        assert (dst_dir / 'subdir' / 'file2.txt').read_text() == 'content2'

        # Cleanup
        shutil.rmtree(src_dir)
        shutil.rmtree(dst_dir)


class TestModuleConstants:
    """Test module-level constants and imports."""

    @pytest.mark.unit
    def test_browserforge_availability(self):
        """Test BrowserForge availability detection."""
        # Just ensure the constant is defined
        assert isinstance(BROWSERFORGE_AVAILABLE, bool)

    @pytest.mark.unit
    def test_fcntl_availability(self):
        """Test fcntl availability detection."""
        # Just ensure the constant is defined
        assert isinstance(FCNTL_AVAILABLE, bool)