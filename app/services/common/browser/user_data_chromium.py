"""Manages Chromium user data directories with master/clone architecture."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ContextManager, Dict, Optional, Tuple

from app.services.common.browser.chromium_cookie_synchronizer import (
    ChromiumCookieSynchronizer,
)
from app.services.common.browser.chromium_disk_statistics import ChromiumDiskStatistics
from app.services.common.browser.chromium_profile_housekeeping import (
    ChromiumProfileHousekeeping,
)
from app.services.common.browser.chromium_user_data_context import (
    ChromiumUserDataContextManager,
    CleanupFn,
)
from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.types import CleanupResult, DiskUsageStats


class ChromiumUserDataManager:
    """Orchestrates Chromium user data operations via dedicated helpers."""

    def __init__(self, user_data_dir: Optional[str] = None) -> None:
        self.user_data_dir = user_data_dir
        self.enabled = user_data_dir is not None
        self._base_path = Path(user_data_dir) if user_data_dir else None

        self.path_manager = ChromiumPathManager(user_data_dir)
        self.profile_manager: Optional[ChromiumProfileManager] = None
        self.cookie_manager: Optional[ChromiumCookieManager] = None

        if self.enabled:
            self.profile_manager = ChromiumProfileManager(
                self.path_manager.metadata_file,
                self.path_manager.fingerprint_file,
            )
            self.cookie_manager = ChromiumCookieManager(
                self.path_manager.get_cookies_db_path(),
            )

        self._context_manager = ChromiumUserDataContextManager(
            enabled=self.enabled,
            path_manager=self.path_manager,
            profile_manager=self.profile_manager,
        )
        self._cookie_synchronizer = ChromiumCookieSynchronizer(
            enabled=self.enabled,
            path_manager=self.path_manager,
            cookie_manager=self.cookie_manager,
            profile_manager=self.profile_manager,
        )
        self._housekeeping = ChromiumProfileHousekeeping(
            enabled=self.enabled,
            path_manager=self.path_manager,
            profile_manager=self.profile_manager,
        )
        self._disk_statistics = ChromiumDiskStatistics(
            enabled=self.enabled,
            path_manager=self.path_manager,
            profile_manager=self.profile_manager,
        )

    @property
    def base_path(self) -> Optional[Path]:
        """Return the base user-data directory path."""

        return self._base_path

    @property
    def master_dir(self) -> Optional[Path]:
        """Expose the master profile directory for compatibility."""

        if not self.enabled or not getattr(self.path_manager, "enabled", False):
            return None
        return self.path_manager.master_dir

    @property
    def clones_dir(self) -> Optional[Path]:
        """Expose the clones directory for compatibility."""

        if not self.enabled or not getattr(self.path_manager, "enabled", False):
            return None
        return self.path_manager.clones_dir

    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, CleanupFn]]:
        """Get a user data directory context for Chromium operations."""

        return self._context_manager.get_user_data_context(mode)

    def export_cookies(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """Export cookies from the master profile."""

        return self._cookie_synchronizer.export_cookies(format)

    def import_cookies(self, cookie_data: Dict[str, Any]) -> bool:
        """Import cookies to the master profile."""

        return self._cookie_synchronizer.import_cookies(cookie_data)

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""

        if not self.enabled or not self.profile_manager:
            return
        self.profile_manager.update_metadata(updates)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current metadata from master profile."""

        if not self.enabled or not self.profile_manager:
            return None
        return self.profile_manager.read_metadata()

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""

        if not self.enabled or not self.profile_manager:
            return None
        return self.profile_manager.get_browserforge_fingerprint()

    def is_enabled(self) -> bool:
        """Return whether Chromium user data management is enabled."""

        return self.enabled

    def get_master_dir(self) -> Optional[str]:
        """Get the master directory path if enabled."""

        return self.path_manager.get_master_dir()

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> CleanupResult:
        """Clean up old clone directories to prevent disk bloat."""

        return self._housekeeping.cleanup_old_clones(max_age_hours, max_count)

    def get_disk_usage_stats(self) -> DiskUsageStats:
        """Get disk usage statistics for the user data directories."""

        return self._disk_statistics.get_disk_usage_stats()

    def _copytree_recursive(self, src: Path, dst: Path) -> None:
        """Recursively copy Chromium user data from src to dst."""

        from app.services.common.browser.utils import copytree_recursive

        copytree_recursive(src, dst)
