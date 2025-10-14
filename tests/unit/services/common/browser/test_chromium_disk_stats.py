"""Unit tests for :mod:`app.services.common.browser.disk_stats`."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pytest

from app.services.common.browser.disk_stats import ChromiumDiskStats
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture()
def disk_stats_components(tmp_path: Path) -> Dict[str, object]:
    path_manager = ChromiumPathManager(str(tmp_path))
    path_manager.ensure_directories_exist()
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    profile_manager.ensure_metadata()
    stats = ChromiumDiskStats(path_manager, profile_manager, enabled=True)
    return {
        "path_manager": path_manager,
        "profile_manager": profile_manager,
        "stats": stats,
    }


class TestChromiumDiskStats:
    """Validate disk usage aggregation."""

    @pytest.mark.unit
    def test_collects_sizes(self, disk_stats_components: Dict[str, object]) -> None:
        path_manager: ChromiumPathManager = disk_stats_components["path_manager"]  # type: ignore[assignment]
        stats: ChromiumDiskStats = disk_stats_components["stats"]  # type: ignore[assignment]

        (path_manager.master_dir / "Default").mkdir(parents=True, exist_ok=True)
        (path_manager.master_dir / "Default" / "file.bin").write_bytes(b"x" * 1024 * 1024)
        clone_dir = path_manager.clones_dir / "sample"
        clone_dir.mkdir(parents=True, exist_ok=True)
        (clone_dir / "data.bin").write_bytes(b"y" * 512 * 1024)

        result = stats.get_disk_usage_stats()
        assert result["enabled"] is True
        assert result["master_size_mb"] >= 0.9
        assert result["clones_size_mb"] >= 0.4
        assert result["clone_count"] == 1

    @pytest.mark.unit
    def test_disabled_stats(self, tmp_path: Path) -> None:
        path_manager = ChromiumPathManager(str(tmp_path))
        stats = ChromiumDiskStats(path_manager, None, enabled=False)

        assert stats.get_disk_usage_stats() == {"enabled": False}
