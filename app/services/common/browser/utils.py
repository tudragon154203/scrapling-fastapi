"""Utilities for file operations, cleanup, and resource management."""

import os
import random
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Optional


def copytree_recursive(src: Path, dst: Path) -> None:
    """Recursively copy directory tree, preserving metadata.

    Args:
        src: Source directory
        dst: Destination directory
    """
    # Create destination
    dst.mkdir(parents=True, exist_ok=True)

    # Copy contents
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            copytree_recursive(item, dest_item)
        else:
            # shutil.copy2 does not leave open handles; use directly
            shutil.copy2(item, dest_item)


def chmod_tree(path: Path, mode: int = 0o777) -> None:
    """Recursively chmod a directory tree to mitigate Windows permission/lock issues.

    Args:
        path: Root path to modify
        mode: Permission mode (default 0o777 for maximal permissions)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        if path.exists():
            try:
                os.chmod(path, mode)
            except Exception:
                pass
            for p in path.rglob("*"):
                try:
                    os.chmod(p, mode)
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Best-effort chmod tree failed for {path}: {e}")


def best_effort_close_sqlite(root: Path) -> None:
    """Best-effort attempt to ensure SQLite-related file handles are closed before deletion.

    Args:
        root: Root directory to search for SQLite files
    """
    try:
        for db in root.rglob("*"):
            if db.is_file():
                name = db.name.lower()
                if (db.suffix in (".db", ".sqlite") or
                    "cookies" in name or
                    name.endswith("-wal") or
                        name.endswith("-journal")):
                    try:
                        # Open and immediately close to release any lingering handles in this process
                        with sqlite3.connect(db):
                            pass
                    except Exception:
                        # Ignore errors; other processes may still hold locks
                        pass
    except Exception:
        pass


def rmtree_with_retries(
    target: Path,
    max_attempts: int = 10,
    initial_delay: float = 0.1
) -> bool:
    """Robust deletion with chmod, onerror handling, and exponential backoff.

    Args:
        target: Directory to remove
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)

    Returns:
        True if deletion succeeded, False otherwise
    """
    if not target.exists():
        return True

    delay = initial_delay
    last_err: Optional[Exception] = None

    def _onerror(func, path, exc_info):
        try:
            os.chmod(path, 0o777)
        except Exception:
            pass
        try:
            if os.path.isdir(path):
                os.rmdir(path)
            else:
                os.unlink(path)
        except Exception:
            pass

    for attempt in range(1, max_attempts + 1):
        try:
            # Loosen permissions before each attempt
            chmod_tree(target, 0o777)
            shutil.rmtree(target, onerror=_onerror)
            return True
        except Exception as e:
            last_err = e
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"shutil.rmtree failed for {target} (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(delay + random.uniform(0, 0.2))
            delay = min(2.0, delay * 2)

    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to delete {target} after {max_attempts} attempts: {last_err}")
    return False


def get_directory_size(path: Path) -> float:
    """Get directory size in megabytes.

    Args:
        path: Directory to measure

    Returns:
        Size in megabytes, rounded to 2 decimal places
    """
    try:
        total_bytes = 0
        for item in path.rglob("*"):
            if item.is_file():
                total_bytes += item.stat().st_size
        return round(total_bytes / (1024 * 1024), 2)  # Convert to MB
    except Exception:
        return 0.0


def atomic_file_replace(source: Path, destination: Path, max_attempts: int = 25) -> bool:
    """Atomically replace a file with retry logic for Windows file locking.

    Args:
        source: Source file to move
        destination: Destination file to replace
        max_attempts: Maximum number of replacement attempts

    Returns:
        True if replacement succeeded, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)

    delay = 0.1
    last_err: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            # Best-effort: try to loosen file permissions on existing destination
            try:
                if destination.exists():
                    os.chmod(destination, 0o666)
            except Exception as chmod_err:
                logger.debug(f"Best-effort chmod before replace on {destination}: {chmod_err}")

            os.replace(source, destination)
            return True
        except (PermissionError, OSError) as e:
            last_err = e
            logger.warning(f"Atomic replace failed (attempt {attempt}/{max_attempts}): {e}")

            # Fallback: try unlink+replace
            if destination.exists():
                unlink_attempts = 10
                unlink_delay = 0.1
                for u_attempt in range(1, unlink_attempts + 1):
                    try:
                        os.unlink(destination)
                        break
                    except Exception as ue:
                        logger.warning(f"Unlink failed (attempt {u_attempt}/{unlink_attempts}): {ue}")
                        time.sleep(unlink_delay)
                        unlink_delay = min(5.0, unlink_delay * 2)

                # Retry replacement after unlink
                try:
                    os.replace(source, destination)
                    return True
                except (PermissionError, OSError) as e2:
                    logger.warning(f"Retry replace after unlink failed: {e2}")

                    # Final fallback: use shutil.move
                    try:
                        shutil.move(str(source), str(destination))
                        return True
                    except Exception as e3:
                        last_err = e3
        except Exception as e:
            last_err = e
            logger.warning(f"Unexpected error during replace: {e}")

        time.sleep(delay + random.uniform(0, 0.2))
        delay = min(5.0, delay * 2)

    logger.warning(f"Failed atomic replace after {max_attempts} attempts: {last_err}")
    return False
