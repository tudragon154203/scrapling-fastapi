import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import app


class TestUserDataAPI:
    """Test suite for user data API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    def test_crawl_endpoint_with_read_mode(self):
        """Test crawl endpoint with force_user_data and read mode."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True,
            "user_data_mode": "read"
        }
        
        with patch('app.api.routes.crawl') as mock_crawl:
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
            assert call_args.user_data_mode == "read"

    def test_crawl_endpoint_with_write_mode(self):
        """Test crawl endpoint with force_user_data and write mode."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True,
            "user_data_mode": "write"
        }
        
        with patch('app.api.routes.crawl') as mock_crawl:
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
            assert call_args.user_data_mode == "write"

    def test_crawl_endpoint_with_default_mode(self):
        """Test crawl endpoint with force_user_data but default user_data_mode."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True
            # user_data_mode should default to "read"
        }
        
        with patch('app.api.routes.crawl') as mock_crawl:
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
            assert call_args.user_data_mode == "read"  # Default

    def test_crawl_endpoint_without_force_user_data(self):
        """Test crawl endpoint without force_user_data (should not use user data)."""
        payload = {
            "url": "https://example.com",
            "force_user_data": False
        }
        
        with patch('app.api.routes.crawl') as mock_crawl:
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

    def test_crawl_endpoint_invalid_mode(self):
        """Test crawl endpoint with invalid user_data_mode should fail validation."""
        payload = {
            "url": "https://example.com",
            "force_user_data": True,
            "user_data_mode": "invalid_mode"
        }
        
        response = self.client.post("/crawl", json=payload)
        assert response.status_code == 422  # Validation error
        
        # Should contain validation error for user_data_mode
        error_data = response.json()
        assert "detail" in error_data
        assert any(
            error["loc"] == ["body", "user_data_mode"] and 
            error["msg"] == "user_data_mode must be either 'read' or 'write'"
            for error in error_data["detail"]
        )

    def test_dpd_endpoint_with_user_data(self):
        """Test DPD endpoint with user data support."""
        payload = {
            "tracking_number": "1234567890",
            "force_user_data": True,
            "user_data_mode": "read"
        }
        
        with patch('app.api.routes.crawl_dpd') as mock_crawl_dpd:
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
            assert call_args.user_data_mode == "read"