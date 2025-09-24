import sys
from textwrap import dedent

sys.path.insert(0, '.github/workflows/scripts/bots/opencode')

import pytest
from typing import Any, Dict

from build_comment import (
    clean_stream,
    extract_review_section,
    filter_to_latest_review,
    format_comment,
)

class TestFilterToLatestReview:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("", ""),
            ("No review heading here", "No review heading here"),
            (
                "### 🙋 OpenCode Review\nSummary line",
                "### 🙋 OpenCode Review\nSummary line",
            ),
            (
                "Progress update\n### 🙋 OpenCode Review\nLatest findings",
                "### 🙋 OpenCode Review\nLatest findings",
            ),
            (
                "First section\n### 🙋 OpenCode Review\nOld review\nAnother line\n### 🙋 OpenCode Review\nNew review",
                "### 🙋 OpenCode Review\nNew review",
            ),
            (
                "Lead-in text\n### 🙋 OpenCode Review",
                "### 🙋 OpenCode Review",
            ),
        ],
    )
    def test_various_headings(self, raw: str, expected: str) -> None:
        assert filter_to_latest_review(raw) == expected


class TestExtractReviewSection:
    def test_no_markers(self):
        text = "Some progress output\nNo findings here."
        result, extracted = extract_review_section(text)
        assert result == text
        assert not extracted

    def test_with_full_review(self):
        text = """Progress line 1
Progress line 2

## Findings
Some findings.

**Suggestions:**
Some suggestions.

**Confidence:**
High confidence."""
        expected = """## Findings
Some findings.

**Suggestions:**
Some suggestions.

**Confidence:**
High confidence."""
        result, extracted = extract_review_section(text)
        assert result.strip() == expected.strip()
        assert extracted

    def test_with_header_inclusion(self):
        text = """Progress

# Code Review

**Findings:**
Issues found.

**Suggestions:**
Fixes."""
        expected = """# Code Review

**Findings:**
Issues found.

**Suggestions:**
Fixes."""
        result, extracted = extract_review_section(text)
        assert result.strip() == expected.strip()
        assert extracted

    def test_missing_other_sections(self):
        text = """Progress

**Findings:**
Only findings, no suggestions or confidence."""
        result, extracted = extract_review_section(text)
        assert result == text
        assert not extracted

    def test_only_suggestions_no_findings(self):
        text = """**Suggestions:**
Some suggestions."""
        result, extracted = extract_review_section(text)
        assert result == text
        assert not extracted

    def test_empty_input(self):
        result, extracted = extract_review_section("")
        assert result == ""
        assert not extracted

    def test_trailing_empty_lines(self):
        text = """Progress

**Findings:**
Findings.

**Suggestions:**
Suggestions.


More empty lines after."""
        expected = """**Findings:**
Findings.

**Suggestions:**
Suggestions."""
        result, extracted = extract_review_section(text)
        assert result.strip() == expected.strip()
        assert extracted

    def test_multiple_findings_markers(self):
        text = """Progress

Findings: First.

## Findings
Second findings.

**Suggestions:**
Suggestions."""
        expected = """Findings: First.

## Findings
Second findings.

**Suggestions:**
Suggestions."""
        result, extracted = extract_review_section(text)
        assert result.strip() == expected.strip()
        assert extracted

    def test_malformed_review(self):
        text = """**Findings:**
Incomplete."""
        result, extracted = extract_review_section(text)
        assert result == text
        assert not extracted


