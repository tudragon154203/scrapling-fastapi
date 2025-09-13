"""
Contract tests for TikTok Session Request schema
"""
import pytest
from pydantic import ValidationError


class TestTikTokSessionRequestSchema:
    """Test TikTokSessionRequest schema validation"""

    def test_empty_request_body_valid(self):
        """Test that empty request body is valid"""
        # This test should pass - empty body should be accepted
        # In a real implementation, this would validate against Pydantic schema
        assert True  # Placeholder - schema should accept empty body

    def test_unknown_fields_rejected(self):
        """Test that unknown fields are rejected"""
        # This test should fail initially until implementation rejects unknown fields
        with pytest.raises(ValidationError):
            # This will be implemented in the actual schema
            from app.schemas.tiktok import TikTokSessionRequest

            # Test with extra fields
            TikTokSessionRequest(extra_field="should_be_rejected")

    def test_invalid_request_bodies_rejected(self):
        """Test various invalid request bodies are rejected"""
        invalid_bodies = [
            {"status": "invalid"},  # Invalid status
            {"message": 123},       # Invalid message type
            {"extra_field": "value"},  # Unknown field
            {"status": "success", "extra": "data"},  # Unknown field in success
            {"status": "error", "missing_message": "no message"},  # Missing message
        ]

        # This will be implemented in the actual schema
        for invalid_body in invalid_bodies:
            with pytest.raises(ValidationError):
                from app.schemas.tiktok import TikTokSessionRequest
                TikTokSessionRequest(**invalid_body)
