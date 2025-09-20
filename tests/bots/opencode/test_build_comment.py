"""Tests for the opencode comment builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github/workflows/scripts/bots/opencode/build-comment.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_comment", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_extract_review_section_omits_progress():
    module = load_module()
    text = (
        "I'll review the pull request now.\n"
        "Gathering context...\n\n"
        "## Review Summary\n"
        "**Findings:** The changes update comment formatting.\n"
        "**Suggestions:** Consider adding regression tests.\n"
        "**Confidence:** 7/10"
    )

    review, extracted = module.extract_review_section(text)

    assert extracted is True
    assert review.startswith("## Review Summary")
    assert "**Confidence:** 7/10" in review
    assert "Gathering context" not in review


def test_extract_review_section_falls_back_without_markers():
    module = load_module()
    text = "Processing...\nAlmost done."

    review, extracted = module.extract_review_section(text)

    assert extracted is False
    assert review == text


def test_format_comment_skips_missing_review_diagnostic_when_sections_present():
    module = load_module()
    metadata = {
        "summary": "Automated review",
        "model": "test-model",
        "event_name": "pull_request",
    }
    stdout = (
        "## Review Summary\n"
        "**Findings:** Looks good.\n"
        "**Suggestions:** None.\n"
        "**Confidence:** 9/10"
    )

    comment = module.format_comment(metadata, stdout, "", 0)

    assert "No structured review" not in comment


def test_format_comment_escapes_html_like_sequences():
    module = load_module()
    metadata = {
        "summary": "Automated review",
        "model": "test-model",
        "event_name": "pull_request",
        "thinking_mode": "tool-calling",
    }

    comment = module.format_comment(metadata, "<Tool use>\nAll good!", "", 0)

    assert "&lt;Tool use&gt;" in comment
    assert "<Tool use>" not in comment
    assert "Thinking mode: `tool-calling`" in comment
    assert "tool invocation markup" in comment
    assert "No structured review" in comment
    assert "Disable tool-calling" in comment


def test_format_comment_includes_troubleshooting_guidance_when_cli_fails():
    module = load_module()
    metadata = {
        "summary": "Automated review",
        "model": "test-model",
        "event_name": "pull_request",
    }

    comment = module.format_comment(metadata, "", "error", 2)

    assert "Troubleshooting the opencode CLI" in comment
    assert "ACTIONS_STEP_DEBUG" in comment


def test_format_comment_does_not_flag_when_markup_absent():
    module = load_module()
    metadata = {
        "summary": "Automated review",
        "model": "test-model",
        "event_name": "pull_request",
    }

    comment = module.format_comment(metadata, "All good!", "", 0)

    assert "tool invocation markup" not in comment
    assert "Disable tool-calling" not in comment


def test_format_comment_adds_non_tool_diagnostic():
    module = load_module()
    metadata = {
        "summary": "Automated review",
        "model": "test-model",
        "event_name": "pull_request",
    }

    comment = module.format_comment(metadata, "Thinking...", "", 0)

    assert "No structured review" in comment
    assert "tool invocation markup" not in comment
