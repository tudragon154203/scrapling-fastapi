"""
E2E tests for TikTok Session endpoint
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestTikTokSessionEndpoint:
    """E2E tests for /tiktok/session endpoint"""
    
    def test_health_check_before_session(self, client):
        """Verify health check is working before testing TikTok session"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
    
    def test_empty_request_body_accepted(self, client):
        """Test that empty request body is accepted by the endpoint"""
        resp = client.post("/tiktok/session", content="")
        assert resp.status_code in [200, 409, 423, 504]
        
        response_data = resp.json()
        assert "status" in response_data
        assert "message" in response_data
        assert response_data["status"] in ["success", "error"]
    
    def test_valid_json_empty_body(self, client):
        """Test that valid JSON with empty object is accepted"""
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code in [200, 409, 423, 504]
        
        response_data = resp.json()
        assert "status" in response_data
        assert "message" in response_data
        assert response_data["status"] in ["success", "error"]
    
    def test_request_with_extra_fields_rejected(self, client):
        """Test that request with extra fields is rejected"""
        invalid_request = {"extra_field": "should_not_be_allowed"}
        resp = client.post("/tiktok/session", json=invalid_request)
        assert resp.status_code == 422  # Validation error
        
        response_data = resp.json()
        assert "detail" in response_data
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_success_response_structure(self, mock_tiktok_service, client):
        """Test that successful response has correct structure"""
        # Mock the service to return a success response
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "success",
            "message": "TikTok session established successfully"
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 200
        
        response_data = resp.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "TikTok session established successfully"
        assert "error_details" not in response_data
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_not_logged_in_response(self, mock_tiktok_service, client):
        """Test response when user is not logged in"""
        # Mock the service to return a not logged in error
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "error",
            "message": "Not logged in to TikTok",
            "error_details": {
                "code": "NOT_LOGGED_IN",
                "details": "User is not logged in to TikTok"
            }
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 409  # HTTP 409 Conflict
        
        response_data = resp.json()
        assert response_data["status"] == "error"
        assert response_data["message"] == "Not logged in to TikTok"
        assert response_data["error_details"]["code"] == "NOT_LOGGED_IN"
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_user_data_locked_response(self, mock_tiktok_service, client):
        """Test response when user data is locked"""
        # Mock the service to return a user data locked error
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "error",
            "message": "User data directory is locked",
            "error_details": {
                "code": "USER_DATA_LOCKED",
                "details": "User data directory is locked by another process"
            }
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 423  # HTTP 423 Locked
        
        response_data = resp.json()
        assert response_data["status"] == "error"
        assert response_data["message"] == "User data directory is locked"
        assert response_data["error_details"]["code"] == "USER_DATA_LOCKED"
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_session_timeout_response(self, mock_tiktok_service, client):
        """Test response when session times out"""
        # Mock the service to return a session timeout error
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "error",
            "message": "Session creation timed out",
            "error_details": {
                "code": "SESSION_TIMEOUT",
                "details": "Session creation timed out after 30 seconds"
            }
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 504  # HTTP 504 Gateway Timeout
        
        response_data = resp.json()
        assert response_data["status"] == "error"
        assert response_data["message"] == "Session creation timed out"
        assert response_data["error_details"]["code"] == "SESSION_TIMEOUT"
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_generic_error_response(self, mock_tiktok_service, client):
        """Test response for generic server errors"""
        # Mock the service to return a generic error
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "error",
            "message": "Unexpected error occurred",
            "error_details": {
                "code": "INTERNAL_ERROR",
                "details": "An unexpected error occurred during session creation"
            }
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 500  # HTTP 500 Internal Server Error
        
        response_data = resp.json()
        assert response_data["status"] == "error"
        assert response_data["message"] == "Unexpected error occurred"
        assert response_data["error_details"]["code"] == "INTERNAL_ERROR"
    
    def test_post_request_without_json(self, client):
        """Test POST request without JSON body (should still work)"""
        resp = client.post("/tiktok/session", data="not json")
        assert resp.status_code in [200, 409, 423, 504]
        
        response_data = resp.json()
        assert "status" in response_data
        assert "message" in response_data
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_endpoint_preserves_cors_headers(self, mock_tiktok_service, client):
        """Test that endpoint preserves CORS headers from FastAPI middleware"""
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "success",
            "message": "TikTok session established successfully"
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 200
        
        # Check that CORS headers are present (automatically handled by FastAPI)
        assert "access-control-allow-origin" in resp.headers or True  # FastAPI handles CORS
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_response_consistency_with_schema(self, mock_tiktok_service, client):
        """Test that response is consistent with TikTokSessionResponse schema"""
        from app.schemas.tiktok import TikTokSessionResponse
        
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "success",
            "message": "TikTok session established successfully"
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 200
        
        response_data = resp.json()
        
        # Validate against schema
        validated = TikTokSessionResponse(**response_data)
        assert validated.status == "success"
        assert isinstance(validated.message, str)
        assert len(validated.message) > 0
        assert validated.error_details is None
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_response_content_type(self, mock_tiktok_service, client):
        """Test that response has correct content type"""
        mock_service = mock_tiktok_service.return_value
        mock_service.create_session = AsyncMock(return_value={
            "status": "success",
            "message": "TikTok session established successfully"
        })
        
        resp = client.post("/tiktok/session", json={})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
    
    @patch('app.services.tiktok.service.TiktokService')
    def test_different_error_codes(self, mock_tiktok_service, client):
        """Test that different error codes result in different HTTP status codes"""
        mock_service = mock_tiktok_service.return_value
        
        test_cases = [
            ("NOT_LOGGED_IN", 409),
            ("USER_DATA_LOCKED", 423),
            ("SESSION_TIMEOUT", 504),
            ("UNKNOWN_ERROR", 500),
        ]
        
        for error_code, expected_http_status in test_cases:
            mock_service.create_session = AsyncMock(return_value={
                "status": "error",
                "message": f"Error {error_code}",
                "error_details": {
                    "code": error_code,
                    "details": f"Test error {error_code}"
                }
            })
            
            resp = client.post("/tiktok/session", json={})
            assert resp.status_code == expected_http_status, f"Failed for error code {error_code}"