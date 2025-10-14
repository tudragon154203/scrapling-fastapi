"""Disk usage helpers for Chromium user-data directories."""

from __future__ import annotations

import logging
from typing import Optional

from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.utils import get_directory_size
from app.services.common.browser.types import DiskUsageStats

logger = logging.getLogger(__name__)


class ChromiumDiskStatistics:
    """Compute disk utilization details for Chromium user-data directories."""

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

    def get_disk_usage_stats(self) -> DiskUsageStats:
        """Return disk usage metrics for master and clone directories."""

        if not self._enabled:
            return {"enabled": False}

        master_dir = getattr(self._path_manager, "master_dir", None)
        clones_dir = getattr(self._path_manager, "clones_dir", None)

        try:
            master_size = get_directory_size(master_dir) if master_dir and master_dir.exists() else 0
            clones_size = get_directory_size(clones_dir) if clones_dir and clones_dir.exists() else 0
            total_size = master_size + clones_size

            clone_count = (
                len([directory for directory in clones_dir.iterdir() if directory.is_dir()])
                if clones_dir and clones_dir.exists()
                else 0
            )

            metadata = self._profile_manager.read_metadata() if self._profile_manager else {}

            stats: DiskUsageStats = {
                "enabled": True,
                "master_size_mb": master_size,
                "clones_size_mb": clones_size,
                "total_size_mb": total_size,
                "clone_count": clone_count,
                "master_dir": str(master_dir) if master_dir else None,
                "clones_dir": str(clones_dir) if clones_dir else None,
                "last_cleanup": metadata.get("last_cleanup") if metadata else None,
                "last_cleanup_count": metadata.get("last_cleanup_count", 0) if metadata else 0,
                "last_cleanup_size_saved": metadata.get("last_cleanup_size_saved", 0) if metadata else 0,
            }
            return stats
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to get disk usage stats: %s", exc)
            return {"enabled": True, "error": str(exc)}
