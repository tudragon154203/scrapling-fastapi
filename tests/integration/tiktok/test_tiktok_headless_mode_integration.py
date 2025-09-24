"""Integration tests verifying `/tiktok/search` defaults to headless execution."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.integration


client = TestClient(app)


@pytest.mark.parametrize(
    "request_payload",
    [
        {"query": "street food", "force_headful": False, "numVideos": 3},
        {"query": "street food", "force_headful": "false", "numVideos": 3},
    ],
)
def test_tiktok_search_headless_mode_default(request_payload):
    """Ensure TikTok search requests run in headless mode without forcing headful."""

    response = client.post("/tiktok/search", json=request_payload)

    assert response.status_code == 200

    data = response.json()

    assert data["execution_mode"] == "headless"
    assert data["query"] == "street food"

    metadata = data["search_metadata"]
    assert metadata["executed_path"] == "headless"
    assert metadata["execution_time"] >= 0
    assert isinstance(metadata["request_hash"], str) and metadata["request_hash"]

    assert isinstance(data["results"], list)

    assert isinstance(data["totalResults"], int)
    assert data["totalResults"] >= 0

    for video in data["results"]:
        assert "id" in video
        assert "caption" in video
        assert "authorHandle" in video
        assert "likeCount" in video
        assert "uploadTime" in video
        assert "webViewUrl" in video
