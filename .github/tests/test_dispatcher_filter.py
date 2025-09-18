from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

MODULE_PATH = pathlib.Path(
    ".github/workflows/scripts/common/python/dispatcher_filter.py"
)


@pytest.fixture(scope="session")
def dispatcher_module():
    spec = importlib.util.spec_from_file_location("dispatcher_filter", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_dispatcher(
    dispatcher_module,
    monkeypatch,
    tmp_path,
    *,
    event_name: str,
    payload: dict,
    active_var: str | None = "",
    active_env: str | None = "",
):
    github_output = tmp_path / "out.txt"
    if github_output.exists():
        github_output.unlink()

    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

    if active_var is None:
        monkeypatch.delenv("ACTIVE_BOTS_VAR", raising=False)
    else:
        monkeypatch.setenv("ACTIVE_BOTS_VAR", active_var)

    if active_env is None:
        monkeypatch.delenv("ACTIVE_BOTS_ENV", raising=False)
    else:
        monkeypatch.setenv("ACTIVE_BOTS_ENV", active_env)

    monkeypatch.setenv("EVENT_NAME", event_name)
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

    dispatcher_module.decide()

    output = github_output.read_text(encoding="utf-8").strip()
    if not output:
        return {}
    return dict(line.split("=", 1) for line in output.splitlines())


def test_parse_active_filter_handles_multiple_formats(dispatcher_module):
    parse_active_filter = dispatcher_module.parse_active_filter

    assert parse_active_filter("claude, GEMINI , ") == {"claude", "gemini"}
    assert parse_active_filter('["Claude", "Opencode"]') == {"claude", "opencode"}
    assert parse_active_filter("   ") is None


def test_is_allowed_respects_active_filter(dispatcher_module):
    is_allowed = dispatcher_module.is_allowed

    active_filter = {"claude"}
    assert is_allowed("claude", active_filter)
    assert not is_allowed("gemini", active_filter)
    assert is_allowed("gemini", None)


def test_decide_for_pull_request_trusted_member(monkeypatch, tmp_path, dispatcher_module):
    decide = dispatcher_module.decide

    github_output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.setenv("ACTIVE_BOTS_VAR", "aider,claude,gemini,opencode")
    monkeypatch.setenv("EVENT_NAME", "pull_request")
    payload = {
        "pull_request": {
            "number": 42,
            "author_association": "MEMBER",
            "title": "Add feature",
            "body": "Please review",
        }
    }
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

    decide()

    output = github_output.read_text(encoding="utf-8").strip().splitlines()
    result = dict(line.split("=", 1) for line in output)

    assert result["run_aider"] == "true"
    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "true"
    assert result["run_opencode"] == "false"
    assert result["target_id"] == "42"
    assert result["target_type"] == "pull_request"


def test_decide_for_issue_comment_with_claude_prefix(monkeypatch, tmp_path, dispatcher_module):
    decide = dispatcher_module.decide

    github_output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.setenv("ACTIVE_BOTS_ENV", "claude,opencode")
    monkeypatch.setenv("EVENT_NAME", "issue_comment")
    payload = {
        "issue": {"number": 101},
        "comment": {
            "author_association": "COLLABORATOR",
            "body": "@claude please help",
        },
    }
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

    decide()

    output = github_output.read_text(encoding="utf-8").strip().splitlines()
    result = dict(line.split("=", 1) for line in output)

    assert result["run_aider"] == "false"
    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
    assert result["target_id"] == "101"
    assert result["target_type"] == "issue"


def test_decide_for_issue_with_opencode_keyword(monkeypatch, tmp_path, dispatcher_module):
    decide = dispatcher_module.decide

    github_output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))
    monkeypatch.setenv("ACTIVE_BOTS_ENV", "opencode")
    monkeypatch.setenv("EVENT_NAME", "issues")
    payload = {
        "issue": {
            "number": 7,
            "author_association": "AUTHOR",
            "title": "Add support for /opencode runs",
            "body": "This issue mentions @opencode for assistance.",
        }
    }
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

    decide()

    output = github_output.read_text(encoding="utf-8").strip().splitlines()
    result = dict(line.split("=", 1) for line in output)

    assert result["run_aider"] == "false"
    assert result["run_claude"] == "false"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "true"
    assert result["target_id"] == "7"
    assert result["target_type"] == "issue"


def test_claude_runs_for_pull_request_review(monkeypatch, tmp_path, dispatcher_module):
    payload = {
        "review": {
            "author_association": "MEMBER",
            "body": "@claude take a look",
        },
        "pull_request": {"number": 13, "author_association": "MEMBER"},
    }
    result = run_dispatcher(
        dispatcher_module,
        monkeypatch,
        tmp_path,
        event_name="pull_request_review",
        payload=payload,
        active_var="claude,gemini",
    )

    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
    assert result["run_aider"] == "false"


@pytest.mark.parametrize(
    "bot_name", ["claude", "gemini"],
)
def test_pull_request_review_comment_prefixes(monkeypatch, tmp_path, dispatcher_module, bot_name):
    prefix = "@claude" if bot_name == "claude" else "@gemini"
    payload = {
        "comment": {
            "author_association": "COLLABORATOR",
            "body": f"{prefix} please review",
        },
        "pull_request": {"number": 99, "author_association": "MEMBER"},
    }
    result = run_dispatcher(
        dispatcher_module,
        monkeypatch,
        tmp_path,
        event_name="pull_request_review_comment",
        payload=payload,
        active_var="claude,gemini",
    )

    expected_key = f"run_{bot_name}"
    other_key = "run_claude" if bot_name == "gemini" else "run_gemini"

    assert result[expected_key] == "true"
    assert result[other_key] == "false"
    assert result["run_opencode"] == "false"
    assert result["run_aider"] == "false"


def test_active_bots_var_takes_precedence(monkeypatch, tmp_path, dispatcher_module):
    payload = {
        "pull_request": {
            "number": 5,
            "author_association": "MEMBER",
            "title": "Testing precedence",
            "body": "",
        }
    }
    result = run_dispatcher(
        dispatcher_module,
        monkeypatch,
        tmp_path,
        event_name="pull_request",
        payload=payload,
        active_var="claude",
        active_env="claude,gemini",
    )

    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
