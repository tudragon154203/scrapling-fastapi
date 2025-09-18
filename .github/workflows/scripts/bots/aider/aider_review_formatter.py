from __future__ import annotations

"""Utilities for formatting Aider review comments in the workflow."""

import os
import pathlib
import re

REVIEW_HEADING = "### 📝 Aider Review"
TRUNCATION_NOTE = "\n\n_Note: The diff was truncated to approximately 60k characters for analysis._"
FALLBACK_MESSAGE = "⚠️ Aider review could not be generated automatically."

_STOP_TERMS = (
    "\ntokens:",
    "\nhere are the search/replace",
    "\nsearch/replace blocks",
    "\n```",
    "\nsummarization failed",
    "\nlitellm.",
    "\nretrying in",
    "\nthe api provider's servers are down",
    "\nmodel:",
    "\ngit repo:",
    "\nrepo-map:",
    "\nupdate git name",
    "\nupdate git email",
)

_NOISE_PREFIXES = (
    "aider v",
    "using diff",
    "reading diff",
    "diff size",
    "assistant >",
    "assistant:",
    "user >",
    "user:",
    "system >",
    "system:",
    "aider>",
    "working directory",
    "git status",
    "open an issue",
    "run with --",
    "set --model",
    "tokens used:",
    "tool error",
    "telemetry",
    "fetching update",
    "pip install",
    "to submit feedback",
    "view the diff",
    "dry run is enabled",
    "repo map",
    "repo summary",
    "warning:",
    "update git name",
    "update git email",
    "model:",
    "git repo:",
    "repo-map:",
    "scraping #",
    "initial repo scan",
    "scanning repo:",
)

_NOISE_CONTAINS = (
    "rate limit",
    "token limit",
    "ctrl-c",
    "keyboardinterrupt",
    "dry-run",
    "model context window",
    "command line args",
    "this action will not",
    "elapsed time",
    "cache size",
    "search/replace",
    "apply_patch",
    "vertexaiexception",
)

_REVIEW_START_PATTERN = re.compile(
    r"(?:^|\n)(?:###\s*📝\s*Aider\s+Review|###\s*✅\s*Summary|###\s*Summary|📝\s*Summary|\*\*\s*Summary\s*\*\*)",
    flags=re.IGNORECASE,
)


def normalize_line_endings(text: str) -> str:
    """Return ``text`` with Windows and legacy newlines replaced by ``\n``."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_spacing(text: str) -> str:
    """Collapse redundant blank lines while keeping tidy spacing around headings."""

    if not text:
        return ""

    lines = normalize_line_endings(text).split("\n")
    normalized: list[str] = []
    just_emitted_heading = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("### "):
            while normalized and normalized[-1] == "":
                normalized.pop()
            if normalized:
                normalized.append("")
            normalized.append(stripped)
            just_emitted_heading = True
            continue

        if not stripped:
            if normalized and normalized[-1] == "":
                continue
            normalized.append("")
            just_emitted_heading = False
            continue

        if just_emitted_heading:
            if not normalized or normalized[-1] != "":
                normalized.append("")
            just_emitted_heading = False

        normalized.append(line)

    while normalized and normalized[-1] == "":
        normalized.pop()

    return "\n".join(normalized)


def extract_review(raw: str) -> str:
    """Extract the human readable review content from the raw aider output."""

    if not raw:
        return ""

    candidate = normalize_line_endings(raw).strip()
    match = _REVIEW_START_PATTERN.search(candidate)
    if match:
        candidate = candidate[match.start():]

    lower = candidate.lower()
    stop_index = len(candidate)
    for term in _STOP_TERMS:
        idx = lower.find(term)
        if idx != -1 and idx < stop_index:
            stop_index = idx
    candidate = candidate[:stop_index].rstrip()

    cleaned_lines: list[str] = []
    for line in candidate.splitlines():
        stripped = line.strip()
        lower_line = stripped.lower()
        if not stripped:
            if cleaned_lines and cleaned_lines[-1] == "":
                continue
            cleaned_lines.append("")
            continue
        if any(lower_line.startswith(prefix) for prefix in _NOISE_PREFIXES):
            continue
        if any(term in lower_line for term in _NOISE_CONTAINS):
            continue
        if re.fullmatch(r"[\w./-]+\.[a-z0-9]+", lower_line):
            continue
        cleaned_lines.append(line.rstrip())

    cleaned = "\n".join(cleaned_lines).strip()
    if cleaned:
        lines = cleaned.splitlines()
        if len(lines) > 400:
            cleaned = "\n".join(lines[:400])
        return cleaned
    return candidate


def tail_lines(text: str, limit: int = 40) -> str:
    """Return the last ``limit`` lines from ``text``."""

    if limit <= 0:
        return ""
    lines = normalize_line_endings(text).splitlines()
    if len(lines) <= limit:
        return "\n".join(lines)
    return "\n".join(lines[-limit:])


def format_review_comment(*, success: bool, truncated: bool, raw_review: str, log_tail: str | None = None) -> str:
    """Build the final Markdown review comment."""

    if success:
        body = extract_review(raw_review)
        if not body.strip():
            body = raw_review.strip()
    else:
        body = FALLBACK_MESSAGE
        if log_tail:
            body += "\n\n```\n" + log_tail + "\n```"

    if not body:
        body = "Aider did not return any feedback for this pull request."

    if truncated:
        body += TRUNCATION_NOTE

    body = normalize_line_endings(body)
    content = body.lstrip()
    lowered = content.lower()
    if lowered.startswith("### 📝 aider review"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.lstrip()
    elif lowered.startswith("📝 aider review"):
        content = content.split("\n", 1)[1] if "\n" in content else ""
        content = content.lstrip()

    content = normalize_spacing(content)

    if content:
        return f"{REVIEW_HEADING}\n\n{content}"
    return REVIEW_HEADING


def main() -> None:
    review_path = pathlib.Path("aider_review_raw.txt")
    raw_review = review_path.read_text() if review_path.exists() else ""
    success = os.environ.get("AIDER_SUCCESS") == "true"
    truncated = os.environ.get("DIFF_TRUNCATED") == "true"

    log_tail = None
    if not success and raw_review:
        log_tail = tail_lines(raw_review, 40)

    comment = format_review_comment(
        success=success,
        truncated=truncated,
        raw_review=raw_review,
        log_tail=log_tail,
    )

    pathlib.Path("review_comment.md").write_text(comment + "\n")


if __name__ == "__main__":  # pragma: no cover - entrypoint
    main()