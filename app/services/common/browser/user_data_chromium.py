"""Chromium user data orchestration for master/clone profiles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, ContextManager, Dict, Optional, Tuple

from app.services.common.browser.context_manager import ChromiumContextManager
from app.services.common.browser.cookie_sync import ChromiumCookieSync
from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.disk_stats import ChromiumDiskStats
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_housekeeping import ChromiumProfileHousekeeping
from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.utils import copytree_recursive


class ChromiumUserDataManager:
    """Coordinate Chromium user data collaborators."""

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
            self.cookie_manager = ChromiumCookieManager(self.path_manager.get_cookies_db_path())

        self.context_manager = ChromiumContextManager(
            self.path_manager,
            self.profile_manager,
            enabled=self.enabled,
        )
        self.cookie_sync = ChromiumCookieSync(
            self.path_manager,
            self.profile_manager,
            self.cookie_manager,
            enabled=self.enabled,
        )
        self.profile_housekeeping = ChromiumProfileHousekeeping(
            self.path_manager,
            self.profile_manager,
            enabled=self.enabled,
        )
        self.disk_stats = ChromiumDiskStats(
            self.path_manager,
            self.profile_manager,
            enabled=self.enabled,
        )

    @property
    def base_path(self) -> Optional[Path]:
        return self._base_path

    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
        return self.context_manager.get_user_data_context(mode)

    def export_cookies(self, format: str = "json") -> Optional[Dict[str, Any]]:
        return self.cookie_sync.export_cookies(format)

    def import_cookies(self, cookie_data: Dict[str, Any]) -> bool:
        return self.cookie_sync.import_cookies(cookie_data)

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        self.profile_housekeeping.update_metadata(updates)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        return self.profile_housekeeping.get_metadata()

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        return self.profile_housekeeping.get_browserforge_fingerprint()

    def is_enabled(self) -> bool:
        return self.enabled

    def get_master_dir(self) -> Optional[str]:
        return self.path_manager.get_master_dir()

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> Dict[str, int]:
        return self.profile_housekeeping.cleanup_old_clones(max_age_hours, max_count)

    def get_disk_usage_stats(self) -> Dict[str, Any]:
        return self.disk_stats.get_disk_usage_stats()

    def _copytree_recursive(self, src: Path, dst: Path) -> None:
        copytree_recursive(src, dst)
