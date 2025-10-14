"""Housekeeping helpers for Chromium profile clones."""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.utils import (
    best_effort_close_sqlite,
    chmod_tree,
    get_directory_size,
    rmtree_with_retries,
)
from app.services.common.browser.types import CleanupResult

logger = logging.getLogger(__name__)


class ChromiumProfileHousekeeping:
    """Perform maintenance on Chromium clone directories."""

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

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> CleanupResult:
        """Remove stale clone directories and report cleanup statistics."""

        clones_dir = getattr(self._path_manager, "clones_dir", None)
        if not self._enabled or clones_dir is None or not clones_dir.exists():
            return {"cleaned": 0, "remaining": 0, "errors": 0}

        try:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            error_count = 0

            clone_stats = []
            for clone_path in clones_dir.iterdir():
                if clone_path.is_dir():
                    try:
                        stat = clone_path.stat()
                        age_seconds = current_time - stat.st_mtime
                        clone_stats.append(
                            {
                                "path": clone_path,
                                "age": age_seconds,
                                "size": get_directory_size(clone_path),
                            },
                        )
                    except Exception as exc:  # pragma: no cover - defensive logging
                        logger.warning(
                            "Failed to stat clone directory %s: %s",
                            clone_path,
                            exc,
                        )
                        error_count += 1

            clone_stats.sort(key=lambda item: (item["age"], -item["size"]))

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
                        logger.warning(
                            "Could not remove clone directory after retries: %s",
                            path,
                        )
                        error_count += 1
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Failed to remove clone directory %s: %s", path, exc)
                    error_count += 1

            total_size_saved = sum(stat["size"] for stat in to_remove)
            if self._profile_manager:
                self._profile_manager.update_metadata(
                    {
                        "last_cleanup": current_time,
                        "last_cleanup_count": cleaned_count,
                        "last_cleanup_size_saved": total_size_saved,
                        "remaining_clones": remaining_count,
                    },
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
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to cleanup old clones: %s", exc)
            return {"cleaned": 0, "remaining": 0, "errors": 1}
