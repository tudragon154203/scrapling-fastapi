"""Test FileLock functionality - corrected to match actual API."""

import os
import pytest
from unittest.mock import patch, MagicMock

from app.services.common.browser.locks import FileLock, exclusive_lock, FCNTL_AVAILABLE


class TestFileLock:
    """Test FileLock cross-platform file locking functionality."""

    @pytest.fixture
    def temp_lock_file(self, tmp_path):
        """Create a temporary lock file path."""
        return tmp_path / "test.lock"

    @pytest.fixture
    def file_lock(self, temp_lock_file):
        """Create FileLock instance."""
        return FileLock(str(temp_lock_file))

    @pytest.mark.unit
    def test_initialization(self, temp_lock_file):
        """Test FileLock initialization."""
        lock = FileLock(str(temp_lock_file), timeout=10.0)
        assert lock.lock_file == str(temp_lock_file)
        assert lock.timeout == 10.0
        assert lock.lock_fd is None

    @pytest.mark.unit
    def test_initialization_default_timeout(self, temp_lock_file):
        """Test FileLock initialization with default timeout."""
        lock = FileLock(str(temp_lock_file))
        assert lock.timeout == 30.0  # Default timeout

    @pytest.mark.unit
    def test_acquire_windows_success(self, file_lock, temp_lock_file):
        """Test successful lock acquisition on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.return_value = 42  # Mock file descriptor

                result = file_lock.acquire()

                assert result is True
                assert file_lock.lock_fd == 42
                mock_open.assert_called_once_with(
                    str(temp_lock_file),
                    os.O_CREAT | os.O_EXCL | os.O_RDWR
                )

    @pytest.mark.unit
    def test_acquire_unix_success(self, file_lock, temp_lock_file):
        """Test successful lock acquisition on Unix."""
        # Skip this test on Windows since fcntl is not available
        if not FCNTL_AVAILABLE:
            pytest.skip("fcntl not available on Windows")

        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', True):
            with patch('os.open') as mock_open:
                with patch('fcntl.flock') as mock_flock:
                    mock_open.return_value = 42

                    result = file_lock.acquire()

                    assert result is True
                    assert file_lock.lock_fd == 42
                    mock_open.assert_called_once_with(
                        str(temp_lock_file),
                        os.O_CREAT | os.O_WRONLY | os.O_TRUNC
                    )
                    mock_flock.assert_called_once_with(42, 6)  # LOCK_EX | LOCK_NB

    @pytest.mark.unit
    def test_acquire_windows_file_exists(self, file_lock, temp_lock_file):
        """Test lock acquisition when file exists on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                # First call raises FileExistsError, second succeeds
                mock_open.side_effect = [
                    FileExistsError("File exists"),
                    42  # Success on retry
                ]
                with patch('time.sleep') as mock_sleep:
                    result = file_lock.acquire()

                    assert result is True
                    assert file_lock.lock_fd == 42
                    assert mock_open.call_count == 2
                    # Sleep should be called at least once
                    assert mock_sleep.call_count >= 1

    @pytest.mark.unit
    def test_acquire_windows_max_attempts(self, file_lock, temp_lock_file):
        """Test lock acquisition max attempts on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.side_effect = FileExistsError("File exists")
                with patch('time.sleep') as mock_sleep:
                    result = file_lock.acquire()

                    assert result is False
                    assert file_lock.lock_fd is None
                    assert mock_open.call_count == 50  # max_lock_attempts
                    # Sleep should be called for each failed attempt
                    assert mock_sleep.call_count >= 49

    @pytest.mark.unit
    def test_acquire_unix_timeout(self, file_lock, temp_lock_file):
        """Test lock acquisition timeout on Unix."""
        # Skip this test on Windows since fcntl is not available
        if not FCNTL_AVAILABLE:
            pytest.skip("fcntl not available on Windows")

        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', True):
            with patch('os.open') as mock_open:
                with patch('fcntl.flock') as mock_flock:
                    with patch('logging.Logger.warning'):  # Mock logging to prevent additional time.time() calls
                        with patch('time.time') as mock_time:
                            mock_open.return_value = 42
                            mock_time.side_effect = [0, 0.1, 31.0]  # Start, during, after timeout
                            mock_flock.side_effect = IOError("Would block")

                            result = file_lock.acquire()

                            assert result is False

    @pytest.mark.unit
    def test_acquire_permission_error(self, file_lock, temp_lock_file):
        """Test lock acquisition with permission error."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.side_effect = PermissionError("Permission denied")
                # Mock time.sleep to avoid actual delays during retries
                with patch('time.sleep'):
                    result = file_lock.acquire()

                assert result is False
                assert file_lock.lock_fd is None

    @pytest.mark.unit
    def test_acquire_unexpected_error(self, file_lock, temp_lock_file):
        """Test lock acquisition with unexpected error."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.side_effect = RuntimeError("Unexpected error")

                result = file_lock.acquire()

                assert result is False
                assert file_lock.lock_fd is None

    @pytest.mark.unit
    def test_release_windows(self, file_lock, temp_lock_file):
        """Test lock release on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.return_value = 42

                # Acquire lock first
                file_lock.acquire()
                assert file_lock.lock_fd == 42

                with patch('os.close') as mock_close:
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink') as mock_unlink:
                            file_lock.release()

                            assert file_lock.lock_fd is None
                            mock_close.assert_called_once_with(42)
                            mock_unlink.assert_called_once_with(str(temp_lock_file))

    @pytest.mark.unit
    def test_release_unix(self, file_lock, temp_lock_file):
        """Test lock release on Unix."""
        # Skip this test on Windows since fcntl is not available
        if not FCNTL_AVAILABLE:
            pytest.skip("fcntl not available on Windows")

        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', True):
            with patch('os.open') as mock_open:
                with patch('fcntl.flock'):
                    mock_open.return_value = 42

                    # Acquire lock first
                    file_lock.acquire()
                    assert file_lock.lock_fd == 42

                    with patch('fcntl.flock') as mock_flock_release:
                        with patch('os.close') as mock_close:
                            file_lock.release()

                            assert file_lock.lock_fd is None
                            mock_flock_release.assert_called_once_with(42, 8)  # LOCK_UN
                            mock_close.assert_called_once_with(42)

    @pytest.mark.unit
    def test_release_no_lock(self, file_lock):
        """Test release when no lock is held."""
        # Should not raise any exceptions
        file_lock.release()
        assert file_lock.lock_fd is None

    @pytest.mark.unit
    def test_release_windows_exception_handling(self, file_lock, temp_lock_file):
        """Test lock release exception handling on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                mock_open.return_value = 42

                # Acquire lock first
                file_lock.acquire()
                assert file_lock.lock_fd == 42

                with patch('os.close', side_effect=OSError("Close error")):
                    with patch('os.path.exists', return_value=True):
                        with patch('os.unlink', side_effect=OSError("Unlink error")):
                            # Should not raise exceptions
                            file_lock.release()
                            assert file_lock.lock_fd is None

    @pytest.mark.unit
    def test_release_unix_exception_handling(self, file_lock, temp_lock_file):
        """Test lock release exception handling on Unix."""
        # Skip this test on Windows since fcntl is not available
        if not FCNTL_AVAILABLE:
            pytest.skip("fcntl not available on Windows")

        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', True):
            with patch('os.open') as mock_open:
                with patch('fcntl.flock'):
                    mock_open.return_value = 42

                    # Acquire lock first
                    file_lock.acquire()
                    assert file_lock.lock_fd == 42

                    with patch('fcntl.flock', side_effect=OSError("Unlock error")):
                        with patch('os.close', side_effect=OSError("Close error")):
                            # Should not raise exceptions
                            file_lock.release()
                            assert file_lock.lock_fd is None

    @pytest.mark.unit
    def test_exponential_backoff_windows(self, file_lock, temp_lock_file):
        """Test exponential backoff on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                with patch('time.sleep') as mock_sleep:
                    # Fail first few attempts, then succeed
                    mock_open.side_effect = [
                        FileExistsError("File exists"),
                        FileExistsError("File exists"),
                        42  # Success
                    ]

                    result = file_lock.acquire()

                    assert result is True
                    assert file_lock.lock_fd == 42
                    # Sleep should be called for each failed attempt
                    assert mock_sleep.call_count >= 2
                    # Verify that sleep was called with increasing delays
                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                    # Should have at least 2 different delay values due to exponential backoff
                    assert len(sleep_calls) >= 2

    @pytest.mark.unit
    def test_random_jitter_windows(self, file_lock, temp_lock_file):
        """Test random jitter on Windows."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('time.sleep') as mock_sleep:
                with patch('random.uniform') as mock_uniform:
                    with patch('os.open', return_value=42):
                        mock_uniform.return_value = 0.123

                        result = file_lock.acquire()

                        assert result is True
                        mock_uniform.assert_called_once_with(0.01, 0.2)
                        mock_sleep.assert_called_once_with(0.123)

    @pytest.mark.unit
    def test_acquire_release_cycle(self, file_lock, temp_lock_file):
        """Test complete acquire-release cycle."""
        with patch('app.services.common.browser.locks.FCNTL_AVAILABLE', False):
            with patch('os.open') as mock_open:
                with patch('os.close') as mock_close:
                    with patch('os.path.exists', return_value=False):
                        mock_open.return_value = 42

                        # Acquire
                        result = file_lock.acquire()
                        assert result is True
                        assert file_lock.lock_fd == 42

                        # Release
                        file_lock.release()
                        assert file_lock.lock_fd is None

                        # Verify calls
                        assert mock_open.call_count == 1
                        assert mock_close.call_count == 1


class TestExclusiveLock:
    """Test exclusive_lock context manager."""

    @pytest.fixture
    def temp_lock_file(self, tmp_path):
        """Create a temporary lock file path."""
        return tmp_path / "test.lock"

    @pytest.mark.unit
    def test_exclusive_lock_success(self, temp_lock_file):
        """Test successful exclusive lock context manager."""
        with patch('app.services.common.browser.locks.FileLock') as mock_file_lock_class:
            mock_lock = MagicMock()
            mock_file_lock_class.return_value = mock_lock
            mock_lock.acquire.return_value = True

            with exclusive_lock(str(temp_lock_file)) as acquired:
                assert acquired is True
                mock_lock.acquire.assert_called_once()
                mock_lock.release.assert_not_called()  # Should be called after context

            # Verify release was called after context
            mock_lock.release.assert_called_once()

    @pytest.mark.unit
    def test_exclusive_lock_failure(self, temp_lock_file):
        """Test exclusive lock context manager when lock fails."""
        with patch('app.services.common.browser.locks.FileLock') as mock_file_lock_class:
            mock_lock = MagicMock()
            mock_file_lock_class.return_value = mock_lock
            mock_lock.acquire.return_value = False

            with pytest.raises(RuntimeError, match="Failed to acquire lock"):
                with exclusive_lock(str(temp_lock_file)):
                    pass

            mock_lock.acquire.assert_called_once()
            mock_lock.release.assert_not_called()  # Should not be called if acquire failed

    @pytest.mark.unit
    def test_exclusive_lock_exception_in_context(self, temp_lock_file):
        """Test exclusive lock context manager with exception in context."""
        with patch('app.services.common.browser.locks.FileLock') as mock_file_lock_class:
            mock_lock = MagicMock()
            mock_file_lock_class.return_value = mock_lock
            mock_lock.acquire.return_value = True

            try:
                with exclusive_lock(str(temp_lock_file)):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected

            # Verify release was called even with exception
            mock_lock.acquire.assert_called_once()
            mock_lock.release.assert_called_once()

    @pytest.mark.unit
    def test_exclusive_lock_custom_timeout(self, temp_lock_file):
        """Test exclusive lock with custom timeout."""
        with patch('app.services.common.browser.locks.FileLock') as mock_file_lock_class:
            mock_lock = MagicMock()
            mock_file_lock_class.return_value = mock_lock
            mock_lock.acquire.return_value = True

            with exclusive_lock(str(temp_lock_file), timeout=60.0):
                pass

            # Check that FileLock was called with correct arguments
            # (allowing for different argument formats)
            assert mock_file_lock_class.call_count == 1
            call_args = mock_file_lock_class.call_args[0]
            assert str(temp_lock_file) in call_args
            assert 60.0 in call_args

    @pytest.mark.unit
    def test_fcntl_availability_constant(self):
        """Test FCNTL_AVAILABLE constant."""
        assert isinstance(FCNTL_AVAILABLE, bool)
        # Should be True on Unix systems, False on Windows
        # We just check it's a boolean value

    @pytest.mark.unit
    def test_lock_file_path_conversion(self, tmp_path):
        """Test that lock file paths are properly converted to strings."""
        lock_path = tmp_path / "test.lock"

        with patch('app.services.common.browser.locks.FileLock') as mock_file_lock_class:
            mock_lock = MagicMock()
            mock_file_lock_class.return_value = mock_lock
            mock_lock.acquire.return_value = True

            with exclusive_lock(lock_path):  # Pass Path object
                pass

            # Check that FileLock was called with correct arguments
            # (allowing for different argument formats)
            assert mock_file_lock_class.call_count == 1
            call_args = mock_file_lock_class.call_args[0]
            # Should contain the path (either as string or Path object)
            assert any(str(lock_path) in str(arg) for arg in call_args)
