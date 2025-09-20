"""Tests for the Gemini key rotation helper script."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the rotate_key package to the path
WORKFLOWS_DIR = next(
    parent for parent in Path(__file__).resolve().parents if parent.name == "workflows"
)
COMMON_DIR = WORKFLOWS_DIR / "scripts" / "bots" / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

import pytest

from rotate_key.gemini import GeminiKeyRotator


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

    rotator = GeminiKeyRotator()
    candidates = rotator.gather_candidate_keys("GEMINI_API_KEY")

    ordered_names = [candidate.env_name for candidate in candidates]
    assert ordered_names == [
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_2",
        "GEMINI_API_KEY_10",
    ]

    selected = rotator.select_key(candidates, seed=1)
    assert selected.env_name == "GEMINI_API_KEY_2"


def test_select_key_requires_candidates():
    rotator = GeminiKeyRotator()
    with pytest.raises(RuntimeError):
        rotator.select_key([], seed=0)


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
            "gemini.py",
            "--output-selected-name",
            "selected_key_name",
        ],
    )

    rotator = GeminiKeyRotator()
    rotator.run()

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