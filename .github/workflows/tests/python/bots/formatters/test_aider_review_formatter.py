"""Tests for the aider review formatter workflow helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


WORKFLOWS_DIR = next(
    parent for parent in Path(__file__).resolve().parents if parent.name == "workflows"
)
MODULE_PATH = (
    WORKFLOWS_DIR / "scripts" / "bots" / "aider" / "aider_review_formatter.py"
)


@pytest.fixture(scope="module")
def formatter_module():
    """Import the aider review formatter module for testing."""
    spec = importlib.util.spec_from_file_location(
        "aider_review_formatter", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader  # narrow mypy / pytest type checking
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def test_normalize_spacing_cleans_redundant_blank_lines(formatter_module):
    """normalize_spacing should collapse excess blank lines and trim trailing space."""
    raw = "### Heading\r\n\r\nLine one with space   \r\n\r\n\r\nNext paragraph\n"
    expected = "### Heading\n\nLine one with space\n\nNext paragraph"

    result = formatter_module.normalize_spacing(raw)

    assert result == expected


def test_extract_review_removes_noise_and_stop_sections(formatter_module):
    """extract_review should keep the meaningful summary while discarding noise."""
    raw = "\n".join(
        [
            "intro line",
            "### Summary",
            "aider v3.50.0",  # noise prefix
            "assistant: please ignore",  # noise prefix
            "Real insight worth keeping.",
            "",
            "Tokens: 123 (stop term should truncate below)",
            "This line should be removed.",
        ]
    )

    result = formatter_module.extract_review(raw)

    assert result == "### Summary\nReal insight worth keeping."


def test_tail_lines_returns_expected_number_of_lines(formatter_module):
    """tail_lines should return the requested number of trailing lines."""
    source = "\n".join(f"line {i}" for i in range(1, 51))

    assert formatter_module.tail_lines(source, limit=3) == "\n".join(
        ["line 48", "line 49", "line 50"]
    )
    assert formatter_module.tail_lines(source, limit=100) == source
    assert formatter_module.tail_lines(source, limit=0) == ""


def test_format_review_comment_success_path(formatter_module):
    """Successful formatting should produce a tidy Markdown review comment."""
    raw_review = "\n".join(["### Summary", "Important fix applied."])

    comment = formatter_module.format_review_comment(
        success=True,
        truncated=False,
        raw_review=raw_review,
    )

    assert comment.startswith(formatter_module.REVIEW_HEADING)
    assert "### Summary\n\nImportant fix applied." in comment
    assert formatter_module.TRUNCATION_NOTE not in comment


def test_format_review_comment_failure_includes_log_tail_and_note(formatter_module):
    """Failure mode should include fallback message, log tail, and truncation note."""
    comment = formatter_module.format_review_comment(
        success=False,
        truncated=True,
        raw_review="irrelevant",
        log_tail="error 1\nerror 2",
    )

    assert comment.startswith(formatter_module.REVIEW_HEADING)
    assert formatter_module.FALLBACK_MESSAGE in comment
    assert "```\nerror 1\nerror 2\n```" in comment
    assert formatter_module.TRUNCATION_NOTE.strip() in comment
