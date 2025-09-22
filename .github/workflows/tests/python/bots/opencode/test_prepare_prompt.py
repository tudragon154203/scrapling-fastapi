import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, '.github/workflows/scripts/bots/opencode')

import json
import pytest
from prepare_prompt import (
    PromptContext,
    WorkflowError,
    build_prompt,
    load_event_payload,
    _format_person,
    _strip_prefix,
)


@pytest.fixture
def sample_pr_payload():
    return {
        "pull_request": {
            "title": "Test PR Title",
            "user": {"login": "testuser"},
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"},
            "body": "This is a test PR body.",
        }
    }


@pytest.fixture
def sample_comment_payload():
    return {"comment": {"body": "/opencode Fix the bug", "user": {"login": "commenter"}}}


@pytest.fixture
def sample_issue_payload():
    return {
        "issue": {
            "title": "Test Issue",
            "body": "@oc Help with this",
            "user": {"login": "issuer"},
        }
    }


def test_load_event_payload_valid_json(tmp_path: Path):
    payload = {"event": "data"}
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(payload))
    result = load_event_payload(event_file)
    assert result == payload


def test_load_event_payload_file_not_found(tmp_path: Path):
    event_file = tmp_path / "nonexistent.json"
    with pytest.raises(WorkflowError, match="not found"):
        load_event_payload(event_file)


def test_load_event_payload_invalid_json(tmp_path: Path):
    event_file = tmp_path / "invalid.json"
    event_file.write_text("invalid json")
    with pytest.raises(WorkflowError, match="not valid JSON"):
        load_event_payload(event_file)


def test_format_person_valid():
    user = {"login": "testuser"}
    assert _format_person(user) == "@testuser"


def test_format_person_invalid():
    assert _format_person(None) == "unknown user"
    assert _format_person("not a dict") == "unknown user"
    assert _format_person({}) == "unknown user"


def test_strip_prefix_with_prefix():
    command = "/opencode Fix bug"
    remainder, prefix = _strip_prefix(command)
    assert remainder == "Fix bug"
    assert prefix == "/opencode"


def test_strip_prefix_without_prefix():
    command = "Just text"
    remainder, prefix = _strip_prefix(command)
    assert remainder == "Just text"
    assert prefix is None


def test_strip_prefix_substring():
    command = "Some /oc command here"
    remainder, prefix = _strip_prefix(command)
    assert remainder == "command here"
    assert prefix == "/oc"


def test_build_prompt_pull_request(sample_pr_payload):
    event_name = "pull_request"
    target_type = "pull_request"
    target_id = "123"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_pr_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert isinstance(context, PromptContext)
    assert "opencode CLI running inside a GitHub Actions workflow" in context.prompt
    assert f"Review pull request #{target_id} titled \"Test PR Title\" authored by @testuser" in context.prompt
    assert "Base branch: main" in context.prompt
    assert "Head branch: feature-branch" in context.prompt
    assert "Pull request description:\nThis is a test PR body." in context.prompt
    assert "### 👀 Findings:" in context.prompt
    assert "### 💡 Suggestions:" in context.prompt
    assert "### 💯 Confidence:" in context.prompt
    assert context.summary == "Automated review of pull request #123"
    assert context.command_text is None


def test_build_prompt_pull_request_no_body(sample_pr_payload):
    sample_pr_payload["pull_request"]["body"] = ""
    event_name = "pull_request"
    target_type = "pull_request"
    target_id = "123"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_pr_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert "Pull request description:" not in context.prompt


def test_build_prompt_issue_comment(sample_comment_payload):
    event_name = "issue_comment"
    target_type = "issue"
    target_id = "456"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_comment_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert "A issue comment from @commenter requested opencode on issue #456" in context.prompt
    assert "Command text:\nFix the bug" in context.prompt
    assert context.summary == "Command `/opencode` handled for issue #456"
    assert context.command_text == "Fix the bug"


def test_build_prompt_issue_comment_no_prefix(sample_comment_payload):
    sample_comment_payload["comment"]["body"] = "No prefix here"
    event_name = "issue_comment"
    target_type = "issue"
    target_id = "456"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_comment_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert "Command text:\nNo prefix here" in context.prompt
    assert context.summary == "Command handled for issue #456"
    assert context.command_text == "No prefix here"


def test_build_prompt_pull_request_review_comment(sample_comment_payload):
    event_name = "pull_request_review_comment"
    target_type = "pull_request"
    target_id = "789"
    repository = "test/repo"
    sample_comment_payload["comment"]["path"] = ".specify/src/file.py"
    sample_comment_payload["comment"]["line"] = 42

    context = build_prompt(
        event_name=event_name,
        payload=sample_comment_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert "A pull request review comment from @commenter requested opencode on pull request #789" in context.prompt
    assert "Command text:\nFix the bug" in context.prompt
    assert "File: .specify/src/file.py, Line: 42" in context.prompt
    assert context.summary == "Command `/opencode` handled for pull request #789"


def test_build_prompt_issues(sample_issue_payload):
    event_name = "issues"
    target_type = "issue"
    target_id = "101"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_issue_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert f"Issue #{target_id} created by @issuer asked for opencode support." in context.prompt
    assert "Issue title: Test Issue" in context.prompt
    assert "Request:\nHelp with this" in context.prompt
    assert context.summary == "Command `@oc` handled for issue #101"
    assert context.command_text == "Help with this"


def test_build_prompt_default_event():
    event_name = "unknown_event"
    target_type = ""
    target_id = ""
    repository = "test/repo"
    payload = {}

    context = build_prompt(
        event_name=event_name,
        payload=payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert f"Event `{event_name}` triggered opencode for repository ." in context.prompt
    assert context.summary == "opencode run for unknown_event"
    assert context.command_text is None


def test_build_prompt_pull_request_missing_keys(sample_pr_payload):
    # Remove some keys to test robustness
    del sample_pr_payload["pull_request"]["head"]
    del sample_pr_payload["pull_request"]["base"]
    sample_pr_payload["pull_request"]["user"] = None

    event_name = "pull_request"
    target_type = "pull_request"
    target_id = "123"
    repository = "test/repo"

    context = build_prompt(
        event_name=event_name,
        payload=sample_pr_payload,
        target_type=target_type,
        target_id=target_id,
        repository=repository,
    )

    assert "authored by unknown user" in context.prompt
    assert "Base branch: unknown" in context.prompt
    assert "Head branch: unknown" in context.prompt