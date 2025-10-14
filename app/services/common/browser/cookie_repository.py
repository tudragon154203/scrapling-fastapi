"""SQLite data-access layer for Chromium cookies."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional, Sequence

from app.services.common.browser.sqlite_utils import (
    SQLiteExecutionError,
    copy_database_with_retries,
    execute_with_retries,
    initialize_database,
    replace_database_atomic,
)


def _safe_unlink(path: Path) -> None:
    """Remove the temporary SQLite file with backwards-compatible semantics."""

    try:
        path.unlink(missing_ok=True)
    except TypeError:  # pragma: no cover - compatibility for Python < 3.8
        if path.exists():
            path.unlink()


def create_cookies_table(connection: sqlite3.Connection) -> None:
    """Create Chromium cookies table and indexes if they are missing."""

    cursor = connection.cursor()
    cursor.execute(
        """
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
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_domain_index ON cookies (host_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_name_index ON cookies (name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS cookies_path_index ON cookies (path)")


class ChromiumCookieRepository:
    """Data-layer helper responsible for executing SQLite operations."""

    def __init__(
        self,
        cookies_db_path: Path,
        *,
        max_copy_attempts: int,
        max_sql_attempts: int,
        max_atomic_attempts: int,
    ) -> None:
        self.cookies_db_path = cookies_db_path
        self.max_copy_attempts = max_copy_attempts
        self.max_sql_attempts = max_sql_attempts
        self.max_atomic_attempts = max_atomic_attempts

    def ensure_schema(self) -> None:
        """Ensure the cookies database exists with the expected schema."""

        try:
            self.cookies_db_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.cookies_db_path.exists():
                initialize_database(self.cookies_db_path, create_cookies_table)
                return

            with sqlite3.connect(self.cookies_db_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                cursor = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'"
                )
                if cursor.fetchone() is None:
                    create_cookies_table(connection)
                    connection.commit()
        except sqlite3.DatabaseError as exc:
            raise SQLiteExecutionError("Failed to validate Chromium cookies schema") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise SQLiteExecutionError("Unexpected error ensuring cookies schema") from exc

    def reinitialize_database(self, *, logger: Optional[logging.Logger] = None) -> bool:
        """Recreate the cookies database from scratch."""

        temp_new = self.cookies_db_path.parent / f"reinit_cookies_{uuid.uuid4().hex}.db"
        try:
            initialize_database(temp_new, create_cookies_table)
            return replace_database_atomic(
                temp_new,
                self.cookies_db_path,
                max_attempts=self.max_atomic_attempts,
                logger=logger,
            )
        finally:
            _safe_unlink(temp_new)

    def fetch_all(self, *, logger: Optional[logging.Logger] = None) -> List[sqlite3.Row]:
        """Fetch all rows from the cookies table."""

        if not self.cookies_db_path.exists():
            return []

        temp_db = self.cookies_db_path.parent / f"temp_cookies_{uuid.uuid4().hex}.db"
        try:
            copied = copy_database_with_retries(
                self.cookies_db_path,
                temp_db,
                max_attempts=self.max_copy_attempts,
                logger=logger,
            )
            if not copied:
                raise SQLiteExecutionError("Failed to copy cookies database for reading")

            return execute_with_retries(
                temp_db,
                lambda connection: list(connection.execute(self._select_all_sql())),
                max_attempts=self.max_sql_attempts,
                logger=logger,
                row_factory=sqlite3.Row,
            )
        finally:
            _safe_unlink(temp_db)

    def write_rows(
        self,
        rows: Sequence[Sequence[object]],
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Write the provided cookie rows to the database."""

        temp_db = self.cookies_db_path.parent / f"temp_cookies_write_{uuid.uuid4().hex}.db"
        try:
            if self.cookies_db_path.exists():
                copied = copy_database_with_retries(
                    self.cookies_db_path,
                    temp_db,
                    max_attempts=self.max_copy_attempts,
                    logger=logger,
                )
                if not copied:
                    raise SQLiteExecutionError("Failed to copy cookies database for writing")
            else:
                initialize_database(temp_db, create_cookies_table)

            execute_with_retries(
                temp_db,
                lambda connection: self._write_rows(connection, rows),
                max_attempts=self.max_sql_attempts,
                logger=logger,
            )

            success = replace_database_atomic(
                temp_db,
                self.cookies_db_path,
                max_attempts=self.max_atomic_attempts,
                logger=logger,
            )
            if not success:
                raise SQLiteExecutionError("Failed to replace cookies database after write")
        finally:
            _safe_unlink(temp_db)

    @staticmethod
    def _write_rows(
        connection: sqlite3.Connection,
        rows: Sequence[Sequence[object]],
    ) -> None:
        cursor = connection.cursor()
        cursor.executemany(
            """
            INSERT OR REPLACE INTO cookies (
                creation_utc, host_key, name, value, path, expires_utc,
                is_secure, is_httponly, samesite, last_access_utc,
                has_expires, is_persistent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    @staticmethod
    def _select_all_sql() -> str:
        return (
            "SELECT creation_utc, host_key, name, value, path, expires_utc, "
            "is_secure, is_httponly, samesite, last_access_utc, has_expires, is_persistent "
            "FROM cookies ORDER BY creation_utc DESC"
        )


__all__ = [
    "ChromiumCookieRepository",
    "create_cookies_table",
]
