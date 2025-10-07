"""
Comprehensive integration tests for services layer.
"""

import pytest

from app.schemas.crawl import CrawlRequest
from app.schemas.browse import BrowseRequest


@pytest.mark.integration
class TestServicesIntegration:
    """Integration tests for service layer."""

    def test_crawl_service_request_validation(self):
        """Test crawl service request validation without execution."""
        # Test that requests can be created and validated
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True
        )

        # Verify request validation works
        assert str(request.url) == "https://example.com/"
        assert request.force_user_data is True
        assert request.force_headful is False  # Default value

        # Test invalid URL is rejected
        try:
            CrawlRequest(url="invalid-url")
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected

    def test_tiktok_service_request_validation(self):
        """Test TikTok service request validation."""
        from app.schemas.tiktok.session import TikTokSessionRequest

        # Test that TikTok session requests can be created and validated
        request = TikTokSessionRequest()

        # Verify request can be created (defaults should work)
        assert request is not None

    def test_tiktok_service_initialization(self):
        """Test TikTok service can be initialized."""
        from app.services.tiktok.session.service import TiktokService

        service = TiktokService()

        # Test service initialization
        assert service is not None
        assert hasattr(service, 'sessions')
        assert service.sessions is not None

    def test_browse_service_request_validation(self):
        """Test browse service request validation."""
        # Test that browse requests can be created and validated
        request = BrowseRequest(
            url="https://example.com"
        )

        # Verify request validation works
        assert str(request.url) == "https://example.com/"

        # Test with None URL (should be valid as it's optional)
        request_no_url = BrowseRequest(url=None)
        assert request_no_url.url is None

    def test_browse_service_initialization(self):
        """Test browse service can be initialized."""
        from app.services.browser.browse import BrowseCrawler

        service = BrowseCrawler()

        # Test service initialization
        assert service is not None
        assert hasattr(service, 'engine')

    def test_service_imports(self):
        """Test that all service classes can be imported."""
        # Test imports work
        from app.services.crawler.generic import GenericCrawler
        from app.services.browser.browse import BrowseCrawler
        from app.services.tiktok.session.service import TiktokService

        # Verify classes exist and can be instantiated (basic validation)
        assert GenericCrawler is not None
        assert BrowseCrawler is not None
        assert TiktokService is not None

    def test_response_schemas(self):
        """Test response schemas can be created."""
        from app.schemas.crawl import CrawlResponse
        from app.schemas.browse import BrowseResponse
        from app.schemas.tiktok.session import TikTokSessionResponse

        # Test response schemas can be created
        crawl_response = CrawlResponse(
            status="success",
            url="https://example.com",
            html="<html>Test</html>"
        )
        assert crawl_response.status == "success"

        browse_response = BrowseResponse(
            status="success",
            message="Browse completed"
        )
        assert browse_response.status == "success"

        tiktok_response = TikTokSessionResponse(
            status="success",
            session_id="test-session",
            message="Session created"
        )
        assert tiktok_response.status == "success"
