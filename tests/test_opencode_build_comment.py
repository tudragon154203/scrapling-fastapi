from __future__ import annotations

import importlib.util
import pathlib
from textwrap import dedent

import pytest

MODULE_PATH = pathlib.Path(".github/workflows/scripts/bots/opencode/build_comment.py")


@pytest.fixture(scope="session")
def build_comment_module():
    spec = importlib.util.spec_from_file_location("opencode_build_comment", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("", ""),
        ("No review heading here", "No review heading here"),
        ("### 🙋 OpenCode Review\nContent", "### 🙋 OpenCode Review\nContent"),
        (
            "Progress update\n### 🙋 OpenCode Review\nLatest findings",
            "### 🙋 OpenCode Review\nLatest findings",
        ),
        (
            "First\n### 🙋 OpenCode Review\nOld review\nAnother line\n### 🙋 OpenCode Review\nNew review",
            "### 🙋 OpenCode Review\nNew review",
        ),
        (
            "Leading text\n### 🙋 OpenCode Review",
            "### 🙋 OpenCode Review",
        ),
    ],
)
def test_filter_to_latest_review_cases(build_comment_module, raw, expected):
    filter_to_latest_review = build_comment_module.filter_to_latest_review
    assert filter_to_latest_review(raw) == expected


def test_format_comment_filters_to_latest_review(build_comment_module):
    format_comment = build_comment_module.format_comment
    metadata = {
        "summary": "Automated review summary.",
        "command_text": "opencode review",
        "model": "gpt-test",
        "event_name": "push",
    }
    stdout = dedent(
        """
        Progress: preparing analysis
        ### 🙋 OpenCode Review

        **Findings:**
        - Earlier issue

        **Suggestions:**
        - Earlier suggestion

        **Confidence:**
        - Medium

        Another progress update
        ### 🙋 OpenCode Review

        **Findings:**
        - Final issue

        **Suggestions:**
        - Final suggestion

        **Confidence:**
        - High
        """
    ).strip()
    comment = format_comment(metadata=metadata, stdout=stdout, stderr="", exit_code=0)

    assert "Progress: preparing analysis" not in comment
    assert "Another progress update" not in comment
    assert "Final issue" in comment
    assert "Final suggestion" in comment
    assert "### 🙋 OpenCode Review" in comment
    assert "Progress output from the CLI was omitted" in comment
