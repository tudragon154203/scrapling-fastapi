from pathlib import Path
from typing import Dict

import pytest

from app.services.common.browser.chromium_disk_statistics import ChromiumDiskStatistics
from app.services.common.browser.paths import ChromiumPathManager


class DummyProfileManager:
    def __init__(self, metadata: Dict[str, float] | None = None) -> None:
        self._metadata = metadata or {}

    def read_metadata(self) -> Dict[str, float]:
        return self._metadata


@pytest.fixture()
def path_manager(tmp_path: Path) -> ChromiumPathManager:
    manager = ChromiumPathManager(str(tmp_path))
    manager.ensure_directories_exist()
    return manager


def test_disk_usage_disabled_returns_flag(path_manager: ChromiumPathManager) -> None:
    stats = ChromiumDiskStatistics(
        enabled=False,
        path_manager=path_manager,
        profile_manager=None,
    )

    assert stats.get_disk_usage_stats() == {"enabled": False}


def test_disk_usage_reports_sizes(monkeypatch: pytest.MonkeyPatch, path_manager: ChromiumPathManager) -> None:
    clones_dir = path_manager.clones_dir
    (clones_dir / "clone_a").mkdir()
    (clones_dir / "clone_b").mkdir()

    reported_paths: list[Path] = []

    def fake_size(path: Path) -> float:
        reported_paths.append(path)
        if path == path_manager.master_dir:
            return 10.0
        return 5.0

    monkeypatch.setattr(
        "app.services.common.browser.chromium_disk_statistics.get_directory_size",
        fake_size,
    )

    profile_manager = DummyProfileManager({"last_cleanup": 123.0})
    stats = ChromiumDiskStatistics(
        enabled=True,
        path_manager=path_manager,
        profile_manager=profile_manager,
    )

    result = stats.get_disk_usage_stats()

    assert result["enabled"] is True
    assert result["master_size_mb"] == 10.0
    assert result["clones_size_mb"] == 5.0
    assert result["total_size_mb"] == 15.0
    assert result["clone_count"] == 2
    assert result["last_cleanup"] == 123.0
    assert path_manager.master_dir in reported_paths
    assert path_manager.clones_dir in reported_paths
