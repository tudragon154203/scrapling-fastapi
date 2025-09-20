import json
from pathlib import Path
import pytest
import sys

# Ensure project root is on sys.path for imports
ROOT = Path(__file__).resolve().parents[3]  # Adjust for .github/workflows/tests/ depth
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture
def pr_payload():
    """Mock payload for pull_request event."""
    return {
        "pull_request": {
            "author_association": "MEMBER",
            "number": 42,
            "title": "Update",
            "body": "",
        }
    }

@pytest.fixture
def issue_comment_payload():
    """Mock payload for issue_comment event."""
    return {
        "comment": {
            "author_association": "MEMBER",
            "body": "@claude please help",
        },
        "issue": {"number": 7},
    }

@pytest.fixture
def github_env(monkeypatch, tmp_path):
    """Fixture to set up GitHub Action environment variables and output file."""
    output_path = tmp_path / "GITHUB_OUTPUT"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.delenv("ACTIVE_BOTS_VAR", raising=False)
    monkeypatch.delenv("ACTIVE_BOTS_ENV", raising=False)
    monkeypatch.delenv("EVENT_NAME", raising=False)
    monkeypatch.delenv("EVENT_PAYLOAD", raising=False)
    return output_path

@pytest.fixture
def set_dispatch_event(monkeypatch, github_env, request):
    """Fixture to set EVENT_NAME and EVENT_PAYLOAD for a dispatch event."""
    event_name = getattr(request, "param", {}).get("event_name", "pull_request")
    payload = getattr(request, "param", {}).get("payload", {})
    monkeypatch.setenv("EVENT_NAME", event_name)
    monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))
    yield
    # Cleanup after test
    monkeypatch.delenv("EVENT_NAME", raising=False)
    monkeypatch.delenv("EVENT_PAYLOAD", raising=False)

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
