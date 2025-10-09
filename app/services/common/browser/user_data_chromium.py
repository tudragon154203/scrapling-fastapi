import os
import json
import shutil
import tempfile
import uuid
import logging
import time
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Tuple, Optional, Dict, Any, List

try:
    import browserforge
    BROWSERFORGE_AVAILABLE = True
except ImportError:
    BROWSERFORGE_AVAILABLE = False

# fcntl is not available on Windows, so we need to handle this gracefully
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChromiumUserDataManager:
    """Manages Chromium user data directories with master/clone architecture.

    Provides persistent Chromium profiles for TikTok downloads and browse sessions.
    Mirrors Camoufox user data management semantics for Chromium.
    """

    def __init__(self, user_data_dir: Optional[str] = None):
        """Initialize the Chromium user data manager.

        Args:
            user_data_dir: Root directory for Chromium profiles. If None,
                          user data management is disabled.
        """
        self.user_data_dir = user_data_dir
        self.enabled = user_data_dir is not None
        if self.enabled:
            self.base_path = Path(user_data_dir)
            self.master_dir = self.base_path / 'master'
            self.clones_dir = self.base_path / 'clones'
            self.lock_file = self.base_path / 'chromium_profile.lock'
            self.metadata_file = self.master_dir / 'metadata.json'

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
        if not self.enabled:
            logger.warning("Chromium user data management disabled, using temporary profile")
            # Return empty temporary directory for backward compatibility
            temp_dir = tempfile.mkdtemp(prefix="chromium_temp_")

            def cleanup():
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

            yield temp_dir, cleanup
            return

        if mode not in ('read', 'write'):
            raise ValueError(f"user_data_mode must be 'read' or 'write', got '{mode}'")

        try:
            if mode == 'write':
                effective_dir, cleanup_func = self._write_mode_context()
            else:  # mode == 'read'
                effective_dir, cleanup_func = self._read_mode_context()

            yield effective_dir, cleanup_func
        except Exception as e:
            logger.error(f"Error in Chromium user data context mode={mode}: {e}")
            raise

    def _write_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Write mode context: uses master directory with exclusive lock."""
        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)

        # Acquire exclusive lock
        lock_fd = None
        if not FCNTL_AVAILABLE:
            logger.warning("fcntl not available on this platform, using exclusive fallback")
            # Use a simpler approach for systems without fcntl (like Windows)
            if self.lock_file.exists():
                raise RuntimeError("Chromium profile already in use (write mode)")
            self.lock_file.touch()
        else:
            try:
                lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
                # Try to acquire exclusive lock with timeout
                timeout = 30  # 30 seconds timeout
                start_time = time.time()
                while True:
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break  # Lock acquired
                    except (IOError, BlockingIOError):
                        if time.time() - start_time > timeout:
                            raise RuntimeError("Timeout waiting for exclusive Chromium profile lock")
                        time.sleep(0.1)
                logger.debug(f"Acquired exclusive lock for Chromium write mode on {self.master_dir}")
            except Exception as e:
                if lock_fd is not None:
                    try:
                        os.close(lock_fd)
                    except Exception:
                        pass
                raise RuntimeError(f"Failed to acquire Chromium profile lock: {e}")

        # Initialize metadata if not exists
        self._ensure_metadata()

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
                        if self.lock_file.exists():
                            self.lock_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to remove lock file: {e}")
                logger.debug(f"Released exclusive lock for Chromium write mode on {self.master_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup Chromium profile lock: {e}")

        return str(self.master_dir), cleanup

    def _read_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Read mode context: clones master directory to temporary location."""
        clone_id = str(uuid.uuid4())
        clone_dir = self.clones_dir / clone_id

        # Ensure directories exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.clones_dir.mkdir(parents=True, exist_ok=True)

        # Check if master exists
        if not self.master_dir.exists():
            logger.warning(f"Chromium master profile not found at {self.master_dir}, creating empty clone")
            clone_dir.mkdir(parents=True, exist_ok=True)

            def cleanup():
                try:
                    if clone_dir.exists():
                        shutil.rmtree(clone_dir, ignore_errors=True)
                        logger.debug(f"Cleaned up Chromium clone directory: {clone_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup Chromium clone directory: {e}")

            return str(clone_dir), cleanup

        # Clone from master
        try:
            clone_dir.mkdir(parents=True, exist_ok=True)
            self._copytree_recursive(self.master_dir, clone_dir)
            logger.debug(f"Created Chromium clone directory: {clone_dir}")

            def cleanup():
                try:
                    if clone_dir.exists():
                        shutil.rmtree(clone_dir, ignore_errors=True)
                        logger.debug(f"Cleaned up Chromium clone directory: {clone_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup Chromium clone directory {clone_dir}: {e}")

            return str(clone_dir), cleanup
        except Exception as e:
            # Cleanup on error
            if clone_dir.exists():
                try:
                    shutil.rmtree(clone_dir)
                except Exception:
                    pass
            raise RuntimeError(f"Failed to create Chromium clone from {self.master_dir}: {e}")

    def _ensure_metadata(self) -> None:
        """Ensure metadata file exists in master profile."""
        if not self.metadata_file.exists():
            # Get BrowserForge version if available
            browserforge_version = None
            if BROWSERFORGE_AVAILABLE:
                try:
                    browserforge_version = getattr(browserforge, '__version__', 'unknown')
                except Exception:
                    browserforge_version = 'unknown'

            metadata = {
                "version": "1.0",
                "created_at": time.time(),
                "last_updated": time.time(),
                "browserforge_version": browserforge_version,
                "profile_type": "chromium"
            }
            try:
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                logger.debug(f"Created Chromium profile metadata: {self.metadata_file}")

                # Generate and store BrowserForge fingerprint if available
                if BROWSERFORGE_AVAILABLE:
                    self._generate_browserforge_fingerprint()
            except Exception as e:
                logger.warning(f"Failed to create Chromium profile metadata: {e}")

    def _generate_browserforge_fingerprint(self) -> None:
        """Generate and store BrowserForge fingerprint for Chromium profile."""
        if not BROWSERFORGE_AVAILABLE:
            return

        try:
            # Generate fingerprint for Chromium
            fingerprint = browserforge.generate(
                browser='chrome',
                os='windows',
                mobile=False
            )

            # Store fingerprint in master profile
            fingerprint_file = self.master_dir / 'browserforge_fingerprint.json'
            with open(fingerprint_file, 'w') as f:
                json.dump(fingerprint, f, indent=2, default=str)

            logger.debug(f"Generated BrowserForge fingerprint: {fingerprint_file}")

            # Update metadata with fingerprint info
            self.update_metadata({
                "browserforge_fingerprint_generated": True,
                "browserforge_fingerprint_file": str(fingerprint_file)
            })
        except Exception as e:
            logger.warning(f"Failed to generate BrowserForge fingerprint: {e}")

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""
        if not BROWSERFORGE_AVAILABLE:
            return None

        fingerprint_file = self.master_dir / 'browserforge_fingerprint.json'
        if not fingerprint_file.exists():
            return None

        try:
            with open(fingerprint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read BrowserForge fingerprint: {e}")
            return None

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""
        if not self.enabled or not self.metadata_file.exists():
            return

        try:
            # Read existing metadata
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)

            # Update with new data
            metadata.update(updates)
            metadata["last_updated"] = time.time()

            # Write back
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.debug(f"Updated Chromium profile metadata: {updates}")
        except Exception as e:
            logger.warning(f"Failed to update Chromium profile metadata: {e}")

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current metadata from master profile."""
        if not self.enabled or not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read Chromium profile metadata: {e}")
            return None

    def _copytree_recursive(self, src: Path, dst: Path) -> None:
        """Recursively copy directory tree, preserving metadata."""
        # Create destination
        dst.mkdir(parents=True, exist_ok=True)

        # Copy contents
        for item in src.iterdir():
            dest_item = dst / item.name
            if item.is_dir():
                self._copytree_recursive(item, dest_item)
            else:
                shutil.copy2(item, dest_item)

    def is_enabled(self) -> bool:
        """Check if Chromium user data management is enabled."""
        return self.enabled

    def get_master_dir(self) -> Optional[str]:
        """Get the master directory path if enabled."""
        return str(self.master_dir) if self.enabled else None

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

        if not self.master_dir.exists():
            logger.warning(f"Chromium master profile not found at {self.master_dir}")
            return None

        try:
            # Path to Chromium cookies database
            cookies_db = self.master_dir / "Default" / "Cookies"

            if not cookies_db.exists():
                logger.debug(f"No cookies database found at {cookies_db}")
                return {
                    "format": format,
                    "cookies": [],
                    "profile_metadata": self.get_metadata(),
                    "cookies_available": False,
                    "master_profile_path": str(self.master_dir)
                }

            # Read cookies from SQLite database
            cookies = self._read_cookies_from_db(cookies_db)

            if format == "storage_state":
                # Convert to Playwright storage_state format
                storage_state = {
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
                return {
                    "format": format,
                    "cookies": cookies,
                    "profile_metadata": self.get_metadata(),
                    "cookies_available": len(cookies) > 0,
                    "master_profile_path": str(self.master_dir),
                    "export_timestamp": time.time()
                }

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

        if not self.master_dir.exists():
            logger.warning(f"Chromium master profile not found at {self.master_dir}")
            return False

        try:
            # Ensure Default directory exists
            default_dir = self.master_dir / "Default"
            default_dir.mkdir(parents=True, exist_ok=True)

            # Path to Chromium cookies database
            cookies_db = default_dir / "Cookies"

            # Extract cookies based on format
            if cookie_data.get("format") == "storage_state":
                cookies = cookie_data.get("cookies", [])
            else:
                cookies = cookie_data.get("cookies", [])

            if not cookies:
                logger.info("No cookies to import")
                return True

            # Import cookies to database
            success = self._write_cookies_to_db(cookies_db, cookies)

            if success:
                # Update metadata to reflect cookie import
                self.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_count": len(cookies),
                    "cookie_import_status": "success"
                })
                logger.info(f"Successfully imported {len(cookies)} cookies to Chromium master profile")
                return True
            else:
                self.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_status": "failed"
                })
                return False

        except Exception as e:
            logger.warning(f"Failed to import cookies: {e}")
            self.update_metadata({
                "last_cookie_import": time.time(),
                "cookie_import_status": f"error: {str(e)}"
            })
            return False

    def _read_cookies_from_db(self, cookies_db: Path) -> List[Dict[str, Any]]:
        """Read cookies from Chromium SQLite database."""
        try:
            # Create a temporary copy to avoid locking issues
            temp_db = cookies_db.parent / f"temp_cookies_{uuid.uuid4().hex}.db"
            shutil.copy2(cookies_db, temp_db)

            cookies = []
            with sqlite3.connect(temp_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query cookies table
                cursor.execute("""
                    SELECT creation_utc, host_key, name, value, path, expires_utc,
                           is_secure, is_httponly, samesite, last_access_utc,
                           has_expires, is_persistent
                    FROM cookies
                    ORDER BY creation_utc DESC
                """)

                for row in cursor.fetchall():
                    cookie = {
                        "name": row["name"],
                        "value": row["value"],
                        "domain": row["host_key"],
                        "path": row["path"],
                        "expires": row["expires_utc"] if row["has_expires"] else -1,
                        "httpOnly": bool(row["is_httponly"]),
                        "secure": bool(row["is_secure"]),
                        "sameSite": self._convert_samesite(row["samesite"]),
                        "creationTime": row["creation_utc"],
                        "lastAccessTime": row["last_access_utc"],
                        "persistent": bool(row["is_persistent"])
                    }
                    cookies.append(cookie)

            # Clean up temporary database
            temp_db.unlink()
            return cookies

        except Exception as e:
            logger.warning(f"Failed to read cookies from database: {e}")
            return []

    def _write_cookies_to_db(self, cookies_db: Path, cookies: List[Dict[str, Any]]) -> bool:
        """Write cookies to Chromium SQLite database."""
        try:
            # Create database if it doesn't exist
            if not cookies_db.exists():
                self._create_cookies_database(cookies_db)

            # Create a temporary copy for writing
            temp_db = cookies_db.parent / f"temp_cookies_write_{uuid.uuid4().hex}.db"
            if cookies_db.exists():
                shutil.copy2(cookies_db, temp_db)
            else:
                self._create_cookies_database(temp_db)

            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()

                # Insert or update cookies
                for cookie in cookies:
                    # Convert samesite back to database format
                    samesite_db = self._convert_samesite_to_db(cookie.get("sameSite", "None"))

                    cursor.execute("""
                        INSERT OR REPLACE INTO cookies (
                            creation_utc, host_key, name, value, path, expires_utc,
                            is_secure, is_httponly, samesite, last_access_utc,
                            has_expires, is_persistent
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        int(time.time() * 1000000),  # creation_utc in microseconds
                        cookie.get("domain", ""),
                        cookie.get("name", ""),
                        cookie.get("value", ""),
                        cookie.get("path", "/"),
                        cookie.get("expires", -1),
                        1 if cookie.get("secure", False) else 0,
                        1 if cookie.get("httpOnly", False) else 0,
                        samesite_db,
                        int(time.time() * 1000000),  # last_access_utc in microseconds
                        1 if cookie.get("expires", -1) != -1 else 0,
                        1 if cookie.get("persistent", True) else 0
                    ))

                conn.commit()

            # Replace original database with temporary one
            if cookies_db.exists():
                cookies_db.unlink()
            shutil.move(temp_db, cookies_db)
            return True

        except Exception as e:
            logger.warning(f"Failed to write cookies to database: {e}")
            # Clean up temporary database if it exists
            if 'temp_db' in locals() and temp_db.exists():
                temp_db.unlink()
            return False

    def _create_cookies_database(self, cookies_db: Path) -> None:
        """Create a new Chromium cookies database with proper schema."""
        cookies_db.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(cookies_db) as conn:
            cursor = conn.cursor()

            # Create cookies table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cookies (
                    creation_utc INTEGER NOT NULL,
                    host_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    path TEXT NOT NULL,
                    expires_utc INTEGER NOT NULL,
                    is_secure INTEGER NOT NULL,
                    is_httponly INTEGER NOT NULL,
                    samesite INTEGER NOT NULL,
                    last_access_utc INTEGER NOT NULL,
                    has_expires INTEGER NOT NULL DEFAULT 1,
                    is_persistent INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 1,
                    encrypted_value BLOB DEFAULT '',
                    samesite_scheme INTEGER NOT NULL DEFAULT 0,
                    source_scheme INTEGER NOT NULL DEFAULT 0,
                    UNIQUE (creation_utc, host_key, name, path)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS cookies_domain_index ON cookies (host_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS cookies_name_index ON cookies (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS cookies_path_index ON cookies (path)")

            conn.commit()

    def _convert_samesite(self, samesite_int: int) -> str:
        """Convert Chromium samesite integer to string."""
        mapping = {
            0: "None",
            1: "Lax",
            2: "Strict",
            -1: "None"  # Unspecified
        }
        return mapping.get(samesite_int, "None")

    def _convert_samesite_to_db(self, samesite_str: str) -> int:
        """Convert samesite string to Chromium database integer."""
        mapping = {
            "None": 0,
            "Lax": 1,
            "Strict": 2,
            "none": 0,
            "lax": 1,
            "strict": 2
        }
        return mapping.get(samesite_str, 0)

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> Dict[str, int]:
        """Clean up old clone directories to prevent disk bloat.

        Args:
            max_age_hours: Maximum age of clone directories in hours
            max_count: Maximum number of clone directories to keep

        Returns:
            Dictionary with cleanup statistics
        """
        if not self.enabled or not self.clones_dir.exists():
            return {"cleaned": 0, "remaining": 0, "errors": 0}

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            error_count = 0

            # Get all clone directories with their stats
            clone_stats = []
            for clone_path in self.clones_dir.iterdir():
                if clone_path.is_dir():
                    try:
                        stat = clone_path.stat()
                        age_seconds = current_time - stat.st_mtime
                        clone_stats.append({
                            "path": clone_path,
                            "age": age_seconds,
                            "size": self._get_directory_size(clone_path)
                        })
                    except Exception as e:
                        logger.warning(f"Failed to stat clone directory {clone_path}: {e}")
                        error_count += 1

            # Sort by age (oldest first) and size
            clone_stats.sort(key=lambda x: (x["age"], -x["size"]))

            # Determine which clones to remove
            to_remove = []
            remaining_count = len(clone_stats)

            # Remove clones older than max_age_hours
            for i, clone_stat in enumerate(clone_stats):
                if clone_stat["age"] > max_age_seconds:
                    to_remove.append(clone_stat)
                elif i >= max_count:  # Keep only the most recent max_count clones
                    to_remove.append(clone_stat)

            # Remove the identified clones
            for clone_stat in to_remove:
                try:
                    shutil.rmtree(clone_stat["path"], ignore_errors=True)
                    cleaned_count += 1
                    remaining_count -= 1
                    logger.debug(f"Cleaned up old clone: {clone_stat['path']} "
                               f"(age: {clone_stat['age']/3600:.1f}h, size: {clone_stat['size']}MB)")
                except Exception as e:
                    logger.warning(f"Failed to remove clone directory {clone_stat['path']}: {e}")
                    error_count += 1

            total_size_saved = sum(cs["size"] for cs in to_remove)
            self.update_metadata({
                "last_cleanup": current_time,
                "last_cleanup_count": cleaned_count,
                "last_cleanup_size_saved": total_size_saved,
                "remaining_clones": remaining_count
            })

            logger.info(f"Cleanup completed: removed {cleaned_count} clones, "
                       f"freed {total_size_saved}MB, {remaining_count} remaining, {error_count} errors")

            return {
                "cleaned": cleaned_count,
                "remaining": remaining_count,
                "errors": error_count,
                "size_saved_mb": total_size_saved
            }

        except Exception as e:
            logger.error(f"Failed to cleanup old clones: {e}")
            return {"cleaned": 0, "remaining": 0, "errors": 1}

    def get_disk_usage_stats(self) -> Dict[str, Any]:
        """Get disk usage statistics for the user data directories.

        Returns:
            Dictionary with disk usage information
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            master_size = self._get_directory_size(self.master_dir) if self.master_dir.exists() else 0
            clones_size = self._get_directory_size(self.clones_dir) if self.clones_dir.exists() else 0
            total_size = master_size + clones_size

            clone_count = len([d for d in self.clones_dir.iterdir() if d.is_dir()]) if self.clones_dir.exists() else 0

            # Get metadata
            metadata = self.get_metadata() or {}

            return {
                "enabled": True,
                "master_size_mb": master_size,
                "clones_size_mb": clones_size,
                "total_size_mb": total_size,
                "clone_count": clone_count,
                "master_dir": str(self.master_dir),
                "clones_dir": str(self.clones_dir),
                "last_cleanup": metadata.get("last_cleanup"),
                "last_cleanup_count": metadata.get("last_cleanup_count", 0),
                "last_cleanup_size_saved": metadata.get("last_cleanup_size_saved", 0)
            }

        except Exception as e:
            logger.warning(f"Failed to get disk usage stats: {e}")
            return {"enabled": True, "error": str(e)}

    def _get_directory_size(self, path: Path) -> float:
        """Get directory size in megabytes."""
        try:
            total_bytes = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total_bytes += item.stat().st_size
            return round(total_bytes / (1024 * 1024), 2)  # Convert to MB
        except Exception:
            return 0.0