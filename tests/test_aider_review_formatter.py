from __future__ import annotations

import importlib.util
import pathlib
from textwrap import dedent

import pytest

MODULE_PATH = pathlib.Path(".github/workflows/scripts/aider_review_formatter.py")


@pytest.fixture(scope="session")
def formatter_module():
    spec = importlib.util.spec_from_file_location("aider_review_formatter", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_normalize_spacing_removes_duplicate_blank_lines(formatter_module):
    normalize_spacing = formatter_module.normalize_spacing
    raw = dedent(
        """

            ### ✅ Summary
            - Bullet one


            ### ⚠️ Issues


            None.


        """
    )
    expected = dedent(
        """
            ### ✅ Summary

            - Bullet one

            ### ⚠️ Issues

            None.
        """
    ).strip()
    assert normalize_spacing(raw) == expected


def test_normalize_spacing_inserts_blank_after_heading(formatter_module):
    normalize_spacing = formatter_module.normalize_spacing
    raw = "### ✅ Summary\n- Item"
    expected = "### ✅ Summary\n\n- Item"
    assert normalize_spacing(raw) == expected


def test_format_review_comment_success_flow(formatter_module):
    format_review_comment = formatter_module.format_review_comment
    raw_output = dedent(
        """
        aider vX.Y
        ### 📝 Aider Review

        ### ✅ Summary

        - Bullet one

        ### ⚠️ Issues

        None.

        ### 💡 Suggestions

        None.

        Tokens: 123
        """
    )
    expected = dedent(
        """
        ### 📝 Aider Review

        ### ✅ Summary

        - Bullet one

        ### ⚠️ Issues

        None.

        ### 💡 Suggestions

        None.
        """
    ).strip()
    result = format_review_comment(success=True, truncated=False, raw_review=raw_output, log_tail=None)
    assert result == expected


def test_format_review_comment_includes_log_when_failed(formatter_module):
    format_review_comment = formatter_module.format_review_comment
    log_tail = "Error line 1\nError line 2"
    result = format_review_comment(success=False, truncated=False, raw_review="", log_tail=log_tail)
    assert "```\nError line 1\nError line 2\n```" in result
    assert result.startswith("### 📝 Aider Review\n\n⚠️ Aider review could not be generated automatically.")


def test_format_review_comment_appends_truncation_note(formatter_module):
    format_review_comment = formatter_module.format_review_comment
    result = format_review_comment(success=True, truncated=True, raw_review="### ✅ Summary\nItem", log_tail=None)
    assert result.endswith(
        "\n\n_Note: The diff was truncated to approximately 60k characters for analysis._"
    )


def test_tail_lines_limits_output(formatter_module):
    tail_lines = formatter_module.tail_lines
    raw = "\n".join(f"line {i}" for i in range(50))
    assert tail_lines(raw, 5) == "\n".join(f"line {i}" for i in range(45, 50))
    assert tail_lines(raw, 0) == ""
