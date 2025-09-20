# dispatcher_filter.py
# This script determines which bots (Aider, Claude, Gemini, Opencode) should run based on GitHub event triggers
# and active bot filters. It outputs GitHub Action variables for conditional workflow execution.
# It reads environment variables set by the main.yml workflow:
# - ACTIVE_BOTS_VAR: Comma-separated or JSON list of active bots (e.g., "claude,gemini")
# - EVENT_NAME: The GitHub event name (e.g., "pull_request", "issue_comment")
# - EVENT_PAYLOAD: JSON string of the full event payload
#
# Outputs:
# - run_aider: "true" or "false"
# - run_claude: "true" or "false"
# - run_gemini: "true" or "false"
# - run_opencode: "true" or "false"
# - target_id: PR or issue number
# - target_type: "pull_request" or "issue"

import csv
import json
import os
import re
from dataclasses import dataclass
from io import StringIO
from typing import Callable, Iterable, Optional, Sequence, Set


def _normalize_candidates(items: Iterable[object]) -> Set[str]:
    # Normalize a list of items to lowercase, stripped strings, removing empty ones
    normalized = set()
    for item in items:
        text = str(item).strip().lower()
        if text:
            normalized.add(text)
    return normalized


def _strip_enclosing_quotes(value: str) -> str:
    """Remove matching single or double quotes surrounding a value."""

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _parse_sequence_from_string(raw_value: str) -> Sequence[str]:
    """Parse a non-JSON string into a sequence of candidate names."""

    if not raw_value:
        return []

    replaced = raw_value.replace(";", ",")
    reader = csv.reader(StringIO(replaced))
    tokens = []
    for row in reader:
        tokens.extend(row)

    cleaned = []
    for token in tokens:
        if not token:
            continue
        stripped = token.strip()
        if not stripped:
            continue
        normalized = _strip_enclosing_quotes(stripped)
        if normalized:
            cleaned.append(normalized)

    if cleaned:
        return cleaned

    fallback = []
    for token in re.split(r"[\s,;]+", raw_value):
        stripped = token.strip()
        if not stripped:
            continue
        normalized = _strip_enclosing_quotes(stripped)
        if normalized:
            fallback.append(normalized)

    return fallback


def parse_active_filter(raw_value: str) -> Optional[Set[str]]:
    # Parse the active bots filter from environment variable.
    # Supports comma-separated strings or JSON lists/objects.
    if not raw_value:
        return None

    raw_value = raw_value.strip()
    if not raw_value:
        return None

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        # Fallback to parsing with CSV/regex heuristics
        return _normalize_candidates(_parse_sequence_from_string(raw_value))

    if isinstance(parsed, list):
        return _normalize_candidates(parsed)

    if isinstance(parsed, str):
        return _normalize_candidates([parsed])

    # For other types, treat as single item
    return _normalize_candidates([parsed])


def is_allowed(bot: str, active_filter: Optional[Set[str]]) -> bool:
    # Check if a bot is allowed to run based on the active filter
    if active_filter is None:
        return True
    return bot in active_filter


# Trusted user roles for triggering bots. All bots follow the Opencode
# standard: pull requests and interactive events are limited to trusted
# members.
TRUSTED_MEMBERS = {"OWNER", "COLLABORATOR", "MEMBER"}

# Prefixes that trigger specific bots in comments or bodies
AIDER_PREFIXES = ("@aider", "AIDER", "/aider")
CLAUDE_PREFIXES = ("@claude", "CLAUDE", "/claude")
GEMINI_PREFIXES = ("GEMINI", "@gemini", "@gemini-cli", "/gemini")
OPENCODE_PREFIXES = ("@opencode", "OPENCODE", "/opencode")

BOT_PREFIXES = {
    "aider": AIDER_PREFIXES,
    "claude": CLAUDE_PREFIXES,
    "gemini": GEMINI_PREFIXES,
    "opencode": OPENCODE_PREFIXES,
}


def get(payload: dict, *keys):
    # Safely get nested value from payload dict
    data = payload
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def text(value) -> str:
    # Convert value to string or empty string
    if value is None:
        return ""
    return str(value)


def startswith_any(value: str, prefixes) -> bool:
    # Check if value starts with any prefix
    return any(value.startswith(prefix) for prefix in prefixes)


def contains_any(value: str, substrings) -> bool:
    # Check if value contains any substring
    return any(sub in value for sub in substrings)


