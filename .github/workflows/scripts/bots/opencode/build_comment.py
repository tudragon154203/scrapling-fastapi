#!/usr/bin/env python3
"""Compose the GitHub comment body using opencode CLI output."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
MAX_STREAM_SECTION = 2000

_HTML_TAG_RE = re.compile(r"<([^>\n]+)>")
_TOOL_MARKUP_RE = re.compile(r"<(Tool\s+use|/Tool)>", re.IGNORECASE)
_THINKING_MARKUP_RE = re.compile(r"<(/?think(?:ing)?)>", re.IGNORECASE)
_THINK_BLOCK_RE = re.compile(
    r"<(?P<tag>think(?:ing)?)>(?P<content>.*?)</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
_THINK_SECTION_START_RE = re.compile(r"<(think|thinking)>", re.IGNORECASE)
_THINK_SECTION_END_RE = re.compile(r"</(think|thinking)>", re.IGNORECASE)
_SECTION_KEYWORD_RE = re.compile(r"\b(findings|suggestions|confidence)\b", re.IGNORECASE)
_SECTION_PREFIX_CHARS = "#>*-+0123456789.)("


def _normalize_section_header(line: str) -> str:
    """Return a normalized version of a potential section header."""

    normalized = line.lower().strip()
    if not normalized:
        return ""

    while normalized and normalized[0] in _SECTION_PREFIX_CHARS:
        normalized = normalized[1:].lstrip()

    while normalized.startswith("*"):
        normalized = normalized[1:].lstrip()

    return normalized


def _match_section_keyword(line: str) -> str | None:
    normalized = _normalize_section_header(line)
    if not normalized:
        return None

    for keyword in ("findings", "suggestions", "confidence"):
        if normalized.startswith(keyword):
            boundary_index = len(keyword)
            if boundary_index == len(normalized):
                return keyword
            next_char = normalized[boundary_index]
            if next_char in {":", "-", " ", "\t", "\n", "."}:
                return keyword
    return None


def _contains_review_markers(text: str) -> bool:
    if not text:
        return False

    return any(
        _match_section_keyword(line) in {"findings", "suggestions", "confidence"}
        for line in text.splitlines()
    )


def _collect_section_keywords(text: str) -> set[str]:
    return {
        keyword
        for keyword in (
            _match_section_keyword(line)
            for line in text.splitlines()
        )
        if keyword
    }


def _strip_closed_think_blocks(text: str) -> str:
    """Remove hidden reasoning wrapped in <think>/<thinking> pairs."""

    if "<" not in text:
        return text

    def _replace(match: re.Match[str]) -> str:
        content = match.group("content")
        if _contains_review_markers(content):
            return content
        return ""

    return _THINK_BLOCK_RE.sub(_replace, text)


def _strip_think_sections(text: str) -> str:
    """Remove hidden reasoning enclosed in <think>/<thinking> tags."""

    if "<" not in text:
        return text

    parts: list[str] = []
    cursor = 0
    while True:
        start = _THINK_SECTION_START_RE.search(text, cursor)
        if not start:
            parts.append(text[cursor:])
            break
        parts.append(text[cursor:start.start()])
        end = _THINK_SECTION_END_RE.search(text, start.end())
        if end:
            cursor = end.end()
            continue

        remainder = text[start.end():]
        marker_match = _SECTION_KEYWORD_RE.search(remainder)

        if marker_match is None:
            return "".join(parts)

        line_start = remainder.rfind("\n", 0, marker_match.start())
        if line_start == -1:
            cursor = start.end()
        else:
            cursor = start.end() + line_start + 1
        while cursor < len(text) and text[cursor] in "\r\n ":
            cursor += 1

    return "".join(parts)


def clean_stream(text: str) -> str:
    if not text:
        return ""
    cleaned = _collapse_carriage_returns(text)
    cleaned = _strip_closed_think_blocks(cleaned)
    cleaned = _strip_think_sections(cleaned)
    cleaned = ANSI_ESCAPE_RE.sub("", cleaned)
    cleaned = CONTROL_CHAR_RE.sub("", cleaned)
    # Remove thinking and tool markup from the stream
    cleaned = _THINKING_MARKUP_RE.sub("", cleaned)
    cleaned = _TOOL_MARKUP_RE.sub("", cleaned)
    return cleaned.strip()


def extract_review_section(text: str) -> tuple[str, bool]:
    """Return the review portion of the CLI output when available.

    The opencode CLI streams progress updates before emitting the final
    review. We try to detect the structured review by looking for the
    "Findings" section the workflow asks the model to produce. If we find a
    likely review block we return it and signal that progress updates were
    removed. Otherwise we fall back to the original text.
    """

    if not text:
        return "", False

    lines = text.splitlines()
    start_index: int | None = None

    for index, line in enumerate(lines):
        keyword = _match_section_keyword(line)
        if keyword == "findings":
            start_index = index
            break

    if start_index is None:
        return text, False

    start_i = start_index
    if start_index > 0:
        header_index = start_index - 1
        while header_index >= 0 and not lines[header_index].strip():
            header_index -= 1
        if header_index >= 0:
            header = lines[header_index].strip()
            if header.startswith("#") or "review" in header.lower():
                start_i = header_index

    full_review_lines = lines[start_i:]
    review_lines = []
    sections_seen: set[str] = set()
    previous_empty = False
    for line in full_review_lines:
        stripped = line.strip()
        is_empty = not stripped
        keyword = _match_section_keyword(line)
        if keyword:
            sections_seen.add(keyword)
        if (
            is_empty
            and previous_empty
            and "findings" in sections_seen
            and len(sections_seen) >= 2
        ):
            break
        review_lines.append(line)
        previous_empty = is_empty

    review_text = "\n".join(review_lines).rstrip()
    if not review_text:
        return text, False

    section_keywords = _collect_section_keywords(review_text)

    has_findings = "findings" in section_keywords
    has_other_section = bool(
        {"suggestions", "confidence"}.intersection(section_keywords)
    )

    if not has_findings or not has_other_section:
        return text, False

    return review_text, True


def _escape_html_like_tags(text: str) -> str:
    """Escape angle-bracket tags so GitHub does not treat them as HTML."""

    if "<" not in text or ">" not in text:
        return text

    def _replace(match: re.Match[str]) -> str:
        content = match.group(1)
        return f"&lt;{content}&gt;"

    return _HTML_TAG_RE.sub(_replace, text)




def _summarize_tool_calls(streams: Dict[str, str]) -> list[str]:
    """Return a summary of tool calls in the output streams."""
    summaries = []
    for name, stream in streams.items():
        for match in _TOOL_MARKUP_RE.finditer(stream):
            tag = match.group(1)
            summaries.append(f"<{tag}> in {name}")
    return summaries


def _has_expected_review_sections(text: str) -> bool:
    """Return True when the text looks like a structured opencode review."""

    if not text:
        return False

    section_keywords = _collect_section_keywords(text)
    has_findings = "findings" in section_keywords
    has_other_section = bool(
        {"suggestions", "confidence"}.intersection(section_keywords)
    )
    return has_findings and has_other_section


def _diagnose_missing_review(
    stdout_clean: str,
    stdout_display: str,
    metadata: Dict[str, Any],
    tool_markup_detected: bool,
) -> list[str]:
    """Return explanatory notes when the CLI output lacks a review."""

    diagnostics: list[str] = []
    if _has_expected_review_sections(stdout_display or stdout_clean):
        return diagnostics

    if not (stdout_clean or stdout_display):
        return diagnostics

    diagnostics.append(
        "No structured review (findings/suggestions/confidence) was detected in the "
        "CLI output, so the run likely stopped before the model returned its review."
    )

    thinking_mode = metadata.get("thinking_mode")
    if tool_markup_detected:
        if isinstance(thinking_mode, str) and thinking_mode.strip().lower().startswith(
            "tool"
        ):
            diagnostics.append(
                "The run is using tool-calling mode, but the workflow never executed "
                "the requested tool. Disable tool-calling or ensure the workflow "
                "handles tool invocations so the review can complete."
            )
        else:
            diagnostics.append(
                "Tool invocation markup like `&lt;Tool use&gt;` appeared in the output; "
                "make sure your workflow can respond to tool calls or re-run in "
                "standard thinking mode."
            )

    return diagnostics


def _build_troubleshooting_section(exit_code: int) -> str | None:
    """Return additional debugging guidance when the CLI fails."""

    if exit_code == 0:
        return None

    tips = [
        "- Expand the **Run opencode CLI** step in the workflow run to inspect the raw stdout/stderr captured on the runner.",
        "- Re-run the workflow with the repository secret `ACTIONS_STEP_DEBUG` set to `true` to enable verbose shell logging.",
    ]

    lines = ["#### Troubleshooting the opencode CLI", ""]
    lines.extend(tips)
    return "\n".join(lines)


def _collapse_carriage_returns(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text



def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_metadata(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_comment(
    metadata: Dict[str, Any],
    stdout: str,
    stderr: str,
    exit_code: int,
) -> str:
    stdout_clean = clean_stream(stdout)
    stderr_clean = clean_stream(stderr)
    stdout_display, extracted = extract_review_section(stdout_clean)
    tool_markup_detected = bool(_TOOL_MARKUP_RE.search(stdout_clean) or _TOOL_MARKUP_RE.search(stderr_clean))
    sections = ["#### dY opencode CLI"]

    summary = metadata.get("summary")
    if isinstance(summary, str) and summary.strip():
        sections.append(summary.strip())

    command_text = metadata.get("command_text")
    if isinstance(command_text, str) and command_text.strip():
        safe_command = command_text.replace("\r\n", "\n").replace("\n", "<br>")
        sections.append(f"> **Command:** {safe_command}")

    if extracted: # if a review was successfully extracted
        # Clean tool markup from the extracted review section as well
        cleaned_stdout_display = _TOOL_MARKUP_RE.sub("", stdout_display)
        sections.append(_escape_html_like_tags(cleaned_stdout_display))
    elif stdout_clean: # if no review was extracted but there's some output
        sections.append("#### Raw CLI Output (no structured review detected)")
        sections.append("```text")
        # Ensure raw output is also clean of tool markup
        cleaned_stdout_for_display = _TOOL_MARKUP_RE.sub("", stdout_clean)
        sections.append(_escape_html_like_tags(cleaned_stdout_for_display))
        sections.append("```")
    else: # if there's absolutely no output
        sections.append("_The opencode CLI did not return any output._")

    diagnostics = _diagnose_missing_review(
        stdout_clean=stdout_clean,
        stdout_display=stdout_display,
        metadata=metadata,
        tool_markup_detected=tool_markup_detected,
    )
    notes: list[str] = []

    if not extracted and diagnostics:
        notes.extend(diagnostics)

    if exit_code != 0:
        notes.append(
            "The CLI exited with a non-zero status. Review the stderr output for additional details."
        )
    elif not extracted and tool_markup_detected:
        notes.append(
            "The CLI response includes tool invocation markup (for example `&lt;Tool use&gt;`), "
            "which suggests the model attempted to call a tool instead of returning a review."
        )
        tool_summaries = _summarize_tool_calls({"stdout": stdout_clean, "stderr": stderr_clean})
        if tool_summaries:
            notes.append("Tool call requests observed before the run stopped:")
            notes.extend(f"- {summary}" for summary in tool_summaries)

    include_stderr = os.getenv("INCLUDE_OPENCODE_STDERR") == "1"
    appended_stderr = False

    if include_stderr:
        display = stderr_clean or (stderr.strip() if stderr else "")
        truncated = False
        if display:
            if len(display) > MAX_STREAM_SECTION:
                truncated = True
                display = display[-MAX_STREAM_SECTION:]
            block_lines = ["#### CLI stderr (debug mode)", "", "```text", display]
            if truncated:
                block_lines.append("...(truncated)")
            block_lines.append("```")
            sections.append("\n".join(block_lines))
            appended_stderr = True

    if not appended_stderr and stderr_clean and stderr_clean != stdout_clean:
        display = stderr_clean
        truncated = False
        if len(display) > MAX_STREAM_SECTION:
            truncated = True
            display = display[-MAX_STREAM_SECTION:]
        block_lines = ["#### CLI stderr", "", "```text", display]
        if truncated:
            block_lines.append("...(truncated)")
        block_lines.append("```")
        sections.append("\n".join(block_lines))

    if notes:
        sections.append("\n".join(notes))

    troubleshooting = _build_troubleshooting_section(exit_code)
    if troubleshooting:
        sections.append(troubleshooting)

    return "\n\n".join(sections).strip()



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta", required=True, help="Path to the metadata JSON file created earlier.")
    parser.add_argument("--stdout", required=True, help="File containing opencode stdout output.")
    parser.add_argument("--stderr", required=True, help="File containing opencode stderr output.")
    parser.add_argument("--exit-code", required=True, type=int, help="Exit code returned by the opencode CLI.")
    parser.add_argument("--output", required=True, help="Where to write the formatted GitHub comment body.")
    parser.add_argument("--outputs", help="Path to write GitHub Actions step outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = load_metadata(Path(args.meta))
    summary = metadata.get("summary")
    thinking_mode = metadata.get("thinking_mode")
    print(f"[debug] summary: {summary!r}")
    print(f"[debug] thinking_mode: {thinking_mode!r}")
    stdout = read_text(Path(args.stdout))
    stderr = read_text(Path(args.stderr))
    comment = format_comment(metadata, stdout, stderr, args.exit_code)
    output_path = Path(args.output)
    output_path.write_text(comment, encoding="utf-8")

    if args.outputs:
        outputs_path = Path(args.outputs)
        with outputs_path.open("a", encoding="utf-8") as handle:
            handle.write(f"comment_file={output_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

