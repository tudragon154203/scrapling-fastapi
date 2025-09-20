"""Tests for the BaseKeyRotator abstract base class."""

from __future__ import annotations

import hashlib
import os
import random
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the rotate_key package to the path
WORKFLOWS_DIR = next(
    parent for parent in Path(__file__).resolve().parents if parent.name == "workflows"
)
COMMON_DIR = WORKFLOWS_DIR / "scripts" / "bots" / "common"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

from rotate_key.base_rotator import BaseKeyRotator, KeyEntry


class ConcreteKeyRotator(BaseKeyRotator):
    """Concrete implementation for testing the base class."""

    @property
    def default_prefix(self) -> str:
        return "TEST_API_KEY"

    @property
    def error_message(self) -> str:
        return "No test API keys were provided."

    @property
    def success_message(self) -> str:
        return "Selected test key from {} -> {}"


@pytest.fixture
def rotator():
    """Create a concrete rotator instance for testing."""
    return ConcreteKeyRotator()


def test_key_entry_creation():
    """Test that KeyEntry can be created with expected attributes."""
    entry = KeyEntry(env_name="TEST_API_KEY_1", value="secret123", order=(1, "TEST_API_KEY_1"))
    assert entry.env_name == "TEST_API_KEY_1"
    assert entry.value == "secret123"
    assert entry.order == (1, "TEST_API_KEY_1")


def test_derive_order_base_key(rotator):
    """Test that the base key gets the correct order."""
    order = rotator.derive_order("TEST_API_KEY", "TEST_API_KEY")
    assert order == (0, "TEST_API_KEY")


def test_derive_order_numeric_suffix(rotator):
    """Test that numeric suffixes get ordered correctly."""
    order = rotator.derive_order("TEST_API_KEY_2", "TEST_API_KEY")
    assert order == (2, "TEST_API_KEY_2")


def test_derive_order_non_numeric_suffix(rotator):
    """Test that non-numeric suffixes get ordered last."""
    order = rotator.derive_order("TEST_API_KEY_ALPHA", "TEST_API_KEY")
    assert order == (10_000, "TEST_API_KEY_ALPHA")


def test_parse_seed_integer():
    """Test parsing integer seeds."""
    rotator = ConcreteKeyRotator()
    result = rotator.parse_seed("12345")
    assert result == 12345


def test_parse_seed_string():
    """Test parsing string seeds by hashing."""
    rotator = ConcreteKeyRotator()
    result = rotator.parse_seed("some_string")
    # Should be an integer derived from hashing
    assert isinstance(result, int)
    assert result > 0


