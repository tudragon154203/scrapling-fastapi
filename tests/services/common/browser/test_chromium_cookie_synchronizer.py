import time
from pathlib import Path
from typing import Any, Dict

import pytest

from app.services.common.browser.chromium_cookie_synchronizer import (
    ChromiumCookieSynchronizer,
)
from app.services.common.browser.paths import ChromiumPathManager


class DummyProfileManager:
    def __init__(self) -> None:
        self.metadata_updates: Dict[str, Any] = {}
        self.read_metadata_return: Dict[str, Any] = {"foo": "bar"}

    def read_metadata(self) -> Dict[str, Any]:
        return self.read_metadata_return

    def ensure_metadata(self) -> None:  # pragma: no cover - used implicitly
        pass

    def update_metadata(self, updates: Dict[str, Any]) -> None:
        self.metadata_updates.update(updates)


class DummyCookieManager:
    def __init__(self) -> None:
        self.written_cookies: Any = None
        self.cookies_to_read = [
            {
                "name": "session",
                "value": "abc",
                "domain": ".example.com",
                "path": "/",
                "expires": int(time.time()) + 3600,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
        self.write_result = True

    def read_cookies_from_db(self):
        return self.cookies_to_read

    def write_cookies_to_db(self, cookies):
        self.written_cookies = cookies
        return self.write_result


@pytest.fixture()
def path_manager(tmp_path: Path) -> ChromiumPathManager:
    manager = ChromiumPathManager(str(tmp_path))
    manager.ensure_directories_exist()
    (manager.master_dir / "Default").mkdir(parents=True, exist_ok=True)
    return manager


def test_export_cookies_storage_state(path_manager: ChromiumPathManager) -> None:
    profile_manager = DummyProfileManager()
    cookie_manager = DummyCookieManager()

    sync = ChromiumCookieSynchronizer(
        enabled=True,
        path_manager=path_manager,
        cookie_manager=cookie_manager,
        profile_manager=profile_manager,
    )

    result = sync.export_cookies("storage_state")

    assert result is not None
    assert result["cookies"][0]["name"] == "session"
    assert result["origins"] == []


def test_export_cookies_disabled_returns_none(path_manager: ChromiumPathManager) -> None:
    sync = ChromiumCookieSynchronizer(
        enabled=False,
        path_manager=path_manager,
        cookie_manager=DummyCookieManager(),
        profile_manager=DummyProfileManager(),
    )

    assert sync.export_cookies() is None


def test_import_cookies_updates_metadata(path_manager: ChromiumPathManager) -> None:
    profile_manager = DummyProfileManager()
    cookie_manager = DummyCookieManager()
    sync = ChromiumCookieSynchronizer(
        enabled=True,
        path_manager=path_manager,
        cookie_manager=cookie_manager,
        profile_manager=profile_manager,
    )

    payload: Dict[str, Any] = {
        "format": "json",
        "cookies": cookie_manager.cookies_to_read,
    }

    assert sync.import_cookies(payload) is True
    assert cookie_manager.written_cookies == cookie_manager.cookies_to_read
    assert profile_manager.metadata_updates["cookie_import_status"] == "success"
    assert profile_manager.metadata_updates["cookie_import_count"] == len(
        cookie_manager.cookies_to_read
    )
