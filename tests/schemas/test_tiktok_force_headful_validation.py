"""Unit tests for TikTok search request validation."""

import pytest
from pydantic import ValidationError

from app.schemas.tiktok.search import TikTokSearchRequest


class TestForceHeadfulValidation:
    """Unit tests for force_headful parameter and request schema."""

    def test_force_headful_true(self):
        """force_headful=True should validate and be accessible."""
        request = TikTokSearchRequest(query="test query", force_headful=True)
        assert request.force_headful is True

    def test_force_headful_false(self):
        """force_headful=False should validate and be accessible."""
        request = TikTokSearchRequest(query="test query", force_headful=False)
        assert request.force_headful is False

    def test_force_headful_missing(self):
        """Missing force_headful should default to False."""
        request = TikTokSearchRequest(query="test query")
        assert request.force_headful is False

    def test_extra_fields_are_captured(self):
        """Extra fields should be rejected with a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TikTokSearchRequest(query="test", force_headful=True, strategy="legacy")
        assert "Extra inputs are not permitted" in str(exc_info.value)
