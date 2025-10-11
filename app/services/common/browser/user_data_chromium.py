"""Manages Chromium user data directories with master/clone architecture.

Provides persistent Chromium profiles for TikTok downloads and browse sessions.
Mirrors Camoufox user data management semantics for Chromium.
"""

import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Dict, Any, Optional, Tuple

from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.locks import exclusive_lock
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import (
    ChromiumProfileManager,
    clone_profile,
    create_temporary_profile,
)
from app.services.common.browser.types import (
    DiskUsageStats,
    CleanupResult,
    CookieExportResult,
    StorageStateResult,
)
from app.services.common.browser.utils import (
    best_effort_close_sqlite,
    chmod_tree,
    get_directory_size,
    rmtree_with_retries,
)

logger = logging.getLogger(__name__)


class ChromiumUserDataManager:
    """Orchestrator class for Chromium user data management using extracted concerns."""

    def __init__(self, user_data_dir: Optional[str] = None):
        """Initialize the Chromium user data manager.

        Args:
            user_data_dir: Root directory for Chromium profiles. If None,
                          user data management is disabled.
        """
        self.user_data_dir = user_data_dir
        self.enabled = user_data_dir is not None

        # Initialize extracted managers
        self.path_manager = ChromiumPathManager(user_data_dir)
        self._write_lock = threading.Lock()  # In-process mutex for DB replacement operations

        if self.enabled:
            self.profile_manager = ChromiumProfileManager(
                self.path_manager.metadata_file,
                self.path_manager.fingerprint_file
            )
            self.cookie_manager = ChromiumCookieManager(self.path_manager.get_cookies_db_path())

    @contextmanager
    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
        """Get a user data directory context for Chromium operations.

        Args:
            mode: Either 'read' (clone master) or 'write' (use master with lock)

        Yields:
            Tuple of (effective_directory_path, cleanup_function)

        Raises:
            ValueError: If mode is not 'read' or 'write'
            RuntimeError: If user data management is disabled or lock cannot be acquired
        """
        # Disabled path: create a temporary profile and ensure auto-cleanup
        if not self.enabled:
            logger.warning("Chromium user data management disabled, using temporary profile")
            temp_dir, cleanup_func = create_temporary_profile()
            try:
                yield temp_dir, cleanup_func
            except Exception as e:
                logger.error(f"Error in Chromium user data context mode={mode}: {e}")
                raise
            finally:
                try:
                    if callable(cleanup_func):
                        cleanup_func()
                except Exception as e:
                    logger.warning(f"Automatic cleanup failed for temp directory {temp_dir}: {e}")
            return

        # Validate mode for enabled path
        if mode not in ('read', 'write'):
            raise ValueError(f"user_data_mode must be 'read' or 'write', got '{mode}'")

        effective_dir: Optional[str] = None
        cleanup_func: Optional[Callable[[], None]] = None

        try:
            if mode == 'write':
                effective_dir, cleanup_func = self._write_mode_context()
            else:  # mode == 'read'
                effective_dir, cleanup_func = self._read_mode_context()

            yield effective_dir, cleanup_func
        except Exception as e:
            logger.error(f"Error in Chromium user data context mode={mode}: {e}")
            raise
        finally:
            try:
                if callable(cleanup_func):
                    cleanup_func()
            except Exception as e:
                logger.warning(f"Automatic cleanup failed for Chromium user data context: {e}")

    def _write_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Write mode context: uses master directory with exclusive lock."""
        # Ensure directories exist
        self.path_manager.ensure_directories_exist()

        # Acquire exclusive lock
        with exclusive_lock(str(self.path_manager.lock_file), timeout=30.0) as acquired:
            if not acquired:
                raise RuntimeError("Failed to acquire Chromium profile lock for write mode")

            # Initialize profile metadata
            self.profile_manager.ensure_metadata()

        cleanup_func: Callable[[], None] = lambda: None  # Lock cleanup handled by context manager
        return str(self.path_manager.master_dir), cleanup_func

    def _read_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Read mode context: clones master directory to temporary location."""
        clone_dir = self.path_manager.generate_clone_path()

        # Ensure directories exist
        self.path_manager.ensure_directories_exist()

        # Check if master exists, create empty clone if not
        if not self.path_manager.master_dir.exists():
            logger.warning(f"Chromium master profile not found at {self.path_manager.master_dir}, creating empty clone")
            clone_dir.mkdir(parents=True, exist_ok=True)

            def cleanup():
                try:
                    if clone_dir.exists():
                        chmod_tree(clone_dir, 0o777)
                        best_effort_close_sqlite(clone_dir)
                        if rmtree_with_retries(clone_dir, max_attempts=12, initial_delay=0.1):
                            logger.debug(f"Cleaned up Chromium clone directory: {clone_dir}")
                        else:
                            logger.warning(f"Failed to cleanup Chromium clone directory after retries: {clone_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup Chromium clone directory: {e}")

            return str(clone_dir), cleanup

        # Clone from master directory
        return clone_profile(self.path_manager.master_dir, clone_dir)

    def export_cookies(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """Export cookies from the master profile.

        Args:
            format: Export format ('json' or 'storage_state')

        Returns:
            Cookie data in the specified format, or None if export fails
        """
        if not self.enabled:
            logger.warning("Chromium user data management disabled, cannot export cookies")
            return None

        if not self.path_manager.master_dir.exists():
            logger.warning(f"Chromium master profile not found at {self.path_manager.master_dir}")
            return None

        try:
            # Read cookies from database
            cookies = self.cookie_manager.read_cookies_from_db()

            if format == "storage_state":
                # Convert to Playwright storage_state format
                storage_state: StorageStateResult = {
                    "cookies": [
                        {
                            "name": cookie["name"],
                            "value": cookie["value"],
                            "domain": cookie["domain"],
                            "path": cookie["path"],
                            "expires": cookie.get("expires", -1),
                            "httpOnly": cookie.get("httpOnly", False),
                            "secure": cookie.get("secure", False),
                            "sameSite": cookie.get("sameSite", "None")
                        }
                        for cookie in cookies
                    ],
                    "origins": []
                }
                return storage_state
            else:
                # JSON format
                cookie_result: CookieExportResult = {
                    "format": format,
                    "cookies": cookies,
                    "profile_metadata": self.profile_manager.read_metadata(),
                    "cookies_available": bool(cookies),
                    "master_profile_path": str(self.path_manager.master_dir),
                    "export_timestamp": time.time()
                }
                return cookie_result

        except Exception as e:
            logger.warning(f"Failed to export cookies: {e}")
            return None

    def import_cookies(self, cookie_data: Dict[str, Any]) -> bool:
        """Import cookies to the master profile.

        Args:
            cookie_data: Cookie data in JSON or storage_state format

        Returns:
            True if import succeeded, False otherwise
        """
        if not self.enabled:
            logger.warning("Chromium user data management disabled, cannot import cookies")
            return False

        # Proactively initialize the master profile directories
        try:
            self.path_manager.ensure_directories_exist()
            default_dir = self.path_manager.master_dir / "Default"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.profile_manager.ensure_metadata()
        except Exception as e:
            logger.warning(f"Failed to initialize Chromium master profile directories: {e}")
            return False

        try:
            # Extract cookies based on format
            if cookie_data.get("format") == "storage_state":
                cookies = cookie_data.get("cookies", [])
            else:
                cookies = cookie_data.get("cookies", [])

            if not cookies:
                logger.info("No cookies to import")
                self.profile_manager.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_count": 0,
                    "cookie_import_status": "success"
                })
                return True

            # Import cookies to database
            success = self.cookie_manager.write_cookies_to_db(cookies)

            if success:
                self.profile_manager.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_count": len(cookies),
                    "cookie_import_status": "success"
                })
                logger.info(f"Successfully imported {len(cookies)} cookies to Chromium master profile")
                return True
            else:
                self.profile_manager.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_status": "failed"
                })
                return False

        except Exception as e:
            logger.warning(f"Failed to import cookies: {e}")
            self.profile_manager.update_metadata({
                "last_cookie_import": time.time(),
                "cookie_import_status": f"error: {str(e)}"
            })
            return False

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""
        if not self.enabled:
            return
        self.profile_manager.update_metadata(updates)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current metadata from master profile."""
        if not self.enabled:
            return None
        return self.profile_manager.read_metadata()

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""
        if not self.enabled:
            return None
        return self.profile_manager.get_browserforge_fingerprint()

    def is_enabled(self) -> bool:
        """Check if Chromium user data management is enabled."""
        return self.enabled

    def get_master_dir(self) -> Optional[str]:
        """Get the master directory path if enabled."""
        return self.path_manager.get_master_dir()

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> Dict[str, int]:
        """Clean up old clone directories to prevent disk bloat.

        Args:
            max_age_hours: Maximum age of clone directories in hours
            max_count: Maximum number of clone directories to keep

        Returns:
            Dictionary with cleanup statistics
        """
        if not self.enabled or not self.path_manager.clones_dir.exists():
            return {"cleaned": 0, "remaining": 0, "errors": 0}

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            error_count = 0

            # Get all clone directories with their stats
            clone_stats = []
            for clone_path in self.path_manager.clones_dir.iterdir():
                if clone_path.is_dir():
                    try:
                        stat = clone_path.stat()
                        age_seconds = current_time - stat.st_mtime
                        clone_stats.append({
                            "path": clone_path,
                            "age": age_seconds,
                            "size": get_directory_size(clone_path)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to stat clone directory {clone_path}: {e}")
                        error_count += 1

            # Sort by age (oldest first) and size
            clone_stats.sort(key=lambda x: (x["age"], -x["size"]))

            # Determine which clones to remove
            to_remove = []
            remaining_count = len(clone_stats)

            for i, clone_stat in enumerate(clone_stats):
                if clone_stat["age"] > max_age_seconds or i >= max_count:
                    to_remove.append(clone_stat)

            # Remove the identified clones
            for clone_stat in to_remove:
                path = clone_stat["path"]
                try:
                    # Loosen permissions and best-effort close sqlite handles
                    chmod_tree(path, 0o777)
                    best_effort_close_sqlite(path)
                    if rmtree_with_retries(path, max_attempts=12, initial_delay=0.1):
                        cleaned_count += 1
                        remaining_count -= 1
                        logger.debug(f"Cleaned up old clone: {path} "
                                     f"(age: {clone_stat['age']/3600:.1f}h, size: {clone_stat['size']}MB)")
                    else:
                        logger.warning(f"Could not remove clone directory after retries: {path}")
                        error_count += 1
                except Exception as e:
                    logger.warning(f"Failed to remove clone directory {path}: {e}")
                    error_count += 1

            total_size_saved = sum(cs["size"] for cs in to_remove)
            self.profile_manager.update_metadata({
                "last_cleanup": current_time,
                "last_cleanup_count": cleaned_count,
                "last_cleanup_size_saved": total_size_saved,
                "remaining_clones": remaining_count
            })

            logger.info(f"Cleanup completed: removed {cleaned_count} clones, "
                        f"freed {total_size_saved}MB, {remaining_count} remaining, {error_count} errors")

            result: CleanupResult = {
                "cleaned": cleaned_count,
                "remaining": remaining_count,
                "errors": error_count,
                "size_saved_mb": total_size_saved
            }
            return result

        except Exception as e:
            logger.error(f"Failed to cleanup old clones: {e}")
            return {"cleaned": 0, "remaining": 0, "errors": 1}

    def _copytree_recursive(self, src: Path, dst: Path) -> None:
        """Recursively copy Chromium user data from src to dst, delegating to common utility.

        Args:
            src: Source directory to copy from
            dst: Destination directory to copy to
        """
        from app.services.common.browser.utils import copytree_recursive
        copytree_recursive(src, dst)

    def get_disk_usage_stats(self) -> Dict[str, Any]:
        """Get disk usage statistics for the user data directories.

        Returns:
            Dictionary with disk usage information
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            master_size = (
                get_directory_size(self.path_manager.master_dir)
                if self.path_manager.master_dir.exists() else 0
            )
            clones_size = (
                get_directory_size(self.path_manager.clones_dir)
                if self.path_manager.clones_dir.exists() else 0
            )
            total_size = master_size + clones_size

            clone_count = len(
                [d for d in self.path_manager.clones_dir.iterdir() if d.is_dir()]
            ) if self.path_manager.clones_dir.exists() else 0

            # Get metadata
            metadata = self.profile_manager.read_metadata() or {}

            stats: DiskUsageStats = {
                "enabled": True,
                "master_size_mb": master_size,
                "clones_size_mb": clones_size,
                "total_size_mb": total_size,
                "clone_count": clone_count,
                "master_dir": str(self.path_manager.master_dir),
                "clones_dir": str(self.path_manager.clones_dir),
                "last_cleanup": metadata.get("last_cleanup"),
                "last_cleanup_count": metadata.get("last_cleanup_count", 0),
                "last_cleanup_size_saved": metadata.get("last_cleanup_size_saved", 0)
            }
            return stats

        except Exception as e:
            logger.warning(f"Failed to get disk usage stats: {e}")
            return {"enabled": True, "error": str(e)}
