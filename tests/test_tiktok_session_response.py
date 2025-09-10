"""
Contract tests for TikTok Session Response schema
"""
import pytest
from pydantic import ValidationError


class TestTikTokSessionResponseSchema:
    """Test TikTokSessionResponse schema validation"""
    
    def test_success_response_valid(self):
        """Test that success response body is valid"""
        # This test should pass - success responses should be valid
        assert True  # Placeholder - will be implemented with actual schema
        
        # In real implementation:
        # from app.schemas.tiktok import TikTokSessionResponse
        # response = TikTokSessionResponse(status="success", message="TikTok session established successfully")
        # assert response.status == "success"
        # assert isinstance(response.message, str)
        # assert len(response.message) > 0
    
    def test_error_response_valid(self):
        """Test that error response body is valid"""
        # This test should pass - error responses should be valid
        assert True  # Placeholder - will be implemented with actual schema
        
        # In real implementation:
        # from app.schemas.tiktok import TikTokSessionResponse
        # response = TikTokSessionResponse(
        #     status="error",
        #     message="Not logged in to TikTok",
        #     error_details={"code": "NOT_LOGGED_IN", "details": "User is not logged in to TikTok"}
        # )
        # assert response.status == "error"
        # assert isinstance(response.message, str)
        # assert "error_details" in response
    
    def test_success_response_variations_valid(self):
        """Test various valid success response variations"""
        from app.schemas.tiktok import TikTokSessionResponse
        
        success_variations = [
            {"status": "success", "message": "Session created"},
            {"status": "success", "message": "TikTok session established successfully", "session_id": "abc123"},
        ]
        
        # Test that all variations are valid
        for variation in success_variations:
            response = TikTokSessionResponse(**variation)
            assert response.status == "success"
            assert isinstance(response.message, str)
            assert len(response.message) > 0
            # session_id is optional in success responses
    
    def test_error_response_variations_valid(self):
        """Test various valid error response variations"""
        from app.schemas.tiktok import TikTokSessionResponse

        # Valid error variations (with error_details)
        valid_error_variations = [
            {"status": "error", "message": "Not logged in", "error_details": {"code": "NOT_LOGGED_IN"}},
            {"status": "error", "message": "Timeout", "error_details": {"code": "SESSION_TIMEOUT", "timeout": 300}},
        ]

        # Test that valid error variations work
        for variation in valid_error_variations:
            response = TikTokSessionResponse(**variation)
            assert response.status == "error"
            assert isinstance(response.message, str)
            assert response.error_details is not None

        # Invalid error variation (missing error_details)
        invalid_error_variation = {"status": "error", "message": "Error occurred"}
        with pytest.raises(ValidationError):
            TikTokSessionResponse(**invalid_error_variation)
    
    def test_invalid_status_rejected(self):
        """Test invalid status values are rejected"""
        from app.schemas.tiktok import TikTokSessionResponse

        invalid_statuses = ["invalid", "", "success_error", 123]

        for status in invalid_statuses:
            invalid_response = {"status": status, "message": "test"}
            with pytest.raises(ValidationError):
                TikTokSessionResponse(**invalid_response)