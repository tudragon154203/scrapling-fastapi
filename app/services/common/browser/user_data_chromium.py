import os
import json
import shutil
import tempfile
import uuid
import logging
import time
import random
import sqlite3
import threading
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
            self.fingerprint_file = self.master_dir / 'browserforge_fingerprint.json'

        # In-process mutex to guard DB replacement operations on Windows
        self._write_lock = threading.Lock()

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
            temp_dir = tempfile.mkdtemp(prefix="chromium_temp_")

            def cleanup():
                try:
                    temp_path = Path(temp_dir)
                    if temp_path.exists():
                        # Best-effort: loosen permissions and close any SQLite handles
                        self._chmod_tree(temp_path, 0o777)
                        self._best_effort_close_sqlite(temp_path)
                        # Retry/backoff deletion
                        success = self._rmtree_with_retries(temp_path, max_attempts=10, initial_delay=0.1)
                        if not success:
                            logger.warning(f"Failed to fully cleanup temp directory {temp_path} after retries")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

            cleanup_func: Optional[Callable[[], None]] = cleanup
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
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)

        # Acquire exclusive lock
        lock_fd = None
        if not FCNTL_AVAILABLE:
            logger.warning("fcntl not available on this platform, using exclusive fallback")
            # Robust exclusive file-based locking for Windows using os.open with O_CREAT|O_EXCL
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
                    lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    # Keep the file descriptor open to maintain exclusivity for the duration of the context
                    logger.debug(f"Acquired exclusive Windows lock for Chromium write mode on {self.master_dir}")
                    break
                except (FileExistsError, PermissionError):
                    # Lock is held by another process; retry with exponential backoff
                    if attempt == max_lock_attempts:
                        raise RuntimeError("Chromium profile already in use (write mode)")
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
                except Exception as e:
                    # Unexpected error - propagate with context
                    raise RuntimeError(f"Failed to acquire Chromium profile lock: {e}")
            else:
                # Safety net: if loop completes without break, consider lock acquisition failed
                raise RuntimeError("Chromium profile already in use (write mode)")
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
                    # Windows: explicitly close descriptor and remove lock file
                    try:
                        if lock_fd is not None:
                            try:
                                os.close(lock_fd)
                            except OSError as e:
                                # Ignore EBADF (Bad file descriptor) errors as they're expected on Windows
                                if e.errno != 9:  # EBADF
                                    logger.warning(f"Failed to close Windows lock fd: {e}")
                            except Exception as e:
                                logger.warning(f"Failed to close Windows lock fd: {e}")
                        if self.lock_file.exists():
                            self.lock_file.unlink()
                    except Exception as e:
                        logger.warning(f"Failed to remove Windows lock file: {e}")
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
                        self._chmod_tree(clone_dir, 0o777)
                        self._best_effort_close_sqlite(clone_dir)
                        if self._rmtree_with_retries(clone_dir, max_attempts=12, initial_delay=0.1):
                            logger.debug(f"Cleaned up Chromium clone directory: {clone_dir}")
                        else:
                            logger.warning(f"Failed to cleanup Chromium clone directory after retries: {clone_dir}")
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
                        self._chmod_tree(clone_dir, 0o777)
                        self._best_effort_close_sqlite(clone_dir)
                        if self._rmtree_with_retries(clone_dir, max_attempts=12, initial_delay=0.1):
                            logger.debug(f"Cleaned up Chromium clone directory: {clone_dir}")
                        else:
                            logger.warning(f"Failed to cleanup Chromium clone directory {clone_dir} after retries")
                except Exception as e:
                    logger.warning(f"Failed to cleanup Chromium clone directory {clone_dir}: {e}")

            return str(clone_dir), cleanup
        except Exception as e:
            # Cleanup on error
            if clone_dir.exists():
                try:
                    self._chmod_tree(clone_dir, 0o777)
                    self._best_effort_close_sqlite(clone_dir)
                    self._rmtree_with_retries(clone_dir, max_attempts=8, initial_delay=0.1)
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

        # Even if metadata already exists, ensure fingerprint file is present when BrowserForge is available
        if BROWSERFORGE_AVAILABLE:
            try:
                if not self.fingerprint_file.exists():
                    self._generate_browserforge_fingerprint()
            except Exception as e:
                logger.warning(f"Failed to ensure BrowserForge fingerprint presence: {e}")

    def _generate_browserforge_fingerprint(self) -> None:
        """Generate and store BrowserForge fingerprint for Chromium profile."""
        if not self.enabled or not BROWSERFORGE_AVAILABLE:
            return

        try:
            # Ensure master directory exists
            self.master_dir.mkdir(parents=True, exist_ok=True)

            # Resolve BrowserForge generate function robustly:
            # 1) Prefer top-level browserforge.generate if present
            # 2) Fallback to browserforge.fingerprint.generate if available
            # 3) If all fail, create a minimal default fingerprint
            gen_func = None
            source = "fallback"

            try:
                if hasattr(browserforge, "generate") and callable(getattr(browserforge, "generate")):
                    gen_func = getattr(browserforge, "generate")
                    source = "browserforge.generate"
                else:
                    try:
                        from importlib import import_module
                        bf_fp = import_module("browserforge.fingerprint")
                        if hasattr(bf_fp, "generate") and callable(getattr(bf_fp, "generate")):
                            gen_func = getattr(bf_fp, "generate")
                            source = "browserforge.fingerprint.generate"
                    except Exception:
                        # Keep source="fallback"
                        pass
            except Exception:
                # Keep source="fallback"
                gen_func = None

            fingerprint: Dict[str, Any]
            if gen_func is not None:
                try:
                    fingerprint = gen_func(
                        browser="chrome",
                        os="windows",
                        mobile=False
                    )
                except Exception as e:
                    logger.warning(f"BrowserForge generate failed, using fallback fingerprint: {e}")
                    source = "fallback"
                    fingerprint = {
                        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "viewport": {"width": 1920, "height": 1080},
                        "screen": {"width": 1920, "height": 1080, "pixelRatio": 1}
                    }
            else:
                fingerprint = {
                    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "viewport": {"width": 1920, "height": 1080},
                    "screen": {"width": 1920, "height": 1080, "pixelRatio": 1}
                }

            # Persist fingerprint atomically to file system
            tmp_file = self.fingerprint_file.with_suffix('.json.tmp')
            with open(tmp_file, 'w') as f:
                json.dump(fingerprint, f, indent=2, default=str)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    # fsync may not be available or necessary on all platforms
                    pass

            # Hardened replacement with retries/backoff and fallback unlink+replace
            try:
                if self.fingerprint_file.exists():
                    os.chmod(self.fingerprint_file, 0o666)  # Best-effort: loosen locks
            except Exception as chmod_err:
                logger.debug(f"Best-effort chmod before fingerprint replace on {self.fingerprint_file}: {chmod_err}")

            max_replace_attempts = 35
            delay = 0.2
            replaced = False
            last_err: Optional[Exception] = None

            for attempt in range(1, max_replace_attempts + 1):
                try:
                    # Guard replacement with in-process mutex
                    with self._write_lock:
                        os.replace(tmp_file, self.fingerprint_file)
                    replaced = True
                    break
                except (PermissionError, OSError) as e:
                    last_err = e
                    logger.warning(
                        f"Replace fingerprint file failed (attempt {attempt}/{max_replace_attempts}): {e}"
                    )
                    # Fallback: attempt to unlink the existing target with retries/backoff
                    if self.fingerprint_file.exists():
                        unlink_attempts = 15
                        unlink_delay = 0.2
                        for u_attempt in range(1, unlink_attempts + 1):
                            try:
                                os.unlink(self.fingerprint_file)
                                break
                            except Exception as ue:
                                logger.warning(
                                    f"Unlink of existing fingerprint file failed (attempt {u_attempt}/{unlink_attempts}): {ue}"
                                )
                                time.sleep(unlink_delay + random.uniform(0, 0.2))
                                unlink_delay = min(10.0, unlink_delay * 2)
                    # Retry replacement after unlink
                    try:
                        with self._write_lock:
                            os.replace(tmp_file, self.fingerprint_file)
                        replaced = True
                        break
                    except (PermissionError, OSError) as e2:
                        logger.warning(f"Retry replace after unlink failed: {e2}; attempting shutil.move")
                        try:
                            with self._write_lock:
                                shutil.move(str(tmp_file), str(self.fingerprint_file))
                            replaced = True
                            break
                        except Exception as e3:
                            last_err = e3
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error during fingerprint replace: {e}")
                time.sleep(delay + random.uniform(0, 0.2))
                delay = min(10.0, delay * 2)

            if not replaced:
                # Cleanup temp file on failure
                try:
                    if tmp_file.exists():
                        tmp_file.unlink()
                except Exception:
                    pass
                logger.warning(f"Failed to replace fingerprint file after retries: {last_err}")
                return

            logger.debug(f"Generated BrowserForge fingerprint: {self.fingerprint_file}")

            # Update metadata with fingerprint info
            self.update_metadata({
                "browserforge_fingerprint_generated": True,
                "browserforge_fingerprint_file": str(self.fingerprint_file),
                "browserforge_fingerprint_source": source
            })
        except Exception as e:
            logger.warning(f"Failed to generate BrowserForge fingerprint: {e}")

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""
        if not self.enabled or not BROWSERFORGE_AVAILABLE:
            return None

        if not self.fingerprint_file.exists():
            return None

        try:
            with open(self.fingerprint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read BrowserForge fingerprint: {e}")
            return None

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""
        if not self.enabled or not self.metadata_file.exists():
            return

        try:
            # Read existing metadata with fallback for empty/invalid JSON
            metadata = None
            try:
                with open(self.metadata_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        metadata = json.loads(content)
                    else:
                        logger.warning("Metadata file is empty, creating new metadata")
                        metadata = None
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read existing metadata, creating new: {e}")
                metadata = None

            # If we couldn't read valid metadata, create a fresh structure
            if metadata is None:
                metadata = {
                    "version": "1.0",
                    "created_at": time.time(),
                    "profile_type": "chromium"
                }

            # Update with new data
            metadata.update(updates)
            metadata["last_updated"] = time.time()

            # Write back atomically with retries for concurrent access
            temp_file = self.metadata_file.with_suffix('.json.tmp')
            max_attempts = 10
            delay = 0.05

            for attempt in range(1, max_attempts + 1):
                try:
                    with open(temp_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())

                    # Replace original file with retry logic
                    with self._write_lock:
                        os.replace(temp_file, self.metadata_file)
                    break  # Success

                except (PermissionError, OSError) as e:
                    if attempt == max_attempts:
                        raise e
                    # Brief delay before retry
                    time.sleep(delay)
                    delay = min(1.0, delay * 2)
                except Exception as e:
                    # Cleanup temp file on non-retryable error
                    if temp_file.exists():
                        try:
                            temp_file.unlink()
                        except Exception:
                            pass
                    raise e

            # Cleanup temp file if it still exists (shouldn't)
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

            logger.debug(f"Updated Chromium profile metadata: {updates}")
        except Exception as e:
            logger.warning(f"Failed to update Chromium profile metadata: {e}")

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current metadata from master profile."""
        if not self.enabled or not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    logger.warning("Metadata file is empty")
                    return None
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to read Chromium profile metadata: {e}")
            return None
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
                # shutil.copy2 does not leave open handles; use directly
                shutil.copy2(item, dest_item)

    def _chmod_tree(self, path: Path, mode: int = 0o777) -> None:
        """Recursively chmod a directory tree to a permissive mode to mitigate Windows permission/lock issues."""
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

    def _best_effort_close_sqlite(self, root: Path) -> None:
        """Best-effort attempt to ensure SQLite-related file handles are closed before deletion."""
        try:
            for db in root.rglob("*"):
                if db.is_file():
                    name = db.name.lower()
                    if db.suffix in (".db", ".sqlite") or "cookies" in name or name.endswith("-wal") or name.endswith("-journal"):
                        try:
                            # Open and immediately close to release any lingering handles in this process
                            with sqlite3.connect(db):
                                pass
                        except Exception:
                            # Ignore errors; other processes may still hold locks
                            pass
        except Exception:
            pass

    def _rmtree_with_retries(self, target: Path, max_attempts: int = 10, initial_delay: float = 0.1) -> bool:
        """Robust deletion with chmod, onerror handling, and exponential backoff. Returns True on success."""
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
                self._chmod_tree(target, 0o777)
                shutil.rmtree(target, onerror=_onerror)
                return True
            except Exception as e:
                last_err = e
                logger.warning(f"shutil.rmtree failed for {target} (attempt {attempt}/{max_attempts}): {e}")
                time.sleep(delay + random.uniform(0, 0.2))
                delay = min(2.0, delay * 2)
        logger.warning(f"Failed to delete {target} after {max_attempts} attempts: {last_err}")
        return False

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
            # For unit expectations: return None when master profile is missing
            return None

        try:
            # Path to Chromium cookies database
            cookies_db = self.master_dir / "Default" / "Cookies"

            # Ensure database file and schema exist before any read
            self._ensure_cookies_database(cookies_db)

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
                    # cookies_available should reflect actual presence of cookies
                    "cookies_available": bool(cookies),
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

        # Proactively initialize the master profile directories to avoid premature failure
        try:
            # Ensure base and master directories exist
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.master_dir.mkdir(parents=True, exist_ok=True)
            # Ensure Default subdirectory exists
            default_dir = self.master_dir / "Default"
            default_dir.mkdir(parents=True, exist_ok=True)
            # Initialize metadata for a newly created master profile
            self._ensure_metadata()
        except Exception as e:
            logger.warning(f"Failed to initialize Chromium master profile directories: {e}")
            return False

        try:
            # Path to Chromium cookies database
            cookies_db = default_dir / "Cookies"

            # Extract cookies based on format
            if cookie_data.get("format") == "storage_state":
                cookies = cookie_data.get("cookies", [])
            else:
                cookies = cookie_data.get("cookies", [])

            if not cookies:
                logger.info("No cookies to import")
                # Still update metadata to reflect an import event with zero cookies
                self.update_metadata({
                    "last_cookie_import": time.time(),
                    "cookie_import_count": 0,
                    "cookie_import_status": "success"
                })
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
        """Read cookies from Chromium SQLite database with robust Windows lock handling."""
        try:
            # Ensure database file and schema exist before any read
            self._ensure_cookies_database(cookies_db)

            # Create a temporary copy to avoid locking issues
            temp_db = cookies_db.parent / f"temp_cookies_{uuid.uuid4().hex}.db"

            # Retry copying the locked database with exponential backoff
            max_copy_attempts = 10
            delay = 0.1
            copied = False
            for attempt in range(1, max_copy_attempts + 1):
                try:
                    shutil.copy2(cookies_db, temp_db)
                    copied = True
                    break
                except Exception as e:
                    logger.warning(
                        f"Temp cookies copy failed (attempt {attempt}/{max_copy_attempts}): {e}"
                    )
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
            if not copied:
                logger.warning(f"Failed to copy cookies DB to temp file: {cookies_db}")
                return []

            # Read cookies with retries to handle transient sqlite3.OperationalError
            cookies: List[Dict[str, Any]] = []
            max_sql_attempts = 10
            delay = 0.1
            last_err: Optional[Exception] = None
            for attempt in range(1, max_sql_attempts + 1):
                try:
                    with sqlite3.connect(temp_db) as conn:
                        conn.execute("PRAGMA busy_timeout = 5000")
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
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
                    break
                except sqlite3.OperationalError as e:
                    last_err = e
                    logger.warning(
                        f"sqlite3 OperationalError reading cookies (attempt {attempt}/{max_sql_attempts}): {e}"
                    )
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error reading temp cookies DB: {e}")
                    break

            # Clean up temporary database
            try:
                temp_db.unlink()
            except Exception:
                pass

            if cookies:
                return cookies

            if last_err:
                logger.warning(f"Failed to read cookies from database after retries: {last_err}")
            return []

        except Exception as e:
            logger.warning(f"Failed to read cookies from database: {e}")
            # Ensure cleanup if temp_db was created
            try:
                if 'temp_db' in locals() and temp_db.exists():
                    temp_db.unlink()
            except Exception:
                pass
            return []

    def _write_cookies_to_db(self, cookies_db: Path, cookies: List[Dict[str, Any]]) -> bool:
        """Write cookies to Chromium SQLite database with robust Windows lock handling."""
        try:
            # Ensure database file and schema exist before any write
            self._ensure_cookies_database(cookies_db)

            # Create a temporary copy for writing
            temp_db = cookies_db.parent / f"temp_cookies_write_{uuid.uuid4().hex}.db"
            if cookies_db.exists():
                # Retry copy with exponential backoff to avoid file locking
                max_copy_attempts = 10
                delay = 0.1
                copied = False
                for attempt in range(1, max_copy_attempts + 1):
                    try:
                        shutil.copy2(cookies_db, temp_db)
                        copied = True
                        break
                    except Exception as e:
                        logger.warning(
                            f"Temp cookies write copy failed (attempt {attempt}/{max_copy_attempts}): {e}"
                        )
                        time.sleep(delay)
                        delay = min(2.0, delay * 2)
                if not copied:
                    logger.warning(f"Failed to copy cookies DB to temp file for write: {cookies_db}")
                    return False
            else:
                self._create_cookies_database(temp_db)

            # Insert/update with retries to handle sqlite3.OperationalError (database is locked)
            max_sql_attempts = 10
            delay = 0.1
            sql_success = False
            last_err: Optional[Exception] = None
            for attempt in range(1, max_sql_attempts + 1):
                try:
                    with sqlite3.connect(temp_db) as conn:
                        conn.execute("PRAGMA busy_timeout = 5000")
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
                    sql_success = True
                    break
                except sqlite3.OperationalError as e:
                    last_err = e
                    logger.warning(
                        f"sqlite3 OperationalError writing cookies (attempt {attempt}/{max_sql_attempts}): {e}"
                    )
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error writing temp cookies DB: {e}")
                    break

            if not sql_success:
                # Cleanup temp DB on failure
                try:
                    if temp_db.exists():
                        temp_db.unlink()
                except Exception:
                    pass
                if last_err:
                    logger.warning(f"Failed to write cookies after retries: {last_err}")
                return False

            # Replace original database with temporary one atomically, with hardened Windows handling
            # Ensure any SQLite connections/cursors are closed before file operations (handled above)
            # Best-effort: try to loosen file permissions to mitigate locks
            try:
                if cookies_db.exists():
                    os.chmod(cookies_db, 0o666)
            except Exception as chmod_err:
                logger.debug(f"Best-effort chmod before replace on {cookies_db}: {chmod_err}")
            max_replace_attempts = 25
            delay = 0.1
            last_err: Optional[Exception] = None
            for attempt in range(1, max_replace_attempts + 1):
                try:
                    # Guard replacement with in-process mutex
                    with self._write_lock:
                        os.replace(temp_db, cookies_db)
                    return True
                except (PermissionError, OSError) as e:
                    last_err = e
                    logger.warning(
                        f"Replace cookies DB failed (attempt {attempt}/{max_replace_attempts}): {e}"
                    )
                    # Fallback: try to unlink the existing target with retries/backoff
                    if cookies_db.exists():
                        unlink_attempts = 10
                        unlink_delay = 0.1
                        for u_attempt in range(1, unlink_attempts + 1):
                            try:
                                os.unlink(cookies_db)
                                break
                            except Exception as ue:
                                logger.warning(
                                    f"Unlink of existing cookies DB failed (attempt {u_attempt}/{unlink_attempts}): {ue}"
                                )
                                time.sleep(unlink_delay)
                                unlink_delay = min(5.0, unlink_delay * 2)
                    # Retry replacement after unlink
                    try:
                        with self._write_lock:
                            os.replace(temp_db, cookies_db)
                        return True
                    except (PermissionError, OSError) as e2:
                        logger.warning(f"Retry replace after unlink failed: {e2}; attempting shutil.move")
                        try:
                            with self._write_lock:
                                shutil.move(str(temp_db), str(cookies_db))
                            return True
                        except Exception as e3:
                            last_err = e3
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error during replace: {e}")
                time.sleep(delay + random.uniform(0, 0.2))
                delay = min(5.0, delay * 2)
            # Cleanup temp_db on failure
            try:
                if temp_db.exists():
                    temp_db.unlink()
            except Exception:
                pass
            if last_err:
                logger.warning(f"Failed to replace cookies DB after retries: {last_err}")
            return False

        except Exception as e:
            logger.warning(f"Failed to write cookies to database: {e}")
            # Clean up temporary database if it exists
            try:
                if 'temp_db' in locals() and temp_db.exists():
                    temp_db.unlink()
            except Exception:
                pass
            return False

    def _create_cookies_database(self, cookies_db: Path) -> None:
        """Create a new Chromium cookies database with proper schema."""
        cookies_db.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(cookies_db) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
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

    def _ensure_cookies_database(self, cookies_db: Path) -> bool:
        """Ensure the SQLite cookies DB exists with the expected schema; reinitialize if missing or corrupted.

        Returns:
            True if the database is ready for use, False if reinitialization failed.
        """
        try:
            # Ensure parent directory exists (e.g., Default/)
            cookies_db.parent.mkdir(parents=True, exist_ok=True)

            # Create if missing
            if not cookies_db.exists():
                self._create_cookies_database(cookies_db)
                return True

            # Verify schema presence
            with sqlite3.connect(cookies_db) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
                row = cursor.fetchone()
                if not row:
                    # Table missing (possibly due to corruption or legacy); recreate schema in-place
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
                    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_domain_index ON cookies (host_key)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_name_index ON cookies (name)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_path_index ON cookies (path)")
                    conn.commit()
            return True
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            # Database file is not valid SQLite or locked beyond recovery: reinitialize
            logger.warning(f"Cookies DB invalid or corrupted at {cookies_db}: {e}. Reinitializing.")
            temp_new = cookies_db.parent / f"reinit_cookies_{uuid.uuid4().hex}.db"
            try:
                # Build a fresh DB
                self._create_cookies_database(temp_new)
                # Replace original with retries to handle Windows file locking, atomically
                # Best-effort: try to loosen file permissions on existing DB to mitigate locks
                try:
                    if cookies_db.exists():
                        os.chmod(cookies_db, 0o666)
                except Exception as chmod_err:
                    logger.debug(f"Best-effort chmod before reinit replace on {cookies_db}: {chmod_err}")
                max_replace_attempts = 25
                delay = 0.1
                last_err: Optional[Exception] = None
                for attempt in range(1, max_replace_attempts + 1):
                    try:
                        # Guard replacement with in-process mutex
                        with self._write_lock:
                            os.replace(temp_new, cookies_db)
                        return True
                    except (PermissionError, OSError) as replace_err:
                        last_err = replace_err
                        logger.warning(
                            f"Cookies DB reinit replace failed (attempt {attempt}/{max_replace_attempts}): {replace_err}"
                        )
                        # Fallback: try unlink+replace with retries/backoff
                        if cookies_db.exists():
                            unlink_attempts = 10
                            unlink_delay = 0.1
                            for u_attempt in range(1, unlink_attempts + 1):
                                try:
                                    os.unlink(cookies_db)
                                    break
                                except Exception as ue:
                                    logger.warning(
                                        f"Reinit unlink of existing cookies DB failed (attempt {u_attempt}/{unlink_attempts}): {ue}"
                                    )
                                    time.sleep(unlink_delay)
                                    unlink_delay = min(5.0, unlink_delay * 2)
                        # Retry replacement after unlink
                        try:
                            with self._write_lock:
                                os.replace(temp_new, cookies_db)
                            return True
                        except (PermissionError, OSError) as e2:
                            logger.warning(f"Reinit retry replace after unlink failed: {e2}; attempting shutil.move")
                            try:
                                with self._write_lock:
                                    shutil.move(str(temp_new), str(cookies_db))
                                return True
                            except Exception as e3:
                                last_err = e3
                    except Exception as e:
                        last_err = e
                        logger.warning(f"Unexpected error during reinit replace: {e}")
                    time.sleep(delay + random.uniform(0, 0.2))
                    delay = min(5.0, delay * 2)
            except Exception:
                return False
            finally:
                # Cleanup temp_new if still present
                try:
                    if temp_new.exists():
                        temp_new.unlink()
                except Exception:
                    pass
            if last_err:
                logger.warning(f"Failed to replace cookies DB after retries: {last_err}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error ensuring cookies DB at {cookies_db}: {e}")
            return False

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
                path = clone_stat["path"]
                try:
                    # Loosen permissions and best-effort close sqlite handles
                    self._chmod_tree(path, 0o777)
                    self._best_effort_close_sqlite(path)
                    if self._rmtree_with_retries(path, max_attempts=12, initial_delay=0.1):
                        cleaned_count += 1
                        remaining_count -= 1
                        logger.debug(f"Cleaned up old clone: {path} "
                                     f"(age: {clone_stat['age']/3600:.1f}h, size: {clone_stat['size']}MB)")
                    else:
                        logger.warning(f"Could not remove clone directory after retries: {path}")
                        error_count += 1
                except Exception as e:
                    # Parallel-safe: swallow to avoid blocking other deletions
                    logger.warning(f"Failed to remove clone directory {path}: {e}")
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
