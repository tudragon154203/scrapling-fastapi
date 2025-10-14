"""Unit tests for ``ChromiumCookieManager`` behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence

import pytest

from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.sqlite_utils import SQLiteExecutionError
from app.services.common.browser.types import CookieData


@dataclass
class FakeRepository:
    """Test double for :class:`ChromiumCookieRepository`."""

    ensure_schema_error: Optional[Exception] = None
    reinitialize_result: bool = True
    fetch_all_result: Sequence[Any] = field(default_factory=list)
    fetch_all_error: Optional[Exception] = None
    write_rows_error: Optional[Exception] = None

    ensure_schema_called: int = 0
    reinitialize_called: int = 0
    fetch_all_called: int = 0
    write_rows_called: int = 0
    captured_rows: Optional[List[Sequence[object]]] = None

    def ensure_schema(self) -> None:
        self.ensure_schema_called += 1
        if self.ensure_schema_error is not None:
            raise self.ensure_schema_error

    def reinitialize_database(self, *, logger: Optional[Any] = None) -> bool:  # pragma: no cover - logger unused
        self.reinitialize_called += 1
        return self.reinitialize_result

    def fetch_all(self, *, logger: Optional[Any] = None):  # pragma: no cover - logger unused
        self.fetch_all_called += 1
        if self.fetch_all_error is not None:
            raise self.fetch_all_error
        return list(self.fetch_all_result)

    def write_rows(
        self,
        rows: Sequence[Sequence[object]],
        *,
        logger: Optional[Any] = None,  # pragma: no cover - logger unused
    ) -> None:
        self.write_rows_called += 1
        if self.write_rows_error is not None:
            raise self.write_rows_error
        self.captured_rows = [tuple(row) for row in rows]


@pytest.fixture()
def temp_db(tmp_path):
    return tmp_path / "Cookies"


@pytest.fixture()
def fake_repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture()
def manager(temp_db, fake_repository):
    return ChromiumCookieManager(temp_db, repository=fake_repository)


@pytest.mark.unit
def test_ensure_cookies_database_success(manager, fake_repository):
    assert manager.ensure_cookies_database() is True
    assert fake_repository.ensure_schema_called == 1
    assert fake_repository.reinitialize_called == 0


@pytest.mark.unit
def test_ensure_cookies_database_reinitializes_on_error(manager, fake_repository):
    fake_repository.ensure_schema_error = SQLiteExecutionError("boom")
    fake_repository.reinitialize_result = True

    assert manager.ensure_cookies_database() is True
    assert fake_repository.ensure_schema_called == 1
    assert fake_repository.reinitialize_called == 1


@pytest.mark.unit
def test_ensure_cookies_database_returns_false_when_reinit_fails(manager, fake_repository):
    fake_repository.ensure_schema_error = SQLiteExecutionError("boom")
    fake_repository.reinitialize_result = False

    assert manager.ensure_cookies_database() is False
    assert fake_repository.reinitialize_called == 1


@pytest.mark.unit
def test_read_cookies_from_db_maps_fields(manager, fake_repository):
    base_ts = 1234567890
    fake_repository.fetch_all_result = [
        {
            "name": "session",
            "value": "abc123",
            "host_key": ".example.com",
            "path": "/",
            "expires_utc": base_ts + 10,
            "is_secure": 1,
            "is_httponly": 1,
            "samesite": 1,
            "creation_utc": base_ts,
            "last_access_utc": base_ts,
            "has_expires": 1,
            "is_persistent": 1,
        }
    ]

    cookies = manager.read_cookies_from_db()

    assert cookies == [
        CookieData(
            name="session",
            value="abc123",
            domain=".example.com",
            path="/",
            expires=base_ts + 10,
            httpOnly=True,
            secure=True,
            sameSite="Lax",
            creationTime=base_ts,
            lastAccessTime=base_ts,
            persistent=True,
        )
    ]
    assert fake_repository.ensure_schema_called == 1
    assert fake_repository.fetch_all_called == 1


@pytest.mark.unit
def test_read_cookies_returns_empty_on_repository_error(manager, fake_repository):
    fake_repository.fetch_all_error = SQLiteExecutionError("read failure")

    cookies = manager.read_cookies_from_db()

    assert cookies == []
    assert fake_repository.fetch_all_called == 1


@pytest.mark.unit
def test_read_cookies_returns_empty_when_database_invalid(manager, fake_repository):
    fake_repository.ensure_schema_error = SQLiteExecutionError("invalid schema")
    fake_repository.reinitialize_result = False

    cookies = manager.read_cookies_from_db()

    assert cookies == []
    assert fake_repository.reinitialize_called == 1


@pytest.mark.unit
def test_write_cookies_to_db_noop_for_empty_input(manager, fake_repository):
    assert manager.write_cookies_to_db([]) is True
    assert fake_repository.ensure_schema_called == 0
    assert fake_repository.write_rows_called == 0


@pytest.mark.unit
def test_write_cookies_to_db_transforms_rows(manager, fake_repository, monkeypatch):
    monkeypatch.setattr(
        "app.services.common.browser.cookies.time.time",
        lambda: 1000.0,
    )

    cookies: List[CookieData] = [
        CookieData(
            name="session",
            value="abc123",
            domain=".example.com",
            path="/",
            expires=-1,
            httpOnly=False,
            secure=True,
            sameSite="Strict",
            persistent=False,
        )
    ]

    assert manager.write_cookies_to_db(cookies) is True
    assert fake_repository.ensure_schema_called == 1
    assert fake_repository.write_rows_called == 1
    assert fake_repository.captured_rows is not None

    first_row = fake_repository.captured_rows[0]
    creation_ts = int(1000.0 * 1_000_000)
    assert first_row[0] == creation_ts
    assert first_row[1] == ".example.com"
    assert first_row[2] == "session"
    assert first_row[3] == "abc123"
    assert first_row[4] == "/"
    assert first_row[5] == -1
    assert first_row[6] == 1
    assert first_row[7] == 0
    assert first_row[8] == 2  # Strict
    assert first_row[9] == creation_ts
    assert first_row[10] == 0  # has_expires because expires=-1
    assert first_row[11] == 0  # persistent flag from input


@pytest.mark.unit
def test_write_cookies_to_db_handles_repository_error(manager, fake_repository):
    fake_repository.write_rows_error = SQLiteExecutionError("write failure")

    assert manager.write_cookies_to_db([CookieData(name="a", value="b")]) is False
    assert fake_repository.write_rows_called == 1


@pytest.mark.unit
def test_write_cookies_to_db_returns_false_when_database_invalid(manager, fake_repository):
    fake_repository.ensure_schema_error = SQLiteExecutionError("invalid schema")
    fake_repository.reinitialize_result = False

    assert manager.write_cookies_to_db([CookieData(name="a", value="b")]) is False
    assert fake_repository.reinitialize_called == 1
