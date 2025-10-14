"""Disk usage reporting for Chromium user-data directories."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.types import DiskUsageStats
from app.services.common.browser.utils import get_directory_size

logger = logging.getLogger(__name__)


class ChromiumDiskStats:
    """Aggregate disk usage metrics for Chromium user-data storage."""

    def __init__(
        self,
        path_manager: ChromiumPathManager,
        profile_manager: Optional[ChromiumProfileManager],
        enabled: bool,
    ) -> None:
        self._path_manager = path_manager
        self._profile_manager = profile_manager
        self._enabled = enabled

    def get_disk_usage_stats(self) -> Dict[str, Any]:
        if not self._enabled or self._profile_manager is None:
            return {"enabled": False}

        try:
            master_size = (
                get_directory_size(self._path_manager.master_dir)
                if self._path_manager.master_dir.exists()
                else 0
            )
            clones_size = (
                get_directory_size(self._path_manager.clones_dir)
                if self._path_manager.clones_dir.exists()
                else 0
            )
            total_size = master_size + clones_size

            clone_count = (
                len([d for d in self._path_manager.clones_dir.iterdir() if d.is_dir()])
                if self._path_manager.clones_dir.exists()
                else 0
            )

            metadata = self._profile_manager.read_metadata() or {}

            stats: DiskUsageStats = {
                "enabled": True,
                "master_size_mb": master_size,
                "clones_size_mb": clones_size,
                "total_size_mb": total_size,
                "clone_count": clone_count,
                "master_dir": str(self._path_manager.master_dir),
                "clones_dir": str(self._path_manager.clones_dir),
                "last_cleanup": metadata.get("last_cleanup"),
                "last_cleanup_count": metadata.get("last_cleanup_count", 0),
                "last_cleanup_size_saved": metadata.get("last_cleanup_size_saved", 0),
            }
            return stats

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to get disk usage stats: %s", exc)
            return {"enabled": True, "error": str(exc)}
