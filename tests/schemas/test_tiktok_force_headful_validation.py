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
        """force_headful=False should validate and be accessible with numVideos <= 15."""
        request = TikTokSearchRequest(query="test query", force_headful=False, numVideos=15)
        assert request.force_headful is False
        assert request.numVideos == 15

    def test_force_headful_false_num_videos_exceeds_limit(self):
        """force_headful=False with numVideos > 15 should raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TikTokSearchRequest(query="test query", force_headful=False, numVideos=20)
        assert "numVideos cannot exceed 15 in headless mode" in str(exc_info.value)

    def test_force_headful_missing(self):
        """Missing force_headful should default to False and validate numVideos <= 15."""
        request = TikTokSearchRequest(query="test query", numVideos=15)
        assert request.force_headful is False
        assert request.numVideos == 15

    def test_force_headful_missing_num_videos_exceeds_limit(self):
        """Missing force_headful with numVideos > 15 should raise a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TikTokSearchRequest(query="test query", numVideos=20)
        assert "numVideos cannot exceed 15 in headless mode" in str(exc_info.value)

    def test_extra_fields_are_captured(self):
        """Extra fields should be rejected with a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TikTokSearchRequest(query="test", force_headful=True, strategy="legacy")
        assert "Extra inputs are not permitted" in str(exc_info.value)