class TestFormatComment:
    def test_with_review(self):
        metadata: Dict[str, Any] = {
            "summary": "Test summary",
            "command_text": "opencode --prompt test",
            "model": "gpt-4",
            "event_name": "pull_request",
            "thinking_mode": "standard",
        }
        stdout = """Progress

**Findings:**
Good code.

**Suggestions:**
Minor fixes.

**Confidence:**
High."""
        stderr = ""
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        # No header is added before extracted review content in the new pipeline
        assert "Test summary" in comment
        assert "> **Command:** opencode --prompt test" in comment
        assert "**Findings:**" in comment
        assert "**Suggestions:**" in comment
        assert "**Confidence:**" in comment
        assert "Model:" not in comment
        assert "Event:" not in comment
        assert "Thinking mode:" not in comment
        assert "Exit code:" not in comment

    def test_filters_to_latest_review(self):
        metadata: Dict[str, Any] = {
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

        comment = format_comment(metadata, stdout, stderr="", exit_code=0)

        assert "Progress: preparing analysis" not in comment
        assert "Another progress update" not in comment
        assert "Final issue" in comment
        assert "Final suggestion" in comment
        assert "### 🙋 OpenCode Review" in comment
        assert "Progress output" not in comment

    def test_without_review(self):
        metadata: Dict[str, Any] = {"model": "gpt-4", "event_name": "pull_request"}
        stdout = "Only progress, no review."
        stderr = ""
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "#### Raw CLI Output (no structured review detected)" in comment
        assert "```text" in comment
        assert "Only progress, no review." in comment
        assert "```" in comment
        assert "No structured review (findings/suggestions/confidence) was detected" in comment
        assert "Model:" not in comment
        assert "Exit code:" not in comment

    def test_with_stderr(self):
        metadata: Dict[str, Any] = {"model": "gpt-4"}
        stdout = "**Findings:** Test."
        stderr = "Some error message."
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "**Findings:**" in comment
        assert "CLI stderr" not in comment
        assert "Some error message." not in comment
        assert "Debug:" not in comment

    def test_non_zero_exit_code(self):
        metadata: Dict[str, Any] = {"model": "gpt-4"}
        stdout = ""
        stderr = "Error."
        exit_code = 1

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "The CLI exited with a non-zero status." in comment
        assert "#### Troubleshooting the opencode CLI" in comment
        assert "- Expand the **Run opencode CLI** step" in comment

    def test_no_unwanted_elements(self):
        # Test cleaning: ANSI, control chars, thinking blocks, tool uses, errors
        metadata: Dict[str, Any] = {"model": "gpt-4"}
        stdout = "\x1B[31mRed text\x1B[0m\nThinking: <thinking>stuff</thinking>\n<Tool use> call </Tool>\nError: boom\n**Findings:** Clean."
        stderr = "stderr with \r\n carriage."
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        # Should clean ANSI, control, but extract review
        assert "\x1B" not in comment  # No ANSI
        assert "<thinking>" not in comment  # Thinking block in progress, removed by extract
        assert "<Tool" not in comment  # Tool markup in progress, removed; if in review, would be escaped to <Tool
        # But since in prefix, removed
        assert "Error: boom" in comment  # In progress, not removed by clean_stream
        assert "**Findings:** Clean." in comment
        assert "CLI stderr" not in comment
        assert "carriage" not in comment

    def test_empty_inputs(self):
        metadata: Dict[str, Any] = {}
        stdout = ""
        stderr = ""
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "_The opencode CLI did not return any output._" in comment
        assert "Model:" not in comment
        assert "Event:" not in comment
        assert "Exit code:" not in comment

    def test_html_like_tags_escaped(self):
        metadata: Dict[str, Any] = {"model": "gpt-4"}
        stdout = "**Findings:** <b>Bold</b> text."
        stderr = ""
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "&lt;b&gt;Bold&lt;/b&gt;" in comment  # Escaped in review


class TestCleanStream:
    def test_ansi_removal(self):
        text = "\x1B[31mRed\x1B[0m normal"
        cleaned = clean_stream(text)
        assert cleaned == "Red normal"

    def test_control_chars(self):
        text = "Line\x01with\x07bell"
        cleaned = clean_stream(text)
        assert cleaned == "Linewithbell"

    def test_carriage_returns(self):
        text = "Line1\r\nLine2\rLine3\n"
        cleaned = clean_stream(text)
        assert cleaned == "Line1\nLine2\nLine3"

    def test_empty(self):
        assert clean_stream("") == ""