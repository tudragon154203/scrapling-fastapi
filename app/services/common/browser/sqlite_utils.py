"""Reusable SQLite utility functions with retry semantics."""

from __future__ import annotations

import logging
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Callable, Optional, TypeVar

from app.services.common.browser.utils import atomic_file_replace

T = TypeVar("T")


class SQLiteExecutionError(RuntimeError):
    """Raised when a SQLite operation fails after all retry attempts."""


def copy_database_with_retries(
    source: Path,
    destination: Path,
    *,
    max_attempts: int,
    initial_delay: float = 0.1,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """Copy a SQLite database, retrying transient failures."""
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            shutil.copy2(source, destination)
            return True
        except Exception as exc:  # pragma: no cover - defensive guard
            if logger:
                logger.warning(
                    "SQLite copy failed (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
            if attempt >= max_attempts:
                break
            time.sleep(delay)
            delay = min(2.0, delay * 2)

    return False


def execute_with_retries(
    db_path: Path,
    operation: Callable[[sqlite3.Connection], T],
    *,
    max_attempts: int,
    initial_delay: float = 0.1,
    logger: Optional[logging.Logger] = None,
    row_factory: Optional[Callable[[sqlite3.Cursor], sqlite3.Row]] = None,
) -> T:
    """Execute a SQLite callable with retry support."""
    delay = initial_delay
    last_error: Optional[BaseException] = None

    for attempt in range(1, max_attempts + 1):
        try:
            with sqlite3.connect(db_path) as connection:
                connection.execute("PRAGMA busy_timeout = 5000")
                if row_factory is not None:
                    connection.row_factory = row_factory  # type: ignore[attr-defined]
                result = operation(connection)
                return result
        except sqlite3.OperationalError as exc:
            last_error = exc
            if logger:
                logger.warning(
                    "SQLite operational error (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
            if attempt >= max_attempts:
                break
            time.sleep(delay)
            delay = min(2.0, delay * 2)
        except Exception as exc:  # pragma: no cover - unexpected errors bubble
            raise SQLiteExecutionError(str(exc)) from exc

    if last_error is not None:
        raise SQLiteExecutionError(str(last_error)) from last_error
    raise SQLiteExecutionError("SQLite operation failed without a captured error")


def initialize_database(
    db_path: Path,
    initializer: Callable[[sqlite3.Connection], None],
) -> None:
    """Create a SQLite database and apply the provided initializer."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA busy_timeout = 5000")
        initializer(connection)
        connection.commit()


def replace_database_atomic(
    source: Path,
    destination: Path,
    *,
    max_attempts: int,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """Replace the destination database atomically using retries."""
    success = atomic_file_replace(source, destination, max_attempts=max_attempts)
    if not success and logger:
        logger.warning(
            "Atomic replace failed after %s attempts for %s", max_attempts, destination
        )
    return success


__all__ = [
    "SQLiteExecutionError",
    "copy_database_with_retries",
    "execute_with_retries",
    "initialize_database",
    "replace_database_atomic",
]
