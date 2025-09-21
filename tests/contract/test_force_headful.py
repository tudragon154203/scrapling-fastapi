import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_force_headful_mode(monkeypatch):
    """Test that searches run in headful mode when force_headful is explicitly set to true."""
    # Ensure we're not in a test environment for this specific test
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    response = client.post("/tiktok/search", json={"query": "funny videos", "force_headful": True})
    assert response.status_code == 200
    data = response.json()
    assert "execution_mode" in data
    assert data["execution_mode"] == "headful"
    assert "results" in data
    assert "totalResults" in data
    assert "query" in data
