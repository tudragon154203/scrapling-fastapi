"""Tests for the OpenRouter key rotation helper script."""

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

from rotate_key.base_rotator import BaseKeyRotator
from rotate_key.openrouter import OpenRouterKeyRotator


class _DummyRotator(BaseKeyRotator):
    """Test-specific rotator that exposes BaseKeyRotator helpers."""

    @property
    def default_prefix(self) -> str:
        return "DUMMY"

    @property
    def error_message(self) -> str:
        return ""

    @property
    def success_message(self) -> str:
        return ""


def _clear_openrouter_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in list(os.environ):
        if env_name.startswith("OPENROUTER_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)


def _clear_seed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in [
        "ROTATION_SEED",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_SHA",
        "GITHUB_JOB",
        "GITHUB_WORKFLOW",
    ]:
        monkeypatch.delenv(env_name, raising=False)


def test_gather_candidate_keys_orders_by_suffix(monkeypatch):
    """Candidate keys should be ordered base, numeric suffix, then lexicographic."""

    _clear_openrouter_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "base")
    monkeypatch.setenv("OPENROUTER_API_KEY_10", "ten")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "two")
    monkeypatch.setenv("OPENROUTER_API_KEY_EXTRA", "extra")

    rotator = OpenRouterKeyRotator()
    candidates = rotator.gather_candidate_keys("OPENROUTER_API_KEY")

    ordered_names = [candidate.env_name for candidate in candidates]
    assert ordered_names == [
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_2",
        "OPENROUTER_API_KEY_10",
        "OPENROUTER_API_KEY_EXTRA",
    ]

    selected = rotator.select_key(candidates, seed=1)
    assert selected.env_name == "OPENROUTER_API_KEY_2"


def test_select_key_requires_candidates():
    rotator = OpenRouterKeyRotator()
    with pytest.raises(RuntimeError):
        rotator.select_key([], seed=0)


def test_main_exports_to_github_files(monkeypatch, tmp_path, capfd):
    """Running the script writes to GitHub env/output files and masks the key."""

    _clear_openrouter_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "primary")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "secondary")
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "env"))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("ROTATION_SEED", "1")

    monkeypatch.setattr(sys, "argv", ["openrouter.py"])

    rotator = OpenRouterKeyRotator()
    rotator.run()

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
        "selected_key_name=OPENROUTER_API_KEY_2",
        "key_present=true",
    ]

    # Ensure seed env var does not leak into subsequent tests.
    monkeypatch.delenv("ROTATION_SEED", raising=False)


def test_derive_seed_changes_with_attempt(monkeypatch):
    """Retries within the same run should lead to different seeds."""

    _clear_seed_env(monkeypatch)
    rotator = _DummyRotator()

    monkeypatch.setenv("GITHUB_RUN_ID", "123456")
    monkeypatch.setenv("GITHUB_JOB", "claude")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    first_seed = rotator.derive_seed(None)

    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    second_seed = rotator.derive_seed(None)

    assert first_seed != second_seed


def test_derive_seed_uses_attempt_when_primary_missing(monkeypatch):
    """Run attempt should still influence the seed when run metadata is absent."""

    _clear_seed_env(monkeypatch)
    rotator = _DummyRotator()

    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "7")
    seed_one = rotator.derive_seed(None)

    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "8")
    seed_two = rotator.derive_seed(None)

    assert seed_one != seed_two


def test_derive_seed_varies_by_workflow(monkeypatch):
    """Different workflows within the same run should not share seeds."""

    _clear_seed_env(monkeypatch)
    rotator = _DummyRotator()

    monkeypatch.setenv("GITHUB_RUN_ID", "13579")
    monkeypatch.setenv("GITHUB_JOB", "shared")
    monkeypatch.setenv("GITHUB_WORKFLOW", "🤖 Claude")
    claude_seed = rotator.derive_seed(None)

    monkeypatch.setenv("GITHUB_WORKFLOW", "🪐 Gemini")
    gemini_seed = rotator.derive_seed(None)

    assert claude_seed != gemini_seed