@dataclass(frozen=True)
class InteractionDetails:
    association: str
    texts: Sequence[str]
    matcher: Callable[[str, Sequence[str]], bool]


def _build_interaction_details(
    event_name: str, payload: dict
) -> Optional[InteractionDetails]:
    """Build details for interactive events that may trigger bots."""

    if event_name == "issue_comment":
        return InteractionDetails(
            association=text(get(payload, "comment", "author_association")),
            texts=[text(get(payload, "comment", "body"))],
            matcher=startswith_any,
        )

    if event_name == "pull_request_review_comment":
        return InteractionDetails(
            association=text(get(payload, "comment", "author_association")),
            texts=[text(get(payload, "comment", "body"))],
            matcher=startswith_any,
        )

    if event_name == "pull_request_review":
        return InteractionDetails(
            association=text(get(payload, "review", "author_association")),
            texts=[text(get(payload, "review", "body"))],
            matcher=startswith_any,
        )

    if event_name == "issues":
        return InteractionDetails(
            association=text(get(payload, "issue", "author_association")),
            texts=[
                text(get(payload, "issue", "body")),
                text(get(payload, "issue", "title")),
            ],
            matcher=contains_any,
        )

    return None


def _should_run_interactive_bot(
    prefixes: Sequence[str], details: Optional[InteractionDetails]
) -> bool:
    """Return True when an interactive event should trigger a bot."""

    if details is None:
        return False

    if details.association not in TRUSTED_MEMBERS:
        return False

    return any(
        details.matcher(candidate, prefixes)
        for candidate in details.texts
        if candidate
    )


def write_output(name: str, value: str) -> None:
    # Write output variable for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def decide() -> None:
    # Main logic to decide which bots run and extract target info
    active_var = (os.environ.get("ACTIVE_BOTS_VAR") or "").strip()
    active_filter = parse_active_filter(active_var)

    event_name = os.environ.get("EVENT_NAME") or ""
    payload = json.loads(os.environ.get("EVENT_PAYLOAD") or "{}")

    interactive_details = _build_interaction_details(event_name, payload)

    should_run_flags = {bot: False for bot in BOT_PREFIXES}

    if event_name == "pull_request":
        pr_association = text(get(payload, "pull_request", "author_association"))
        for bot in should_run_flags:
            if is_allowed(bot, active_filter):
                should_run_flags[bot] = pr_association in TRUSTED_MEMBERS
    else:
        for bot, prefixes in BOT_PREFIXES.items():
            if is_allowed(bot, active_filter):
                should_run_flags[bot] = _should_run_interactive_bot(
                    prefixes, interactive_details
                )

    # Output the decisions for GitHub Actions to use in conditional jobs
    write_output("run_aider", "true" if should_run_flags["aider"] else "false")
    write_output("run_claude", "true" if should_run_flags["claude"] else "false")
    write_output("run_gemini", "true" if should_run_flags["gemini"] else "false")
    write_output("run_opencode", "true" if should_run_flags["opencode"] else "false")

    # Export active filter outputs
    if active_filter is None:
        active_filter_str = "all (no restrictions)"
        active_filter_json_str = json.dumps([])
    else:
        active_filter_list = sorted(active_filter)
        active_filter_str = ",".join(active_filter_list)
        active_filter_json_str = json.dumps(active_filter_list)

    write_output("active_filter", active_filter_str)
    write_output("active_filter_json", active_filter_json_str)

    print(f"  - run_aider: {'true' if should_run_flags['aider'] else 'false'}")
    print(f"  - run_claude: {'true' if should_run_flags['claude'] else 'false'}")
    print(f"  - run_gemini: {'true' if should_run_flags['gemini'] else 'false'}")
    print(f"  - run_opencode: {'true' if should_run_flags['opencode'] else 'false'}")

    # Extract target ID and type for the event (PR or issue number)
    target_id = ""
    target_type = ""

    pr_payload = get(payload, "pull_request")
    if isinstance(pr_payload, dict):
        target_id = str(pr_payload.get("number") or "")
        if target_id:
            target_type = "pull_request"

    if not target_id:
        issue_payload = get(payload, "issue")
        if isinstance(issue_payload, dict):
            target_id = str(issue_payload.get("number") or "")
            if target_id:
                target_type = "issue"

    write_output("target_id", target_id)
    write_output("target_type", target_type)


if __name__ == "__main__":
    decide()
