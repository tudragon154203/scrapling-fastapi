"""
Comprehensive tests for ScraplingFetcherAdapter to increase coverage.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.common.adapters.fetch_arg_composer import FetchArgComposer
from app.services.common.adapters.fetch_params import FetchParams


class TestScraplingFetcherAdapter:
    """Test ScraplingFetcherAdapter comprehensive functionality."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return ScraplingFetcherAdapter()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.scrapling_stealthy = True
        settings.default_headless = True
        settings.camoufox_user_data_dir = "/tmp/user_data"
        return settings

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization."""
        assert hasattr(adapter, 'fetch')
        assert hasattr(adapter, 'detect_capabilities')

    def test_detect_capabilities(self, adapter):
        """Test capability detection."""
        capabilities = adapter.detect_capabilities()

        from app.services.common.types import FetchCapabilities
        assert isinstance(capabilities, FetchCapabilities)
        # Check for expected capability attributes
        expected_attrs = [
            "supports_proxy",
            "supports_user_data",
            "supports_network_idle",
            "supports_timeout",
            "supports_extra_headers"
        ]

        for attr in expected_attrs:
            assert hasattr(capabilities, attr)
            assert isinstance(getattr(capabilities, attr), bool)

    def test_detect_capabilities_with_system_info(self, adapter):
        """Test capability detection includes system info."""
        with patch('platform.system', return_value='Linux'):
            capabilities = adapter.detect_capabilities()

            # Should still return basic capabilities
            from app.services.common.types import FetchCapabilities
            assert isinstance(capabilities, FetchCapabilities)
            assert hasattr(capabilities, 'supports_proxy')
            assert isinstance(capabilities.supports_proxy, bool)

    @pytest.mark.asyncio
    async def test_fetch_basic_success(self, adapter):
        """Test basic successful fetch."""
        url = "https://example.com"
        options = {
            "timeout_seconds": 30,
            "headless": True
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Test content</html>",
                status_code=200,
                url=url
            ))

            result = await adapter.fetch(url, options)

            assert hasattr(result, 'html_content')
            assert result.html_content == "<html>Test content</html>"
            mock_fetcher_class.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_with_proxy(self, adapter):
        """Test fetch with proxy configuration."""
        url = "https://example.com"
        proxy = {"http": "http://proxy:8080"}
        options = {
            "timeout_seconds": 30,
            "proxy": proxy
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Proxied content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>Proxied content</html>"

    @pytest.mark.asyncio
    async def test_fetch_with_user_data(self, adapter):
        """Test fetch with user data directory."""
        url = "https://example.com"
        user_data_dir = "/tmp/browser_profile"
        options = {
            "timeout_seconds": 30,
            "user_data_dir": user_data_dir
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>User data content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>User data content</html>"

    @pytest.mark.asyncio
    async def test_fetch_with_headers(self, adapter):
        """Test fetch with custom headers."""
        url = "https://example.com"
        headers = {"User-Agent": "CustomBot/1.0"}
        options = {
            "timeout_seconds": 30,
            "extra_headers": headers
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Custom headers content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>Custom headers content</html>"

    @pytest.mark.asyncio
    async def test_fetch_with_javascript_disabled(self, adapter):
        """Test fetch with JavaScript disabled."""
        url = "https://example.com"
        options = {
            "timeout_seconds": 30,
            "javascript_enabled": False
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>No JS content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>No JS content</html>"

    @pytest.mark.asyncio
    async def test_fetch_with_wait_for_selector(self, adapter):
        """Test fetch with wait for selector."""
        url = "https://example.com"
        options = {
            "timeout_seconds": 30,
            "wait_for_selector": ".content",
            "wait_for_selector_state": "visible"
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            # Mock the class method fetch directly
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html><div class='content'>Content loaded</div></html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert "Content loaded" in result.html_content

    @pytest.mark.asyncio
    async def test_fetch_with_viewport(self, adapter):
        """Test fetch with viewport settings."""
        url = "https://example.com"
        options = {
            "timeout_seconds": 30,
            "viewport": {"width": 1920, "height": 1080}
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Viewport content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>Viewport content</html>"

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self, adapter):
        """Test fetch error handling."""
        url = "https://example.com"
        options = {"timeout_seconds": 30}

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(side_effect=Exception("Fetch failed"))

            with pytest.raises(Exception, match="Fetch failed"):
                await adapter.fetch(url, options)

    @pytest.mark.asyncio
    async def test_fetch_timeout_error(self, adapter):
        """Test fetch timeout error."""
        url = "https://example.com"
        options = {"timeout_seconds": 30}

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(side_effect=TimeoutError("Request timed out"))

            with pytest.raises(TimeoutError, match="Request timed out"):
                await adapter.fetch(url, options)

    @pytest.mark.asyncio
    async def test_fetch_connection_error(self, adapter):
        """Test fetch connection error."""
        url = "https://example.com"
        options = {"timeout_seconds": 30}

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(side_effect=ConnectionError("Connection failed"))

            with pytest.raises(ConnectionError, match="Connection failed"):
                await adapter.fetch(url, options)

    @pytest.mark.asyncio
    async def test_fetch_with_empty_options(self, adapter):
        """Test fetch with minimal options."""
        url = "https://example.com"
        options = {}

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Minimal options content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>Minimal options content</html>"

    @pytest.mark.asyncio
    async def test_fetch_with_stealth_mode(self, adapter):
        """Test fetch with stealth mode enabled."""
        url = "https://example.com"
        options = {
            "timeout_seconds": 30,
            "stealth": True
        }

        with patch.object(adapter, '_get_stealthy_fetcher') as mock_get_fetcher:
            mock_fetcher_class = MagicMock()
            mock_get_fetcher.return_value = mock_fetcher_class
            mock_fetcher_class.fetch = AsyncMock(return_value=MagicMock(
                html_content="<html>Stealth mode content</html>",
                status_code=200
            ))

            result = await adapter.fetch(url, options)

            assert result.html_content == "<html>Stealth mode content</html>"


class TestFetchArgComposer:
    """Test FetchArgComposer comprehensive functionality."""

    @pytest.fixture
    def composer(self):
        """Create composer instance."""
        return FetchArgComposer()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.scrapling_stealthy = True
        settings.default_headless = True
        settings.camoufox_user_data_dir = "/tmp/user_data"
        return settings

    def test_compose_basic_options(self, composer, mock_settings):
        """Test composing basic options."""
        options = {
            "url": "https://example.com",
            "timeout_seconds": 30
        }
        caps = {"supports_stealth": True}
        selected_proxy = None
        additional_args = {}
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=selected_proxy,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)
        # Should contain processed options

    def test_compose_with_proxy(self, composer, mock_settings):
        """Test composing options with proxy."""
        options = {"url": "https://example.com"}
        caps = {"supports_proxy": True}
        selected_proxy = {"http": "http://proxy:8080"}
        additional_args = {}
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=selected_proxy,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_user_data(self, composer, mock_settings):
        """Test composing options with user data."""
        options = {
            "url": "https://example.com",
            "user_data_dir": "/tmp/profile"
        }
        caps = {"supports_user_data": True}
        additional_args = {}
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_headers(self, composer, mock_settings):
        """Test composing options with headers."""
        options = {"url": "https://example.com"}
        caps = {}
        additional_args = {}
        extra_headers = {"User-Agent": "CustomBot/1.0"}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_capabilities(self, composer, mock_settings):
        """Test composing options based on capabilities."""
        options = {"url": "https://example.com"}
        caps = {
            "supports_stealth": True,
            "supports_headless": True,
            "supports_javascript": True,
            "supports_user_data": True,
            "supports_proxy": True
        }
        additional_args = {}
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_page_action(self, composer, mock_settings):
        """Test composing options with page action."""
        options = {"url": "https://example.com"}
        caps = {}
        additional_args = {}
        extra_headers = {}
        page_action = {"type": "wait", "seconds": 2}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=page_action
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_additional_args(self, composer, mock_settings):
        """Test composing options with additional args."""
        options = {"url": "https://example.com"}
        caps = {}
        additional_args = {
            "user_data_dir": "/tmp/custom",
            "headless": False
        }
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_error_handling(self, composer, mock_settings):
        """Test composer error handling."""
        options = None  # Invalid options
        caps = {}
        additional_args = {}
        extra_headers = {}

        # Should handle invalid inputs gracefully
        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_complex_options(self, composer, mock_settings):
        """Test composing complex options."""
        options = {
            "url": "https://example.com",
            "timeout_seconds": 60,
            "wait_for_selector": ".content",
            "javascript_enabled": True,
            "viewport": {"width": 1920, "height": 1080}
        }
        caps = {
            "supports_stealth": True,
            "supports_headless": True,
            "supports_javascript": True
        }
        selected_proxy = {"http": "http://proxy:8080"}
        additional_args = {
            "user_data_dir": "/tmp/profile",
            "locale": "en-US"
        }
        extra_headers = {
            "User-Agent": "CustomBot/1.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=selected_proxy,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=mock_settings,
            page_action=None
        )

        assert isinstance(result, FetchParams)

    def test_compose_with_none_settings(self, composer):
        """Test composer with None settings."""
        options = {"url": "https://example.com"}
        caps = {}
        additional_args = {}
        extra_headers = {}

        result = composer.compose(
            options=options,
            caps=caps,
            selected_proxy=None,
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=None,
            page_action=None
        )

        assert isinstance(result, FetchParams)
