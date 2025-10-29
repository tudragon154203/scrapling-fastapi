from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Tuple

import pytest

from app.services.common.browser.chromium_user_data_context import (
    ChromiumUserDataContextManager,
)
from app.services.common.browser.paths import ChromiumPathManager


class DummyProfileManager:
    def __init__(self) -> None:
        self.ensure_calls = 0
        self.metadata_updates: Dict[str, float] = {}

    def ensure_metadata(self) -> None:
        self.ensure_calls += 1

    def update_metadata(self, updates: Dict[str, float]) -> None:
        self.metadata_updates.update(updates)


@pytest.fixture()
def path_manager(tmp_path: Path) -> ChromiumPathManager:
    manager = ChromiumPathManager(str(tmp_path))
    manager.ensure_directories_exist()
    manager.master_dir.mkdir(parents=True, exist_ok=True)
    return manager


def test_disabled_uses_temporary_profile(monkeypatch: pytest.MonkeyPatch, path_manager: ChromiumPathManager) -> None:
    cleanup_called = False

    def fake_temp_profile() -> Tuple[str, Callable[[], None]]:
        def cleanup() -> None:
            nonlocal cleanup_called
            cleanup_called = True

        return str(path_manager.master_dir), cleanup

    monkeypatch.setattr(
        "app.services.common.browser.chromium_user_data_context.create_temporary_profile",
        fake_temp_profile,
    )

    manager = ChromiumUserDataContextManager(
        enabled=False,
        path_manager=path_manager,
        profile_manager=None,
    )

    with manager.get_user_data_context("read") as (profile_path, _cleanup):
        assert profile_path == str(path_manager.master_dir)

    assert cleanup_called is True


def test_write_mode_ensures_metadata(monkeypatch: pytest.MonkeyPatch, path_manager: ChromiumPathManager) -> None:
    profile_manager = DummyProfileManager()

    @contextmanager
    def fake_lock(_lock_file: str, timeout: float = 30.0):
        _ = timeout
        yield True

    monkeypatch.setattr(
        "app.services.common.browser.chromium_user_data_context.exclusive_lock",
        fake_lock,
    )

    manager = ChromiumUserDataContextManager(
        enabled=True,
        path_manager=path_manager,
        profile_manager=profile_manager,
    )

    with manager.get_user_data_context("write") as (profile_path, cleanup):
        assert profile_path == str(path_manager.master_dir)
        assert callable(cleanup)

    assert profile_manager.ensure_calls == 1


def test_read_mode_clones_profile(monkeypatch: pytest.MonkeyPatch, path_manager: ChromiumPathManager) -> None:
    profile_manager = DummyProfileManager()

    clone_called: Dict[str, Path] = {}

    def fake_clone_profile(master_dir: Path, clone_dir: Path):
        clone_called["master"] = master_dir
        clone_called["clone"] = clone_dir

        def cleanup() -> None:
            clone_called["cleanup"] = clone_dir

        return str(clone_dir), cleanup

    monkeypatch.setattr(
        "app.services.common.browser.chromium_user_data_context.clone_profile",
        fake_clone_profile,
    )

    manager = ChromiumUserDataContextManager(
        enabled=True,
        path_manager=path_manager,
        profile_manager=profile_manager,
    )

    with manager.get_user_data_context("read") as (profile_path, cleanup):
        assert Path(profile_path).parent == path_manager.clones_dir
        assert callable(cleanup)

    assert clone_called["master"] == path_manager.master_dir
    assert clone_called["clone"].parent == path_manager.clones_dir
    assert clone_called.get("cleanup") == clone_called["clone"]
