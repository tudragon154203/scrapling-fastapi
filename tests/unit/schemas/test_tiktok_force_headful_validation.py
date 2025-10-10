"""Comprehensive validation tests for TikTok download force_headful field."""

import pytest
from pydantic import ValidationError
from app.schemas.tiktok.download import TikTokDownloadRequest

pytestmark = [pytest.mark.unit]


class TestTikTokForceHeadfulValidation:
    """Test cases for force_headful field validation in TikTokDownloadRequest."""

    def test_reject_unknown_fields_when_force_headful_present(self):
        """Test that unknown fields are rejected even when force_headful is present."""
        # Test with extra field 'unknown_field'
        with pytest.raises(ValidationError) as exc_info:
            TikTokDownloadRequest(
                url="https://www.tiktok.com/@username/video/1234567890",
                force_headful=True,
                unknown_field="should_be_rejected"
            )
        assert "extra" in str(exc_info.value).lower()

        # Test with extra field 'quality' (common field name that might be attempted)
        with pytest.raises(ValidationError) as exc_info:
            TikTokDownloadRequest(
                url="https://www.tiktok.com/@username/video/1234567890",
                force_headful=False,
                quality="hd"
            )
        assert "extra" in str(exc_info.value).lower()

    def test_json_schema_includes_force_headful_field(self):
        """Test that the JSON schema includes the force_headful field."""
        schema = TikTokDownloadRequest.model_json_schema()

        # Check that force_headful is in the properties
        assert "force_headful" in schema["properties"]

        # Check the field definition
        force_headful_schema = schema["properties"]["force_headful"]
        assert force_headful_schema["type"] == "boolean"
        assert force_headful_schema.get("default", False) is False

        # Check that it's not required (has default)
        assert "force_headful" not in schema.get("required", [])

    def test_force_headful_type_validation(self):
        """Test that force_headful accepts and coerces values to boolean."""
        valid_url = "https://www.tiktok.com/@username/video/1234567890"

        # Test valid boolean values
        request_true = TikTokDownloadRequest(url=valid_url, force_headful=True)
        assert request_true.force_headful is True

        request_false = TikTokDownloadRequest(url=valid_url, force_headful=False)
        assert request_false.force_headful is False

        # Test Pydantic type coercion - string "true" becomes True
        request_string_true = TikTokDownloadRequest(url=valid_url, force_headful="true")
        assert request_string_true.force_headful is True

        # Test Pydantic type coercion - string "false" becomes False
        request_string_false = TikTokDownloadRequest(url=valid_url, force_headful="false")
        assert request_string_false.force_headful is False

        # Test Pydantic type coercion - integer 1 becomes True
        request_int_true = TikTokDownloadRequest(url=valid_url, force_headful=1)
        assert request_int_true.force_headful is True

        # Test Pydantic type coercion - integer 0 becomes False
        request_int_false = TikTokDownloadRequest(url=valid_url, force_headful=0)
        assert request_int_false.force_headful is False

        # Test invalid type - None (this should still raise ValidationError)
        with pytest.raises(ValidationError):
            TikTokDownloadRequest(url=valid_url, force_headful=None)

        # Test invalid type - empty string
        with pytest.raises(ValidationError):
            TikTokDownloadRequest(url=valid_url, force_headful="")

    def test_force_headful_with_various_url_formats(self):
        """Test force_headful works correctly with different valid URL formats."""
        test_urls = [
            "https://www.tiktok.com/@username/video/1234567890",
            "https://tiktok.com/@user/video/123",
            "https://vm.tiktok.com/abcdefg/",
        ]

        for url in test_urls:
            # Test with force_headful=True
            request = TikTokDownloadRequest(url=url, force_headful=True)
            assert request.force_headful is True
            assert str(request.url) == url

            # Test with force_headful=False
            request = TikTokDownloadRequest(url=url, force_headful=False)
            assert request.force_headful is False
            assert str(request.url) == url

    def test_serialization_with_force_headful_omit_none(self):
        """Test that serialization behavior is correct with force_headful."""
        request = TikTokDownloadRequest(
            url="https://www.tiktok.com/@username/video/1234567890"
        )

        # When force_headful is False (default), it should be included in serialization
        # since it's an explicit field with default value
        data = request.model_dump(mode='json')
        assert "force_headful" in data
        assert data["force_headful"] is False

        # When force_headful is explicitly True, it should be included
        request_explicit_true = TikTokDownloadRequest(
            url="https://www.tiktok.com/@username/video/1234567890",
            force_headful=True
        )
        data = request_explicit_true.model_dump(mode='json')
        assert "force_headful" in data
        assert data["force_headful"] is True

    def test_force_headful_field_metadata(self):
        """Test force_headful field metadata and configuration."""
        # Check field is properly defined in model fields
        fields = TikTokDownloadRequest.model_fields
        assert "force_headful" in fields

        force_headful_field = fields["force_headful"]
        assert force_headful_field.annotation is bool  # Should be boolean type
        assert force_headful_field.default is False  # Should default to False
        assert not force_headful_field.is_required()  # Should not be required
