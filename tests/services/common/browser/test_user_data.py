from pathlib import Path

import pytest

from app.services.common.browser import user_data


pytestmark = pytest.mark.unit


def test_user_data_context_rejects_invalid_mode(tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"
    with pytest.raises(ValueError):
        with user_data.user_data_context(str(base_dir), "invalid"):
            pass


def test_write_mode_without_fcntl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"
    monkeypatch.setattr(user_data, "FCNTL_AVAILABLE", False)

    with user_data.user_data_context(str(base_dir), "write") as (profile_dir, cleanup):
        master_dir = Path(profile_dir)
        lock_file = base_dir / "master.lock"
        assert master_dir.exists()
        assert lock_file.exists()

    cleanup()
    assert not (base_dir / "master.lock").exists()


def test_read_mode_creates_empty_clone_when_master_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"

    with user_data.user_data_context(str(base_dir), "read") as (clone_dir, cleanup):
        path = Path(clone_dir)
        assert path.exists()
        assert list(path.iterdir()) == []

    cleanup()
    assert not Path(clone_dir).exists()


def test_read_mode_clones_existing_master(tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"
    master_dir = base_dir / "master"
    master_dir.mkdir(parents=True, exist_ok=True)
    (master_dir / "config.json").write_text("{}")

    with user_data.user_data_context(str(base_dir), "read") as (clone_dir, cleanup):
        clone_path = Path(clone_dir)
        assert clone_path.exists()
        assert (clone_path / "config.json").read_text() == "{}"

    cleanup()
    assert not Path(clone_dir).exists()
