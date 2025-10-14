"""Chromium user-data context lifecycle management."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Callable, ContextManager, Optional, Tuple

from app.services.common.browser.locks import exclusive_lock
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import (
    ChromiumProfileManager,
    clone_profile,
    create_temporary_profile,
)
from app.services.common.browser.utils import (
    best_effort_close_sqlite,
    chmod_tree,
    rmtree_with_retries,
)

logger = logging.getLogger(__name__)


class ChromiumContextManager:
    """Provide read/write Chromium profile contexts with robust cleanup."""

    def __init__(
        self,
        path_manager: ChromiumPathManager,
        profile_manager: Optional[ChromiumProfileManager],
        enabled: bool,
    ) -> None:
        self._path_manager = path_manager
        self._profile_manager = profile_manager
        self._enabled = enabled

    @property
    def path_manager(self) -> ChromiumPathManager:
        """Return the configured path manager."""

        return self._path_manager

    @property
    def profile_manager(self) -> Optional[ChromiumProfileManager]:
        """Return the configured profile manager if available."""

        return self._profile_manager

    @contextmanager
    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
        """Yield a Chromium profile directory and cleanup hook for the requested mode."""

        if not self._enabled:
            logger.warning(
                "Chromium user data management disabled, using temporary profile",
            )
            temp_dir, cleanup_func = create_temporary_profile()
            try:
                yield temp_dir, cleanup_func
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Error in Chromium user data context mode=%s: %s", mode, exc)
                raise
            finally:
                try:
                    if callable(cleanup_func):
                        cleanup_func()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "Automatic cleanup failed for temp directory %s: %s",
                        temp_dir,
                        exc,
                    )
            return

        if mode not in ("read", "write"):
            raise ValueError(f"user_data_mode must be 'read' or 'write', got '{mode}'")

        cleanup_func: Optional[Callable[[], None]] = None
        try:
            if mode == "write":
                effective_dir, cleanup_func = self._write_mode_context()
            else:
                effective_dir, cleanup_func = self._read_mode_context()

            yield effective_dir, cleanup_func
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error in Chromium user data context mode=%s: %s", mode, exc)
            raise
        finally:
            try:
                if callable(cleanup_func):
                    cleanup_func()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "Automatic cleanup failed for Chromium user data context: %s",
                    exc,
                )

    def _write_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Return master profile directory guarded by the filesystem lock."""

        self._path_manager.ensure_directories_exist()

        with exclusive_lock(str(self._path_manager.lock_file), timeout=30.0) as acquired:
            if not acquired:
                raise RuntimeError("Failed to acquire Chromium profile lock for write mode")

            if self._profile_manager is not None:
                self._profile_manager.ensure_metadata()

        cleanup_func: Callable[[], None] = lambda: None
        return str(self._path_manager.master_dir), cleanup_func

    def _read_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Clone the master profile for read-only consumers."""

        clone_dir = self._path_manager.generate_clone_path()
        self._path_manager.ensure_directories_exist()

        if not self._path_manager.master_dir.exists():
            logger.warning(
                "Chromium master profile not found at %s, creating empty clone",
                self._path_manager.master_dir,
            )
            clone_dir.mkdir(parents=True, exist_ok=True)

            def cleanup() -> None:
                try:
                    if clone_dir.exists():
                        chmod_tree(clone_dir, 0o777)
                        best_effort_close_sqlite(clone_dir)
                        if rmtree_with_retries(clone_dir, max_attempts=12, initial_delay=0.1):
                            logger.debug("Cleaned up Chromium clone directory: %s", clone_dir)
                        else:
                            logger.warning(
                                "Failed to cleanup Chromium clone directory after retries: %s",
                                clone_dir,
                            )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Failed to cleanup Chromium clone directory: %s", exc)

            return str(clone_dir), cleanup

        return clone_profile(self._path_manager.master_dir, clone_dir)
