"""Chromium cookie database management with SQLite operations."""

import logging
import os
import shutil
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from app.services.common.browser.types import (
    CookieData,
    CookieList,
    convert_samesite,
    convert_samesite_to_db,
)
from app.services.common.browser.utils import atomic_file_replace

logger = logging.getLogger(__name__)


class ChromiumCookieManager:
    """Manages Chromium cookie database operations with robust Windows lock handling."""

    def __init__(self, cookies_db_path: Path):
        """Initialize the cookie manager.

        Args:
            cookies_db_path: Path to Chromium cookies database
        """
        self.cookies_db_path = cookies_db_path
        # Use smaller retry counts in test environment to speed up tests
        self.is_test_env = os.getenv('PYTEST_CURRENT_TEST') is not None
        if self.is_test_env:
            self.max_copy_attempts = 2  # Reduced from 10
            self.max_sql_attempts = 2   # Reduced from 10
            self.max_atomic_attempts = 5  # Reduced from 25
        else:
            self.max_copy_attempts = 10
            self.max_sql_attempts = 10
            self.max_atomic_attempts = 25

    def ensure_cookies_database(self) -> bool:
        """Ensure the SQLite cookies DB exists with expected schema.

        Returns:
            True if database is ready for use, False if reinitialization failed
        """
        try:
            # Ensure parent directory exists
            self.cookies_db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create if missing
            if not self.cookies_db_path.exists():
                self._create_cookies_database(self.cookies_db_path)
                return True

            # Verify schema presence
            with sqlite3.connect(self.cookies_db_path) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
                row = cursor.fetchone()
                if not row:
                    # Table missing; recreate schema in-place
                    self._create_cookies_table(conn)
            return True

        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            # Database corrupt; reinitialize
            logger.warning(f"Cookies DB invalid at {self.cookies_db_path}: {e}. Reinitializing.")
            return self._reinitialize_corrupted_database()
        except Exception as e:
            logger.warning(f"Unexpected error ensuring cookies DB: {e}")
            return False

    def read_cookies_from_db(self) -> CookieList:
        """Read cookies from Chromium SQLite database with robust Windows lock handling.

        Returns:
            List of cookie dictionaries
        """
        try:
            self.ensure_cookies_database()

            # Create temporary copy to avoid locking issues
            temp_db = self.cookies_db_path.parent / f"temp_cookies_{uuid.uuid4().hex}.db"

            # Retry copying with exponential backoff
            delay = 0.1
            copied = False
            for attempt in range(1, self.max_copy_attempts + 1):
                try:
                    shutil.copy2(self.cookies_db_path, temp_db)
                    copied = True
                    break
                except Exception as e:
                    logger.warning(f"Temp copy failed (attempt {attempt}/{self.max_copy_attempts}): {e}")
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)

            if not copied:
                logger.warning(f"Failed to copy cookies DB: {self.cookies_db_path}")
                return []

            # Read cookies with retries for transient errors
            cookies: CookieList = []
            delay = 0.1
            last_err: Optional[Exception] = None

            for attempt in range(1, self.max_sql_attempts + 1):
                try:
                    with sqlite3.connect(temp_db) as conn:
                        conn.execute("PRAGMA busy_timeout = 5000")
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT creation_utc, host_key, name, value, path, expires_utc,
                                   is_secure, is_httponly, samesite, last_access_utc,
                                   has_expires, is_persistent
                            FROM cookies
                            ORDER BY creation_utc DESC
                        """)
                        for row in cursor.fetchall():
                            cookie = CookieData(
                                name=row["name"],
                                value=row["value"],
                                domain=row["host_key"],
                                path=row["path"],
                                expires=row["expires_utc"] if row["has_expires"] else -1,
                                httpOnly=bool(row["is_httponly"]),
                                secure=bool(row["is_secure"]),
                                sameSite=convert_samesite(row["samesite"]),
                                creationTime=row["creation_utc"],
                                lastAccessTime=row["last_access_utc"],
                                persistent=bool(row["is_persistent"])
                            )
                            cookies.append(cookie)
                    break
                except sqlite3.OperationalError as e:
                    last_err = e
                    logger.warning(f"SQLite OperationalError (attempt {attempt}/{self.max_sql_attempts}): {e}")
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error reading temp DB: {e}")
                    break

            # Cleanup temp database
            try:
                temp_db.unlink()
            except Exception:
                pass

            if cookies:
                return cookies

            if last_err:
                logger.warning(f"Failed to read cookies after retries: {last_err}")
            return []

        except Exception as e:
            logger.warning(f"Failed to read cookies: {e}")
            # Ensure cleanup if temp_db was created
            try:
                if 'temp_db' in locals() and temp_db.exists():
                    temp_db.unlink()
            except Exception:
                pass
            return []

    def write_cookies_to_db(self, cookies: CookieList) -> bool:
        """Write cookies to Chromium SQLite database with robust Windows lock handling.

        Args:
            cookies: List of cookie dictionaries to write

        Returns:
            True if write succeeded, False otherwise
        """
        if not cookies:
            return True

        try:
            self.ensure_cookies_database()

            # Create temporary copy for writing
            temp_db = self.cookies_db_path.parent / f"temp_cookies_write_{uuid.uuid4().hex}.db"

            if self.cookies_db_path.exists():
                # Copy existing database with retries
                delay = 0.1
                copied = False
                for attempt in range(1, self.max_copy_attempts + 1):
                    try:
                        shutil.copy2(self.cookies_db_path, temp_db)
                        copied = True
                        break
                    except Exception as e:
                        logger.warning(f"Write copy failed (attempt {attempt}/{self.max_copy_attempts}): {e}")
                        time.sleep(delay)
                        delay = min(2.0, delay * 2)
                if not copied:
                    logger.warning(f"Failed to copy DB for write: {self.cookies_db_path}")
                    return False
            else:
                self._create_cookies_database(temp_db)

            # Insert/update cookies with retries
            delay = 0.1
            sql_success = False
            last_err: Optional[Exception] = None

            for attempt in range(1, self.max_sql_attempts + 1):
                try:
                    with sqlite3.connect(temp_db) as conn:
                        conn.execute("PRAGMA busy_timeout = 5000")
                        cursor = conn.cursor()

                        for cookie in cookies:
                            samesite_db = convert_samesite_to_db(cookie.get("sameSite", "None"))

                            cursor.execute("""
                                INSERT OR REPLACE INTO cookies (
                                    creation_utc, host_key, name, value, path, expires_utc,
                                    is_secure, is_httponly, samesite, last_access_utc,
                                    has_expires, is_persistent
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                int(time.time() * 1000000),  # creation_utc in microseconds
                                cookie.get("domain", ""),
                                cookie.get("name", ""),
                                cookie.get("value", ""),
                                cookie.get("path", "/"),
                                cookie.get("expires", -1),
                                1 if cookie.get("secure", False) else 0,
                                1 if cookie.get("httpOnly", False) else 0,
                                samesite_db,
                                int(time.time() * 1000000),  # last_access_utc in microseconds
                                1 if cookie.get("expires", -1) != -1 else 0,
                                1 if cookie.get("persistent", True) else 0
                            ))

                        conn.commit()
                    sql_success = True
                    break
                except sqlite3.OperationalError as e:
                    last_err = e
                    logger.warning(f"SQLite OperationalError writing (attempt {attempt}/{self.max_sql_attempts}): {e}")
                    time.sleep(delay)
                    delay = min(2.0, delay * 2)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Unexpected error writing temp DB: {e}")
                    break

            if not sql_success:
                try:
                    if temp_db.exists():
                        temp_db.unlink()
                except Exception:
                    pass
                if last_err:
                    logger.warning(f"Failed to write cookies after retries: {last_err}")
                return False

            # Replace original database atomically
            return atomic_file_replace(temp_db, self.cookies_db_path, max_attempts=self.max_atomic_attempts)

        except Exception as e:
            logger.warning(f"Failed to write cookies: {e}")
            try:
                if 'temp_db' in locals() and temp_db.exists():
                    temp_db.unlink()
            except Exception:
                pass
            return False

    def _create_cookies_database(self, db_path: Path) -> None:
        """Create a new Chromium cookies database with proper schema."""
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            self._create_cookies_table(conn)

    def _create_cookies_table(self, conn: sqlite3.Connection) -> None:
        """Create cookies table and indexes."""
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cookies (
                creation_utc INTEGER NOT NULL,
                host_key TEXT NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                path TEXT NOT NULL,
                expires_utc INTEGER NOT NULL,
                is_secure INTEGER NOT NULL,
                is_httponly INTEGER NOT NULL,
                samesite INTEGER NOT NULL,
                last_access_utc INTEGER NOT NULL,
                has_expires INTEGER NOT NULL DEFAULT 1,
                is_persistent INTEGER NOT NULL DEFAULT 1,
                priority INTEGER NOT NULL DEFAULT 1,
                encrypted_value BLOB DEFAULT '',
                samesite_scheme INTEGER NOT NULL DEFAULT 0,
                source_scheme INTEGER NOT NULL DEFAULT 0,
                UNIQUE (creation_utc, host_key, name, path)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS cookies_domain_index ON cookies (host_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS cookies_name_index ON cookies (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS cookies_path_index ON cookies (path)")

        conn.commit()

    def _reinitialize_corrupted_database(self) -> bool:
        """Reinitialize a corrupted cookie database."""
        temp_new = self.cookies_db_path.parent / f"reinit_cookies_{uuid.uuid4().hex}.db"

        try:
            # Build a fresh DB
            self._create_cookies_database(temp_new)

            # Replace original atomically
            success = atomic_file_replace(temp_new, self.cookies_db_path, max_attempts=self.max_atomic_attempts)
            if not success:
                raise RuntimeError("Failed to replace corrupted database")

            return True
        except Exception:
            return False
        finally:
            # Cleanup temp file
            try:
                if temp_new.exists():
                    temp_new.unlink()
            except Exception:
                pass
