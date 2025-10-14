"""Unit tests for :mod:`app.services.common.browser.profile_housekeeping`."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict

import pytest

from app.services.common.browser.profile_housekeeping import ChromiumProfileHousekeeping
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture()
def housekeeping_components(tmp_path: Path) -> Dict[str, object]:
    path_manager = ChromiumPathManager(str(tmp_path))
    path_manager.ensure_directories_exist()
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    profile_manager.ensure_metadata()
    housekeeping = ChromiumProfileHousekeeping(path_manager, profile_manager, enabled=True)
    return {
        "path_manager": path_manager,
        "profile_manager": profile_manager,
        "housekeeping": housekeeping,
    }


class TestChromiumProfileHousekeeping:
    """Validate metadata access and cleanup logic."""

    @pytest.mark.unit
    def test_metadata_roundtrip(self, housekeeping_components: Dict[str, object]) -> None:
        housekeeping: ChromiumProfileHousekeeping = housekeeping_components["housekeeping"]  # type: ignore[assignment]

        housekeeping.update_metadata({"foo": "bar"})
        metadata = housekeeping.get_metadata()
        assert metadata is not None
        assert metadata.get("foo") == "bar"

    @pytest.mark.unit
    def test_cleanup_old_clones(self, housekeeping_components: Dict[str, object]) -> None:
        path_manager: ChromiumPathManager = housekeeping_components["path_manager"]  # type: ignore[assignment]
        housekeeping: ChromiumProfileHousekeeping = housekeeping_components["housekeeping"]  # type: ignore[assignment]

        # Create an old clone and a fresh clone
        old_clone = path_manager.clones_dir / "old"
        new_clone = path_manager.clones_dir / "new"
        old_clone.mkdir(parents=True, exist_ok=True)
        new_clone.mkdir(parents=True, exist_ok=True)

        (old_clone / "data.bin").write_bytes(b"x" * 1024 * 1024)
        (new_clone / "data.bin").write_bytes(b"y")

        past_time = time.time() - (48 * 3600)
        os.utime(old_clone, (past_time, past_time))

        result = housekeeping.cleanup_old_clones(max_age_hours=24, max_count=5)
        assert result["cleaned"] == 1
        assert result["remaining"] >= 1
        assert not old_clone.exists()
        assert new_clone.exists()

    @pytest.mark.unit
    def test_disabled_housekeeping_returns_defaults(self, tmp_path: Path) -> None:
        path_manager = ChromiumPathManager(str(tmp_path))
        housekeeping = ChromiumProfileHousekeeping(path_manager, None, enabled=False)

        assert housekeeping.get_metadata() is None
        assert housekeeping.get_browserforge_fingerprint() is None
        assert housekeeping.cleanup_old_clones() == {"cleaned": 0, "remaining": 0, "errors": 0}
