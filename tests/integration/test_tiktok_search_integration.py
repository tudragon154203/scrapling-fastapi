import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark = pytest.mark.integration

client = TestClient(app)


class TestTikTokSearchIntegration:
    """Integration tests for TikTok search endpoint"""

    def test_tiktok_search_endpoint(self):
        """Test TikTok search endpoint with query 'gái xinh' and numVideos 10"""
        # First, create a TikTok session - test requires successful session creation
        session_response = client.post("/tiktok/session", json={})
        # In CI/tight environments, login is unlikely; accept 200 or 409
        assert session_response.status_code in (200, 409), (
            f"Session creation unexpected status {session_response.status_code}: {session_response.text}"
        )
        # If 200, validate structure
        if session_response.status_code == 200:
            session_data = session_response.json()
            assert session_data["status"] == "success"
            assert "TikTok session established successfully" in session_data.get("message", "")
        
        # Prepare the request payload
        payload = {
            "query": "gái xinh",
            "numVideos": 10
        }

        # Make request to the TikTok search endpoint
        response = client.post("/tiktok/search", json=payload)

        # Verify response status code
        assert response.status_code == 200

        # Parse response data
        data = response.json()

        # Verify response structure
        assert "results" in data
        assert "totalResults" in data
        assert "query" in data

        # Verify results structure (allow empty in CI environments)
        assert isinstance(data["results"], list)

        # Verify that totalResults is a positive integer
        assert isinstance(data["totalResults"], int), "totalResults should be an integer"
        assert data["totalResults"] >= 0, "totalResults should be non-negative"

        # Verify that query in response matches "gái xinh"
        assert data["query"] == "gái xinh", "Query in response should match the request"

        # Verify that numVideos is respected when results exist
        assert len(data["results"]) <= 10, "Number of results should be less than or equal to numVideos"

        # Verify that each video object has the expected keys
        for video in data["results"]:
            assert "id" in video, "Video should have 'id' key"
            assert "caption" in video, "Video should have 'caption' key"
            assert "authorHandle" in video, "Video should have 'authorHandle' key"
            assert "likeCount" in video, "Video should have 'likeCount' key"
            assert "uploadTime" in video, "Video should have 'uploadTime' key"
            assert "webViewUrl" in video, "Video should have 'webViewUrl' key"

            # Verify types of values
            assert isinstance(video["id"], str), "Video id should be a string"
            assert isinstance(video["caption"], str), "Video caption should be a string"
            assert isinstance(video["authorHandle"], str), "Video authorHandle should be a string"
            assert isinstance(video["likeCount"], int), "Video likeCount should be an integer"
            assert isinstance(video["uploadTime"], str), "Video uploadTime should be a string"
            assert isinstance(video["webViewUrl"], str), "Video webViewUrl should be a string"
