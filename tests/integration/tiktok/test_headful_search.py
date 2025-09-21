import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_headful_search_behavior(monkeypatch):
    """Integration test for headful search behavior - should run in headful mode when requested."""
    # Ensure we're not in a test environment for this specific test
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    # Even with force_headful=True, should run in headful mode in non-test environment
    response = client.post("/tiktok/search", json={"query": "funny dogs", "force_headful": True})
    assert response.status_code == 200
    data = response.json()
    assert data["execution_mode"] == "headful"
    assert "results" in data
    assert isinstance(data["results"], list)
