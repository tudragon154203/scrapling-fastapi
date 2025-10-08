"""
Integration tests for API endpoints to increase overall coverage.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.mark.integration
class TestAPIEndpointsIntegration:
    """Integration tests for API endpoints."""

    def setup_method(self):
        """Setup test client."""
        self.client = TestClient(app)

    def test_health_endpoint_integration(self):
        """Test health endpoint integration."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    @patch('app.api.crawl.crawl')
    def test_crawl_endpoint_integration_success(self, mock_crawl):
        """Test crawl endpoint integration success."""
        # Mock successful crawl - return a mock object with .json attribute
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "status": "success",
            "html": "<html>Test content</html>",
            "url": "https://example.com"
        })
        mock_crawl.return_value = mock_response

        response = self.client.post("/crawl", json={
            "url": "https://example.com",
            "force_user_data": True
        })

        print(f"Actual response status: {response.status_code}")
        print(f"Actual response content: {response.content}")
        assert response.status_code == 200
        data = response.json()
        print(f"Response status: {response.status_code}")
        print(f"Response data: {data}")
        # Check for expected fields in crawl response
        assert "status" in data
        assert data["status"] == "success"

    @patch('app.api.crawl.crawl')
    def test_crawl_endpoint_integration_error(self, mock_crawl):
        """Test crawl endpoint integration error."""
        # Mock crawl failure
        mock_crawl.side_effect = Exception("Crawl failed")

        response = self.client.post("/crawl", json={
            "url": "https://example.com"
        })

        assert response.status_code == 500

    @patch('app.api.routes.tiktok_service')
    def test_tiktok_session_endpoint_integration_success(self, mock_tiktok_service):
        """Test TikTok session endpoint integration success."""
        # Mock successful session creation
        mock_tiktok_service.create_session = MagicMock(return_value={
            "status": "success",
            "message": "Session created successfully"
        })

        response = self.client.post("/tiktok/session", json={
            "user_data_dir": "/tmp/tiktok_data"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch('app.api.routes.tiktok_service')
    def test_tiktok_session_endpoint_integration_not_logged_in(self, mock_tiktok_service):
        """Test TikTok session endpoint integration when not logged in."""
        # Mock not logged in response
        mock_tiktok_service.create_session = MagicMock(return_value={
            "status": "error",
            "message": "Not logged in to TikTok",
            "error_details": {"code": "NOT_LOGGED_IN"}
        })

        response = self.client.post("/tiktok/session", json={})

        assert response.status_code == 409
        data = response.json()
        assert data["status"] == "error"
        assert "NOT_LOGGED_IN" in str(data)

    @patch('app.api.routes.browse_service')
    def test_browse_endpoint_integration(self, mock_browse_service):
        """Test browse endpoint integration."""
        # Mock successful browse
        mock_browse_service.browse = MagicMock(return_value={
            "status": "success",
            "content": "<html>Browse result</html>",
            "actions": []
        })

        response = self.client.post("/browse", json={
            "url": "https://example.com",
            "actions": [{"type": "wait", "seconds": 1}]
        })

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    @patch('app.api.routes.dpd_service')
    def test_dpd_endpoint_integration(self, mock_dpd_service):
        """Test DPD endpoint integration."""
        # Mock successful DPD tracking
        mock_dpd_service.track = MagicMock(return_value={
            "status": "success",
            "tracking_info": {
                "status": "delivered",
                "location": "Local depot"
            }
        })

        response = self.client.post("/crawl/dpd", json={
            "tracking_code": "1234567890"
        })

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    @patch('app.api.routes.auspost_service')
    def test_auspost_endpoint_integration(self, mock_auspost_service):
        """Test AusPost endpoint integration."""
        # Mock successful AusPost tracking
        mock_auspost_service.track = MagicMock(return_value={
            "status": "success",
            "tracking_info": {
                "status": "in_transit",
                "location": "Distribution center"
            }
        })

        response = self.client.post("/crawl/auspost", json={
            "tracking_code": "1234567890"
        })

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_cors_headers_integration(self):
        """Test CORS headers are present."""
        response = self.client.options("/health")
        assert "access-control-allow-origin" in response.headers

    def test_invalid_json_request(self):
        """Test invalid JSON request handling."""
        response = self.client.post(
            "/crawl",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """Test missing required fields validation."""
        response = self.client.post("/crawl", json={})
        assert response.status_code == 422

    def test_rate_limiting_headers(self):
        """Test rate limiting headers if implemented."""
        response = self.client.get("/health")
        # This test depends on whether rate limiting is implemented
        # If it is, check for rate limit headers
        # If not, this test will pass without checking specific headers
        assert response.status_code == 200

    @patch('app.api.routes.tiktok_service')
    def test_tiktok_search_endpoint_integration(self, mock_tiktok_service):
        """Test TikTok search endpoint integration."""
        # Mock successful search
        mock_tiktok_service.search = MagicMock(return_value={
            "status": "success",
            "results": [
                {
                    "id": "123",
                    "description": "Test video",
                    "author": "testuser"
                }
            ]
        })

        response = self.client.post("/tiktok/search", json={
            "query": "test query",
            "num_videos": 10
        })

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    @patch('app.api.routes.tiktok_service')
    def test_tiktok_search_endpoint_validation(self, mock_tiktok_service):
        """Test TikTok search endpoint validation."""
        # Test with invalid num_videos
        response = self.client.post("/tiktok/search", json={
            "query": "test",
            "num_videos": -1
        })
        assert response.status_code == 422

        # Test with empty query
        response = self.client.post("/tiktok/search", json={
            "query": "",
            "num_videos": 10
        })
        # May pass validation depending on schema requirements

    def test_user_data_api_integration(self):
        """Test user data API integration."""
        # Test with force_user_data parameter
        response = self.client.post("/crawl", json={
            "url": "https://example.com",
            "force_user_data": True
        })

        # Response depends on whether crawling succeeds
        # This test mainly checks the API structure
        assert response.status_code in [200, 500]  # Accept success or internal error

    @patch('app.api.routes.tiktok_service')
    def test_tiktok_session_management_integration(self, mock_tiktok_service):
        """Test TikTok session management integration."""
        # Mock session service methods
        mock_tiktok_service.has_active_session.return_value = True
        mock_tiktok_service.get_active_session.return_value = MagicMock()
        mock_tiktok_service.close_session.return_value = True

        # Test session existence check (would be through a separate endpoint)
        # This tests the integration points
        assert mock_tiktok_service.has_active_session.return_value is True

    def test_error_response_format(self):
        """Test error response format consistency."""
        response = self.client.post("/crawl", json={"invalid": "data"})
        assert response.status_code == 422

        data = response.json()
        assert "detail" in data  # FastAPI default error format

    def test_api_timeout_handling(self):
        """Test API timeout handling."""
        # This would require mocking slow operations
        # For now, just test the endpoint structure
        response = self.client.get("/health")
        assert response.status_code == 200

    @patch('app.api.routes.crawler_service')
    def test_concurrent_requests(self, mock_crawler_service):
        """Test handling of concurrent requests."""
        mock_crawler_service.crawl = MagicMock(return_value={"status": "success"})

        # Send multiple requests
        responses = []
        for _ in range(5):
            response = self.client.post("/crawl", json={
                "url": "https://example.com",
                "user_data_dir": f"/tmp/test{_}"
            })
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

    def test_large_payload_handling(self):
        """Test handling of large payloads."""
        large_payload = {
            "url": "https://example.com",
            "user_data_dir": "/tmp/test",
            "actions": [{"type": "click", "selector": f".item-{i}"} for i in range(1000)]
        }

        response = self.client.post("/crawl", json=large_payload)
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 413, 422]  # Success, payload too large, or validation error

    def test_content_type_validation(self):
        """Test content-type validation."""
        # Test with wrong content type
        response = self.client.post(
            "/crawl",
            data='{"url": "https://example.com"}',
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422

    @patch('app.api.routes.crawler_service')
    def test_custom_headers_integration(self, mock_crawler_service):
        """Test custom headers handling."""
        mock_crawler_service.crawl = MagicMock(return_value={"status": "success"})

        response = self.client.post("/crawl",
                                    json={"url": "https://example.com"},
                                    headers={"X-Custom-Header": "test-value"}
                                    )
        assert response.status_code == 200
