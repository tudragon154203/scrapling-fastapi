"""Tests for model normalization helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github/workflows/scripts/bots/opencode/model_utils.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("model_utils", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_canonicalize_model_accepts_prefixed_slugs():
    module = load_module()
    assert (
        module.canonicalize_model("openrouter/deepseek/deepseek-r1:free")
        == "openrouter.deepseek-r1-free"
    )


def test_canonicalize_model_trims_whitespace():
    module = load_module()
    assert module.canonicalize_model("  OPENROUTER.GPT-4O-MINI  ") == "openrouter.gpt-4o-mini"


def test_canonicalize_model_leaves_simple_ids():
    module = load_module()
    assert module.canonicalize_model("gpt-4o-mini") == "gpt-4o-mini"

