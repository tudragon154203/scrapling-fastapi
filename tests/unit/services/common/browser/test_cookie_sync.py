"""Tests for :mod:`app.services.common.browser.cookie_sync`."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Tuple
from unittest.mock import MagicMock

import pytest

from app.services.common.browser.cookie_sync import ChromiumCookieSync
from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


CookieSyncFixture = Tuple[
    ChromiumCookieSync,
    ChromiumPathManager,
    ChromiumProfileManager,
    ChromiumCookieManager,
]


@pytest.fixture
def cookie_sync(temp_data_dir: Path) -> Iterator[CookieSyncFixture]:
    """Provide a configured ``ChromiumCookieSync`` instance for testing."""
    path_manager = ChromiumPathManager(str(temp_data_dir))
    path_manager.ensure_directories_exist()
    profile_manager = MagicMock(spec=ChromiumProfileManager)
    profile_manager.read_metadata.return_value = {"profile_type": "chromium"}
    cookie_manager = MagicMock(spec=ChromiumCookieManager)
    sync = ChromiumCookieSync(
        path_manager,
        profile_manager,
        cookie_manager,
        enabled=True,
    )
    yield sync, path_manager, profile_manager, cookie_manager


class TestChromiumCookieSync:
    """Behavioural checks for the cookie synchronisation helper."""

    @pytest.mark.unit
    def test_export_cookies_returns_metadata(self, cookie_sync: CookieSyncFixture) -> None:
        sync, path_manager, _profile_manager, cookie_manager = cookie_sync
        cookie_manager.read_cookies_from_db.return_value = [
            {
                "name": "session",
                "value": "abc",
                "domain": "example.com",
                "path": "/",
                "expires": -1,
            }
        ]
        (path_manager.master_dir / "Default").mkdir(parents=True, exist_ok=True)

        result = sync.export_cookies()
        assert result is not None
        assert result["format"] == "json"
        assert result["cookies_available"] is True

    @pytest.mark.unit
    def test_import_cookies_updates_metadata(self, cookie_sync: CookieSyncFixture) -> None:
        sync, path_manager, profile_manager, cookie_manager = cookie_sync
        (path_manager.master_dir / "Default").mkdir(parents=True, exist_ok=True)
        cookie_manager.write_cookies_to_db.return_value = True

        result = sync.import_cookies({"cookies": [{"name": "session"}]})

        assert result is True
        profile_manager.update_metadata.assert_called()
        cookie_manager.write_cookies_to_db.assert_called_once()

    @pytest.mark.unit
    def test_disabled_sync_noop(self, temp_data_dir) -> None:
        path_manager = ChromiumPathManager(str(temp_data_dir))
        sync = ChromiumCookieSync(path_manager, None, None, enabled=False)
        assert sync.export_cookies() is None
        assert sync.import_cookies({}) is False
