"""API tests for the TikTok search endpoint."""

from unittest.mock import AsyncMock, patch
from app.schemas.tiktok.search import TikTokSearchResponse

import pytest

pytestmark = [pytest.mark.unit]


SAMPLE_SEARCH_RESULT = {
    "results": [
        {
            "id": "123456789",
            "caption": "Test video caption",
            "authorHandle": "testuser",
            "likeCount": 100,
            "uploadTime": "2023-01-01T00:00:00Z",
            "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789",
        }
    ],
    "totalResults": 1,
    "query": "test",
}


class TestTikTokSearchEndpoint:
    """Behavioral tests for /tiktok/search."""

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_headless_request_success(self, mock_search, client):
        """force_headful=False should drive the headless path with a successful response."""
        mock_search.return_value = SAMPLE_SEARCH_RESULT

        payload = {
            "query": "test",
            "force_headful": False,
            "numVideos": 10,
        }

        response = client.post("/tiktok/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert mock_search.await_count == 1
        args, kwargs = mock_search.await_args
        assert kwargs["query"] == "test"
        assert kwargs["num_videos"] == 10
        assert data["execution_mode"] == "headless"
        assert data["search_metadata"]["executed_path"] == "headless"
        assert data["search_metadata"]["execution_time"] >= 0
        assert isinstance(data["search_metadata"]["request_hash"], str)
        TikTokSearchResponse(**data)  # schema validation should pass

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_headful_request_success(self, mock_search, client):
        """force_headful=True should select the browser-based path outside test env."""
        mock_search.return_value = SAMPLE_SEARCH_RESULT

        with patch(
            "specify_src.services.execution_context_service.ExecutionContextService.is_test_environment",
            return_value=False,
        ):
            response = client.post(
                "/tiktok/search",
                json={"query": "test", "force_headful": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["execution_mode"] == "headful"
        assert data["search_metadata"]["executed_path"] == "browser-based"

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_force_headful_accepts_string_values(self, mock_search, client):
        """String representations of booleans should be coerced for force_headful."""
        mock_search.return_value = SAMPLE_SEARCH_RESULT

        with patch(
            "specify_src.services.execution_context_service.ExecutionContextService.is_test_environment",
            return_value=False,
        ):
            response = client.post(
                "/tiktok/search",
                json={"query": "test", "force_headful": "TRUE"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["search_metadata"]["executed_path"] == "browser-based"

    def test_strategy_parameter_rejected(self, client):
        """Requests containing strategy should be rejected with a descriptive error."""
        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": True, "strategy": "multistep"},
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("strategy" in item.get("loc", [""])[-1] for item in detail)

    def test_unknown_parameter_rejected(self, client):
        """Unknown parameters should also be rejected with the standard format."""
        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": False, "unexpected": 1},
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any("unexpected" in item.get("loc", [""])[-1] for item in detail)

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_missing_force_headful_defaults_to_headless_and_respects_num_videos_limit(self, mock_search, client):
        """Missing force_headful defaults to False and uses headless path."""
        mock_search.return_value = SAMPLE_SEARCH_RESULT

        response = client.post("/tiktok/search", json={"query": "test", "numVideos": 15})

        assert response.status_code == 200
        data = response.json()
        assert data["execution_mode"] == "headless"
        assert data["search_metadata"]["executed_path"] == "headless"

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_invalid_force_headful_value(self, mock_search, client):
        """Values outside the accepted coercions should raise validation errors."""
        mock_search.return_value = SAMPLE_SEARCH_RESULT

        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": "maybe"},
        )

        assert response.status_code == 422

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_string_error_normalization(self, mock_search, client):
        """String errors from the service are normalized to structured payloads."""
        mock_search.return_value = {"error": "session not logged in"}

        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": False, "numVideos": 15},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"]["code"] == "NOT_LOGGED_IN"

    @patch("app.services.tiktok.search.service.TikTokSearchService.search", new_callable=AsyncMock)
    def test_structured_error_passthrough(self, mock_search, client):
        """Structured error payloads should be returned as-is."""
        mock_search.return_value = {
            "error": {
                "code": "RATE_LIMITED",
                "message": "Slow down",
            }
        }

        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": False, "numVideos": 15},
        )

        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMITED"
