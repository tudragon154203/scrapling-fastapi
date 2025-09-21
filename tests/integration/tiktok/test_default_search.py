import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_default_search_behavior():
    """Integration test for default search behavior - should run in headless mode."""
    response = client.post("/tiktok/search", json={"query": "funny cats"})
    assert response.status_code == 200
    data = response.json()
    assert data["execution_mode"] == "headless"
    assert "results" in data
    assert isinstance(data["results"], list)
