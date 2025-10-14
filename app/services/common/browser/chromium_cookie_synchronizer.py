"""Cookie export/import helpers for Chromium user-data management."""

from __future__ import annotations

import logging
import time
from typing import Dict, Any, Optional

from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager
from app.services.common.browser.types import CookieExportResult, StorageStateResult

logger = logging.getLogger(__name__)


class ChromiumCookieSynchronizer:
    """Synchronize cookies between Chromium profiles and serialized formats."""

    def __init__(
        self,
        *,
        enabled: bool,
        path_manager: ChromiumPathManager,
        cookie_manager: Optional[ChromiumCookieManager],
        profile_manager: Optional[ChromiumProfileManager],
    ) -> None:
        self._enabled = enabled
        self._path_manager = path_manager
        self._cookie_manager = cookie_manager
        self._profile_manager = profile_manager

    def export_cookies(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """Export cookies from the master profile."""

        if not self._enabled:
            logger.warning("Chromium user data management disabled, cannot export cookies")
            return None

        master_dir = getattr(self._path_manager, "master_dir", None)
        if not master_dir or not master_dir.exists():
            logger.warning("Chromium master profile not found at %s", master_dir)
            return None

        if not self._cookie_manager or not self._profile_manager:
            logger.warning("Cookie synchronization dependencies not ready")
            return None

        try:
            cookies = self._cookie_manager.read_cookies_from_db()

            if format == "storage_state":
                storage_state: StorageStateResult = {
                    "cookies": [
                        {
                            "name": cookie["name"],
                            "value": cookie["value"],
                            "domain": cookie["domain"],
                            "path": cookie["path"],
                            "expires": cookie.get("expires", -1),
                            "httpOnly": cookie.get("httpOnly", False),
                            "secure": cookie.get("secure", False),
                            "sameSite": cookie.get("sameSite", "None"),
                        }
                        for cookie in cookies
                    ],
                    "origins": [],
                }
                return storage_state

            cookie_result: CookieExportResult = {
                "format": format,
                "cookies": cookies,
                "profile_metadata": self._profile_manager.read_metadata(),
                "cookies_available": bool(cookies),
                "master_profile_path": str(master_dir),
                "export_timestamp": time.time(),
            }
            return cookie_result
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to export cookies: %s", exc)
            return None

    def import_cookies(self, cookie_data: Dict[str, Any]) -> bool:
        """Import cookies to the master profile."""

        if not self._enabled:
            logger.warning("Chromium user data management disabled, cannot import cookies")
            return False

        master_dir = getattr(self._path_manager, "master_dir", None)
        if not self._cookie_manager or not self._profile_manager or not master_dir:
            logger.warning("Cookie synchronization dependencies not ready")
            return False

        try:
            self._path_manager.ensure_directories_exist()
            default_dir = master_dir / "Default"
            default_dir.mkdir(parents=True, exist_ok=True)
            self._profile_manager.ensure_metadata()
        except Exception as exc:
            logger.warning(
                "Failed to initialize Chromium master profile directories: %s",
                exc,
            )
            return False

        try:
            if cookie_data.get("format") == "storage_state":
                cookies = cookie_data.get("cookies", [])
            else:
                cookies = cookie_data.get("cookies", [])

            if not cookies:
                logger.info("No cookies to import")
                self._profile_manager.update_metadata(
                    {
                        "last_cookie_import": time.time(),
                        "cookie_import_count": 0,
                        "cookie_import_status": "success",
                    },
                )
                return True

            success = self._cookie_manager.write_cookies_to_db(cookies)

            timestamp = time.time()
            if success:
                self._profile_manager.update_metadata(
                    {
                        "last_cookie_import": timestamp,
                        "cookie_import_count": len(cookies),
                        "cookie_import_status": "success",
                    },
                )
                logger.info(
                    "Successfully imported %s cookies to Chromium master profile",
                    len(cookies),
                )
                return True

            self._profile_manager.update_metadata(
                {
                    "last_cookie_import": timestamp,
                    "cookie_import_status": "failed",
                },
            )
            return False
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to import cookies: %s", exc)
            try:
                self._profile_manager.update_metadata(
                    {
                        "last_cookie_import": time.time(),
                        "cookie_import_status": f"error: {str(exc)}",
                    },
                )
            except Exception:  # pragma: no cover - nested failure
                logger.debug("Unable to update metadata after cookie import failure")
            return False
