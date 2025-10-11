"""Cross-platform file locking utilities for Chromium user data."""

import logging
import os
import random
import time
from contextlib import contextmanager
from typing import Optional

# fcntl is not available on Windows, so we need to handle this gracefully
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileLock:
    """Cross-platform file-based lock with timeout support."""

    def __init__(self, lock_file: str, timeout: float = 30.0):
        """Initialize the file lock.

        Args:
            lock_file: Path to the lock file
            timeout: Maximum time to wait for lock (seconds)
        """
        self.lock_file = lock_file
        self.timeout = timeout
        self.lock_fd: Optional[int] = None

    def acquire(self) -> bool:
        """Acquire the lock with timeout."""
        if not FCNTL_AVAILABLE:
            return self._windows_acquire()
        else:
            return self._unix_acquire()

    def _windows_acquire(self) -> bool:
        """Acquire lock on Windows using exclusive file creation."""
        # Small random jitter to reduce thundering herd
        try:
            time.sleep(random.uniform(0.01, 0.2))
        except Exception:
            pass

        max_lock_attempts = 50
        delay = 0.05

        for attempt in range(1, max_lock_attempts + 1):
            try:
                # Attempt to create the lock file exclusively; succeeds only if it doesn't exist
                self.lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                logger.debug(f"Acquired exclusive Windows lock: {self.lock_file}")
                return True
            except (FileExistsError, PermissionError):
                # Lock is held by another process; retry with exponential backoff
                if attempt == max_lock_attempts:
                    logger.warning(f"Failed to acquire lock after {max_lock_attempts} attempts")
                    return False
                time.sleep(delay)
                delay = min(2.0, delay * 2)
            except Exception as e:
                logger.warning(f"Unexpected error acquiring lock: {e}")
                return False

        return False

    def _unix_acquire(self) -> bool:
        """Acquire lock on Unix/Linux using fcntl."""
        try:
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)

            # Try to acquire exclusive lock with timeout
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    logger.debug(f"Acquired exclusive Unix lock: {self.lock_file}")
                    return True
                except (IOError, BlockingIOError):
                    if time.time() - start_time > self.timeout:
                        logger.warning(f"Timeout waiting for lock: {self.lock_file}")
                        self.release()
                        return False
                    time.sleep(0.1)
        except Exception as e:
            logger.warning(f"Failed to acquire Unix lock: {e}")
            self.release()
            return False

    def release(self) -> None:
        """Release the lock."""
        if self.lock_fd is None:
            return

        try:
            if FCNTL_AVAILABLE:
                # Unix/Linux: release fcntl lock
                try:
                    fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                    os.close(self.lock_fd)
                except Exception as e:
                    logger.warning(f"Failed to release fcntl lock: {e}")
            else:
                # Windows: explicitly close descriptor and remove lock file
                try:
                    if self.lock_fd is not None:
                        try:
                            os.close(self.lock_fd)
                        except Exception as e:
                            logger.warning(f"Failed to close Windows lock fd: {e}")
                    if os.path.exists(self.lock_file):
                        os.unlink(self.lock_file)
                except Exception as e:
                    logger.warning(f"Failed to remove Windows lock file: {e}")
            logger.debug(f"Released lock: {self.lock_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup lock: {e}")
        finally:
            self.lock_fd = None


@contextmanager
def exclusive_lock(lock_file: str, timeout: float = 30.0):
    """Context manager for exclusive file locking.

    Args:
        lock_file: Path to the lock file
        timeout: Maximum time to wait for lock (seconds)

    Yields:
        True if lock acquired, False otherwise

    Raises:
        RuntimeError: If lock cannot be acquired
    """
    lock = FileLock(lock_file, timeout)
    acquired = lock.acquire()

    if not acquired:
        raise RuntimeError(f"Failed to acquire lock: {lock_file}")

    try:
        yield True
    finally:
        lock.release()
