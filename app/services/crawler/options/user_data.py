import os
import shutil
import tempfile
import uuid
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Tuple, Optional

# fcntl is not available on Windows, so we need to handle this gracefully
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)


@contextmanager
def user_data_context(base_dir: str, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
    """Context manager for managing user data directories with exclusive locking.

    Args:
        base_dir: Root directory for user data
        mode: Either 'read' or 'write'
        
    Yields:
        Tuple of (effective_directory_path, cleanup_function)
        
    Raises:
        ValueError: If mode is not 'read' or 'write'
        RuntimeError: If write lock cannot be acquired
    """
    if mode not in ('read', 'write'):
        raise ValueError(f"user_data_mode must be 'read' or 'write', got '{mode}'")
    
    base_path = Path(base_dir)
    
    try:
        if mode == 'write':
            effective_dir, cleanup_func = _write_mode_context(base_path)
        else:  # mode == 'read'
            effective_dir, cleanup_func = _read_mode_context(base_path)
        
        yield effective_dir, cleanup_func
        
    except Exception as e:
        logger.error(f"Error in user_data_context mode={mode}: {e}")
        raise


def _write_mode_context(base_path: Path) -> Tuple[str, Callable[[], None]]:
    """Write mode context: uses master directory with exclusive lock."""
    master_dir = base_path / 'master'
    lock_file = base_path / 'master.lock'
    
    # Ensure master directory exists
    master_dir.mkdir(parents=True, exist_ok=True)
    
    # Acquire exclusive lock
    lock_fd = None
    if not FCNTL_AVAILABLE:
        logger.warning("fcntl not available on this platform, using exclusive fallback")
        # Use a simpler approach for systems without fcntl (like Windows)
        lock_file.touch()
    else:
        try:
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            
            # Try to acquire exclusive lock with timeout
            timeout = 30  # 30 seconds timeout
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break  # Lock acquired
                except (IOError, BlockingIOError):
                    if time.time() - start_time > timeout:
                        raise RuntimeError("Timeout waiting for exclusive user-data lock")
                    time.sleep(0.1)
            
            logger.debug(f"Acquired exclusive lock for write mode on {master_dir}")
            
        except Exception as e:
            if lock_fd is not None:
                try:
                    os.close(lock_fd)
                except:
                    pass
            raise RuntimeError(f"Failed to acquire lock for write mode: {e}")
    
    # Cleanup function: release lock and cleanup lock file
    def cleanup():
        try:
            if FCNTL_AVAILABLE and lock_fd is not None:
                # Unix/Linux: release fcntl lock
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except Exception as e:
                    logger.warning(f"Failed to release fcntl lock: {e}")
            else:
                # Windows: cleanup lock file
                try:
                    if lock_file.exists():
                        lock_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove lock file: {e}")
            
            logger.debug(f"Released exclusive lock for write mode on {master_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup lock: {e}")
    
    return str(master_dir), cleanup


def _read_mode_context(base_path: Path) -> Tuple[str, Callable[[], None]]:
    """Read mode context: clones master directory to temporary location."""
    master_dir = base_path / 'master'
    clone_dir = base_path / 'clones' / str(uuid.uuid4())
    
    # Ensure master directory exists
    if not master_dir.exists():
        clone_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created empty clone directory: {clone_dir}")
        
        def cleanup():
            try:
                if clone_dir.exists():
                    shutil.rmtree(clone_dir)
                    logger.debug(f"Cleaned up clone directory: {clone_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup clone directory: {e}")
        
        return str(clone_dir), cleanup
    
    # Clone from master
    try:
        clone_dir.mkdir(parents=True, exist_ok=True)
        _copytree_recursive(master_dir, clone_dir)
        logger.debug(f"Created clone directory: {clone_dir}")
        
        # Cleanup function: remove clone directory
        def cleanup():
            try:
                if clone_dir.exists():
                    shutil.rmtree(clone_dir)
                    logger.debug(f"Cleaned up clone directory: {clone_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup clone directory: {e}")
        
        return str(clone_dir), cleanup
        
    except Exception as e:
        # Cleanup on error
        if clone_dir.exists():
            try:
                shutil.rmtree(clone_dir)
            except:
                pass
        raise RuntimeError(f"Failed to create clone from {master_dir}: {e}")


def _copytree_recursive(src: Path, dst: Path) -> None:
    """Recursively copy directory tree, preserving metadata."""
    # Create destination
    dst.mkdir(parents=True, exist_ok=True)
    
    # Copy contents
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            _copytree_recursive(item, dest_item)
        else:
            shutil.copy2(item, dest_item)