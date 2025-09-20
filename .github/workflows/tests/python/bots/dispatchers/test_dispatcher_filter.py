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


WORKFLOWS_DIR = next(
    parent for parent in Path(__file__).resolve().parents if parent.name == "workflows"
)
DISPATCHER_PATH = (
    WORKFLOWS_DIR / "scripts" / "bots" / "common" / "dispatcher_filter.py"
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
def test_pull_request_from_untrusted_author_skips_standardised_bots(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv(
        "ACTIVE_BOTS_VAR",
        '["aider", "claude", "gemini", "opencode"]',
    )
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "false"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "pull_request",
            "payload": {
                "pull_request": {
                    "author_association": "CONTRIBUTOR",
                    "number": 101,
                    "title": "Update",
                    "body": "",
                }
            },
        }
    ],
    indirect=True,
)
def test_pull_request_from_contributor_skips_standardised_bots(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv(
        "ACTIVE_BOTS_VAR",
        '["aider", "claude", "gemini", "opencode"]',
    )
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"
    assert outputs["run_claude"] == "false"
    assert outputs["run_gemini"] == "false"
    assert outputs["run_opencode"] == "false"


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
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "MEMBER",
                    "body": "@claude please help",
                    "user": {"login": "maintainer"},
                },
                "issue": {
                    "number": 7,
                    "user": {"login": "original-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_decide_for_issue_comment_commands(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["claude", "opencode"]')
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
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "NONE",
                    "body": "@opencode run",
                    "user": {"login": "external-author"},
                },
                "issue": {
                    "number": 11,
                    "user": {"login": "external-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_opencode_requires_trusted_commenter(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["opencode"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_opencode"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "MEMBER",
                    "body": "@opencode please help",
                    "user": {"login": "maintainer"},
                },
                "issue": {
                    "number": 15,
                    "user": {"login": "original-author"},
                },
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


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "NONE",
                    "body": "@aider please review",
                    "user": {"login": "external-author"},
                },
                "issue": {
                    "number": 21,
                    "user": {"login": "external-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_aider_requires_trusted_member_for_issue_comments(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["aider"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "MEMBER",
                    "body": "@aider please review",
                    "user": {"login": "maintainer"},
                },
                "issue": {
                    "number": 27,
                    "user": {"login": "original-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_aider_trusted_member_comment_runs(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["aider"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "true"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "MEMBER",
                    "body": "please help",
                    "user": {"login": "maintainer"},
                },
                "issue": {
                    "number": 22,
                    "user": {"login": "original-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_aider_requires_prefix_for_issue_comments(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["aider"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_aider"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issue_comment",
            "payload": {
                "comment": {
                    "author_association": "NONE",
                    "body": "@claude assist",
                    "user": {"login": "external-author"},
                },
                "issue": {
                    "number": 23,
                    "user": {"login": "external-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_claude_requires_trusted_member_for_issue_comments(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["claude"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_claude"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "pull_request_review",
            "payload": {
                "review": {
                    "author_association": "MEMBER",
                    "body": "@gemini take a look",
                    "user": {"login": "maintainer"},
                },
                "pull_request": {
                    "number": 24,
                    "user": {"login": "original-author"},
                },
            },
        }
    ],
    indirect=True,
)
def test_gemini_supports_pull_request_reviews(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["gemini"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_gemini"] == "true"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issues",
            "payload": {
                "issue": {
                    "author_association": "MEMBER",
                    "body": "Need @gemini to investigate",
                    "title": "Bug report",
                    "number": 25,
                    "user": {"login": "maintainer"},
                },
                "sender": {"login": "maintainer"},
            },
        }
    ],
    indirect=True,
)
def test_gemini_supports_issue_prefix_detection(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["gemini"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_gemini"] == "true"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issues",
            "payload": {
                "issue": {
                    "author_association": "NONE",
                    "body": "Need @gemini to investigate",
                    "title": "Bug report",
                    "number": 28,
                    "user": {"login": "external-author"},
                },
                "sender": {"login": "external-author"},
            },
        }
    ],
    indirect=True,
)
def test_gemini_requires_trusted_member_for_issues(
    monkeypatch, set_dispatch_event, github_env
):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["gemini"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_gemini"] == "false"


@pytest.mark.parametrize(
    "set_dispatch_event",
    [
        {
            "event_name": "issues",
            "payload": {
                "issue": {
                    "author_association": "MEMBER",
                    "body": "No prefix here",
                    "title": "General question",
                    "number": 26,
                    "user": {"login": "maintainer"},
                },
                "sender": {"login": "maintainer"},
            },
        }
    ],
    indirect=True,
)
def test_gemini_requires_prefix_for_issues(monkeypatch, set_dispatch_event, github_env):
    monkeypatch.setenv("ACTIVE_BOTS_VAR", '["gemini"]')
    dispatcher_filter.decide()
    outputs = read_github_output(github_env)

    assert outputs["run_gemini"] == "false"

