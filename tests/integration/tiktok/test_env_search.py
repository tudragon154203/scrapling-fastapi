import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]

client = TestClient(app)


def test_env_search_behavior(monkeypatch):
    """Integration test for test environment behavior - should always run in headless mode."""
    # Set environment variable to indicate test environment
    monkeypatch.setenv("TESTING", "true")

    # Even with force_headful=True, should run in headless mode in test environment
    response = client.post("/tiktok/search", json={"query": "funny birds", "force_headful": True})
    assert response.status_code == 200
    data = response.json()
    assert data["execution_mode"] == "headless"  # Should be headless in test environment
    assert "results" in data
    assert isinstance(data["results"], list)
