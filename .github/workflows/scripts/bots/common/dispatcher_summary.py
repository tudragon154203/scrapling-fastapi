"""Generate GitHub Actions job summary for bot dispatcher decisions."""

from __future__ import annotations

import os
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

BOT_ENV_VARS = (
    ("Aider", "RUN_AIDER"),
    ("Claude", "RUN_CLAUDE"),
    ("Gemini", "RUN_GEMINI"),
    ("Opencode", "RUN_OPENCODE"),
)


def normalize_bool(value: str) -> bool:
    """Interpret dispatcher flag values coming from environment variables.

    GitHub Actions exposes all environment variables as strings, so the
    dispatcher-specific flags arrive as stringified booleans such as ``"true"``
    or ``"false"``.  This helper normalizes those values (case- and
    whitespace-insensitively) so the rest of the module can reason about them as
    plain ``bool`` objects.
    """

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
    target_type: Optional[str],
    target_id: Optional[str],
    event_name: Optional[str],
) -> List[str]:
    """Build the list of summary lines for the dispatcher job.

    ``target_type``, ``target_id`` and ``event_name`` may not be available for
    every triggering event, so the formatter is defensive about absent values
    and only renders metadata that is both present and meaningful.
    """

    lines: List[str] = ["## Bot workflow dispatch summary", ""]

    lines.append(f"**{summarize_active_filter(active_filter_json)}**")

    triggered: List[str] = []
    skipped: List[str] = []
    for name, should_run in statuses:
        (triggered if should_run else skipped).append(name)

    triggered_count = len(triggered)
    skipped_count = len(skipped)
    total_count = triggered_count + skipped_count

    if total_count:
        lines.append(
            f"**Decisions:** {triggered_count} triggered · {skipped_count} skipped"
        )
        lines.append("")
        lines.extend(["| Workflow | Decision |", "| --- | --- |"])

        for name in triggered:
            decision = "Triggered"
            emoji = "✅"
            lines.append(f"| {emoji} {name} | {decision} |")

        for name in skipped:
            decision = "Skipped"
            emoji = "⛔"
            lines.append(f"| {emoji} {name} | {decision} |")
    else:
        lines.append("**No workflows evaluated.**")

    metadata: List[str] = []
    clean_target_type = (target_type or "").strip()
    clean_target_id = (target_id or "").strip()
    clean_event_name = (event_name or "").strip()

    if clean_target_type and clean_target_id:
        metadata.append(f"**Target:** {clean_target_type} #{clean_target_id}")
    elif clean_target_type:
        metadata.append(f"**Target:** {clean_target_type}")
    elif clean_target_id:
        metadata.append(f"**Target ID:** #{clean_target_id}")

    if clean_event_name:
        metadata.append(f"**Event:** {clean_event_name}")

    if metadata:
        lines.extend(["", *metadata])

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
