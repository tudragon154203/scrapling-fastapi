#!/usr/bin/env python3
"""Compose the GitHub comment body using opencode CLI output."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-9;?]*[ -/]*[@-~]")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
MAX_STREAM_SECTION = 2000

_FINDINGS_MARKERS = ("**findings:**", "findings:", "## findings")
_SUGGESTIONS_MARKERS = ("**suggestions:**", "suggestions:", "## suggestions")
_CONFIDENCE_MARKERS = ("**confidence:**", "confidence:", "## confidence")

def clean_stream(text: str) -> str:
    if not text:
        return ""
    cleaned = _collapse_carriage_returns(text)
    cleaned = ANSI_ESCAPE_RE.sub("", cleaned)
    cleaned = CONTROL_CHAR_RE.sub("", cleaned)
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
        stripped = line.strip().lower()
        if not stripped:
            continue
        if any(marker in stripped for marker in _FINDINGS_MARKERS):
            start_index = index
            break

    if start_index is None:
        return text, False

    review_lines = lines[start_index:]
    if start_index > 0:
        header_index = start_index - 1
        while header_index >= 0 and not lines[header_index].strip():
            header_index -= 1
        if header_index >= 0:
            header = lines[header_index].strip()
            if header.startswith("#") or "review" in header.lower():
                review_lines = lines[header_index:]

    review_text = "\n".join(review_lines).strip()
    if not review_text:
        return text, False

    lowered = review_text.lower()
    has_findings = any(marker in lowered for marker in _FINDINGS_MARKERS)
    has_other_section = any(
        any(marker in lowered for marker in markers)
        for markers in (_SUGGESTIONS_MARKERS, _CONFIDENCE_MARKERS)
    )

    if not has_findings or not has_other_section:
        return text, False

    return review_text, True


def _collapse_carriage_returns(text: str) -> str:
    text = text.replace("\r\n", "\n")
    lines: list[str] = []
    current: list[str] = []

    for char in text:
        if char == "\r":
            current = []
            continue
        if char == "\n":
            lines.append("".join(current))
            current = []
            continue
        current.append(char)

    if current:
        lines.append("".join(current))

    return "\n".join(lines)



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
    sections = ["#### dY opencode CLI"]

    summary = metadata.get("summary")
    if isinstance(summary, str) and summary.strip():
        sections.append(summary.strip())

    command_text = metadata.get("command_text")
    if isinstance(command_text, str) and command_text.strip():
        safe_command = command_text.replace("\r\n", "\n").replace("\n", "<br>")
        sections.append(f"> **Command:** {safe_command}")

    if stdout_display:
        sections.append(stdout_display)
    else:
        sections.append("_The opencode CLI did not return any output._")

    meta_lines: list[str] = []
    model = metadata.get("model") or "unknown"
    meta_lines.append(f"Model: `{model}`")
    event_name = metadata.get("event_name") or "unknown"
    meta_lines.append(f"Event: `{event_name}`")
    meta_lines.append(f"Exit code: `{exit_code}`")
    if extracted:
        meta_lines.append("Progress output from the CLI was omitted to highlight the final review.")
    if exit_code != 0:
        meta_lines.append(
            "The CLI exited with a non-zero status. Review the stderr output for additional details."
        )

    if stderr_clean and stderr_clean != stdout_clean:
        display = stderr_clean
        truncated = False
        if len(display) > MAX_STREAM_SECTION:
            truncated = True
            display = display[-MAX_STREAM_SECTION:]
        block_lines = ["CLI stderr:", "```text", display]
        if truncated:
            block_lines.append("...(truncated)")
        block_lines.append("```")
        meta_lines.append("\n".join(block_lines))
    elif stderr and stderr.strip():
        meta_lines.append("CLI stderr contained only formatting codes and was omitted.")

    sections.append("\n".join(meta_lines))
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
