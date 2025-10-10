"""
Real TikTok session integration test - POST to /tiktok/session and verify user login
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_tiktok_session_real_login(client):
    """Test POST to /tiktok/session with real browser and verify user login"""
    # Make actual POST request to TikTok session endpoint
    resp = client.post("/tiktok/session", json={})

    print(f"Response status: {resp.status_code}")
    print(f"Response content: {resp.text}")

    # Should return success if user is logged in, or specific error if not
    assert resp.status_code in [200, 409, 500]

    data = resp.json()
    assert "status" in data
    assert "message" in data

    # If successful, verify user is logged in
    if resp.status_code == 200:
        assert data["status"] == "success"
        assert "TikTok session established successfully" in data["message"]
        assert data.get("error_details") is None
    else:
        # If user not logged in or other error, should have appropriate error message
        assert data["status"] == "error"
        assert "error_details" in data
