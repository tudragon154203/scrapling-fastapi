from __future__ import annotations

import pytest


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


def test_decide_for_pull_request_trusted_member(run_dispatcher):
    payload = {
        "pull_request": {
            "number": 42,
            "author_association": "MEMBER",
            "title": "Add feature",
            "body": "Please review",
        }
    }
    result = run_dispatcher(
        event_name="pull_request",
        payload=payload,
        active_var="aider,claude,gemini,opencode",
    )

    assert result["run_aider"] == "true"
    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "true"
    assert result["run_opencode"] == "false"
    assert result["target_id"] == "42"
    assert result["target_type"] == "pull_request"


def test_decide_for_issue_comment_with_claude_prefix(run_dispatcher):
    payload = {
        "issue": {"number": 101},
        "comment": {
            "author_association": "COLLABORATOR",
            "body": "@claude please help",
        },
    }
    result = run_dispatcher(
        event_name="issue_comment",
        payload=payload,
        active_env="claude,opencode",
    )

    assert result["run_aider"] == "false"
    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
    assert result["target_id"] == "101"
    assert result["target_type"] == "issue"


def test_decide_for_issue_with_opencode_keyword(run_dispatcher):
    payload = {
        "issue": {
            "number": 7,
            "author_association": "AUTHOR",
            "title": "Add support for /opencode runs",
            "body": "This issue mentions @opencode for assistance.",
        }
    }
    result = run_dispatcher(
        event_name="issues",
        payload=payload,
        active_env="opencode",
    )

    assert result["run_aider"] == "false"
    assert result["run_claude"] == "false"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "true"
    assert result["target_id"] == "7"
    assert result["target_type"] == "issue"


def test_claude_runs_for_pull_request_review(run_dispatcher):
    payload = {
        "review": {
            "author_association": "MEMBER",
            "body": "@claude take a look",
        },
        "pull_request": {"number": 13, "author_association": "MEMBER"},
    }
    result = run_dispatcher(
        event_name="pull_request_review",
        payload=payload,
        active_var="claude,gemini",
    )

    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
    assert result["run_aider"] == "false"


@pytest.mark.parametrize("bot_name", ["claude", "gemini"])
def test_pull_request_review_comment_prefixes(run_dispatcher, bot_name):
    prefix = "@claude" if bot_name == "claude" else "@gemini"
    payload = {
        "comment": {
            "author_association": "COLLABORATOR",
            "body": f"{prefix} please review",
        },
        "pull_request": {"number": 99, "author_association": "MEMBER"},
    }
    result = run_dispatcher(
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


def test_active_bots_var_takes_precedence(run_dispatcher):
    payload = {
        "pull_request": {
            "number": 5,
            "author_association": "MEMBER",
            "title": "Testing precedence",
            "body": "",
        }
    }
    result = run_dispatcher(
        event_name="pull_request",
        payload=payload,
        active_var="claude",
        active_env="claude,gemini",
    )

    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"


def test_issue_comment_without_issue_payload(run_dispatcher):
    payload = {
        "comment": {
            "author_association": "COLLABORATOR",
            "body": "@claude can you review this snippet?",
        }
    }
    result = run_dispatcher(
        event_name="issue_comment",
        payload=payload,
        active_var="claude",
    )

    assert result["run_claude"] == "true"
    assert result["run_gemini"] == "false"
    assert result["run_opencode"] == "false"
    assert result.get("target_id", "") == ""
    assert result.get("target_type", "") == ""
