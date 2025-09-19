"""Tests for the OpenRouter key rotation helper script."""

from __future__ import annotations

import os
import sys
from importlib import util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "rotate_openrouter_key.py"
)

spec = util.spec_from_file_location("rotate_openrouter_key", SCRIPT_PATH)
rotate_key = util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = rotate_key
spec.loader.exec_module(rotate_key)  # type: ignore[union-attr]


def _clear_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in list(os.environ):
        if env_name.startswith("OPENROUTER_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)


def test_gather_candidate_keys_orders_by_suffix(monkeypatch):
    """Candidate keys should be ordered base, numeric suffix, then lexicographic."""

    _clear_openrouter_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "base")
    monkeypatch.setenv("OPENROUTER_API_KEY_10", "ten")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "two")
    monkeypatch.setenv("OPENROUTER_API_KEY_EXTRA", "extra")

    candidates = rotate_key.gather_candidate_keys("OPENROUTER_API_KEY")

    ordered_names = [candidate.env_name for candidate in candidates]
    assert ordered_names == [
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_2",
        "OPENROUTER_API_KEY_10",
        "OPENROUTER_API_KEY_EXTRA",
    ]

    selected = rotate_key.select_key(candidates, seed=1)
    assert selected.env_name == "OPENROUTER_API_KEY_2"


def test_select_key_requires_candidates():
    with pytest.raises(RuntimeError):
        rotate_key.select_key([], seed=0)


def test_main_exports_to_github_files(monkeypatch, tmp_path, capfd):
    """Running the script writes to GitHub env/output files and masks the key."""

    _clear_openrouter_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "primary")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "secondary")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "env"))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("ROTATION_SEED", "1")

    monkeypatch.setattr(sys, "argv", ["rotate_openrouter_key.py"])

    rotate_key.main()

    captured = capfd.readouterr().out
    assert "::add-mask::secondary" in captured
    assert (
        "Selected OpenRouter key from OPENROUTER_API_KEY_2 -> OPENROUTER_API_KEY"
        in captured
    )

    env_file = Path(os.environ["GITHUB_ENV"])
    output_file = Path(os.environ["GITHUB_OUTPUT"])

    assert env_file.read_text(encoding="utf-8").splitlines() == [
        "OPENROUTER_API_KEY=secondary"
    ]
    assert output_file.read_text(encoding="utf-8").splitlines() == [
        "selected_key_name=OPENROUTER_API_KEY_2"
    ]

    # Ensure seed env var does not leak into subsequent tests.
    monkeypatch.delenv("ROTATION_SEED", raising=False)

