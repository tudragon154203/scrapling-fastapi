"""API tests for the TikTok search endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.tiktok.search import TikTokSearchResponse


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
        }

        response = client.post("/tiktok/search", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert mock_search.await_count == 1
        args, kwargs = mock_search.await_args
        assert kwargs["query"] == "test"
        assert kwargs["num_videos"] == 20
        assert kwargs["sort_type"] == "RELEVANCE"
        assert kwargs["recency_days"] == "ALL"
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

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_PARAMETER"
        assert "strategy" in data["error"]["message"].lower()
        assert data["error"]["field"] == "strategy"

    def test_unknown_parameter_rejected(self, client):
        """Unknown parameters should also be rejected with the standard format."""
        response = client.post(
            "/tiktok/search",
            json={"query": "test", "force_headful": False, "unexpected": 1},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_PARAMETER"
        assert "unexpected" in data["error"]["message"]
        assert "force_headful" in ", ".join(data["error"]["details"]["accepted_parameters"])

    def test_missing_force_headful_fails_validation(self, client):
        """force_headful remains a required field."""
        response = client.post("/tiktok/search", json={"query": "test"})

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert any(item.get("loc", ["", ""])[-1] == "force_headful" for item in detail)

    def test_invalid_force_headful_value(self, client):
        """Values outside the accepted coercions should raise validation errors."""
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
            json={"query": "test", "force_headful": False},
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
            json={"query": "test", "force_headful": False},
        )

        assert response.status_code == 429
        data = response.json()
        assert data["error"]["code"] == "RATE_LIMITED"
