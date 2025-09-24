"""Contract tests for the TikTok search endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.integration

CONTRACT_SAMPLE_RESULT = {
    "results": [
        {
            "id": "contract123",
            "caption": "Contract test",
            "authorHandle": "contract",
            "likeCount": 7,
            "uploadTime": "2024-02-02T00:00:00Z",
            "webViewUrl": "https://www.tiktok.com/@contract/video/contract123",
        }
    ],
    "totalResults": 1,
    "query": "contract",
}


class TestTikTokSearchContract:
    """Ensure the public contract matches expectations."""

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_successful_response_shape(self, mock_search, client):
        """Successful responses must match the documented schema."""
        mock_search.return_value = CONTRACT_SAMPLE_RESULT

        response = client.post(
            "/tiktok/search",
            json={"query": "contract", "force_headful": False},
        )

        assert response.status_code == 200
        payload = response.json()
        assert sorted(payload.keys()) == sorted(
            ["results", "totalResults", "query", "execution_mode", "search_metadata"]
        )
        assert isinstance(payload["results"], list)
        assert payload["search_metadata"].keys() >= {"executed_path", "execution_time", "request_hash"}

    def test_strategy_rejection_contract(self, client):
        """Strategy parameter rejection should follow the documented error format."""
        response = client.post(
            "/tiktok/search",
            json={"query": "contract", "force_headful": True, "strategy": "browser"},
        )

        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] == "INVALID_PARAMETER"
        assert payload["error"]["field"] == "strategy"

    def test_validation_error_contract(self, client):
        """Validation errors should bubble up as FastAPI-formatted details."""
        response = client.post(
            "/tiktok/search",
            json={"force_headful": True},
        )

        assert response.status_code == 422
        payload = response.json()
        assert "detail" in payload
        assert any(item.get("loc", [None])[-1] == "query" for item in payload["detail"])
