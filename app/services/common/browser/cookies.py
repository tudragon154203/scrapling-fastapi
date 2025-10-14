"""Chromium cookie database management with SQLite operations."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Sequence

from app.services.common.browser.cookie_repository import ChromiumCookieRepository
from app.services.common.browser.sqlite_utils import SQLiteExecutionError
from app.services.common.browser.types import (
    CookieData,
    CookieList,
    convert_samesite,
    convert_samesite_to_db,
)

logger = logging.getLogger(__name__)


class ChromiumCookieManager:
    """Manages Chromium cookie database operations with robust Windows lock handling."""

    def __init__(
        self,
        cookies_db_path: Path,
        *,
        repository: Optional[ChromiumCookieRepository] = None,
    ) -> None:
        """Initialize the cookie manager."""
        self.cookies_db_path = cookies_db_path
        self.is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None
        if self.is_test_env:
            self.max_copy_attempts = 2
            self.max_sql_attempts = 2
            self.max_atomic_attempts = 5
        else:
            self.max_copy_attempts = 10
            self.max_sql_attempts = 10
            self.max_atomic_attempts = 25

        self.repository = repository or ChromiumCookieRepository(
            cookies_db_path,
            max_copy_attempts=self.max_copy_attempts,
            max_sql_attempts=self.max_sql_attempts,
            max_atomic_attempts=self.max_atomic_attempts,
        )

    def ensure_cookies_database(self) -> bool:
        """Ensure the SQLite cookies DB exists with expected schema."""
        try:
            self.repository.ensure_schema()
            return True
        except SQLiteExecutionError as exc:
            logger.warning("Cookies DB invalid at %s: %s. Reinitializing.", self.cookies_db_path, exc)
            return self.repository.reinitialize_database(logger=logger)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Unexpected error ensuring cookies DB: %s", exc)
            return False

    def read_cookies_from_db(self) -> CookieList:
        """Read cookies from Chromium SQLite database."""
        try:
            if not self.ensure_cookies_database():
                return []

            rows = self.repository.fetch_all(logger=logger)
            cookies: CookieList = []
            for row in rows:
                cookie: CookieData = {
                    "name": row["name"],
                    "value": row["value"],
                    "domain": row["host_key"],
                    "path": row["path"],
                    "expires": row["expires_utc"] if row["has_expires"] else -1,
                    "httpOnly": bool(row["is_httponly"]),
                    "secure": bool(row["is_secure"]),
                    "sameSite": convert_samesite(row["samesite"]),
                    "creationTime": row["creation_utc"],
                    "lastAccessTime": row["last_access_utc"],
                    "persistent": bool(row["is_persistent"]),
                }
                cookies.append(cookie)
            return cookies
        except SQLiteExecutionError as exc:
            logger.warning("Failed to read cookies after retries: %s", exc)
            return []
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to read cookies: %s", exc)
            return []

    def write_cookies_to_db(self, cookies: CookieList) -> bool:
        """Write cookies to Chromium SQLite database."""
        if not cookies:
            return True

        if not self.ensure_cookies_database():
            return False

        try:
            now = int(time.time() * 1_000_000)
            rows: List[Sequence[object]] = []
            for cookie in cookies:
                expires = cookie.get("expires", -1) or -1
                has_expires = 1 if expires != -1 else 0
                rows.append(
                    (
                        now,
                        cookie.get("domain", ""),
                        cookie.get("name", ""),
                        cookie.get("value", ""),
                        cookie.get("path", "/"),
                        expires,
                        1 if cookie.get("secure", False) else 0,
                        1 if cookie.get("httpOnly", False) else 0,
                        convert_samesite_to_db(cookie.get("sameSite", "None")),
                        now,
                        has_expires,
                        1 if cookie.get("persistent", True) else 0,
                    )
                )
                now += 1  # ensure unique creation timestamps for UNIQUE constraint

            self.repository.write_rows(rows, logger=logger)
            return True
        except SQLiteExecutionError as exc:
            logger.warning("Failed to write cookies after retries: %s", exc)
            return False
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to write cookies: %s", exc)
            return False
