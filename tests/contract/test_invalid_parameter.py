import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_invalid_parameter_validation():
    """Test that invalid values for force_headful result in validation errors."""
    response = client.post("/tiktok/search", json={"query": "funny videos", "force_headful": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    assert data["detail"][0]["loc"] == ["body", "force_headful"]
    assert "bool_parsing" in data["detail"][0]["type"]
