import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestTikTokSearchIntegration:
    """Integration tests for TikTok search endpoint"""

    def test_tiktok_search_endpoint(self):
        """Test TikTok search endpoint with query 'gái xinh' and numVideos 10"""
        # First, attempt to create a TikTok session
        session_response = client.post("/tiktok/session", json={})
        
        # If session creation fails (user not logged in), test should handle gracefully
        if session_response.status_code != 200:
            # Session creation failed - this is expected in test environments
            # The search endpoint should return a 409 Conflict error in this case
            payload = {
                "query": "gái xinh",
                "numVideos": 10
            }
            
            # Make request to the TikTok search endpoint
            response = client.post("/tiktok/search", json=payload)
            
            # Verify response status code is 409 (Conflict) when not logged in
            assert response.status_code == 409
            
            # Parse response data
            data = response.json()
            
            # Verify error response structure
            assert "error" in data
            assert data["error"]["code"] == "NOT_LOGGED_IN"
            return  # Exit test as we can't proceed without a session
        
        # If session creation was successful, proceed with search
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

        # Verify that results list is not empty
        assert len(data["results"]) > 0, "Results list should not be empty"

        # Verify that totalResults is a positive integer
        assert isinstance(data["totalResults"], int), "totalResults should be an integer"
        assert data["totalResults"] > 0, "totalResults should be a positive integer"

        # Verify that query in response matches "gái xinh"
        assert data["query"] == "gái xinh", "Query in response should match the request"

        # Verify that numVideos is respected
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