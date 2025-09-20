import sys
import os
from pathlib import Path

sys.path.insert(0, '.github/workflows/scripts/bots/opencode')

import pytest
from typing import Dict, Any

from build_comment import extract_review_section, format_comment, clean_stream


@pytest.fixture(autouse=True)
def no_stderr_env(monkeypatch):
    """Ensure INCLUDE_OPENCODE_STDERR is not set to include debug stderr."""
    monkeypatch.setenv("INCLUDE_OPENCODE_STDERR", "0")


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

    def test_heading_variations(self):
        text = """Progress update

### Findings
Details here.

### Suggestions
Try another approach.

### Confidence
Medium."""
        expected = """### Findings
Details here.

### Suggestions
Try another approach.

### Confidence
Medium."""

        result, extracted = extract_review_section(text)
        assert result.strip() == expected.strip()
        assert extracted


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

        assert "#### dY opencode CLI" in comment
        assert "Test summary" in comment
        assert "> **Command:** opencode --prompt test" in comment
        assert "**Findings:**" in comment
        assert "**Suggestions:**" in comment
        assert "**Confidence:**" in comment
        assert "Model:" not in comment
        assert "Event:" not in comment
        assert "Thinking mode:" not in comment
        assert "Exit code:" not in comment
        assert "Progress output from the CLI was omitted" not in comment

    def test_with_review_inside_think_block(self):
        metadata: Dict[str, Any] = {
            "summary": "Model returned review inside think block",
            "thinking_mode": "standard",
        }
        stdout = (
            "Progress output\n"
            "<think>\n"
            "**Findings:** Hidden but real.\n"
            "\n"
            "**Suggestions:** Still valid.\n"
            "\n"
            "**Confidence:** Medium.\n"
            "</think>"
        )

        comment = format_comment(metadata, stdout, stderr="", exit_code=0)

        assert "Hidden but real." in comment
        assert "Still valid." in comment
        assert "Medium." in comment
        assert "_The opencode CLI did not return any output._" not in comment

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
        assert "Exit code: `0`" not in comment

    def test_with_stderr(self):
        metadata: Dict[str, Any] = {"model": "gpt-4"}
        stdout = "**Findings:** Test."
        stderr = "Some error message."
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        assert "#### CLI stderr" in comment
        assert "```text" in comment
        assert "Some error message." in comment
        assert "```" in comment

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
        stdout = (
            "\x1B[31mRed text\x1B[0m\n"
            "Thinking: <thinking>stuff</thinking>\n"
            "Reasoning: <think>hidden</think>\n"
            "<Tool use> call </Tool>\n"
            "Error: boom\n"
            "**Findings:** Clean."
        )
        stderr = "stderr with \r\n carriage."
        exit_code = 0

        comment = format_comment(metadata, stdout, stderr, exit_code)

        # Should clean ANSI, control, but extract review
        assert "\x1B" not in comment  # No ANSI
        assert "<thinking>" not in comment  # Thinking block in progress, removed by extract
        assert "hidden" not in comment  # <think> reasoning removed entirely
        assert "<Tool" not in comment  # Tool markup in progress, removed; if in review, would be escaped to <Tool
        # But since in prefix, removed
        assert "Error: boom" in comment  # In progress, not removed by clean_stream
        assert "**Findings:** Clean." in comment
        assert "#### CLI stderr" in comment
        assert "carriage" in comment  # Cleaned but present in stderr block

    def test_unterminated_think_block_removed(self):
        metadata: Dict[str, Any] = {
            "summary": "Hidden reasoning should be stripped",
            "thinking_mode": "standard",
        }
        stdout = (
            "<think>Deliberate reasoning that should stay hidden.\n"
            "More hidden lines continuing the thought.\n"
            "**Findings:** Visible content.\n"
            "\n"
            "**Suggestions:** Ship it.\n"
            "\n"
            "**Confidence:** High."
        )
        comment = format_comment(metadata, stdout, stderr="", exit_code=0)

        assert "Deliberate reasoning" not in comment
        assert "More hidden lines" not in comment
        assert "**Findings:** Visible content." in comment
        assert "**Suggestions:** Ship it." in comment
        assert "**Confidence:** High." in comment

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

    def test_review_with_hash_headings_inside_think_block(self):
        metadata: Dict[str, Any] = {
            "summary": "Review uses markdown headings",
            "thinking_mode": "standard",
        }
        stdout = (
            "Progress output\n"
            "<think>\n"
            "### Findings\n"
            "Heading variation.\n"
            "\n"
            "### Suggestions\n"
            "Adjust tests.\n"
            "\n"
            "### Confidence\n"
            "Reasonable.\n"
            "</think>"
        )

        comment = format_comment(metadata, stdout, stderr="", exit_code=0)

        assert "Heading variation." in comment
        assert "Adjust tests." in comment
        assert "Reasonable." in comment
        assert "_The opencode CLI did not return any output._" not in comment


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

    def test_unterminated_think_block(self):
        text = "<think>secret reasoning that should be removed"
        cleaned = clean_stream(text)
        assert cleaned == ""

    def test_think_block_with_review_markers_kept(self):
        text = (
            "<think>\n"
            "**Findings:** Issue found.\n"
            "**Suggestions:** Fix it.\n"
            "</think>"
        )
        cleaned = clean_stream(text)
        assert "Issue found." in cleaned
        assert "Fix it." in cleaned

    def test_think_block_with_heading_markers_kept(self):
        text = (
            "<think>\n"
            "### Findings\n"
            "Issue found.\n"
            "- Suggestions\n"
            "Do better.\n"
            "\n"
            "### Confidence\n"
            "High\n"
            "</think>"
        )
        cleaned = clean_stream(text)
        assert "Issue found." in cleaned
        assert "Do better." in cleaned
        assert "High" in cleaned
