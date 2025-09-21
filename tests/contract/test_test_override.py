import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_test_environment_override(monkeypatch):
    """Test that in test environments, searches always run in headless mode regardless of force_headful parameter."""
    # Set environment variable to indicate test environment
    monkeypatch.setenv("TESTING", "true")

    response = client.post("/tiktok/search", json={"query": "funny videos", "force_headful": True})
    assert response.status_code == 200
    data = response.json()
    assert "execution_mode" in data
    assert data["execution_mode"] == "headless"  # Should be headless even though force_headful is True
    assert "results" in data
    assert "totalResults" in data
    assert "query" in data
