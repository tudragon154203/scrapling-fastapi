"""Unit tests for :mod:`app.services.common.browser.context_manager`."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from app.services.common.browser.context_manager import ChromiumContextManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture
def path_manager_enabled(temp_data_dir: Path) -> Iterator[ChromiumPathManager]:
    """Provide a path manager rooted in a temporary directory."""
    manager = ChromiumPathManager(str(temp_data_dir))
    yield manager


class TestChromiumContextManager:
    """Behaviours specific to ``ChromiumContextManager``."""

    @pytest.mark.unit
    def test_disabled_context_uses_temp_profile(self) -> None:
        path_manager = ChromiumPathManager(None)
        context_manager = ChromiumContextManager(path_manager, None, enabled=False)

        with context_manager.get_user_data_context("read") as (temp_dir, cleanup):
            assert temp_dir is not None
            assert Path(temp_dir).exists()
            cleanup()
            assert not Path(temp_dir).exists()

    @pytest.mark.unit
    def test_write_context_initializes_master(self, path_manager_enabled: ChromiumPathManager) -> None:
        path_manager = path_manager_enabled
        context_manager = ChromiumContextManager(
            path_manager,
            ChromiumProfileManager(path_manager.metadata_file, path_manager.fingerprint_file),
            enabled=True,
        )

        assert not path_manager.master_dir.exists()
        with context_manager.get_user_data_context("write") as (effective_dir, _cleanup):
            assert effective_dir == str(path_manager.master_dir)
        assert path_manager.master_dir.exists()

    @pytest.mark.unit
    def test_read_context_creates_clone(self, path_manager_enabled: ChromiumPathManager) -> None:
        path_manager = path_manager_enabled
        profile_manager = ChromiumProfileManager(
            path_manager.metadata_file,
            path_manager.fingerprint_file,
        )
        context_manager = ChromiumContextManager(path_manager, profile_manager, enabled=True)

        with context_manager.get_user_data_context("write"):
            pass

        with context_manager.get_user_data_context("read") as (clone_dir, cleanup):
            clone_path = Path(clone_dir)
            assert clone_path.exists()
        cleanup()
        assert not Path(clone_dir).exists()
