import json
from importlib import util
from pathlib import Path

import pytest


DISPATCHER_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "common" / "python" / "dispatcher_filter.py"
)


spec = util.spec_from_file_location("dispatcher_filter", DISPATCHER_PATH)
dispatcher_filter = util.module_from_spec(spec)
assert spec.loader is not None  # for mypy/pyright type narrowing
spec.loader.exec_module(dispatcher_filter)  # type: ignore[union-attr]


def test_parse_active_filter_variants():
    json_filter = dispatcher_filter.parse_active_filter(
        json.dumps(["aider", "claude"])
    )
    assert json_filter == {"aider", "claude"}

    csv_filter = dispatcher_filter.parse_active_filter("aider, claude")
    assert csv_filter == {"aider", "claude"}

    newline_filter = dispatcher_filter.parse_active_filter("\naider\n")
    assert newline_filter == {"aider"}

    assert dispatcher_filter.parse_active_filter("") is None


@pytest.mark.parametrize(
    "active_filter, bot, expected",
    [
        (None, "aider", True),
        ({"aider"}, "aider", True),
        ({"claude"}, "aider", False),
    ],
)
def test_is_allowed(active_filter, bot, expected):
    assert dispatcher_filter.is_allowed(bot, active_filter) is expected


def run_decide(
    monkeypatch,
    tmp_path,
    *,
    event_name,
    payload,
    active_var=None,
    active_env=None,
):
    monkeypatch.delenv("ACTIVE_BOTS_VAR", raising=False)
    monkeypatch.delenv("ACTIVE_BOTS_ENV", raising=False)
    monkeypatch.delenv("EVENT_NAME", raising=False)
    monkeypatch.delenv("EVENT_PAYLOAD", raising=False)
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    if active_var is not None:
        monkeypatch.setenv("ACTIVE_BOTS_VAR", active_var)
    if active_env is not None:
        monkeypatch.setenv("ACTIVE_BOTS_ENV", active_env)

    monkeypatch.setenv("EVENT_NAME", event_name)
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

    output_path = tmp_path / "output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))

    dispatcher_filter.decide()

    result = {}
    with output_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            key, value = line.strip().split("=", 1)
            result[key] = value
    return result


def test_decide_for_pull_request_trusted_member(monkeypatch, tmp_path):
    payload = {
        "pull_request": {
            "author_association": "MEMBER",
            "number": 42,
            "title": "Update",
            "body": "",
        }
    }
    outputs = run_decide(
        monkeypatch,
        tmp_path,
        event_name="pull_request",
        payload=payload,
        active_var='["aider", "claude", "gemini", "opencode"]',
    )

    assert outputs["run_aider"] == "true"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "true"
    assert outputs["run_opencode"] == "false"
    assert outputs["target_id"] == "42"
    assert outputs["target_type"] == "pull_request"


def test_decide_respects_active_filter(monkeypatch, tmp_path):
    payload = {
        "pull_request": {
            "author_association": "MEMBER",
            "number": 1,
            "title": "",
            "body": "",
        }
    }
    outputs = run_decide(
        monkeypatch,
        tmp_path,
        event_name="pull_request",
        payload=payload,
        active_var='["claude"]',
    )

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"


def test_decide_for_issue_comment_commands(monkeypatch, tmp_path):
    payload = {
        "comment": {
            "author_association": "MEMBER",
            "body": "@claude please help",
        },
        "issue": {"number": 7},
    }
    outputs = run_decide(
        monkeypatch,
        tmp_path,
        event_name="issue_comment",
        payload=payload,
        active_env='["claude", "opencode"]',
    )

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"
    assert outputs["target_id"] == "7"
    assert outputs["target_type"] == "issue"


def test_decide_for_opencode_author_command(monkeypatch, tmp_path):
    payload = {
        "comment": {
            "author_association": "AUTHOR",
            "body": "@opencode run",
        },
        "issue": {"number": 11},
    }
    outputs = run_decide(
        monkeypatch,
        tmp_path,
        event_name="issue_comment",
        payload=payload,
        active_var='["opencode"]',
    )

    assert outputs["run_opencode"] == "true"

