"""Profile metadata and cleanup helpers for Chromium user data."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.types import CleanupResult
from app.services.common.browser.utils import (
    best_effort_close_sqlite,
    chmod_tree,
    get_directory_size,
    rmtree_with_retries,
)

logger = logging.getLogger(__name__)


class ChromiumProfileHousekeeping:
    """Maintain Chromium profile metadata and clone hygiene."""

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

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Apply metadata updates when enabled."""
        if not self._enabled or not self._profile_manager:
            return
        self._profile_manager.update_metadata(updates)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Fetch stored metadata if user data management is enabled."""
        if not self._enabled or not self._profile_manager:
            return None
        return self._profile_manager.read_metadata()

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored BrowserForge fingerprint."""
        if not self._enabled or not self._profile_manager:
            return None
        return self._profile_manager.get_browserforge_fingerprint()

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> Dict[str, int]:
        """Remove aged clone directories and update metadata."""
        if not self._enabled or not self._profile_manager:
            return {"cleaned": 0, "remaining": 0, "errors": 0}
        if not getattr(self._path_manager, "clones_dir", None) or not self._path_manager.clones_dir.exists():
            return {"cleaned": 0, "remaining": 0, "errors": 0}

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        error_count = 0

        clone_stats = []
        for clone_path in self._path_manager.clones_dir.iterdir():
            if not clone_path.is_dir():
                continue
            try:
                stat = clone_path.stat()
                age_seconds = current_time - stat.st_mtime
                clone_stats.append(
                    {
                        "path": clone_path,
                        "age": age_seconds,
                        "size": get_directory_size(clone_path),
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to stat clone directory %s: %s", clone_path, exc)
                error_count += 1

        clone_stats.sort(key=lambda data: (data["age"], -data["size"]))
        to_remove = []
        remaining_count = len(clone_stats)

        for index, clone_stat in enumerate(clone_stats):
            if clone_stat["age"] > max_age_seconds or index >= max_count:
                to_remove.append(clone_stat)

        for clone_stat in to_remove:
            path = clone_stat["path"]
            try:
                chmod_tree(path, 0o777)
                best_effort_close_sqlite(path)
                if rmtree_with_retries(path, max_attempts=12, initial_delay=0.1):
                    cleaned_count += 1
                    remaining_count -= 1
                    logger.debug(
                        "Cleaned up old clone: %s (age: %.1fh, size: %sMB)",
                        path,
                        clone_stat["age"] / 3600,
                        clone_stat["size"],
                    )
                else:
                    logger.warning("Could not remove clone directory after retries: %s", path)
                    error_count += 1
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Failed to remove clone directory %s: %s", path, exc)
                error_count += 1

        total_size_saved = sum(item["size"] for item in to_remove)
        self._profile_manager.update_metadata(
            {
                "last_cleanup": current_time,
                "last_cleanup_count": cleaned_count,
                "last_cleanup_size_saved": total_size_saved,
                "remaining_clones": remaining_count,
            }
        )

        logger.info(
            "Cleanup completed: removed %s clones, freed %sMB, %s remaining, %s errors",
            cleaned_count,
            total_size_saved,
            remaining_count,
            error_count,
        )

        result: CleanupResult = {
            "cleaned": cleaned_count,
            "remaining": remaining_count,
            "errors": error_count,
            "size_saved_mb": total_size_saved,
        }
        return result
