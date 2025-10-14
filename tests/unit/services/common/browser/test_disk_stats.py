"""Unit tests for :mod:`app.services.common.browser.disk_stats`."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from app.services.common.browser.disk_stats import ChromiumDiskStats
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture
def disk_stats(temp_data_dir: Path) -> Iterator[ChromiumDiskStats]:
    """Provide a disk stats helper with prepared directories."""
    path_manager = ChromiumPathManager(str(temp_data_dir))
    path_manager.ensure_directories_exist()
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    profile_manager.ensure_metadata()
    (path_manager.master_dir / "Default").mkdir(parents=True, exist_ok=True)
    stats = ChromiumDiskStats(path_manager, profile_manager, enabled=True)
    yield stats


class TestChromiumDiskStats:
    """Verify disk usage aggregation logic."""

    @pytest.mark.unit
    def test_disk_stats_report(self, disk_stats: ChromiumDiskStats) -> None:
        result = disk_stats.get_disk_usage_stats()
        assert result["enabled"] is True
        assert "master_size_mb" in result
        assert "clone_count" in result
