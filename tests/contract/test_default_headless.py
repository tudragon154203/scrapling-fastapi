import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_default_headless_behavior():
    """Test that searches run in headless mode by default when force_headful is not provided."""
    response = client.post("/tiktok/search", json={"query": "funny videos"})
    assert response.status_code == 200
    data = response.json()
    assert "execution_mode" in data
    assert data["execution_mode"] == "headless"
    assert "results" in data
    assert "totalResults" in data
    assert "query" in data
