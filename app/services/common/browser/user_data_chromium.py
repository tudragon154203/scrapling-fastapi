import os
import json
import shutil
import tempfile
import uuid
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Tuple, Optional, Dict, Any

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