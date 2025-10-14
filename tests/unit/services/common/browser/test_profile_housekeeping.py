"""Unit tests for :mod:`app.services.common.browser.profile_housekeeping`."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Tuple

import pytest

from app.services.common.browser.profile_housekeeping import ChromiumProfileHousekeeping
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


HousekeepingFixture = Tuple[
    ChromiumProfileHousekeeping,
    ChromiumPathManager,
    ChromiumProfileManager,
]


@pytest.fixture
def housekeeping(temp_data_dir: Path) -> Iterator[HousekeepingFixture]:
    """Yield a prepared housekeeping helper and its dependencies."""
    path_manager = ChromiumPathManager(str(temp_data_dir))
    path_manager.ensure_directories_exist()
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    profile_manager.ensure_metadata()
    helper = ChromiumProfileHousekeeping(path_manager, profile_manager, enabled=True)
    yield helper, path_manager, profile_manager


class TestChromiumProfileHousekeeping:
    """Behavioural coverage for profile maintenance logic."""

    @pytest.mark.unit
    def test_update_and_fetch_metadata(self, housekeeping: HousekeepingFixture) -> None:
        housekeeper, _path_manager, profile_manager = housekeeping
        housekeeper.update_metadata({"custom": "value"})
        metadata = housekeeper.get_metadata()
        assert metadata is not None
        assert metadata["custom"] == "value"
        fingerprint = housekeeper.get_browserforge_fingerprint()
        assert fingerprint is None or isinstance(fingerprint, dict)

    @pytest.mark.unit
    def test_cleanup_old_clones(self, housekeeping: HousekeepingFixture) -> None:
        housekeeper, path_manager, profile_manager = housekeeping
        clones_dir = path_manager.clones_dir
        for index in range(3):
            clone_path = clones_dir / f"clone_{index}"
            clone_path.mkdir(parents=True, exist_ok=True)
            (clone_path / "dummy.txt").write_text("data")
        old_clone = clones_dir / "old_clone"
        old_clone.mkdir(parents=True, exist_ok=True)
        (old_clone / "stale.txt").write_text("stale")
        os.utime(old_clone, (0, 0))

        result = housekeeper.cleanup_old_clones(max_age_hours=0, max_count=2)

        assert isinstance(result, dict)
        metadata = profile_manager.read_metadata()
        assert metadata.get("last_cleanup") is not None
