import logging
import sqlite3
from pathlib import Path

import pytest

from app.services.common.browser import sqlite_utils


@pytest.mark.parametrize("failures", [0, 1])
def test_copy_database_with_retries_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failures: int) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "destination.db"

    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE example(id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO example(value) VALUES ('hello')")
        conn.commit()

    attempts = {"count": 0}
    original_copy2 = sqlite_utils.shutil.copy2

    def flaky_copy(src: Path, dest: Path) -> None:
        attempts["count"] += 1
        if attempts["count"] <= failures:
            raise OSError("simulated copy failure")
        original_copy2(src, dest)

    if failures:
        monkeypatch.setattr(sqlite_utils.shutil, "copy2", flaky_copy)

    success = sqlite_utils.copy_database_with_retries(
        source,
        destination,
        max_attempts=3,
        logger=logging.getLogger(__name__),
    )

    assert success is True
    assert destination.exists()
    with sqlite3.connect(destination) as conn:
        row = conn.execute("SELECT value FROM example").fetchone()
        assert row[0] == "hello"


def test_copy_database_with_retries_exhausts_attempts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.db"
    destination = tmp_path / "destination.db"
    source.write_bytes(b"content")

    monkeypatch.setattr(
        sqlite_utils.shutil,
        "copy2",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("always fails")),
    )

    success = sqlite_utils.copy_database_with_retries(
        source,
        destination,
        max_attempts=2,
        logger=logging.getLogger(__name__),
    )

    assert success is False
    assert destination.exists() is False


class _Operation:
    def __init__(self, failures: int, result: int) -> None:
        self.failures = failures
        self.attempts = 0
        self.result = result

    def __call__(self, connection: sqlite3.Connection) -> int:
        self.attempts += 1
        if self.attempts <= self.failures:
            raise sqlite3.OperationalError("temporary lock")
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS counter(val INTEGER)")
        cursor.execute("INSERT INTO counter(val) VALUES (?)", (self.result,))
        connection.commit()
        return self.result


def test_execute_with_retries_eventually_succeeds(tmp_path: Path) -> None:
    db_path = tmp_path / "database.db"

    operation = _Operation(failures=1, result=42)
    output = sqlite_utils.execute_with_retries(
        db_path,
        operation,
        max_attempts=3,
        logger=logging.getLogger(__name__),
    )

    assert output == 42
    assert operation.attempts == 2


def test_execute_with_retries_raises_after_failures(tmp_path: Path) -> None:
    db_path = tmp_path / "database.db"

    operation = _Operation(failures=3, result=5)
    with pytest.raises(sqlite_utils.SQLiteExecutionError):
        sqlite_utils.execute_with_retries(
            db_path,
            operation,
            max_attempts=2,
            logger=logging.getLogger(__name__),
        )

    assert operation.attempts == 2
