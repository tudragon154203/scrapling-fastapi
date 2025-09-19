#!/usr/bin/env python3
"""Compose the GitHub comment body using opencode CLI output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


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
    sections = ["#### dY opencode CLI"]

    summary = metadata.get("summary")
    if isinstance(summary, str) and summary.strip():
        sections.append(summary.strip())

    command_text = metadata.get("command_text")
    if isinstance(command_text, str) and command_text.strip():
        safe_command = command_text.replace("\n", "<br>")
        sections.append(f"> **Command:** {safe_command}")

    if stdout:
        sections.append(stdout)
    else:
        sections.append("_The opencode CLI did not return any output._")

    meta_lines = []
    model = metadata.get("model") or "unknown"
    meta_lines.append(f"Model: `{model}`")
    event_name = metadata.get("event_name") or "unknown"
    meta_lines.append(f"Event: `{event_name}`")
    meta_lines.append(f"Exit code: `{exit_code}`")
    if exit_code != 0:
        meta_lines.append(
            "The CLI exited with a non-zero status. Review the stderr output for additional details."
        )
    if stderr:
        meta_lines.append("CLI stderr:\n```\n" + stderr + "\n```")

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
