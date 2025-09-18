import json
import os
from typing import Iterable, Optional, Set


def _normalize_candidates(items: Iterable[object]) -> Set[str]:
    normalized = set()
    for item in items:
        text = str(item).strip().lower()
        if text:
            normalized.add(text)
    return normalized


def parse_active_filter(raw_value: str) -> Optional[Set[str]]:
    if not raw_value:
        return None

    raw_value = raw_value.strip()
    if not raw_value:
        return None

    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return _normalize_candidates(part for part in raw_value.split(","))

    if isinstance(parsed, list):
        return _normalize_candidates(parsed)

    if isinstance(parsed, str):
        return _normalize_candidates([parsed])

    return _normalize_candidates([parsed])


def is_allowed(bot: str, active_filter: Optional[Set[str]]) -> bool:
    if active_filter is None:
        return True
    return bot in active_filter


TRUSTED_MEMBERS = {"OWNER", "COLLABORATOR", "MEMBER"}
TRUSTED_WITH_AUTHOR = TRUSTED_MEMBERS | {"AUTHOR"}

CLAUDE_PREFIXES = ("@claude", "CLAUDE", "/claude")
GEMINI_PREFIXES = ("Gemini", "GEMINI", "@gemini", "@gemini-cli", "/gemini")
OPENCODE_PREFIXES = ("@opencode", "OPENCODE", "/opencode")


def get(payload: dict, *keys):
    data = payload
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def text(value) -> str:
    return value or ""


def startswith_any(value: str, prefixes) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def contains_any(value: str, substrings) -> bool:
    return any(sub in value for sub in substrings)


def write_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def decide() -> None:
    active_var = (os.environ.get("ACTIVE_BOTS_VAR") or "").strip()
    active_env = (os.environ.get("ACTIVE_BOTS_ENV") or "").strip()
    active_filter = parse_active_filter(active_var or active_env)

    event_name = os.environ.get("EVENT_NAME") or ""
    payload = json.loads(os.environ.get("EVENT_PAYLOAD") or "{}")

    aider_should_run = False
    if is_allowed("aider", active_filter) and event_name == "pull_request":
        assoc = text(get(payload, "pull_request", "author_association"))
        aider_should_run = assoc in TRUSTED_MEMBERS

    claude_should_run = False
    if is_allowed("claude", active_filter):
        if event_name == "pull_request":
            claude_should_run = True
        elif event_name == "issue_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            claude_should_run = assoc in TRUSTED_MEMBERS and startswith_any(body, CLAUDE_PREFIXES)
        elif event_name == "pull_request_review_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            claude_should_run = assoc in TRUSTED_MEMBERS and startswith_any(body, CLAUDE_PREFIXES)
        elif event_name == "pull_request_review":
            assoc = text(get(payload, "review", "author_association"))
            body = text(get(payload, "review", "body"))
            claude_should_run = assoc in TRUSTED_MEMBERS and startswith_any(body, CLAUDE_PREFIXES)
        elif event_name == "issues":
            assoc = text(get(payload, "issue", "author_association"))
            issue_body = text(get(payload, "issue", "body"))
            title = text(get(payload, "issue", "title"))
            claude_should_run = assoc in TRUSTED_MEMBERS and (
                contains_any(issue_body, CLAUDE_PREFIXES) or contains_any(title, CLAUDE_PREFIXES)
            )

    gemini_should_run = False
    if is_allowed("gemini", active_filter):
        if event_name == "pull_request":
            gemini_should_run = True
        elif event_name == "issue_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            gemini_should_run = assoc in TRUSTED_MEMBERS and startswith_any(body, GEMINI_PREFIXES)
        elif event_name == "pull_request_review_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            gemini_should_run = assoc in TRUSTED_MEMBERS and startswith_any(body, GEMINI_PREFIXES)

    opencode_should_run = False
    if is_allowed("opencode", active_filter):
        if event_name == "issue_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            opencode_should_run = assoc in TRUSTED_WITH_AUTHOR and startswith_any(body, OPENCODE_PREFIXES)
        elif event_name == "pull_request_review_comment":
            assoc = text(get(payload, "comment", "author_association"))
            body = text(get(payload, "comment", "body"))
            opencode_should_run = assoc in TRUSTED_WITH_AUTHOR and startswith_any(body, OPENCODE_PREFIXES)
        elif event_name == "pull_request_review":
            assoc = text(get(payload, "review", "author_association"))
            body = text(get(payload, "review", "body"))
            opencode_should_run = assoc in TRUSTED_WITH_AUTHOR and startswith_any(body, OPENCODE_PREFIXES)
        elif event_name == "pull_request":
            assoc = text(get(payload, "pull_request", "author_association"))
            pr_body = text(get(payload, "pull_request", "body"))
            title = text(get(payload, "pull_request", "title"))
            opencode_should_run = assoc in TRUSTED_WITH_AUTHOR and (
                contains_any(pr_body, OPENCODE_PREFIXES) or contains_any(title, OPENCODE_PREFIXES)
            )
        elif event_name == "issues":
            assoc = text(get(payload, "issue", "author_association"))
            issue_body = text(get(payload, "issue", "body"))
            title = text(get(payload, "issue", "title"))
            opencode_should_run = assoc in TRUSTED_WITH_AUTHOR and (
                contains_any(issue_body, OPENCODE_PREFIXES) or contains_any(title, OPENCODE_PREFIXES)
            )

    write_output("run_aider", "true" if aider_should_run else "false")
    write_output("run_claude", "true" if claude_should_run else "false")
    write_output("run_gemini", "true" if gemini_should_run else "false")
    write_output("run_opencode", "true" if opencode_should_run else "false")

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
