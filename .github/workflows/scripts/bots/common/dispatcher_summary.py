"""Generate GitHub Actions job summary for bot dispatcher decisions."""

from __future__ import annotations

import os
from typing import Iterable, List, Mapping, Sequence, Tuple

BOT_ENV_VARS = (
    ("Aider", "RUN_AIDER"),
    ("Claude", "RUN_CLAUDE"),
    ("Gemini", "RUN_GEMINI"),
    ("Opencode", "RUN_OPENCODE"),
)


def normalize_bool(value: str) -> bool:
    """Return ``True`` when ``value`` represents a truthy dispatcher flag."""

    return str(value).strip().lower() == "true"


def summarize_active_filter(raw_filter: str) -> str:
    """Generate the summary line describing the active bots filter."""

    if not raw_filter:
        return "Active bots filter: all (no restrictions)."

    if raw_filter.strip() == "[]":
        return "Active bots filter: none (all bots disabled)."

    return f"Active bots filter: {raw_filter}"


def build_summary_lines(
    active_filter_json: str,
    statuses: Sequence[Tuple[str, bool]],
    target_type: str,
    target_id: str,
    event_name: str,
) -> List[str]:
    """Build the list of summary lines for the dispatcher job."""

    lines: List[str] = [
        summarize_active_filter(active_filter_json),
        "",
        "### Workflow dispatch results",
        "",
    ]

    triggered = [name for name, should_run in statuses if should_run]
    skipped = [name for name, should_run in statuses if not should_run]

    if triggered:
        lines.append("#### Triggered workflows")
        lines.extend(f"- ✅ {name}" for name in triggered)
    else:
        lines.append("No workflows were triggered.")

    if skipped:
        if triggered or (lines and lines[-1] != ""):
            lines.append("")
        lines.append("#### Skipped workflows")
        lines.extend(f"- ⛔ {name}" for name in skipped)

    if target_type and target_id:
        lines.extend(["", f"Target: {target_type} #{target_id}"])

    if event_name:
        lines.append(f"Event: {event_name}")

    return lines


def gather_statuses(env: Mapping[str, str]) -> List[Tuple[str, bool]]:
    """Collect dispatcher statuses for each bot from ``env``."""

    statuses: List[Tuple[str, bool]] = []
    for label, var_name in BOT_ENV_VARS:
        statuses.append((label, normalize_bool(env.get(var_name, ""))))
    return statuses


def write_summary(path: str, lines: Iterable[str]) -> None:
    """Append ``lines`` to the GitHub Actions summary file when ``path`` is set."""

    if not path:
        return

    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def main() -> None:
    env = os.environ

    summary_lines = build_summary_lines(
        active_filter_json=env.get("ACTIVE_FILTER_JSON", ""),
        statuses=gather_statuses(env),
        target_type=env.get("TARGET_TYPE", ""),
        target_id=env.get("TARGET_ID", ""),
        event_name=env.get("EVENT_NAME", ""),
    )

    write_summary(env.get("GITHUB_STEP_SUMMARY", ""), summary_lines)


if __name__ == "__main__":  # pragma: no cover - direct script execution entry point
    main()
