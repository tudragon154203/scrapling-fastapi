"""Test ChromiumPathManager functionality - corrected to match actual API."""

import pytest
from pathlib import Path
from unittest.mock import patch

from app.services.common.browser.paths import ChromiumPathManager


class TestChromiumPathManager:
    """Test ChromiumPathManager path management functionality."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary user data directory."""
        return tmp_path / "test_user_data"

    @pytest.fixture
    def path_manager(self, temp_data_dir):
        """Create path manager instance."""
        return ChromiumPathManager(str(temp_data_dir))

    @pytest.fixture
    def path_manager_no_dir(self):
        """Create path manager without directory."""
        return ChromiumPathManager(None)

    @pytest.mark.unit
    def test_initialization_with_directory(self, temp_data_dir):
        """Test initialization with user data directory."""
        manager = ChromiumPathManager(str(temp_data_dir))
        assert manager.user_data_dir == str(temp_data_dir) or manager.user_data_dir == temp_data_dir
        assert manager.enabled is True
        assert manager.base_path == temp_data_dir
        assert manager.master_dir == temp_data_dir / 'master'
        assert manager.clones_dir == temp_data_dir / 'clones'
        assert manager.lock_file == temp_data_dir / 'chromium_profile.lock'
        assert manager.metadata_file == temp_data_dir / 'master' / 'metadata.json'
        assert manager.fingerprint_file == temp_data_dir / 'master' / 'browserforge_fingerprint.json'

    @pytest.mark.unit
    def test_initialization_without_directory(self):
        """Test initialization without user data directory."""
        manager = ChromiumPathManager(None)
        assert manager.user_data_dir is None
        assert manager.enabled is False
        assert not hasattr(manager, 'base_path')
        assert not hasattr(manager, 'master_dir')
        assert not hasattr(manager, 'clones_dir')
        assert not hasattr(manager, 'lock_file')
        assert not hasattr(manager, 'metadata_file')
        assert not hasattr(manager, 'fingerprint_file')

    @pytest.mark.unit
    def test_get_master_dir_enabled(self, path_manager, temp_data_dir):
        """Test get_master_dir when enabled."""
        result = path_manager.get_master_dir()
        assert result == str(temp_data_dir / 'master')

    @pytest.mark.unit
    def test_get_master_dir_disabled(self, path_manager_no_dir):
        """Test get_master_dir when disabled."""
        result = path_manager_no_dir.get_master_dir()
        assert result is None

    @pytest.mark.unit
    def test_ensure_directories_exist_enabled(self, path_manager, temp_data_dir):
        """Test ensure_directories_exist when enabled."""
        path_manager.ensure_directories_exist()

        assert temp_data_dir.exists()
        assert (temp_data_dir / 'master').exists()
        assert (temp_data_dir / 'clones').exists()

    @pytest.mark.unit
    def test_ensure_directories_exist_disabled(self, path_manager_no_dir):
        """Test ensure_directories_exist when disabled."""
        # Should not raise any exceptions
        path_manager_no_dir.ensure_directories_exist()

    @pytest.mark.unit
    def test_ensure_directories_exist_already_exists(self, path_manager, temp_data_dir):
        """Test ensure_directories_exist when directories already exist."""
        # Create directories first
        temp_data_dir.mkdir(parents=True, exist_ok=True)
        (temp_data_dir / 'master').mkdir(parents=True, exist_ok=True)
        (temp_data_dir / 'clones').mkdir(parents=True, exist_ok=True)

        # Should not raise any exceptions
        path_manager.ensure_directories_exist()

        # Directories should still exist
        assert temp_data_dir.exists()
        assert (temp_data_dir / 'master').exists()
        assert (temp_data_dir / 'clones').exists()

    @pytest.mark.unit
    def test_generate_clone_path(self, path_manager, temp_data_dir):
        """Test generate_clone_path returns unique path."""
        clone_path1 = path_manager.generate_clone_path()
        clone_path2 = path_manager.generate_clone_path()

        assert clone_path1 != clone_path2
        assert clone_path1.parent == temp_data_dir / 'clones'
        assert clone_path2.parent == temp_data_dir / 'clones'
        assert clone_path1.name != clone_path2.name

    @pytest.mark.unit
    def test_generate_clone_path_disabled(self, path_manager_no_dir):
        """Test generate_clone_path when disabled."""
        with pytest.raises(AttributeError):
            path_manager_no_dir.generate_clone_path()

    @pytest.mark.unit
    def test_get_cookies_db_path(self, path_manager, temp_data_dir):
        """Test get_cookies_db_path returns correct path."""
        cookies_path = path_manager.get_cookies_db_path()
        expected = temp_data_dir / 'master' / 'Default' / 'Cookies'
        assert cookies_path == expected

    @pytest.mark.unit
    def test_get_cookies_db_path_disabled(self, path_manager_no_dir):
        """Test get_cookies_db_path when disabled."""
        with pytest.raises(AttributeError):
            path_manager_no_dir.get_cookies_db_path()

    @pytest.mark.unit
    def test_validate_paths_enabled_success(self, path_manager, temp_data_dir):
        """Test validate_paths when enabled and accessible."""
        result = path_manager.validate_paths()
        assert result is True
        assert temp_data_dir.exists()

    @pytest.mark.unit
    def test_validate_paths_disabled(self, path_manager_no_dir):
        """Test validate_paths when disabled."""
        result = path_manager_no_dir.validate_paths()
        assert result is True

    @pytest.mark.unit
    def test_validate_paths_permission_error(self, path_manager, temp_data_dir):
        """Test validate_paths with permission error."""
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Permission denied")):
            result = path_manager.validate_paths()
            assert result is False

    @pytest.mark.unit
    def test_validate_paths_os_error(self, path_manager, temp_data_dir):
        """Test validate_paths with OS error."""
        with patch.object(Path, 'mkdir', side_effect=OSError("OS error")):
            result = path_manager.validate_paths()
            assert result is False

    @pytest.mark.unit
    def test_path_manager_with_path_object(self, temp_data_dir):
        """Test initialization with Path object."""
        manager = ChromiumPathManager(temp_data_dir)
        assert manager.user_data_dir == str(temp_data_dir) or manager.user_data_dir == temp_data_dir
        assert manager.enabled is True

    @pytest.mark.unit
    def test_path_manager_with_empty_string(self):
        """Test initialization with empty string."""
        manager = ChromiumPathManager("")
        assert manager.user_data_dir == ""
        # Empty string should be treated as a valid path
        assert manager.enabled is True

    @pytest.mark.unit
    def test_ensure_directories_exist_permission_error(self, path_manager, temp_data_dir):
        """Test ensure_directories_exist with permission error."""
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Permission denied")):
            # Should raise the permission error
            with pytest.raises(PermissionError):
                path_manager.ensure_directories_exist()

    @pytest.mark.unit
    def test_clone_path_uniqueness(self, path_manager):
        """Test that generated clone paths are unique."""
        paths = set()
        for _ in range(100):
            clone_path = path_manager.generate_clone_path()
            assert clone_path not in paths
            paths.add(clone_path)

    @pytest.mark.unit
    def test_clone_path_is_uuid(self, path_manager):
        """Test that clone path uses UUID format."""
        clone_path = path_manager.generate_clone_path()
        import uuid
        try:
            # Try to parse the filename as UUID
            uuid.UUID(clone_path.name)
            is_uuid = True
        except ValueError:
            is_uuid = False

        assert is_uuid, f"Clone path name {clone_path.name} is not a valid UUID"

    @pytest.mark.unit
    def test_cookies_db_path_structure(self, path_manager, temp_data_dir):
        """Test cookies database path structure."""
        cookies_path = path_manager.get_cookies_db_path()
        assert cookies_path.name == "Cookies"
        assert cookies_path.parent.name == "Default"
        assert cookies_path.parent.parent.name == "master"
        assert cookies_path.parent.parent.parent == temp_data_dir

    @pytest.mark.unit
    def test_lock_file_naming(self, path_manager, temp_data_dir):
        """Test lock file naming convention."""
        assert path_manager.lock_file.name == "chromium_profile.lock"
        assert path_manager.lock_file.parent == temp_data_dir

    @pytest.mark.unit
    def test_metadata_file_naming(self, path_manager, temp_data_dir):
        """Test metadata file naming convention."""
        assert path_manager.metadata_file.name == "metadata.json"
        assert path_manager.metadata_file.parent == temp_data_dir / "master"

    @pytest.mark.unit
    def test_fingerprint_file_naming(self, path_manager, temp_data_dir):
        """Test fingerprint file naming convention."""
        assert path_manager.fingerprint_file.name == "browserforge_fingerprint.json"
        assert path_manager.fingerprint_file.parent == temp_data_dir / "master"

    @pytest.mark.unit
    def test_directory_structure_consistency(self, path_manager, temp_data_dir):
        """Test that all directory paths are consistent."""
        assert path_manager.base_path == temp_data_dir
        assert path_manager.master_dir.parent == temp_data_dir
        assert path_manager.clones_dir.parent == temp_data_dir
        assert path_manager.lock_file.parent == temp_data_dir
        assert path_manager.metadata_file.parent.parent == temp_data_dir
        assert path_manager.fingerprint_file.parent.parent == temp_data_dir
