#!/usr/bin/env python3
"""Utility to gather PR context for comment-triggered Qwen reviews."""

from __future__ import annotations

import json
import os
import subprocess
import sys


def run_gh_command(args: list[str]) -> str:
    """Run a GitHub CLI command and return its stdout without trailing newlines."""
    try:
        return subprocess.check_output(args, text=True).rstrip("\n")
    except subprocess.CalledProcessError as exc:  # pragma: no cover - surfaced in workflow log
        raise RuntimeError(f"Command failed: {' '.join(args)}") from exc


def main() -> None:
    event_name = os.environ.get("EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set")

    with open(event_path, encoding="utf-8") as payload_file:
        payload = json.load(payload_file)

    if event_name == "issue_comment":
        pr_number = payload["issue"]["number"]
        raw_body = payload.get("comment", {}).get("body", "")
    elif event_name == "pull_request_review_comment":
        pr_number = payload["pull_request"]["number"]
        raw_body = payload.get("comment", {}).get("body", "")
    elif event_name == "pull_request_review":
        pr_number = payload["pull_request"]["number"]
        raw_body = payload.get("review", {}).get("body", "")
    else:
        print("Unsupported event", file=sys.stderr)
        sys.exit(1)

    trigger = "@qwen /review"
    additional_instructions = ""
    if raw_body and trigger in raw_body:
        additional_instructions = raw_body.split(trigger, 1)[1].strip()

    pr_number_str = str(pr_number)

    pr_data = run_gh_command(
        [
            "gh",
            "pr",
            "view",
            pr_number_str,
            "--json",
            "title,body,additions,deletions,changedFiles,baseRefName,headRefName",
        ]
    )

    changed_files = run_gh_command([
        "gh",
        "pr",
        "diff",
        pr_number_str,
        "--name-only",
    ])

    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise RuntimeError("GITHUB_OUTPUT is not set")

    with open(output_path, "a", encoding="utf-8") as github_output:
        github_output.write(f"pr_number={pr_number_str}\n")

        if "\n" in additional_instructions:
            github_output.write("additional_instructions<<EOF\n")
            github_output.write(f"{additional_instructions}\nEOF\n")
        else:
            github_output.write(f"additional_instructions={additional_instructions}\n")

        if "\n" in pr_data:
            github_output.write("pr_data<<EOF\n")
            github_output.write(f"{pr_data}\nEOF\n")
        else:
            github_output.write(f"pr_data={pr_data}\n")

        github_output.write("changed_files<<EOF\n")
        if changed_files:
            github_output.write(f"{changed_files}\n")
        github_output.write("EOF\n")


if __name__ == "__main__":
    main()
