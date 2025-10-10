"""Integration tests for the TikTok search endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [
    pytest.mark.unit,
]

SAMPLE_RESULT = {
    "results": [
        {
            "id": "abc123",
            "caption": "Integration test video",
            "authorHandle": "integration",
            "likeCount": 42,
            "uploadTime": "2024-01-01T00:00:00Z",
            "webViewUrl": "https://www.tiktok.com/@integration/video/abc123",
        }
    ],
    "totalResults": 1,
    "query": "integration",
}


class TestTikTokSearchIntegration:
    """High-level behavior that exercises the FastAPI stack."""

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_headless_flow(self, mock_search, client):
        """force_headful=False should produce headless metadata."""
        mock_search.return_value = SAMPLE_RESULT

        response = client.post(
            "/tiktok/search",
            json={"query": "integration", "force_headful": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["search_metadata"]["executed_path"] == "headless"
        assert data["execution_mode"] == "headless"

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_browser_flow(self, mock_search, client):
        """force_headful=True should reach the browser-based metadata path."""
        mock_search.return_value = SAMPLE_RESULT

        with patch(
            "specify_src.services.execution_context_service.ExecutionContextService.is_test_environment",
            return_value=False,
        ):
            response = client.post(
                "/tiktok/search",
                json={"query": "integration", "force_headful": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["search_metadata"]["executed_path"] == "browser-based"
        assert data["execution_mode"] == "headful"

    def test_strategy_rejection(self, client):
        """Legacy strategy payloads should be rejected with informative errors."""
        response = client.post(
            "/tiktok/search",
            json={"query": "integration", "force_headful": True, "strategy": "legacy"},
        )

        assert response.status_code == 422
        data = response.json()
        # Standard Pydantic validation error format with detail array
        assert "detail" in data
        detail = data["detail"]
        assert isinstance(detail, list)
        # Find the strategy validation error
        strategy_error = next((item for item in detail if "strategy" in item.get("loc", [])), None)
        assert strategy_error is not None
        assert "strategy" in strategy_error.get("loc", [])
        assert "extra inputs are not permitted" in strategy_error.get("msg", "").lower()
