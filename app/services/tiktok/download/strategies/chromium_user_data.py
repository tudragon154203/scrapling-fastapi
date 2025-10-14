"""Utilities for acquiring Chromium user data contexts for TikTok downloads."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Optional

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

logger = logging.getLogger(__name__)


@dataclass
class ChromiumUserDataContext:
    """Container for Chromium user data context information."""

    effective_dir: Optional[str]
    cleanup: Optional[Callable[[], None]]


class ChromiumUserDataContextProvider:
    """Acquire user data contexts while encapsulating Chromium manager details."""

    def __init__(self, manager: ChromiumUserDataManager):
        self._manager = manager

    def acquire_read_context(self) -> ChromiumUserDataContext:
        """Return a sanitized read-mode Chromium user data context."""
        if not self._manager.is_enabled():
            logger.debug("Chromium user data manager disabled; no context acquired")
            return ChromiumUserDataContext(effective_dir=None, cleanup=None)

        try:
            context = self._manager.get_user_data_context("read")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to create Chromium user data context; falling back to ephemeral profile: %s",
                exc,
            )
            return ChromiumUserDataContext(effective_dir=None, cleanup=None)

        try:
            directory, _ = context.__enter__()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Failed to enter Chromium user data context; falling back to ephemeral profile: %s",
                exc,
            )
            return ChromiumUserDataContext(effective_dir=None, cleanup=None)

        abs_directory = os.path.abspath(directory) if directory else None
        cleanup_called = False

        def _cleanup() -> None:
            nonlocal cleanup_called
            if cleanup_called:
                return
            cleanup_called = True
            try:
                context.__exit__(None, None, None)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Error cleaning up Chromium user data context: %s", exc)

        if abs_directory:
            logger.debug("Using Chromium user data directory: %s", abs_directory)
        return ChromiumUserDataContext(effective_dir=abs_directory, cleanup=_cleanup)
