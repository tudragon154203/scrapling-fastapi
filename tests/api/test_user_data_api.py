import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app


class TestUserDataAPI:
    """Test suite for user data API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_crawl_endpoint_with_force_user_data(self):
        """Test crawl endpoint with force_user_data."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True
        }
        
        with patch('app.api.crawl.crawl') as mock_crawl:
            mock_crawl.return_value = Mock(
                status_code=200,
                json={"status": "success", "url": "https://example.com", "html": "<html></html>"}
            )
            
            response = self.client.post("/crawl", json=payload)
            assert response.status_code == 200
            
            # Verify the request was processed correctly
            mock_crawl.assert_called_once()
            call_args = mock_crawl.call_args[1]['request']
            assert call_args.url == "https://example.com"
            assert call_args.force_user_data is True

    def test_crawl_endpoint_rejects_write_mode(self):
        """Test crawl endpoint rejects user_data_mode extra field with 422."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True,
            "user_data_mode": "write"
        }
        
        response = self.client.post("/crawl", json=payload)
        assert response.status_code == 422
        # Pydantic validation error structure
        data = response.json()
        assert "detail" in data

    def test_crawl_endpoint_without_force_user_data(self):
        """Test crawl endpoint without force_user_data (should not use user data)."""
        payload = {
            "url": "https://example.com",
            "force_user_data": False
        }
        
        with patch('app.api.crawl.crawl') as mock_crawl:
            mock_crawl.return_value = Mock(
                status_code=200,
                json={"status": "success", "url": "https://example.com", "html": "<html></html>"}
            )
            
            response = self.client.post("/crawl", json=payload)
            assert response.status_code == 200
            
            # Verify the request was processed correctly
            mock_crawl.assert_called_once()
            call_args = mock_crawl.call_args[1]['request']
            assert call_args.url == "https://example.com"
            assert call_args.force_user_data is False

    def test_crawl_endpoint_rejects_extra_fields(self):
        """Test crawl endpoint rejects extra fields."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True,
            "extra_field": "should_be_rejected"
        }
        
        response = self.client.post("/crawl", json=payload)
        assert response.status_code == 422  # Validation error

    def test_dpd_endpoint_with_user_data(self):
        """Test DPD endpoint with user data support."""
        payload = {
            "tracking_number": "1234567890",
            "force_user_data": True
        }
        
        with patch('app.api.crawl.crawl_dpd') as mock_crawl_dpd:
            mock_crawl_dpd.return_value = Mock(
                status_code=200,
                json={"status": "success", "url": "https://example.com", "html": "<html></html>"}
            )
            
            response = self.client.post("/crawl/dpd", json=payload)
            assert response.status_code == 200
            
            # Verify the request was processed correctly
            mock_crawl_dpd.assert_called_once()
            call_args = mock_crawl_dpd.call_args[1]['request']
            assert call_args.tracking_number == "1234567890"
            assert call_args.force_user_data is True
