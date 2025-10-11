"""Test ChromiumUtils functionality - corrected to match actual API."""

import os
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import patch

from app.services.common.browser.utils import (
    copytree_recursive,
    chmod_tree,
    best_effort_close_sqlite,
    rmtree_with_retries,
    get_directory_size,
    atomic_file_replace
)


class TestCopytreeRecursive:
    """Test copytree_recursive function."""

    @pytest.fixture
    def temp_source_dir(self, tmp_path):
        """Create a temporary source directory."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")

        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.txt").write_text("nested_content")

        return source_dir

    @pytest.fixture
    def temp_target_dir(self, tmp_path):
        """Create a temporary target directory path."""
        return tmp_path / "target"

    @pytest.mark.unit
    def test_copytree_recursive_success(self, temp_source_dir, temp_target_dir):
        """Test copytree_recursive successful copy."""
        copytree_recursive(temp_source_dir, temp_target_dir)

        assert temp_target_dir.exists()
        assert (temp_target_dir / "file1.txt").exists()
        assert (temp_target_dir / "file2.txt").exists()
        assert (temp_target_dir / "subdir").exists()
        assert (temp_target_dir / "subdir" / "nested_file.txt").exists()

        # Verify content
        assert (temp_target_dir / "file1.txt").read_text() == "content1"
        assert (temp_target_dir / "subdir" / "nested_file.txt").read_text() == "nested_content"

    @pytest.mark.unit
    def test_copytree_recursive_creates_parent_dirs(self, temp_source_dir, tmp_path):
        """Test copytree_recursive creates parent directories."""
        target_dir = tmp_path / "parent" / "target"

        copytree_recursive(temp_source_dir, target_dir)

        assert target_dir.exists()
        assert target_dir.parent.exists()
        assert (target_dir / "file1.txt").exists()

    @pytest.mark.unit
    def test_copytree_recursive_target_exists(self, temp_source_dir, temp_target_dir):
        """Test copytree_recursive when target directory already exists."""
        temp_target_dir.mkdir()

        copytree_recursive(temp_source_dir, temp_target_dir)

        assert temp_target_dir.exists()
        assert (temp_target_dir / "file1.txt").exists()

    @pytest.mark.unit
    def test_copytree_recursive_empty_source(self, tmp_path):
        """Test copytree_recursive with empty source directory."""
        source_dir = tmp_path / "empty_source"
        source_dir.mkdir()
        target_dir = tmp_path / "target"

        copytree_recursive(source_dir, target_dir)

        assert target_dir.exists()
        assert len(list(target_dir.iterdir())) == 0


class TestChmodTree:
    """Test chmod_tree function."""

    @pytest.fixture
    def temp_dir_with_files(self, tmp_path):
        """Create temporary directory with files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        return test_dir

    @pytest.mark.unit
    def test_chmod_tree_success(self, temp_dir_with_files):
        """Test chmod_tree successful permission change."""
        mode = 0o755

        chmod_tree(temp_dir_with_files, mode)

        # Should not raise any exceptions
        assert temp_dir_with_files.exists()

    @pytest.mark.unit
    def test_chmod_tree_nonexistent_path(self, tmp_path):
        """Test chmod_tree with nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise any exceptions
        chmod_tree(nonexistent, 0o755)

    @pytest.mark.unit
    def test_chmod_tree_permission_error(self, temp_dir_with_files):
        """Test chmod_tree with permission error."""
        with patch('os.chmod', side_effect=PermissionError("Permission denied")):
            # Should not raise any exceptions
            chmod_tree(temp_dir_with_files, 0o755)

    @pytest.mark.unit
    def test_chmod_tree_default_mode(self, temp_dir_with_files):
        """Test chmod_tree with default mode."""
        chmod_tree(temp_dir_with_files)

        # Should not raise any exceptions
        assert temp_dir_with_files.exists()


class TestBestEffortCloseSqlite:
    """Test best_effort_close_sqlite function."""

    @pytest.fixture
    def temp_dir_with_databases(self, tmp_path):
        """Create temporary directory with SQLite files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create SQLite database
        db_path = test_dir / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        # Create WAL and Journal files
        (test_dir / "test-wal").write_text("wal content")
        (test_dir / "test-journal").write_text("journal content")

        # Create cookies file
        (test_dir / "Cookies").write_text("cookies content")

        return test_dir

    @pytest.mark.unit
    def test_best_effort_close_sqlite_success(self, temp_dir_with_databases):
        """Test best_effort_close_sqlite successful operation."""
        best_effort_close_sqlite(temp_dir_with_databases)

        # Should not raise any exceptions
        assert temp_dir_with_databases.exists()

    @pytest.mark.unit
    def test_best_effort_close_sqlite_nonexistent_path(self, tmp_path):
        """Test best_effort_close_sqlite with nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise any exceptions
        best_effort_close_sqlite(nonexistent)

    @pytest.mark.unit
    def test_best_effort_close_sqlite_sqlite_error(self, temp_dir_with_databases):
        """Test best_effort_close_sqlite with SQLite error."""
        with patch('sqlite3.connect', side_effect=sqlite3.Error("SQLite error")):
            # Should not raise any exceptions
            best_effort_close_sqlite(temp_dir_with_databases)

    @pytest.mark.unit
    def test_best_effort_close_sqlite_finds_various_files(self, tmp_path):
        """Test best_effort_close_sqlite finds various SQLite-related files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create various SQLite-related files
        (test_dir / "database.sqlite").write_text("sqlite content")
        (test_dir / "cookies").write_text("cookies content")
        (test_dir / "test-wal").write_text("wal content")
        (test_dir / "test-journal").write_text("journal content")

        best_effort_close_sqlite(test_dir)

        # Should not raise any exceptions
        assert test_dir.exists()


