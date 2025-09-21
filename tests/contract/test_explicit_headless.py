import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_explicit_headless_mode():
    """Test that searches run in headless mode when force_headful is explicitly set to false."""
    response = client.post("/tiktok/search", json={"query": "funny videos", "force_headful": False})
    assert response.status_code == 200
    data = response.json()
    assert "execution_mode" in data
    assert data["execution_mode"] == "headless"
    assert "results" in data
    assert "totalResults" in data
    assert "query" in data
