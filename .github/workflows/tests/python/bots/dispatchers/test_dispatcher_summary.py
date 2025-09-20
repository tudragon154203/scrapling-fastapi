"""Tests for the dispatcher summary GitHub Action helper script."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

WORKFLOWS_DIR = next(
    parent for parent in Path(__file__).resolve().parents if parent.name == "workflows"
)
SCRIPT_PATH = (
    WORKFLOWS_DIR / "scripts" / "bots" / "common" / "dispatcher_summary.py"
)
MODULE = runpy.run_path(str(SCRIPT_PATH))


@pytest.mark.parametrize(
    "raw_filter, expected",
    [
        ("", "Active bots filter: all (no restrictions)."),
        ("[]", "Active bots filter: none (all bots disabled)."),
        ("  []  ", "Active bots filter: none (all bots disabled)."),
        (
            "[\"aider\", \"claude\"]",
            "Active bots filter: [\"aider\", \"claude\"]",
        ),
    ],
)
def test_summarize_active_filter_variants(raw_filter: str, expected: str) -> None:
    summarize = MODULE["summarize_active_filter"]
    assert summarize(raw_filter) == expected


def test_build_summary_lines_groups_triggered_and_skipped() -> None:
    build_lines = MODULE["build_summary_lines"]
    lines = build_lines(
        active_filter_json="[\"gemini\"]",
        statuses=[
            ("Aider", False),
            ("Claude", True),
            ("Gemini", True),
            ("Opencode", False),
        ],
        target_type="pull_request",
        target_id="123",
        event_name="pull_request",
    )

    assert lines == [
        "## Bot workflow dispatch summary",
        "",
        "**Active bots filter: [\"gemini\"]**",
        "**Decisions:** 2 triggered · 2 skipped",
        "",
        "| Workflow | Decision |",
        "| --- | --- |",
        "| ✅ Claude | Triggered |",
        "| ✅ Gemini | Triggered |",
        "| ⛔ Aider | Skipped |",
        "| ⛔ Opencode | Skipped |",
        "",
        "**Target:** pull_request #123",
        "**Event:** pull_request",
    ]


def test_build_summary_lines_handles_all_skipped() -> None:
    build_lines = MODULE["build_summary_lines"]
    lines = build_lines(
        active_filter_json="",
        statuses=[
            ("Aider", False),
            ("Claude", False),
        ],
        target_type="",
        target_id="",
        event_name="issue_comment",
    )

    assert lines == [
        "## Bot workflow dispatch summary",
        "",
        "**Active bots filter: all (no restrictions).**",
        "**Decisions:** 0 triggered · 2 skipped",
        "",
        "| Workflow | Decision |",
        "| --- | --- |",
        "| ⛔ Aider | Skipped |",
        "| ⛔ Claude | Skipped |",
        "",
        "**Event:** issue_comment",
    ]


def test_main_writes_summary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    summary_file = tmp_path / "summary.md"

    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    monkeypatch.setenv("ACTIVE_FILTER_JSON", "")
    monkeypatch.setenv("RUN_AIDER", "true")
    monkeypatch.setenv("RUN_CLAUDE", "false")
    monkeypatch.setenv("RUN_GEMINI", "false")
    monkeypatch.setenv("RUN_OPENCODE", "true")
    monkeypatch.setenv("TARGET_TYPE", "issue")
    monkeypatch.setenv("TARGET_ID", "77")
    monkeypatch.setenv("EVENT_NAME", "issues")

    MODULE["main"]()

    assert summary_file.read_text(encoding="utf-8") == (
        "## Bot workflow dispatch summary\n"
        "\n"
        "**Active bots filter: all (no restrictions).**\n"
        "**Decisions:** 2 triggered · 2 skipped\n"
        "\n"
        "| Workflow | Decision |\n"
        "| --- | --- |\n"
        "| ✅ Aider | Triggered |\n"
        "| ✅ Opencode | Triggered |\n"
        "| ⛔ Claude | Skipped |\n"
        "| ⛔ Gemini | Skipped |\n"
        "\n"
        "**Target:** issue #77\n"
        "**Event:** issues\n"
    )


def test_build_summary_lines_handles_no_statuses() -> None:
    build_lines = MODULE["build_summary_lines"]
    lines = build_lines(
        active_filter_json="",
        statuses=[],
        target_type="",
        target_id="",
        event_name="",
    )

    assert lines == [
        "## Bot workflow dispatch summary",
        "",
        "**Active bots filter: all (no restrictions).**",
        "**No workflows evaluated.**",
    ]


def test_build_summary_lines_trims_and_partially_renders_metadata() -> None:
    build_lines = MODULE["build_summary_lines"]
    lines = build_lines(
        active_filter_json="",
        statuses=[("Claude", True)],
        target_type="  issue  ",
        target_id="  ",
        event_name=" comment ",
    )

    assert lines[-2:] == ["**Target:** issue", "**Event:** comment"]

    lines = build_lines(
        active_filter_json="",
        statuses=[("Claude", True)],
        target_type=None,
        target_id="123",
        event_name=None,
    )

    assert lines[-1:] == ["**Target ID:** #123"]


def test_write_summary_handles_missing_path() -> None:
    write_summary = MODULE["write_summary"]
    # Should not raise when the path is empty and the iterator is consumed lazily
    write_summary("", iter(["ignored"]))
