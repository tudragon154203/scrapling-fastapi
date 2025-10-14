"""Unit tests for :mod:`app.services.common.browser.cookie_sync`."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

import pytest

from app.services.common.browser.cookie_sync import ChromiumCookieSync
from app.services.common.browser.cookies import ChromiumCookieManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture()
def cookie_sync_components(tmp_path: Path) -> Dict[str, object]:
    path_manager = ChromiumPathManager(str(tmp_path))
    path_manager.ensure_directories_exist()
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    profile_manager.ensure_metadata()
    cookie_manager = Mock(spec=ChromiumCookieManager)
    sync = ChromiumCookieSync(cookie_manager, profile_manager, path_manager, enabled=True)
    return {
        "path_manager": path_manager,
        "profile_manager": profile_manager,
        "cookie_manager": cookie_manager,
        "sync": sync,
    }


class TestChromiumCookieSync:
    """Validate cookie import/export flows."""

    @pytest.mark.unit
    def test_export_cookies_json(self, cookie_sync_components: Dict[str, object]) -> None:
        cookie_manager: Mock = cookie_sync_components["cookie_manager"]  # type: ignore[assignment]
        cookie_manager.read_cookies_from_db.return_value = []
        sync: ChromiumCookieSync = cookie_sync_components["sync"]  # type: ignore[assignment]

        export = sync.export_cookies()
        assert export is not None
        assert export["format"] == "json"
        assert export["cookies"] == []
        assert "profile_metadata" in export

    @pytest.mark.unit
    def test_export_cookies_storage_state(self, cookie_sync_components: Dict[str, object]) -> None:
        cookie_manager: Mock = cookie_sync_components["cookie_manager"]  # type: ignore[assignment]
        cookie_manager.read_cookies_from_db.return_value = [
            {
                "name": "session",
                "value": "abc",
                "domain": "example.com",
                "path": "/",
                "expires": int(time.time()) + 3600,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
        sync: ChromiumCookieSync = cookie_sync_components["sync"]  # type: ignore[assignment]

        export = sync.export_cookies(format="storage_state")
        assert export is not None
        assert export["cookies"][0]["name"] == "session"
        assert export["cookies"][0]["httpOnly"] is True
        assert export["origins"] == []

    @pytest.mark.unit
    def test_import_cookies_updates_metadata(self, cookie_sync_components: Dict[str, object]) -> None:
        cookie_manager: Mock = cookie_sync_components["cookie_manager"]  # type: ignore[assignment]
        profile_manager: ChromiumProfileManager = cookie_sync_components["profile_manager"]  # type: ignore[assignment]
        cookie_manager.write_cookies_to_db.return_value = True
        sync: ChromiumCookieSync = cookie_sync_components["sync"]  # type: ignore[assignment]

        result = sync.import_cookies({"cookies": [{"name": "a", "value": "b"}]})
        assert result is True
        metadata = profile_manager.read_metadata()
        assert metadata is not None
        assert metadata.get("cookie_import_count") == 1
        assert metadata.get("cookie_import_status") == "success"

    @pytest.mark.unit
    def test_import_cookies_empty_payload(self, cookie_sync_components: Dict[str, object]) -> None:
        sync: ChromiumCookieSync = cookie_sync_components["sync"]  # type: ignore[assignment]
        profile_manager: ChromiumProfileManager = cookie_sync_components["profile_manager"]  # type: ignore[assignment]

        result = sync.import_cookies({"cookies": []})
        assert result is True
        metadata = profile_manager.read_metadata()
        assert metadata is not None
        assert metadata.get("cookie_import_count") == 0
        assert metadata.get("cookie_import_status") == "success"

    @pytest.mark.unit
    def test_disabled_sync_returns_defaults(self, tmp_path: Path) -> None:
        path_manager = ChromiumPathManager(str(tmp_path))
        sync = ChromiumCookieSync(None, None, path_manager, enabled=False)

        assert sync.export_cookies() is None
        assert sync.import_cookies({"cookies": []}) is False
