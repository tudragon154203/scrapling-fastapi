"""Integration tests verifying `/tiktok/search` defaults to headless execution."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


client = TestClient(app)


def test_tiktok_search_headless_mode_default():
    """Ensure TikTok search requests run in headless mode without forcing headful."""
    request_payload = {"query": "street food", "force_headful": False, "numVideos": 3}

    response = client.post("/tiktok/search", json=request_payload)

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "street food"

    metadata = data["search_metadata"]
    assert metadata["executed_path"] == "headless"
    assert metadata["execution_time"] >= 0
    assert isinstance(metadata["request_hash"], str) and metadata["request_hash"]

    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0, "Should return at least one search result in headless mode"

    assert isinstance(data["totalResults"], int)
    assert data["totalResults"] > 0, "Should have positive total results count"

    # Verify actual search results content quality
    for video in data["results"]:
        assert "id" in video and video["id"], "Video should have non-empty id"
        assert "caption" in video and video["caption"], "Video should have non-empty caption"
        assert "authorHandle" in video and video["authorHandle"], "Video should have non-empty author handle"
        assert "likeCount" in video and isinstance(
            video["likeCount"], int) and video["likeCount"] >= 0, "Video should have valid like count"
        assert "uploadTime" in video and video["uploadTime"], "Video should have upload time"
        assert "webViewUrl" in video and video["webViewUrl"], "Video should have non-empty URL"
