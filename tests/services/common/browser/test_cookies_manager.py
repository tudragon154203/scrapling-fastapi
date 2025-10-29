import sqlite3
from pathlib import Path

import pytest

from app.services.common.browser.cookies import ChromiumCookieManager


@pytest.fixture()
def cookie_manager(tmp_path: Path) -> ChromiumCookieManager:
    cookies_db = tmp_path / "Cookies"
    return ChromiumCookieManager(cookies_db)


def test_ensure_cookies_database_creates_schema(cookie_manager: ChromiumCookieManager) -> None:
    assert cookie_manager.ensure_cookies_database() is True

    with sqlite3.connect(cookie_manager.cookies_db_path) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'"
        )
        assert cursor.fetchone() is not None


def test_write_and_read_roundtrip(cookie_manager: ChromiumCookieManager) -> None:
    cookies = [
        {
            "name": "session",
            "value": "abc123",
            "domain": ".example.com",
            "path": "/",
            "expires": 100,
            "httpOnly": True,
            "secure": False,
            "sameSite": "Lax",
            "persistent": True,
        }
    ]

    assert cookie_manager.write_cookies_to_db(cookies) is True

    read_back = cookie_manager.read_cookies_from_db()
    assert len(read_back) == 1
    stored = read_back[0]
    assert stored["name"] == "session"
    assert stored["value"] == "abc123"
    assert stored["domain"] == ".example.com"
    assert stored["sameSite"] == "Lax"
    assert stored["persistent"] is True


def test_read_cookies_handles_missing_database(cookie_manager: ChromiumCookieManager) -> None:
    # Ensure no database exists
    if cookie_manager.cookies_db_path.exists():
        cookie_manager.cookies_db_path.unlink()

    cookies = cookie_manager.read_cookies_from_db()
    assert cookies == []
