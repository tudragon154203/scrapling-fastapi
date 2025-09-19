"""Tests for the Gemini key rotation helper script."""

from __future__ import annotations

import os
import sys
from importlib import util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "rotate_gemini_key.py"

spec = util.spec_from_file_location("rotate_gemini_key", SCRIPT_PATH)
rotate_key = util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = rotate_key
spec.loader.exec_module(rotate_key)  # type: ignore[union-attr]


def _clear_gemini_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in list(os.environ):
        if env_name.startswith("GEMINI_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)


def test_gather_candidate_keys_orders_by_suffix(monkeypatch):
    """Candidate keys should be ordered base, numeric suffix, then lexicographic."""

    _clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "base")
    monkeypatch.setenv("GEMINI_API_KEY_10", "ten")
    monkeypatch.setenv("GEMINI_API_KEY_2", "two")
    monkeypatch.setenv("GEMINI_API_KEY_LEGACY", "legacy")

    candidates = rotate_key.gather_candidate_keys("GEMINI_API_KEY")

    ordered_names = [candidate.env_name for candidate in candidates]
    assert ordered_names == [
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_2",
        "GEMINI_API_KEY_10",
        "GEMINI_API_KEY_LEGACY",
    ]

    selected = rotate_key.select_key(candidates, seed=1)
    assert selected.env_name == "GEMINI_API_KEY_2"


def test_select_key_requires_candidates():
    with pytest.raises(RuntimeError):
        rotate_key.select_key([], seed=0)


def test_main_exports_to_github_files(monkeypatch, tmp_path, capfd):
    """Running the script writes to GitHub env/output files and masks the key."""

    _clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "primary")
    monkeypatch.setenv("GEMINI_API_KEY_2", "secondary")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "env"))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("ROTATION_SEED", "1")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotate_gemini_key.py",
            "--output-selected-name",
            "selected_key_name",
            "--presence-output",
            "key_present",
        ],
    )

    rotate_key.main()

    captured = capfd.readouterr().out
    assert "::add-mask::secondary" in captured
    assert "Selected Gemini key from GEMINI_API_KEY_2 -> GEMINI_API_KEY" in captured

    env_file = Path(os.environ["GITHUB_ENV"])
    output_file = Path(os.environ["GITHUB_OUTPUT"])

    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "GEMINI_API_KEY=secondary"
    ]
    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "selected_key_name=GEMINI_API_KEY_2",
        "key_present=true",
    ]

    monkeypatch.delenv("ROTATION_SEED", raising=False)


def test_main_handles_missing_keys_when_allowed(monkeypatch, tmp_path, capfd):
    """Allow missing flag should exit successfully without exporting a key."""

    _clear_gemini_env(monkeypatch)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotate_gemini_key.py",
            "--allow-missing",
            "--presence-output",
            "key_present",
        ],
    )

    rotate_key.main()

    captured = capfd.readouterr().out
    assert "::notice::Skipping Gemini key rotation" in captured

    output_file = Path(os.environ["GITHUB_OUTPUT"])
    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "key_present=false"
    ]
