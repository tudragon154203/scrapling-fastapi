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
        """Missing force_headful should raise a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TikTokSearchRequest(query="test query")
        assert "force_headful" in str(exc_info.value)

    def test_force_headful_with_optional_params(self):
        """Optional parameters should coexist with force_headful."""
        request = TikTokSearchRequest(
            query="test query",
            force_headful=True,
            limit=10,
            offset=5,
        )
        assert request.limit == 10
        assert request.offset == 5

    def test_force_headful_with_search_url(self):
        """search_url should remain optional alongside force_headful."""
        url = "https://www.tiktok.com/search/test"
        request = TikTokSearchRequest(query="test query", force_headful=False, search_url=url)
        assert request.search_url == url

    def test_extra_fields_are_captured(self):
        """Extra fields should be preserved for higher-level validation."""
        request = TikTokSearchRequest(query="test", force_headful=True, strategy="legacy")
        assert request.model_extra["strategy"] == "legacy"
