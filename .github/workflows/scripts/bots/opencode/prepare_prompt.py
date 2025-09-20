#!/usr/bin/env python3
"""Generate the opencode prompt and metadata for workflow automation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional, Tuple

PREFIXES = (
    "/opencode",
    "@opencode",
    "opencode",
    "/oc",
    "@oc",
    "oc",
)


@dataclass
class PromptContext:
    """Details about the generated prompt."""

    prompt: str
    summary: str
    command_text: Optional[str]


class WorkflowError(RuntimeError):
    """Raised when the workflow cannot continue."""


def load_event_payload(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise WorkflowError(f"Event payload file '{path}' was not found.") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"Event payload file '{path}' is not valid JSON: {exc}.") from exc


def _strip_prefix(command: str) -> Tuple[str, Optional[str]]:
    stripped = command.lstrip()
    lowered = stripped.lower()

    for prefix in PREFIXES:
        if lowered.startswith(prefix):
            remainder = stripped[len(prefix) :].lstrip(" \t:-")
            return remainder, prefix

    for prefix in PREFIXES:
        index = stripped.lower().find(prefix)
        if index >= 0:
            remainder = stripped[index + len(prefix) :].lstrip(" \t:-")
            return remainder or stripped, prefix

    return stripped, None


def _format_person(user: Optional[Dict[str, Any]]) -> str:
    if not isinstance(user, dict):
        return "unknown user"
    login = user.get("login")
    return f"@{login}" if login else "unknown user"


def build_prompt(
    event_name: str,
    payload: Dict[str, Any],
    target_type: str,
    target_id: str,
    repository: str,
) -> PromptContext:
    intro = (
        "You are the opencode CLI running inside a GitHub Actions workflow. "
        f"You have full access to the checked-out repository ({repository})."
    )

    if event_name == "pull_request":
        pr = payload.get("pull_request", {}) if isinstance(payload, dict) else {}
        title = pr.get("title", "")
        author = _format_person(pr.get("user"))
        head_ref = pr.get("head", {}).get("ref") if isinstance(pr.get("head"), dict) else None
        base_ref = pr.get("base", {}).get("ref") if isinstance(pr.get("base"), dict) else None
        body = pr.get("body", "")

        sections = [intro]
        sections.append(
            dedent(
                f"""
                Review pull request #{target_id} titled "{title}" authored by {author}.
                Base branch: {base_ref or 'unknown'}
                Head branch: {head_ref or 'unknown'}
                """
            ).strip()
        )
        if body:
            sections.append("Pull request description:\n" + body.strip())
        sections.append(
            dedent(
                """
                ### 🛑 Operational guidelines:
                - Treat this workflow as read-only; do not attempt to modify the repository or perform write operations.
                - Minimize shell or tool usage; rely on reasoning over execution and only run commands when indispensable for inspecting the code.

                Return a GitHub-ready review comment with the following structure:

                ### 🙋 OpenCode Review

                ### 👀 Findings:
                - Call out blockers, risks, or explicitly state there are none.
                - Cite relevant file paths when possible.

                ### 💡 Suggestions:
                - Provide optional follow-up actions or tests.

                ### 💯 Confidence:
                - A rating from 0-10.

                If context is missing to complete the review, explain what additional information is required instead of guessing.
                """
            ).strip()
        )
        return PromptContext(
            prompt="\n\n".join(sections).strip(),
            summary=f"Automated review of pull request #{target_id}",
            command_text=None,
        )

    if event_name in {"issue_comment", "pull_request_review_comment", "pull_request_review"}:
        comment = payload.get("comment", {}) if isinstance(payload, dict) else {}
        comment_body = str(comment.get("body", ""))
        cleaned, prefix = _strip_prefix(comment_body)
        command_text = cleaned or "Provide assistance for this discussion."
        author = _format_person(comment.get("user"))

        scope = "pull request" if target_type == "pull_request" else target_type or "discussion"
        sections = [intro]
        sections.append(
            dedent(
                f"""
                A {event_name.replace('_', ' ')} from {author} requested opencode on {scope} #{target_id}.
                Command text:
                {command_text}
                """
            ).strip()
        )
        if event_name == "pull_request_review_comment":
            path = comment.get("path")
            line = comment.get("line")
            if path:
                location = f"File: {path}"
                if line is not None:
                    location += f", Line: {line}"
                sections.append(location)
        sections.append(
            "Perform the requested work and respond with actionable results formatted for a GitHub comment."
        )

        summary = f"Command handled for {scope} #{target_id}" if target_id else "Command handled"
        if prefix:
            summary = (
                f"Command `{prefix}` handled for {scope} #{target_id}"
                if target_id
                else f"Command `{prefix}` handled"
            )
        return PromptContext(
            prompt="\n\n".join(sections).strip(),
            summary=summary,
            command_text=command_text.strip() or None,
        )

    if event_name == "issues":
        issue = payload.get("issue", {}) if isinstance(payload, dict) else {}
        title = issue.get("title", "")
        body = issue.get("body", "")
        cleaned, prefix = _strip_prefix("\n".join(filter(None, [title, body])))
        command_text = cleaned or "Help triage the issue."
        author = _format_person(issue.get("user"))
        sections = [intro]
        sections.append(
            dedent(
                f"""
                Issue #{target_id} created by {author} asked for opencode support.
                Issue title: {title}
                Request:
                {command_text}
                """
            ).strip()
        )
        sections.append("Provide guidance or next steps in Markdown form.")
        summary = f"Issue assistance for #{target_id}" if target_id else "Issue assistance"
        if prefix:
            summary = (
                f"Command `{prefix}` handled for issue #{target_id}"
                if target_id
                else f"Command `{prefix}` handled"
            )
        return PromptContext(
            prompt="\n\n".join(sections).strip(),
            summary=summary,
            command_text=command_text.strip() or None,
        )

    sections = [intro]
    sections.append(
        dedent(
            f"""
            Event `{event_name}` triggered opencode for {target_type or 'repository'} {target_id or ''}.
            Provide a helpful update summarizing any relevant information or next steps.
            """
        ).strip()
    )
    return PromptContext(
        prompt="\n\n".join(sections).strip(),
        summary=f"opencode run for {event_name}",
        command_text=None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, help="Path to the workflow event payload JSON file.")
    parser.add_argument("--prompt", required=True, help="Path where the generated prompt will be written.")
    parser.add_argument("--meta", required=True, help="Path where metadata about the run will be stored as JSON.")
    parser.add_argument("--outputs", help="Path to a file that will receive GitHub Actions outputs.")
    parser.add_argument("--event-name", required=True, help="Name of the GitHub event that triggered the workflow.")
    parser.add_argument("--target-type", default="", help="Target type associated with the workflow event.")
    parser.add_argument("--target-id", default="", help="Target identifier associated with the workflow event.")
    parser.add_argument("--model", required=True, help="Model identifier that opencode will use.")
    parser.add_argument(
        "--repository",
        default="this repository",
        help="Human-readable description of the repository for prompt context.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event_path = Path(args.event)

    try:
        payload = load_event_payload(event_path)
        context = build_prompt(
            event_name=args.event_name,
            payload=payload,
            target_type=args.target_type,
            target_id=args.target_id,
            repository=args.repository,
        )
    except WorkflowError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    prompt_path = Path(args.prompt)
    prompt_path.write_text(context.prompt, encoding="utf-8")

    model = args.model.strip()
    if not model:
        print("::error::Model identifier cannot be empty.", file=sys.stderr)
        return 1

    metadata = {
        "summary": context.summary,
        "command_text": context.command_text,
        "event_name": args.event_name,
        "target_type": args.target_type,
        "target_id": args.target_id,
        "model": model,
    }
    Path(args.meta).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.outputs:
        outputs_path = Path(args.outputs)
        with outputs_path.open("a", encoding="utf-8") as handle:
            handle.write(f"prompt_file={prompt_path}\n")
            handle.write(f"meta_file={Path(args.meta)}\n")
            handle.write(f"model={model}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