def test_gather_candidate_keys_empty(rotator, monkeypatch):
    """Test gathering keys when none are present."""
    # Clear any existing test keys
    for env_name in list(os.environ):
        if env_name.startswith("TEST_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)
    
    candidates = rotator.gather_candidate_keys("TEST_API_KEY")
    assert candidates == []


def test_gather_candidate_keys_with_values(rotator, monkeypatch):
    """Test gathering keys when they are present."""
    # Clear any existing test keys
    for env_name in list(os.environ):
        if env_name.startswith("TEST_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)
    
    # Set up test environment
    monkeypatch.setenv("TEST_API_KEY", "primary")
    monkeypatch.setenv("TEST_API_KEY_2", "secondary")
    monkeypatch.setenv("TEST_API_KEY_10", "ten")
    
    candidates = rotator.gather_candidate_keys("TEST_API_KEY")
    
    # Should have 3 candidates ordered correctly
    assert len(candidates) == 3
    assert candidates[0].env_name == "TEST_API_KEY"
    assert candidates[1].env_name == "TEST_API_KEY_2"
    assert candidates[2].env_name == "TEST_API_KEY_10"


def test_select_key_empty_candidates(rotator):
    """Test that selecting from empty candidates raises an error."""
    with pytest.raises(RuntimeError, match="No test API keys were provided"):
        rotator.select_key([], seed=0)


def test_select_key_with_candidates(rotator, monkeypatch):
    """Test selecting a key from candidates."""
    # Clear any existing test keys
    for env_name in list(os.environ):
        if env_name.startswith("TEST_API_KEY"):
            monkeypatch.delenv(env_name, raising=False)
    
    # Set up test environment
    monkeypatch.setenv("TEST_API_KEY", "primary")
    monkeypatch.setenv("TEST_API_KEY_2", "secondary")
    
    candidates = rotator.gather_candidate_keys("TEST_API_KEY")
    selected = rotator.select_key(candidates, seed=1)
    
    # With seed=1 and 2 candidates, should select index 1 (the second one)
    assert selected.env_name == "TEST_API_KEY_2"


@patch("builtins.print")
def test_mask_value(mock_print, rotator):
    """Test that mask_value prints the correct masking command."""
    rotator.mask_value("secret123")
    mock_print.assert_called_once_with("::add-mask::secret123")


def test_append_to_file_no_path(rotator, capfd):
    """Test appending to file when no path is provided."""
    rotator.append_to_file(None, "test content")
    captured = capfd.readouterr()
    assert captured.out == "test content\n"


def test_append_to_file_with_path(rotator, tmp_path):
    """Test appending to file when a path is provided."""
    test_file = tmp_path / "test.txt"
    rotator.append_to_file(str(test_file), "test content")
    
    assert test_file.read_text() == "test content\n"


def test_derive_seed_from_user_seed(rotator):
    """Test deriving seed from explicit user seed."""
    seed = rotator.derive_seed(12345)
    assert seed == 12345


def test_derive_seed_from_env_seed(rotator, monkeypatch):
    """Test deriving seed from environment variable."""
    monkeypatch.setenv("ROTATION_SEED", "54321")
    seed = rotator.derive_seed(None)
    assert seed == 54321


@patch.dict(os.environ, {
    "GITHUB_RUN_ID": "98765",
    "GITHUB_JOB": "test-job"
}, clear=True)
def test_derive_seed_from_github_metadata(rotator):
    """Test deriving seed from GitHub metadata."""
    # Mock random to make the test deterministic
    with patch.object(random, 'randint', return_value=42):
        seed = rotator.derive_seed(None)
        # Should be based on GITHUB_RUN_ID + job hash + random offset
        assert isinstance(seed, int)
        assert seed > 0


def test_derive_seed_includes_all_metadata(rotator):
    """Seeds must incorporate all configured GitHub metadata."""

    env = {
        "GITHUB_RUN_ID": "123456",
        "GITHUB_RUN_NUMBER": "78",
        "GITHUB_SHA": "abc123def456",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_WORKFLOW": "rotate-key-workflow",
        "GITHUB_JOB": "rotate-key-job",
    }

    with patch.dict(os.environ, env, clear=True):
        with patch.object(random, "randint", return_value=0):
            seed = rotator.derive_seed(None)

    modulus = 2**64
    expected = 0
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_NUMBER", "GITHUB_SHA"):
        expected = (expected + rotator.parse_seed(env[key])) % modulus

    expected = (expected + rotator.parse_seed(env["GITHUB_RUN_ATTEMPT"])) % modulus
    expected = (expected + rotator.parse_seed(env["GITHUB_WORKFLOW"])) % modulus
    expected = (expected + rotator.parse_seed(env["GITHUB_JOB"])) % modulus

    assert seed == expected


def test_derive_seed_varies_with_metadata(rotator):
    """Changing run metadata should alter the derived seed."""

    base_env = {
        "GITHUB_RUN_ID": "111",
        "GITHUB_RUN_NUMBER": "222",
        "GITHUB_SHA": "fffaaa",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW": "workflow-a",
        "GITHUB_JOB": "job-a",
    }

    def compute_seed(**overrides):
        env = {**base_env, **overrides}
        with patch.dict(os.environ, env, clear=True):
            with patch.object(random, "randint", return_value=0):
                return rotator.derive_seed(None)

    base_seed = compute_seed()

    assert compute_seed(GITHUB_RUN_ID="112") != base_seed
    assert compute_seed(GITHUB_RUN_NUMBER="333") != base_seed
    assert compute_seed(GITHUB_RUN_ATTEMPT="2") != base_seed
    assert compute_seed(GITHUB_WORKFLOW="workflow-b") != base_seed
