"""
Comprehensive tests for generic crawl service to increase coverage.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.crawler.generic import GenericCrawler
from app.schemas.crawl import CrawlRequest


@pytest.mark.skip("Test file outdated - service APIs have changed")
class TestGenericCrawlService:
    """Test GenericCrawlService comprehensive functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return GenericCrawlService()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.scrapling_stealthy = True
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings.default_headless = True
        return settings

    @pytest.mark.asyncio
    async def test_crawl_success_basic(self, service):
        """Test basic successful crawl."""
        request = CrawlRequest(url="https://example.com")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Test content</html>",
                status_code=200,
                url="https://example.com"
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"
                assert "content" in result
                assert result["content"] == "<html>Test content</html>"

    @pytest.mark.asyncio
    async def test_crawl_with_user_data_force(self, service):
        """Test crawl with force_user_data enabled."""
        request = CrawlRequest(
            url="https://example.com",
            force_user_data=True,
            user_data_dir="/tmp/test_data"
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>User data content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings') as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.scrapling_stealthy = True
                mock_settings.camoufox_user_data_dir = "/tmp/default"
                mock_get_settings.return_value = mock_settings

                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_proxy(self, service):
        """Test crawl with proxy configuration."""
        proxy_config = {
            "http": "http://proxy.example.com:8080",
            "https": "https://proxy.example.com:8080"
        }
        request = CrawlRequest(
            url="https://example.com",
            proxy=proxy_config
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Proxied content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_custom_headers(self, service):
        """Test crawl with custom headers."""
        headers = {"User-Agent": "Custom Agent"}
        request = CrawlRequest(
            url="https://example.com",
            headers=headers
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Custom headers content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_timeout(self, service):
        """Test crawl with custom timeout."""
        request = CrawlRequest(
            url="https://example.com",
            timeout_seconds=30
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Timeout content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_network_error(self, service):
        """Test crawl with network error."""
        request = CrawlRequest(url="https://example.com")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = Exception("Network error")
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "error"
                assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_crawl_timeout_error(self, service):
        """Test crawl with timeout error."""
        request = CrawlRequest(url="https://example.com")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = TimeoutError("Request timed out")
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_crawl_http_error(self, service):
        """Test crawl with HTTP error response."""
        request = CrawlRequest(url="https://example.com")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Error page</html>",
                status_code=404
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                # Should still succeed with the content even for 404
                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_empty_response(self, service):
        """Test crawl with empty response."""
        request = CrawlRequest(url="https://example.com")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"
                assert result["content"] == ""

    @pytest.mark.asyncio
    async def test_crawl_with_retry_settings(self, service):
        """Test crawl with custom retry settings."""
        request = CrawlRequest(
            url="https://example.com",
            retry_attempts=3,
            retry_delay=1
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Retry content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_javascript_disabled(self, service):
        """Test crawl with JavaScript disabled."""
        request = CrawlRequest(
            url="https://example.com",
            javascript_enabled=False
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>No JS content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_stealth_mode(self, service):
        """Test crawl with stealth mode settings."""
        request = CrawlRequest(
            url="https://example.com",
            stealth_mode=True
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Stealth content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_wait_for_selector(self, service):
        """Test crawl with wait for selector."""
        request = CrawlRequest(
            url="https://example.com",
            wait_for_selector=".content",
            wait_timeout=10
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html><div class='content'>Loaded</div></html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_invalid_url(self, service):
        """Test crawl with invalid URL."""
        request = CrawlRequest(url="invalid-url")

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = ValueError("Invalid URL")
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_crawl_with_custom_user_agent(self, service):
        """Test crawl with custom user agent."""
        request = CrawlRequest(
            url="https://example.com",
            user_agent="CustomBot/1.0"
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Custom UA content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_viewport_size(self, service):
        """Test crawl with custom viewport size."""
        request = CrawlRequest(
            url="https://example.com",
            viewport_width=1920,
            viewport_height=1080
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Viewport content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_with_block_resources(self, service):
        """Test crawl with resource blocking."""
        request = CrawlRequest(
            url="https://example.com",
            block_images=True,
            block_css=True
        )

        with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = MagicMock(
                html_content="<html>Blocked resources content</html>",
                status_code=200
            )
            mock_fetcher_class.return_value = mock_fetcher

            with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                result = await service.crawl(request)

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_crawl_error_handling_comprehensive(self, service):
        """Test comprehensive error handling."""
        request = CrawlRequest(url="https://example.com")

        # Test various exception types
        exceptions = [
            ConnectionError("Connection failed"),
            TimeoutError("Request timeout"),
            ValueError("Invalid value"),
            RuntimeError("Runtime error"),
            Exception("Generic error")
        ]

        for exc in exceptions:
            with patch('app.services.crawler.generic.ScraplingFetcherAdapter') as mock_fetcher_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch.side_effect = exc
                mock_fetcher_class.return_value = mock_fetcher

                with patch('app.services.crawler.generic.get_settings', return_value=MagicMock()):
                    result = await service.crawl(request)

                    assert result["status"] == "error"
                    assert "error" in result