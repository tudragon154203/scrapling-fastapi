"""Tests for user_data_context helper."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

import pytest

from app.services.common.browser import user_data


@pytest.mark.parametrize("mode", ["write", "read"])
@pytest.mark.parametrize("fcntl_available", [True, False])
def test_user_data_context_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    fcntl_available: bool,
) -> None:
    base_dir = tmp_path / "profiles"
    base_dir.mkdir()

    monkeypatch.setattr(user_data, "FCNTL_AVAILABLE", fcntl_available)

    if mode == "read":
        master_dir = base_dir / "master"
        master_dir.mkdir()
        (master_dir / "state.txt").write_text("ready")
        fake_uuid = uuid.UUID("12345678123456781234567812345678")
        monkeypatch.setattr(user_data.uuid, "uuid4", lambda: fake_uuid)

    with user_data.user_data_context(str(base_dir), mode) as (path, cleanup):
        assert callable(cleanup)
        if mode == "write":
            expected_master = base_dir / "master"
            assert Path(path) == expected_master
            lock_file = base_dir / "master.lock"
            assert lock_file.exists()
        else:
            clone_dir = Path(path)
            assert clone_dir.exists()
            assert clone_dir.parent == base_dir / "clones"
            assert (clone_dir / "state.txt").read_text() == "ready"

    cleanup()

    if mode == "write":
        lock_file = base_dir / "master.lock"
        if fcntl_available:
            assert lock_file.exists()
        else:
            assert not lock_file.exists()
    else:
        assert not Path(path).exists()


def test_read_mode_copy_failure_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_dir = tmp_path / "profiles"
    master_dir = base_dir / "master"
    master_dir.mkdir(parents=True)
    (master_dir / "payload.txt").write_text("data")

    fake_uuid = uuid.UUID("12345678123456781234567812345678")
    monkeypatch.setattr(user_data.uuid, "uuid4", lambda: fake_uuid)

    def boom_copytree(_src: Path, _dst: Path) -> None:
        raise OSError("explode")

    monkeypatch.setattr(user_data, "_copytree_recursive", boom_copytree)

    with pytest.raises(RuntimeError) as excinfo:
        with user_data.user_data_context(str(base_dir), "read"):
            pass

    assert "Failed to create clone" in str(excinfo.value)

    clone_dir = base_dir / "clones" / str(fake_uuid)
    assert not clone_dir.exists()


def test_read_mode_cleanup_retries_and_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base_dir = tmp_path / "profiles"
    master_dir = base_dir / "master"
    master_dir.mkdir(parents=True)
    (master_dir / "payload.txt").write_text("data")

    fake_uuid = uuid.UUID("12345678123456781234567812345678")
    monkeypatch.setattr(user_data.uuid, "uuid4", lambda: fake_uuid)

    original_rmtree: Callable[..., None] = user_data.shutil.rmtree
    attempts = {"count": 0}

    def flaky_rmtree(target: Path) -> None:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise OSError("temporary failure")
        original_rmtree(target)

    monkeypatch.setattr(user_data.shutil, "rmtree", flaky_rmtree)

    with user_data.user_data_context(str(base_dir), "read") as (path, cleanup):
        clone_dir = Path(path)
        assert clone_dir.exists()

    caplog.set_level(logging.WARNING)

    cleanup()

    assert attempts["count"] == 3
    assert not clone_dir.exists()

    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len([record for record in warnings if "Attempt" in record.message]) == 2
