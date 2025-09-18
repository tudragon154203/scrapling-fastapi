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
