"""Helpers for managing Chromium user-data contexts."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Callable, ContextManager, Optional, Tuple

from app.services.common.browser.locks import exclusive_lock
from app.services.common.browser.profile_manager import (
    ChromiumProfileManager,
    clone_profile,
    create_temporary_profile,
)
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.utils import (
    best_effort_close_sqlite,
    chmod_tree,
    rmtree_with_retries,
)

logger = logging.getLogger(__name__)

CleanupFn = Callable[[], None]


class ChromiumUserDataContextManager:
    """Provide read/write contexts for Chromium user-data directories."""

    def __init__(
        self,
        *,
        enabled: bool,
        path_manager: ChromiumPathManager,
        profile_manager: Optional[ChromiumProfileManager],
    ) -> None:
        self._enabled = enabled
        self._path_manager = path_manager
        self._profile_manager = profile_manager

    @contextmanager
    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, CleanupFn]]:
        """Yield a context for the requested user-data ``mode``."""

        if not self._enabled:
            logger.warning(
                "Chromium user data management disabled, using temporary profile",
            )
            temp_dir, cleanup_func = create_temporary_profile()
            try:
                yield temp_dir, cleanup_func
            finally:
                try:
                    if callable(cleanup_func):
                        cleanup_func()
                except Exception as exc:  # pragma: no cover - best-effort cleanup
                    logger.warning(
                        "Automatic cleanup failed for temp directory %s: %s",
                        temp_dir,
                        exc,
                    )
            return

        if mode not in ("read", "write"):
            raise ValueError(
                f"user_data_mode must be 'read' or 'write', got '{mode}'",
            )

        effective_dir: Optional[str] = None
        cleanup_func: Optional[CleanupFn] = None

        try:
            if mode == "write":
                effective_dir, cleanup_func = self._write_mode_context()
            else:
                effective_dir, cleanup_func = self._read_mode_context()

            yield effective_dir, cleanup_func
        except Exception:
            logger.exception("Error in Chromium user data context mode=%s", mode)
            raise
        finally:
            try:
                if callable(cleanup_func):
                    cleanup_func()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.warning(
                    "Automatic cleanup failed for Chromium user data context: %s",
                    exc,
                )

    def _write_mode_context(self) -> Tuple[str, CleanupFn]:
        """Provide a write-mode context bound to the master directory."""

        if not self._profile_manager:
            raise RuntimeError("Chromium profile manager unavailable for write mode")

        self._path_manager.ensure_directories_exist()

        with exclusive_lock(str(self._path_manager.lock_file), timeout=30.0) as acquired:
            if not acquired:
                raise RuntimeError(
                    "Failed to acquire Chromium profile lock for write mode",
                )

            self._profile_manager.ensure_metadata()

        cleanup_func: CleanupFn = lambda: None
        return str(self._path_manager.master_dir), cleanup_func

    def _read_mode_context(self) -> Tuple[str, CleanupFn]:
        """Provide a read-mode context using a clone of the master profile."""

        if not self._profile_manager:
            raise RuntimeError("Chromium profile manager unavailable for read mode")

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
                    logger.warning(
                        "Failed to cleanup Chromium clone directory: %s",
                        exc,
                    )

            return str(clone_dir), cleanup

        return clone_profile(self._path_manager.master_dir, clone_dir)
