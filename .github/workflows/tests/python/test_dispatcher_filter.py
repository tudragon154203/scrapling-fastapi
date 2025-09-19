import json
from importlib import util
from pathlib import Path

import pytest

def read_github_output(github_env):
    """Helper to read outputs from GITHUB_OUTPUT file."""
    if not github_env.exists():
        return {}
    result = {}
    with github_env.open("r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                result[key] = value
    return result


DISPATCHER_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "bots" / "common" / "dispatcher_filter.py"
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
    "raw_value, expected",
    [
        ("claude,gemini,opencode", {"claude", "gemini", "opencode"}),
        ("claude; gemini; opencode", {"claude", "gemini", "opencode"}),
        ('"claude","gemini"', {"claude", "gemini"}),
        ('  "claude" ; "gemini" , aider  ', {"claude", "gemini", "aider"}),
        ("claude,,gemini; ; \n opencode\t", {"claude", "gemini", "opencode"}),
    ],
)
def test_parse_active_filter_non_json_variants(raw_value, expected):
    assert dispatcher_filter.parse_active_filter(raw_value) == expected


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




@pytest.mark.parametrize(
    "set_dispatch_event",
    [{"event_name": "pull_request", "payload": {"pull_request": {"author_association": "MEMBER", "number": 42, "title": "Update", "body": ""}}}],
    indirect=True,
)
def test_decide_for_pull_request_trusted_member(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["aider", "claude", "gemini", "opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "true"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "true"
    assert outputs["run_opencode"] == "true"
    assert outputs["target_id"] == "42"
    assert outputs["target_type"] == "pull_request"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "pull_request",
            "payload": {
                "pull_request": {
                    "author_association": "NONE",
                    "number": 99,
                    "title": "Update",
                    "body": "",
                }
            },
        }
    ],
    indirect=True,
)
def test_opencode_runs_for_pull_request_regardless_of_author(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["claude", "gemini", "opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "true"
    assert outputs["run_opencode"] == "true"


@pytest.mark.parametrize("set_dispatch_event", [{"event_name": "pull_request", "payload": {"pull_request": {"author_association": "MEMBER", "number": 1, "title": "", "body": ""}}}], indirect=True)
def test_decide_respects_active_filter(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["claude"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [{"event_name": "issue_comment", "payload": {"comment": {"author_association": "MEMBER", "body": "@claude please help"}, "issue": {"number": 7}}}],
    indirect=True,
)
def test_decide_for_issue_comment_commands(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS", '["claude", "opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "true"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"
    assert outputs["target_id"] == "7"
    assert outputs["target_type"] == "issue"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [{"event_name": "issue_comment", "payload": {"comment": {"author_association": "AUTHOR", "body": "@opencode run"}, "issue": {"number": 11}}}],
    indirect=True,
)
def test_decide_for_opencode_author_command(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_opencode"] == "true"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "AUTHOR",
                    "body": "@opencode please help",
                },
                "issue": {"number": 15},
            },
        }
    ],
    indirect=True,
)
def test_only_opencode_workflow_runs_when_active_filter_is_opencode(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_opencode"] == "true"
    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "false"
    assert outputs["run_gemini"] == "false"

