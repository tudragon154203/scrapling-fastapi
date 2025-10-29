from pathlib import Path

import sqlite3

from app.services.common.browser.cookie_repository import ChromiumCookieRepository


def _make_repository(db_path: Path) -> ChromiumCookieRepository:
    return ChromiumCookieRepository(
        db_path,
        max_copy_attempts=2,
        max_sql_attempts=2,
        max_atomic_attempts=2,
    )


def test_ensure_schema_creates_table(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    repository = _make_repository(db_path)

    repository.ensure_schema()

    assert db_path.exists()
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'"
        )
        assert cursor.fetchone() is not None


def test_fetch_all_returns_empty_when_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    repository = _make_repository(db_path)

    rows = repository.fetch_all()

    assert rows == []


def test_write_rows_and_fetch_all(tmp_path: Path) -> None:
    db_path = tmp_path / "Cookies"
    repository = _make_repository(db_path)

    now = 123456
    rows = [
        (
            now,
            ".example.com",
            "session",
            "abc123",
            "/",
            now + 100,
            1,
            1,
            1,
            now,
            1,
            1,
        )
    ]

    repository.write_rows(rows)
    fetched = repository.fetch_all()

    assert len(fetched) == 1
    assert fetched[0]["name"] == "session"
    assert fetched[0]["host_key"] == ".example.com"
