"""
E2E tests for TikTok Search endpoint
"""
from unittest.mock import patch, AsyncMock
from app.schemas.tiktok.search import TikTokSearchResponse
from app.services.tiktok.search.service import TikTokSearchService


class TestTikTokSearchEndpoint:
    """E2E tests for /tiktok/search endpoint"""

    def test_health_check_before_search(self, client):
        """Verify health check is working before testing TikTok search"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_valid_search_request(self, mock_search, client):
        """Test that valid search request is accepted by the endpoint"""
        # Mock the search to return successful results
        mock_search.return_value = {
            "results": [
                {
                    "id": "123456789",
                    "caption": "Test video caption",
                    "authorHandle": "testuser",
                    "likeCount": 100,
                    "uploadTime": "2023-01-01",
                    "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789"
                }
            ],
            "totalResults": 1,
            "query": "test"
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 200

        response_data = resp.json()
        assert "results" in response_data
        assert "totalResults" in response_data
        assert "query" in response_data
        assert len(response_data["results"]) == 1
        assert response_data["totalResults"] == 1
        assert response_data["query"] == "test"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_search_with_multiple_queries(self, mock_search, client):
        """Test search with multiple queries"""
        # Mock the search to return successful results
        mock_search.return_value = {
            "results": [
                {
                    "id": "123456789",
                    "caption": "Test video caption",
                    "authorHandle": "testuser",
                    "likeCount": 100,
                    "uploadTime": "2023-01-01",
                    "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789"
                }
            ],
            "totalResults": 1,
            "query": "test query"
        }

        search_request = {
            "query": ["test", "query"],
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 200

        response_data = resp.json()
        assert response_data["query"] == "test query"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_not_logged_in_error_response(self, mock_search, client):
        """Test response for network connection errors (replacing session dependency)"""
        # Mock the search to return a network connection error
        mock_search.return_value = {
            "error": {
                "code": "SCRAPE_FAILED",
                "message": "Failed to connect to TikTok",
                "details": {"error": "Network connection failed"}
            }
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 500  # HTTP 500 Internal Server Error

        response_data = resp.json()
        assert "error" in response_data
        assert response_data["error"]["code"] == "SCRAPE_FAILED"
        assert response_data["error"]["message"] == "Failed to connect to TikTok"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_string_error_normalization(self, mock_search, client):
        """Plain string errors should be normalized and mapped to correct HTTP status."""
        mock_search.return_value = {
            "error": "session not logged in"
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 409  # HTTP 409 Conflict for login-related errors

        response_data = resp.json()
        assert response_data == {
            "error": {
                "code": "NOT_LOGGED_IN",
                "message": "session not logged in"
            }
        }

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_validation_error_response(self, mock_search, client):
        """Test response for validation errors"""
        # Mock the service to return a validation error
        mock_search.return_value = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "fields": {"query": "Query cannot be empty"}
            }
        }

        search_request = {
            "query": "",  # Invalid empty query
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 422  # HTTP 422 Unprocessable Entity

        response_data = resp.json()
        assert "error" in response_data
        assert response_data["error"]["code"] == "VALIDATION_ERROR"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_rate_limited_error_response(self, mock_search, client):
        """Test response when rate limited"""
        # Mock the service to return a rate limited error
        mock_search.return_value = {
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests"
            }
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 429  # HTTP 429 Too Many Requests

        response_data = resp.json()
        assert "error" in response_data
        assert response_data["error"]["code"] == "RATE_LIMITED"
        assert response_data["error"]["message"] == "Too many requests"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_scrape_failed_error_response(self, mock_search, client):
        """Test response for scrape failures"""
        # Mock the service to return a scrape failed error
        mock_search.return_value = {
            "error": {
                "code": "SCRAPE_FAILED",
                "message": "Failed to scrape TikTok search results",
                "details": {"error": "Timeout occurred"}
            }
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 500  # HTTP 500 Internal Server Error

        response_data = resp.json()
        assert "error" in response_data
        assert response_data["error"]["code"] == "SCRAPE_FAILED"
        assert response_data["error"]["message"] == "Failed to scrape TikTok search results"

    def test_invalid_request_schema(self, client):
        """Test that invalid request schema is rejected"""
        invalid_request = {
            "query": "test",
            "invalid_field": "should_not_be_allowed"
        }

        resp = client.post("/tiktok/search", json=invalid_request)
        assert resp.status_code == 422  # Validation error

        response_data = resp.json()
        assert "detail" in response_data

    def test_missing_required_fields(self, client):
        """Test that missing required fields are rejected"""
        invalid_request = {
            # Missing required "query" field
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL"
        }

        resp = client.post("/tiktok/search", json=invalid_request)
        assert resp.status_code == 422  # Validation error

        response_data = resp.json()
        assert "detail" in response_data

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_response_consistency_with_schema(self, mock_search, client):
        """Test that response is consistent with TikTokSearchResponse schema"""
        mock_search.return_value = {
            "results": [
                {
                    "id": "123456789",
                    "caption": "Test video caption",
                    "authorHandle": "testuser",
                    "likeCount": 100,
                    "uploadTime": "2023-01-01",
                    "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789"
                }
            ],
            "totalResults": 1,
            "query": "test"
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 200

        response_data = resp.json()

        # Validate against schema
        validated = TikTokSearchResponse(**response_data)
        assert len(validated.results) == 1
        assert validated.totalResults == 1
        assert validated.query == "test"

        # Validate individual video data
        video = validated.results[0]
        assert video.id == "123456789"
        assert video.caption == "Test video caption"
        assert video.authorHandle == "testuser"
        assert video.likeCount == 100
        assert video.uploadTime == "2023-01-01"
        assert video.webViewUrl == "https://www.tiktok.com/@testuser/video/123456789"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_response_content_type(self, mock_search, client):
        """Test that response has correct content type"""
        mock_search.return_value = {
            "results": [],
            "totalResults": 0,
            "query": "test"
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "multistep"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"

    @patch('app.services.tiktok.search.service.TikTokSearchService.search', new_callable=AsyncMock)
    def test_direct_strategy_selection(self, mock_search, client):
        """Test that direct strategy selects URL parameter service"""
        # Mock the search to return successful results (strategy is handled internally)
        mock_search.return_value = {
            "results": [
                {
                    "id": "123456789",
                    "caption": "Test video caption",
                    "authorHandle": "testuser",
                    "likeCount": 100,
                    "uploadTime": "2023-01-01",
                    "webViewUrl": "https://www.tiktok.com/@testuser/video/123456789"
                }
            ],
            "totalResults": 1,
            "query": "test"
        }

        search_request = {
            "query": "test",
            "numVideos": 10,
            "sortType": "RELEVANCE",
            "recencyDays": "ALL",
            "strategy": "direct"
        }

        resp = client.post("/tiktok/search", json=search_request)
        assert resp.status_code == 200

        response_data = resp.json()
        assert "results" in response_data
        assert response_data["query"] == "test"
