"""Chromium profile lifecycle management including metadata and BrowserForge integration."""

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable

from app.services.common.browser.types import ProfileMetadata
from app.services.common.browser.utils import copytree_recursive, rmtree_with_retries

try:
    import browserforge
    BROWSERFORGE_AVAILABLE = True
except ImportError:
    browserforge = None  # type: ignore
    BROWSERFORGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChromiumProfileManager:
    """Manages Chromium profile lifecycle including metadata and BrowserForge integration."""

    def __init__(self, metadata_file: Path, fingerprint_file: Path):
        """Initialize the profile manager.

        Args:
            metadata_file: Path to profile metadata file
            fingerprint_file: Path to BrowserForge fingerprint file
        """
        self.metadata_file = metadata_file
        self.fingerprint_file = fingerprint_file

    def ensure_metadata(self) -> None:
        """Ensure metadata file exists in master profile."""
        if not self.metadata_file.exists():
            # Get BrowserForge version if available
            browserforge_version = None
            if BROWSERFORGE_AVAILABLE:
                try:
                    browserforge_version = getattr(browserforge, '__version__', 'unknown')
                except Exception:
                    browserforge_version = 'unknown'

            metadata = ProfileMetadata(
                version="1.0",
                created_at=time.time(),
                last_updated=time.time(),
                browserforge_version=browserforge_version,
                profile_type="chromium"
            )
            try:
                self.write_metadata_atomically(metadata)
                logger.debug(f"Created Chromium profile metadata: {self.metadata_file}")

                # Generate and store BrowserForge fingerprint if available
                if BROWSERFORGE_AVAILABLE:
                    self.generate_browserforge_fingerprint()
            except Exception as e:
                logger.warning(f"Failed to create Chromium profile metadata: {e}")

        # Even if metadata exists, ensure fingerprint file is present when BrowserForge is available
        if BROWSERFORGE_AVAILABLE:
            try:
                if not self.fingerprint_file.exists():
                    self.generate_browserforge_fingerprint()
            except Exception as e:
                logger.warning(f"Failed to ensure BrowserForge fingerprint: {e}")

    def write_metadata_atomically(self, metadata: ProfileMetadata) -> None:
        """Write metadata atomically to reduce corruption risk."""
        temp_file = self.metadata_file.with_suffix('.json.tmp')

        try:
            with open(temp_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                f.flush()
                # Try to sync to disk on platforms that support it
                try:
                    import os
                    os.fsync(f.fileno())
                except Exception:
                    pass

            # Replace original file
            import os
            if self.metadata_file.exists():
                os.chmod(self.metadata_file, 0o666)
            os.replace(temp_file, self.metadata_file)

        except Exception as e:
            # Cleanup temp file on failure
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
            raise e

    def read_metadata(self) -> Optional[ProfileMetadata]:
        """Read metadata from file with retry logic."""
        if not self.metadata_file.exists():
            return None

        # Read with retry for concurrent access and corrupted files
        max_read_attempts = 5
        delay = 0.01

        for attempt in range(1, max_read_attempts + 1):
            try:
                with open(self.metadata_file, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted metadata JSON (attempt {attempt}/{max_read_attempts}): {e}")
                if attempt == max_read_attempts:
                    # Try to recreate metadata if it's corrupted
                    try:
                        logger.warning("Attempting to recreate corrupted metadata file")
                        self.metadata_file.unlink()
                        self.ensure_metadata()
                        # Read the fresh metadata
                        with open(self.metadata_file, 'r') as f:
                            return json.load(f)
                    except Exception as recreate_e:
                        logger.warning(f"Failed to recreate metadata: {recreate_e}")
                        return {}
                time.sleep(delay)
                delay = min(0.1, delay * 2)
            except Exception as e:
                if attempt == max_read_attempts:
                    logger.warning(f"Failed to read metadata after {max_read_attempts} attempts: {e}")
                    return {}
                time.sleep(delay)
                delay = min(0.1, delay * 2)

        return None

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""
        try:
            # Read existing metadata or create fresh
            metadata = self.read_metadata() or {}

            # Update with new data
            metadata.update(updates)
            metadata["last_updated"] = time.time()

            # Write atomically
            self.write_metadata_atomically(metadata)
            logger.debug(f"Updated Chromium profile metadata: {updates}")

        except Exception as e:
            logger.warning(f"Failed to update Chromium profile metadata: {e}")

    def generate_browserforge_fingerprint(self) -> None:
        """Generate and store BrowserForge fingerprint for Chromium profile."""
        if not BROWSERFORGE_AVAILABLE:
            return

        try:
            # Ensure directory exists
            self.fingerprint_file.parent.mkdir(parents=True, exist_ok=True)

            # Resolve BrowserForge generate function robustly
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
                        pass
            except Exception:
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
                    logger.warning(f"BrowserForge generate failed, using fallback: {e}")
                    source = "fallback"
                    fingerprint = self._get_fallback_fingerprint()
            else:
                fingerprint = self._get_fallback_fingerprint()

            # Persist fingerprint atomically
            self.write_fingerprint_atomically(fingerprint, source)
            logger.debug(f"Generated BrowserForge fingerprint: {self.fingerprint_file}")

        except Exception as e:
            logger.warning(f"Failed to generate BrowserForge fingerprint: {e}")

    def _get_fallback_fingerprint(self) -> Dict[str, Any]:
        """Get fallback fingerprint when BrowserForge is unavailable."""
        return {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "screen": {"width": 1920, "height": 1080, "pixelRatio": 1}
        }

    def write_fingerprint_atomically(self, fingerprint: Dict[str, Any], source: str) -> None:
        """Write fingerprint atomically to file system."""
        import os
        from app.services.common.browser.utils import atomic_file_replace

        temp_file = self.fingerprint_file.with_suffix('.json.tmp')

        try:
            with open(temp_file, 'w') as f:
                json.dump(fingerprint, f, indent=2, default=str)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    pass

            # Hardened replacement
            success = atomic_file_replace(temp_file, self.fingerprint_file, max_attempts=35)

            if success:
                # Update metadata with fingerprint info
                self.update_metadata({
                    "browserforge_fingerprint_generated": True,
                    "browserforge_fingerprint_file": str(self.fingerprint_file),
                    "browserforge_fingerprint_source": source
                })
            else:
                logger.warning("Failed to replace fingerprint file after retries")

        except Exception as e:
            logger.warning(f"Failed to write fingerprint: {e}")
            # Cleanup temp file on failure
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""
        if not BROWSERFORGE_AVAILABLE or not self.fingerprint_file.exists():
            return None

        try:
            with open(self.fingerprint_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read BrowserForge fingerprint: {e}")
            return None


def clone_profile(source_dir: Path, target_dir: Path) -> Tuple[str, Callable[[], None]]:
    """Clone a Chromium profile and return cleanup function."""
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        copytree_recursive(source_dir, target_dir)
        logger.debug(f"Created Chromium clone directory: {target_dir}")

        def cleanup():
            from app.services.common.browser.utils import (
                chmod_tree, best_effort_close_sqlite
            )
            try:
                if target_dir.exists():
                    chmod_tree(target_dir, 0o777)
                    best_effort_close_sqlite(target_dir)
                    if rmtree_with_retries(target_dir, max_attempts=12, initial_delay=0.1):
                        logger.debug(f"Cleaned up Chromium clone directory: {target_dir}")
                    else:
                        logger.warning(f"Failed to cleanup clone directory {target_dir} after retries")
            except Exception as e:
                logger.warning(f"Failed to cleanup Chromium clone directory {target_dir}: {e}")

        return str(target_dir), cleanup

    except Exception as e:
        # Cleanup on error
        if target_dir.exists():
            try:
                from app.services.common.browser.utils import (
                    chmod_tree, best_effort_close_sqlite
                )
                chmod_tree(target_dir, 0o777)
                best_effort_close_sqlite(target_dir)
                rmtree_with_retries(target_dir, max_attempts=8, initial_delay=0.1)
            except Exception:
                pass
        raise RuntimeError(f"Failed to create Chromium clone from {source_dir}: {e}")


def create_temporary_profile() -> Tuple[str, Callable[[], None]]:
    """Create a temporary Chromium profile for disabled mode."""
    temp_dir = tempfile.mkdtemp(prefix="chromium_temp_")

    def cleanup():
        from app.services.common.browser.utils import (
            chmod_tree, best_effort_close_sqlite
        )
        try:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                # Best-effort: loosen permissions and close any SQLite handles
                chmod_tree(temp_path, 0o777)
                best_effort_close_sqlite(temp_path)
                # Retry/backoff deletion
                success = rmtree_with_retries(temp_path, max_attempts=10, initial_delay=0.1)
                if not success:
                    logger.warning(f"Failed to fully cleanup temp directory {temp_path} after retries")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

    return temp_dir, cleanup
