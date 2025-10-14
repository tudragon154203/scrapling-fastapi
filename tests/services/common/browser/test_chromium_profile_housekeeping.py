import os
from pathlib import Path
from typing import Dict

import pytest

from app.services.common.browser.chromium_profile_housekeeping import (
    ChromiumProfileHousekeeping,
)
from app.services.common.browser.paths import ChromiumPathManager


class DummyProfileManager:
    def __init__(self) -> None:
        self.updates: Dict[str, float] = {}

    def update_metadata(self, updates: Dict[str, float]) -> None:
        self.updates.update(updates)


@pytest.fixture()
def path_manager(tmp_path: Path) -> ChromiumPathManager:
    manager = ChromiumPathManager(str(tmp_path))
    manager.ensure_directories_exist()
    return manager


def test_cleanup_old_clones_respects_age(monkeypatch: pytest.MonkeyPatch, path_manager: ChromiumPathManager) -> None:
    clones_dir = path_manager.clones_dir
    old_clone = clones_dir / "old"
    recent_clone = clones_dir / "recent"
    old_clone.mkdir()
    recent_clone.mkdir()

    now = 1_000_000.0

    def fake_time() -> float:
        return now

    monkeypatch.setattr("app.services.common.browser.chromium_profile_housekeeping.time.time", fake_time)

    two_hours_ago = now - 7200
    just_now = now - 60

    os.utime(old_clone, (two_hours_ago, two_hours_ago))
    os.utime(recent_clone, (just_now, just_now))

    removed: list[Path] = []

    def fake_chmod(path: Path, mode: int) -> None:
        pass

    def fake_close_sqlite(path: Path) -> None:
        pass

    def fake_rmtree(path: Path, max_attempts: int = 0, initial_delay: float = 0.0) -> bool:
        removed.append(path)
        return True

    def fake_size(path: Path) -> float:
        if path == old_clone:
            return 5.0
        return 1.0

    monkeypatch.setattr(
        "app.services.common.browser.chromium_profile_housekeeping.chmod_tree",
        fake_chmod,
    )
    monkeypatch.setattr(
        "app.services.common.browser.chromium_profile_housekeeping.best_effort_close_sqlite",
        fake_close_sqlite,
    )
    monkeypatch.setattr(
        "app.services.common.browser.chromium_profile_housekeeping.rmtree_with_retries",
        fake_rmtree,
    )
    monkeypatch.setattr(
        "app.services.common.browser.chromium_profile_housekeeping.get_directory_size",
        fake_size,
    )

    profile_manager = DummyProfileManager()
    housekeeping = ChromiumProfileHousekeeping(
        enabled=True,
        path_manager=path_manager,
        profile_manager=profile_manager,
    )

    result = housekeeping.cleanup_old_clones(max_age_hours=1, max_count=10)

    assert result == {
        "cleaned": 1,
        "remaining": 1,
        "errors": 0,
        "size_saved_mb": 5.0,
    }
    assert removed == [old_clone]
    assert profile_manager.updates["last_cleanup_count"] == 1
    assert profile_manager.updates["remaining_clones"] == 1


def test_cleanup_returns_empty_when_disabled(path_manager: ChromiumPathManager) -> None:
    housekeeping = ChromiumProfileHousekeeping(
        enabled=False,
        path_manager=path_manager,
        profile_manager=None,
    )

    assert housekeeping.cleanup_old_clones() == {"cleaned": 0, "remaining": 0, "errors": 0}
