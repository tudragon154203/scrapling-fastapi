"""Integration test for TikTok multi-step search strategy using real network calls."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.integration


client = TestClient(app)


class TestTikTokMultiStepSearchIntegration:
    """Exercise the TikTok multi-step search flow end-to-end."""

    def test_tiktok_multistep_search_multiple_queries(self):
        """Issue a multi-query search request and validate the response structure."""

        payload = {
            "query": ["street food", "night market"],
            "numVideos": 5,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep",
        }

        response = client.post("/tiktok/search", json=payload)

        assert response.status_code == 200

        data = response.json()

        assert "results" in data
        assert "totalResults" in data
        assert "query" in data

        assert isinstance(data["results"], list)
        assert isinstance(data["totalResults"], int)
        assert data["totalResults"] >= 0
        assert data["query"] == "street food night market"

        assert len(data["results"]) <= payload["numVideos"]

        for video in data["results"]:
            assert "id" in video
            assert "caption" in video
            assert "authorHandle" in video
            assert "likeCount" in video
            assert "uploadTime" in video
            assert "webViewUrl" in video

            assert isinstance(video["id"], str)
            assert isinstance(video["caption"], str)
            assert isinstance(video["authorHandle"], str)
            assert isinstance(video["likeCount"], int)
            assert isinstance(video["uploadTime"], str)
            assert isinstance(video["webViewUrl"], str)
