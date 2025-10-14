"""Unit tests for :mod:`app.services.common.browser.context_manager`."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from app.services.common.browser.context_manager import ChromiumContextManager
from app.services.common.browser.paths import ChromiumPathManager
from app.services.common.browser.profile_manager import ChromiumProfileManager


@pytest.fixture()
def temp_profile_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def enabled_context_manager(temp_profile_dir: Path) -> ChromiumContextManager:
    path_manager = ChromiumPathManager(str(temp_profile_dir))
    profile_manager = ChromiumProfileManager(
        path_manager.metadata_file,
        path_manager.fingerprint_file,
    )
    return ChromiumContextManager(path_manager, profile_manager, enabled=True)


@pytest.fixture()
def disabled_context_manager() -> ChromiumContextManager:
    path_manager = ChromiumPathManager(None)
    return ChromiumContextManager(path_manager, None, enabled=False)


class TestChromiumContextManager:
    """Validate Chromium profile context handling."""

    @pytest.mark.unit
    def test_write_mode_initializes_metadata(self, enabled_context_manager: ChromiumContextManager) -> None:
        path_manager = enabled_context_manager.path_manager

        with enabled_context_manager.get_user_data_context("write") as (effective_dir, cleanup):
            assert Path(effective_dir) == path_manager.master_dir
            assert path_manager.master_dir.exists()
            metadata_file = path_manager.metadata_file
            assert metadata_file.exists()
            assert callable(cleanup)

        # Metadata file should persist after context exit
        assert path_manager.metadata_file.exists()

    @pytest.mark.unit
    def test_read_mode_clones_master_and_cleans_up(self, enabled_context_manager: ChromiumContextManager) -> None:
        path_manager = enabled_context_manager.path_manager

        # Ensure master contains a marker file
        with enabled_context_manager.get_user_data_context("write") as (master_dir, _):
            marker = Path(master_dir) / "marker.txt"
            marker.write_text("hello")

        # Read context should create a clone with the marker file
        with enabled_context_manager.get_user_data_context("read") as (clone_dir, cleanup):
            clone_path = Path(clone_dir)
            assert clone_path.exists()
            assert clone_path != path_manager.master_dir
            assert (clone_path / "marker.txt").read_text() == "hello"
            assert callable(cleanup)

        # Cleanup is invoked automatically when context exits
        assert not clone_path.exists()

    @pytest.mark.unit
    def test_disabled_mode_uses_temporary_profile(self, disabled_context_manager: ChromiumContextManager) -> None:
        with disabled_context_manager.get_user_data_context("read") as (temp_dir, cleanup):
            temp_path = Path(temp_dir)
            assert temp_path.exists()
            assert "chromium_temp_" in temp_path.name
            assert callable(cleanup)

        # Temporary directory should be removed once context exits
        assert not temp_path.exists()

    @pytest.mark.unit
    def test_invalid_mode_raises(self, enabled_context_manager: ChromiumContextManager) -> None:
        with pytest.raises(ValueError):
            with enabled_context_manager.get_user_data_context("invalid"):
                pass

    @pytest.mark.unit
    def test_empty_master_clone_creation(self, enabled_context_manager: ChromiumContextManager) -> None:
        path_manager = enabled_context_manager.path_manager

        # Ensure master directory does not exist yet
        if path_manager.master_dir.exists():
            shutil.rmtree(path_manager.master_dir, ignore_errors=True)

        with enabled_context_manager.get_user_data_context("read") as (clone_dir, _):
            clone_path = Path(clone_dir)
            assert clone_path.exists()
            assert os.listdir(clone_path) == []

        assert not clone_path.exists()