class TestRmtreeWithRetries:
    """Test rmtree_with_retries function."""

    @pytest.fixture
    def temp_dir_with_files(self, tmp_path):
        """Create temporary directory with files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.txt").write_text("nested_content")

        return test_dir

    @pytest.mark.unit
    def test_rmtree_with_retries_success(self, temp_dir_with_files):
        """Test rmtree_with_retries successful deletion."""
        result = rmtree_with_retries(temp_dir_with_files)

        assert result is True
        assert not temp_dir_with_files.exists()

    @pytest.mark.unit
    def test_rmtree_with_retries_nonexistent(self, tmp_path):
        """Test rmtree_with_retries with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        result = rmtree_with_retries(nonexistent)

        assert result is True

    @pytest.mark.unit
    def test_rmtree_with_retries_permission_error_success(self, temp_dir_with_files):
        """Test rmtree_with_retries succeeds after permission error."""
        call_count = 0

        def mock_rmtree(path, onerror=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("Permission denied")
            # Success on second call

        with patch('shutil.rmtree', side_effect=mock_rmtree):
            with patch('time.sleep'):
                result = rmtree_with_retries(temp_dir_with_files, max_attempts=2)

                assert result is True
                assert call_count == 2

    @pytest.mark.unit
    def test_rmtree_with_retries_permission_error_failure(self, temp_dir_with_files):
        """Test rmtree_with_retries fails after max attempts."""
        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            with patch('time.sleep'):
                result = rmtree_with_retries(temp_dir_with_files, max_attempts=3)

                assert result is False

    @pytest.mark.unit
    def test_rmtree_with_retries_custom_attempts_and_delay(self, temp_dir_with_files):
        """Test rmtree_with_retries with custom attempts and delay."""
        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            with patch('time.sleep') as mock_sleep:
                result = rmtree_with_retries(
                    temp_dir_with_files,
                    max_attempts=5,
                    initial_delay=0.2
                )

                assert result is False
                assert mock_sleep.call_count == 5  # Sleep is called for each attempt

    @pytest.mark.unit
    def test_rmtree_with_retries_onerror_handling(self, temp_dir_with_files):
        """Test rmtree_with_retries onerror handling."""
        with patch('shutil.rmtree', side_effect=OSError("Deletion failed")):
            with patch('time.sleep'):
                with patch('os.chmod'):
                    with patch('os.rmdir', side_effect=OSError("Rmdir failed")):
                        with patch('os.unlink', side_effect=OSError("Unlink failed")):
                            result = rmtree_with_retries(
                                temp_dir_with_files,
                                max_attempts=2
                            )

                            assert result is False
                            # The function should attempt deletion multiple times
                            # but onerror may not be called depending on implementation


class TestGetDirectorySize:
    """Test get_directory_size function."""

    @pytest.fixture
    def temp_dir_with_files(self, tmp_path):
        """Create temporary directory with files of known sizes."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create files with specific content
        (test_dir / "file1.txt").write_text("x" * 1024)  # 1KB
        (test_dir / "file2.txt").write_text("x" * 2048)  # 2KB

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("x" * 512)   # 512B

        return test_dir

    @pytest.mark.unit
    def test_get_directory_size_success(self, temp_dir_with_files):
        """Test get_directory_size successful calculation."""
        size_mb = get_directory_size(temp_dir_with_files)

        # Should be (1024 + 2048 + 512) bytes = 3584 bytes = 0.0035 MB
        # Rounded to 2 decimal places = 0.0 MB
        assert size_mb == 0.0

    @pytest.mark.unit
    def test_get_directory_size_empty_directory(self, tmp_path):
        """Test get_directory_size with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        size_mb = get_directory_size(empty_dir)

        assert size_mb == 0.0

    @pytest.mark.unit
    def test_get_directory_size_nonexistent(self, tmp_path):
        """Test get_directory_size with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"

        size_mb = get_directory_size(nonexistent)

        assert size_mb == 0.0

    @pytest.mark.unit
    def test_get_directory_size_permission_error(self, tmp_path):
        """Test get_directory_size with permission error."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        with patch.object(Path, 'rglob', side_effect=PermissionError("Permission denied")):
            size_mb = get_directory_size(test_dir)

            assert size_mb == 0.0

    @pytest.mark.unit
    def test_get_directory_size_large_files(self, tmp_path):
        """Test get_directory_size with larger files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create 1MB file
        (test_dir / "large_file.txt").write_text("x" * (1024 * 1024))

        size_mb = get_directory_size(test_dir)

        # Should be approximately 1.0 MB
        assert abs(size_mb - 1.0) < 0.01

    @pytest.mark.unit
    def test_get_directory_size_rounding(self, tmp_path):
        """Test get_directory_size rounding behavior."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create file that should result in specific MB value
        # 1.5 MB = 1.5 * 1024 * 1024 = 1572864 bytes
        (test_dir / "precise_file.txt").write_text("x" * 1572864)

        size_mb = get_directory_size(test_dir)

        # Should be rounded to 2 decimal places
        assert size_mb == 1.5


class TestAtomicFileReplace:
    """Test atomic_file_replace function."""

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary source and destination files."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "destination.txt"

        source.write_text("source content")
        destination.write_text("original content")

        return source, destination

    @pytest.mark.unit
    def test_atomic_file_replace_success(self, temp_files):
        """Test atomic_file_replace successful replacement."""
        source, destination = temp_files

        result = atomic_file_replace(source, destination)

        assert result is True
        assert destination.exists()
        assert destination.read_text() == "source content"
        assert not source.exists()

    @pytest.mark.unit
    def test_atomic_file_replace_new_destination(self, tmp_path):
        """Test atomic_file_replace with new destination file."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "new_destination.txt"

        source.write_text("source content")

        result = atomic_file_replace(source, destination)

        assert result is True
        assert destination.exists()
        assert destination.read_text() == "source content"
        assert not source.exists()

    @pytest.mark.unit
    def test_atomic_file_replace_permission_error_retry(self, temp_files):
        """Test atomic_file_replace retries on permission error."""
        source, destination = temp_files

        call_count = 0
        original_replace = os.replace

        def mock_replace(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("Permission denied")
            # Success on second call - use the real function
            return original_replace(src, dst)

        with patch('os.replace', side_effect=mock_replace):
            with patch('time.sleep'):
                result = atomic_file_replace(source, destination, max_attempts=3)

                assert result is True
                assert call_count == 2
                # Check that the replacement worked
                assert destination.exists()
                assert destination.read_text() == "source content"
                assert source.exists() is False  # Source should be moved

    @pytest.mark.unit
    def test_atomic_file_replace_permission_error_failure(self, temp_files):
        """Test atomic_file_replace fails after max attempts."""
        source, destination = temp_files

        with patch('os.replace', side_effect=PermissionError("Permission denied")):
            with patch('os.unlink', side_effect=PermissionError("Permission denied")):
                with patch('shutil.move', side_effect=PermissionError("Permission denied")):
                    with patch('time.sleep'):
                        result = atomic_file_replace(source, destination, max_attempts=3)

                        assert result is False
                        # Original content should remain
                        assert destination.read_text() == "original content"

    @pytest.mark.unit
    def test_atomic_file_replace_unlink_fallback_success(self, temp_files):
        """Test atomic_file_replace unlink fallback success."""
        source, destination = temp_files
        original_replace = os.replace

        def mock_replace(src, dst):
            raise PermissionError("Permission denied")

        def mock_unlink(path):
            pass  # Success

        def mock_move(src, dst):
            # Use real replace for success after unlink
            return original_replace(src, dst)

        with patch('os.replace', side_effect=mock_replace):
            with patch('os.unlink', side_effect=mock_unlink):
                with patch('shutil.move', side_effect=mock_move):
                    with patch('time.sleep'):
                        result = atomic_file_replace(source, destination, max_attempts=2)

                        assert result is True
                        assert destination.read_text() == "source content"

    @pytest.mark.unit
    def test_atomic_file_replace_custom_max_attempts(self, temp_files):
        """Test atomic_file_replace with custom max attempts."""
        source, destination = temp_files

        with patch('os.replace', side_effect=PermissionError("Permission denied")):
            with patch('os.unlink', side_effect=PermissionError("Permission denied")):
                with patch('shutil.move', side_effect=PermissionError("Permission denied")):
                    with patch('time.sleep') as mock_sleep:
                        result = atomic_file_replace(source, destination, max_attempts=5)

                        assert result is False
                        # Should have slept at least 5 times (main attempts)
                        # Plus additional sleeps for unlink retries
                        assert mock_sleep.call_count >= 5

    @pytest.mark.unit
    def test_atomic_file_replace_source_not_exists(self, tmp_path):
        """Test atomic_file_replace when source doesn't exist."""
        source = tmp_path / "nonexistent.txt"
        destination = tmp_path / "destination.txt"

        # Mock os.replace to fail immediately to avoid retry delays
        with patch('os.replace', side_effect=FileNotFoundError("No such file or directory")), \
                patch('os.unlink', side_effect=FileNotFoundError("No such file or directory")), \
                patch('shutil.move', side_effect=FileNotFoundError("No such file or directory")), \
                patch('time.sleep'):  # Mock sleep to avoid delays
            result = atomic_file_replace(source, destination)

        assert result is False

    @pytest.mark.unit
    def test_atomic_file_replace_chmod_error_handling(self, temp_files):
        """Test atomic_file_replace chmod error handling."""
        source, destination = temp_files

        with patch('os.replace', side_effect=PermissionError("Permission denied")):
            with patch('os.chmod', side_effect=OSError("Chmod failed")):
                with patch('os.unlink', side_effect=OSError("Unlink failed")):
                    with patch('shutil.move', side_effect=OSError("Move failed")):
                        with patch('time.sleep'):
                            result = atomic_file_replace(source, destination, max_attempts=2)

                            assert result is False

    @pytest.mark.unit
    def test_atomic_file_replace_exponential_backoff(self, temp_files):
        """Test atomic_file_replace exponential backoff."""
        source, destination = temp_files

        sleep_calls = []

        def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch('os.replace', side_effect=PermissionError("Permission denied")):
            with patch('os.unlink', side_effect=PermissionError("Permission denied")):
                with patch('shutil.move', side_effect=PermissionError("Permission denied")):
                    with patch('time.sleep', side_effect=mock_sleep):
                        result = atomic_file_replace(source, destination, max_attempts=4)

                        assert result is False
                        assert len(sleep_calls) >= 4

                        # Check exponential backoff for main attempts (not unlink retries)
                        # The first few sleeps should be for main attempts
                        main_delays = sleep_calls[:4]
                        assert main_delays[1] > main_delays[0]
                        assert main_delays[2] > main_delays[1]

    @pytest.mark.unit
    def test_atomic_file_replace_random_jitter(self, temp_files):
        """Test atomic_file_replace includes random jitter."""
        source, destination = temp_files

        with patch('os.replace', side_effect=PermissionError("Permission denied")):
            with patch('time.sleep') as mock_sleep:
                with patch('random.uniform', return_value=0.123):
                    atomic_file_replace(source, destination, max_attempts=2)

                    # Should include random jitter
                    for call in mock_sleep.call_args_list:
                        delay = call[0][0]
                        # Delay should be base + jitter
                        assert delay >= 0.1  # Base delay
                        assert delay <= 0.2 + 0.123  # Base + max jitter
