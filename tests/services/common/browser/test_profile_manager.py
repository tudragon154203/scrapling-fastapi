import json
from pathlib import Path
from typing import Dict

import pytest

from app.services.common.browser import profile_manager
from app.services.common.browser.profile_manager import (
    ChromiumProfileManager,
    clone_profile,
    create_temporary_profile,
)


pytestmark = pytest.mark.unit


class DummyBrowserforge:
    __version__ = "9.9.9"

    def __init__(self, fingerprint: Dict[str, str]) -> None:
        self._fingerprint = fingerprint

    def generate(self, **_kwargs):  # type: ignore[override]
        return dict(self._fingerprint)


def test_ensure_metadata_creates_files_and_fingerprint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    fingerprint_path = tmp_path / "fingerprint.json"
    manager = ChromiumProfileManager(metadata_path, fingerprint_path)

    fingerprint = {"userAgent": "dummy", "viewport": {"width": 1, "height": 1}}
    dummy_browserforge = DummyBrowserforge(fingerprint)

    monkeypatch.setattr(profile_manager, "BROWSERFORGE_AVAILABLE", True)
    monkeypatch.setattr(profile_manager, "browserforge", dummy_browserforge)

    manager.ensure_metadata()

    assert metadata_path.exists()
    assert fingerprint_path.exists()

    data = json.loads(metadata_path.read_text())
    assert data["version"] == "1.0"
    assert data["browserforge_version"] == dummy_browserforge.__version__
    assert data["browserforge_fingerprint_generated"] is True
    assert data["browserforge_fingerprint_file"] == str(fingerprint_path)
    assert json.loads(fingerprint_path.read_text()) == fingerprint


def test_read_metadata_recovers_from_corruption(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    fingerprint_path = tmp_path / "fingerprint.json"
    manager = ChromiumProfileManager(metadata_path, fingerprint_path)

    metadata_path.write_text("{invalid json")

    monkeypatch.setattr(profile_manager, "BROWSERFORGE_AVAILABLE", False)
    monkeypatch.setattr(profile_manager.time, "sleep", lambda _seconds: None)

    result = manager.read_metadata()

    assert result is not None
    assert result["version"] == "1.0"
    assert metadata_path.exists()
    # Corruption should have been fixed by ensure_metadata
    json.loads(metadata_path.read_text())


def test_update_metadata_merges_fields(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    fingerprint_path = tmp_path / "fingerprint.json"
    manager = ChromiumProfileManager(metadata_path, fingerprint_path)

    original = {"version": "1.0", "last_updated": 0.0, "custom": "value"}
    metadata_path.write_text(json.dumps(original))

    manager.update_metadata({"custom": "updated", "extra": 123})

    updated = json.loads(metadata_path.read_text())
    assert updated["custom"] == "updated"
    assert updated["extra"] == 123
    assert updated["last_updated"] >= original["last_updated"]


def test_clone_profile_creates_copy_and_cleanup(tmp_path: Path) -> None:
    source_dir = tmp_path / "master"
    source_dir.mkdir()
    (source_dir / "file.txt").write_text("hello")
    target_dir = tmp_path / "clone"

    path, cleanup = clone_profile(source_dir, target_dir)

    assert Path(path).exists()
    assert (Path(path) / "file.txt").read_text() == "hello"

    cleanup()
    assert not Path(path).exists()


def test_create_temporary_profile_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    temp_root = tmp_path / "temps"

    def fake_mkdtemp(prefix: str) -> str:
        _ = prefix
        path = temp_root / "profile"
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    monkeypatch.setattr(profile_manager.tempfile, "mkdtemp", fake_mkdtemp)

    path, cleanup = create_temporary_profile()
    assert Path(path).exists()

    cleanup()
    assert not Path(path).exists()
