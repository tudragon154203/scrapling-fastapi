#!/usr/bin/env python3
"""Assemble review inputs for the Qwen workflow."""

from __future__ import annotations

import os
import sys


def main() -> None:
    pr_number = os.environ.get("PR_NUMBER_INPUT", "").strip()
    pr_data = os.environ.get("PR_DATA_INPUT", "")
    additional_instructions = os.environ.get("ADDITIONAL_INSTRUCTIONS_INPUT", "")
    changed_files = os.environ.get("CHANGED_FILES_INPUT", "")

    if not pr_number:
        print("No pull request identified for review.")
        sys.exit(1)

    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise RuntimeError("GITHUB_OUTPUT is not set")

    with open(output_path, "a", encoding="utf-8") as github_output:
        github_output.write(f"pr_number={pr_number}\n")

        if "\n" in pr_data:
            github_output.write("pr_data<<EOF\n")
            github_output.write(f"{pr_data}\nEOF\n")
        else:
            github_output.write(f"pr_data={pr_data}\n")

        if "\n" in additional_instructions:
            github_output.write("additional_instructions<<EOF\n")
            github_output.write(f"{additional_instructions}\nEOF\n")
        else:
            github_output.write(f"additional_instructions={additional_instructions}\n")

        github_output.write("changed_files<<EOF\n")
        if changed_files:
            github_output.write(f"{changed_files}\n")
        github_output.write("EOF\n")


if __name__ == "__main__":
    main()
