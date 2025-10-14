"""Chromium profile context management utilities."""

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
    """Manage Chromium master/clone lifecycle for read/write contexts."""

    def __init__(
        self,
        path_manager: ChromiumPathManager,
        profile_manager: Optional[ChromiumProfileManager],
        *,
        enabled: bool,
    ) -> None:
        self._path_manager = path_manager
        self._profile_manager = profile_manager
        self._enabled = enabled

    @contextmanager
    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
        """Yield a Chromium user data directory for the requested mode."""

        if not self._enabled:
            temp_dir, cleanup = create_temporary_profile()
            try:
                yield temp_dir, cleanup
            finally:
                try:
                    cleanup()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Automatic cleanup failed for temp directory %s: %s", temp_dir, exc)
            return

        if mode not in {"read", "write"}:
            raise ValueError(f"user_data_mode must be 'read' or 'write', got '{mode}'")

        cleanup: Optional[Callable[[], None]] = None
        try:
            if mode == "write":
                directory, cleanup = self._write_mode_context()
            else:
                directory, cleanup = self._read_mode_context()

            yield directory, cleanup
        except Exception:
            logger.exception("Error obtaining Chromium user data context for mode=%s", mode)
            raise
        finally:
            if callable(cleanup):
                try:
                    cleanup()
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Automatic cleanup failed for Chromium user data context: %s", exc)

    def _write_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Provide access to the master profile for write operations."""
        self._path_manager.ensure_directories_exist()
        if not self._profile_manager:
            return self._temporary_context()

        with exclusive_lock(str(self._path_manager.lock_file), timeout=30.0) as acquired:
            if not acquired:
                raise RuntimeError("Failed to acquire Chromium profile lock for write mode")
            self._profile_manager.ensure_metadata()

        return str(self._path_manager.master_dir), (lambda: None)

    def _read_mode_context(self) -> Tuple[str, Callable[[], None]]:
        """Provide a clone of the master profile for read operations."""
        self._path_manager.ensure_directories_exist()
        clone_dir = self._path_manager.generate_clone_path()

        if not self._path_manager.master_dir.exists():
            logger.warning(
                "Chromium master profile not found at %s, creating empty clone", self._path_manager.master_dir
            )
            clone_dir.mkdir(parents=True, exist_ok=True)

            def cleanup() -> None:
                try:
                    if clone_dir.exists():
                        chmod_tree(clone_dir, 0o777)
                        best_effort_close_sqlite(clone_dir)
                        if not rmtree_with_retries(clone_dir, max_attempts=12, initial_delay=0.1):
                            logger.warning("Failed to cleanup Chromium clone directory after retries: %s", clone_dir)
                        else:
                            logger.debug("Cleaned up Chromium clone directory: %s", clone_dir)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Failed to cleanup Chromium clone directory: %s", exc)

            return str(clone_dir), cleanup

        return clone_profile(self._path_manager.master_dir, clone_dir)

    def _temporary_context(self) -> Tuple[str, Callable[[], None]]:
        temp_dir, cleanup = create_temporary_profile()
        return temp_dir, cleanup
