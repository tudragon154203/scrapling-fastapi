"""Manages Chromium user data directories with master/clone architecture."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, ContextManager, Dict, Optional, Tuple

from app.services.common.browser.context_manager import ChromiumContextManager
from app.services.common.browser.cookie_sync import ChromiumCookieSync
from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.disk_stats import ChromiumDiskStats
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_housekeeping import ChromiumProfileHousekeeping
from app.services.common.browser.profile_manager import ChromiumProfileManager

logger = logging.getLogger(__name__)


class ChromiumUserDataManager:
    """Orchestrator class for Chromium user data management using extracted concerns."""

    def __init__(self, user_data_dir: Optional[str] = None):
        """Initialize the Chromium user data manager."""

        self.user_data_dir = user_data_dir
        self.enabled = user_data_dir is not None
        self._base_path = Path(user_data_dir) if user_data_dir else None

        self.path_manager = ChromiumPathManager(user_data_dir)

        self.profile_manager: Optional[ChromiumProfileManager]
        self.cookie_manager: Optional[ChromiumCookieManager]

        if self.enabled:
            self.profile_manager = ChromiumProfileManager(
                self.path_manager.metadata_file,
                self.path_manager.fingerprint_file,
            )
            self.cookie_manager = ChromiumCookieManager(
                self.path_manager.get_cookies_db_path()
            )
        else:
            self.profile_manager = None
            self.cookie_manager = None

        self.context_manager = ChromiumContextManager(
            self.path_manager,
            self.profile_manager,
            self.enabled,
        )
        self.cookie_sync = ChromiumCookieSync(
            self.cookie_manager,
            self.profile_manager,
            self.path_manager,
            self.enabled,
        )
        self.profile_housekeeping = ChromiumProfileHousekeeping(
            self.path_manager,
            self.profile_manager,
            self.enabled,
        )
        self.disk_stats = ChromiumDiskStats(
            self.path_manager,
            self.profile_manager,
            self.enabled,
        )

    @property
    def base_path(self) -> Optional[Path]:
        """Base user data directory for the Chromium manager."""

        return self._base_path

    @property
    def lock_file(self) -> Optional[str]:
        """Expose lock file path for diagnostics."""

        if not self.enabled:
            return None
        return str(self.path_manager.lock_file)

    def get_user_data_context(self, mode: str) -> ContextManager[Tuple[str, Callable[[], None]]]:
        """Get a user data directory context for Chromium operations."""

        return self.context_manager.get_user_data_context(mode)

    def export_cookies(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """Export cookies from the master profile."""

        return self.cookie_sync.export_cookies(format=format)

    def import_cookies(self, cookie_data: Dict[str, Any]) -> bool:
        """Import cookies to the master profile."""

        return self.cookie_sync.import_cookies(cookie_data)

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata file with new information."""

        self.profile_housekeeping.update_metadata(updates)

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Get current metadata from master profile."""

        return self.profile_housekeeping.get_metadata()

    def get_browserforge_fingerprint(self) -> Optional[Dict[str, Any]]:
        """Get stored BrowserForge fingerprint if available."""

        return self.profile_housekeeping.get_browserforge_fingerprint()

    def is_enabled(self) -> bool:
        """Check if Chromium user data management is enabled."""

        return self.enabled

    def get_master_dir(self) -> Optional[str]:
        """Get the master directory path if enabled."""

        return self.path_manager.get_master_dir()

    def cleanup_old_clones(self, max_age_hours: int = 24, max_count: int = 50) -> Dict[str, int]:
        """Clean up old clone directories to prevent disk bloat."""

        return self.profile_housekeeping.cleanup_old_clones(
            max_age_hours=max_age_hours,
            max_count=max_count,
        )

    def get_disk_usage_stats(self) -> Dict[str, Any]:
        """Get disk usage statistics for the user data directories."""

        return self.disk_stats.get_disk_usage_stats()
