"""Tests for browser user_data_context behaviours."""

import logging
import uuid
from pathlib import Path
from typing import Callable

import pytest

from app.services.common.browser import user_data

FAKE_UUID = uuid.UUID("12345678123456781234567812345678")


@pytest.fixture
def user_data_base(tmp_path: Path) -> Path:
    base_dir = tmp_path / "profiles"
    base_dir.mkdir()
    return base_dir


@pytest.fixture
def seed_master() -> Callable[[Path], Path]:
    def _seed(base_dir: Path) -> Path:
        master_dir = base_dir / "master"
        master_dir.mkdir(parents=True, exist_ok=True)
        (master_dir / "state.txt").write_text("ready")
        return master_dir

    return _seed


@pytest.mark.parametrize("mode", ["write", "read"])
@pytest.mark.parametrize("fcntl_available", [True, False])
def test_user_data_context_modes(
    user_data_base: Path,
    seed_master: Callable[[Path], Path],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mode: str,
    fcntl_available: bool,
) -> None:
    monkeypatch.setattr(user_data, "FCNTL_AVAILABLE", fcntl_available)
    if fcntl_available and not hasattr(user_data, "fcntl"):
        class _DummyFcntl:
            LOCK_EX = 1
            LOCK_NB = 2
            LOCK_UN = 8

            @staticmethod
            def flock(_fd: int, _operation: int) -> None:
                return None

        monkeypatch.setattr(user_data, "fcntl", _DummyFcntl)

    if mode == "read":
        seed_master(user_data_base)
        monkeypatch.setattr(user_data.uuid, "uuid4", lambda: FAKE_UUID)

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=user_data.__name__):
        with user_data.user_data_context(str(user_data_base), mode) as (path, cleanup):
            assert callable(cleanup)
            if mode == "write":
                expected_master = user_data_base / "master"
                assert Path(path) == expected_master
                lock_file = user_data_base / "master.lock"
                assert lock_file.exists()
            else:
                clone_dir = Path(path)
                assert clone_dir.exists()
                assert clone_dir.parent == user_data_base / "clones"
                assert (clone_dir / "state.txt").read_text() == "ready"
        cleanup()

    if mode == "write":
        lock_file = user_data_base / "master.lock"
        if fcntl_available:
            assert lock_file.exists()
            assert all("fcntl not available" not in record.message for record in caplog.records)
        else:
            assert not lock_file.exists()
            fallback_messages = [
                record.message
                for record in caplog.records
                if "fcntl not available on this platform" in record.message
            ]
            assert fallback_messages == [
                "fcntl not available on this platform, using exclusive fallback"
            ]
    else:
        assert not Path(path).exists()
        assert all("clone directory" not in record.message for record in caplog.records)


def test_read_mode_copy_failure_cleans_up(
    user_data_base: Path, monkeypatch: pytest.MonkeyPatch, seed_master: Callable[[Path], Path]
) -> None:
    seed_master(user_data_base)
    monkeypatch.setattr(user_data.uuid, "uuid4", lambda: FAKE_UUID)

    def boom_copytree(_src: Path, _dst: Path) -> None:
        raise OSError("explode")

    monkeypatch.setattr(user_data, "_copytree_recursive", boom_copytree)

    with pytest.raises(RuntimeError) as excinfo:
        with user_data.user_data_context(str(user_data_base), "read"):
            pass

    assert "Failed to create clone" in str(excinfo.value)

    clone_dir = user_data_base / "clones" / str(FAKE_UUID)
    assert not clone_dir.exists()


def test_read_mode_cleanup_retries_and_succeeds(
    user_data_base: Path,
    seed_master: Callable[[Path], Path],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    seed_master(user_data_base)
    monkeypatch.setattr(user_data.uuid, "uuid4", lambda: FAKE_UUID)

    original_rmtree: Callable[..., None] = user_data.shutil.rmtree
    attempts = {"count": 0}

    def flaky_rmtree(target: Path) -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("temporary failure")
        original_rmtree(target)

    monkeypatch.setattr(user_data.shutil, "rmtree", flaky_rmtree)

    with user_data.user_data_context(str(user_data_base), "read") as (path, cleanup):
        clone_dir = Path(path)
        assert clone_dir.exists()

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger=user_data.__name__):
        cleanup()

    assert attempts["count"] == 3
    assert not clone_dir.exists()

    warnings = [record for record in caplog.records if "Attempt" in record.message]
    assert len(warnings) == 2
