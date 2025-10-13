import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace

from app.services.crawler.utils.iframe_extractor import IframeExtractor
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.common.adapters.fetch_params import FetchParams

pytestmark = [pytest.mark.unit]


class TestIframeExtractor:
    """Test cases for IframeExtractor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_fetch_client = MagicMock(spec=ScraplingFetcherAdapter)
        self.extractor = IframeExtractor(self.mock_fetch_client)

    def test_extract_iframes_with_no_iframes(self):
        """Test that HTML without iframes is returned unchanged."""
        html = "<html><body><p>No iframes here</p></body></html>"
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url)

        assert result_html == html
        assert results == []

    def test_extract_iframes_with_empty_html(self):
        """Test that empty HTML is handled gracefully."""
        result_html, results = self.extractor.extract_iframes("", "https://example.com")

        assert result_html == ""
        assert results == []

    def test_extract_iframes_with_none_html(self):
        """Test that None HTML is handled gracefully."""
        result_html, results = self.extractor.extract_iframes(None, "https://example.com")

        assert result_html is None
        assert results == []

    def test_should_skip_internal_urls(self):
        """Test that internal URLs are skipped."""
        assert self.extractor._should_skip_iframe("data:text/html,<html></html>")
        assert self.extractor._should_skip_iframe("javascript:void(0)")
        assert self.extractor._should_skip_iframe("about:blank")
        assert self.extractor._should_skip_iframe("mailto:test@example.com")
        assert self.extractor._should_skip_iframe("tel:+1234567890")
        assert self.extractor._should_skip_iframe("file:///local/file.html")
        assert self.extractor._should_skip_iframe("")
        assert self.extractor._should_skip_iframe("#fragment")
        assert not self.extractor._should_skip_iframe("https://example.com")

    def test_is_valid_url(self):
        """Test URL validation."""
        assert self.extractor._is_valid_url("https://example.com")
        assert self.extractor._is_valid_url("http://example.com")
        assert not self.extractor._is_valid_url("ftp://example.com")
        assert not self.extractor._is_valid_url("example.com")  # Missing scheme
        assert not self.extractor._is_valid_url("")  # Empty

    def test_extract_iframes_with_external_src(self):
        """Test successful iframe content extraction."""
        # Mock successful fetch of iframe content
        mock_page = SimpleNamespace(
            html_content="<html><body><iframe content</body></html>",
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        html = '<html><body><iframe src="https://external.com/content"></iframe></body></html>'
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 1
        assert results[0]["src"] == "https://external.com/content"
        assert results[0]["absolute_url"] == "https://external.com/content"
        assert "iframe content" in results[0]["content"]
        assert "<iframe><html><body><iframe content</body></html></iframe>" in result_html
        self.mock_fetch_client.fetch.assert_called_once()

    def test_extract_iframes_with_relative_src(self):
        """Test iframe with relative URL is resolved to absolute."""
        mock_page = SimpleNamespace(
            html_content="<html><body>Relative content</body></html>",
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        html = '<html><body><iframe src="/relative/content.html"></iframe></body></html>'
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 1
        assert results[0]["src"] == "/relative/content.html"
        assert results[0]["absolute_url"] == "https://example.com/relative/content.html"
        self.mock_fetch_client.fetch.assert_called_once()
        fetch_call = self.mock_fetch_client.fetch.call_args
        params = fetch_call.args[1]
        assert isinstance(params, FetchParams)
        assert params.get("timeout") == 10000
        assert params.get("network_idle") is False
        assert "timeout_seconds" not in params

    def test_extract_iframes_fetch_failure(self):
        """Test handling of iframe fetch failures."""
        # Mock failed fetch
        self.mock_fetch_client.fetch.side_effect = Exception("Network error")

        html = '<html><body><iframe src="https://external.com/content"></iframe></body></html>'
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 0  # No successful extractions
        assert result_html == html  # Original HTML unchanged

    def test_extract_iframes_empty_content(self):
        """Test handling of empty iframe content."""
        mock_page = SimpleNamespace(
            html_content="",  # Empty content
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        html = '<html><body><iframe src="https://external.com/content"></iframe></body></html>'
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 0  # No successful extractions
        assert result_html == html  # Original HTML unchanged

    def test_extract_iframes_with_multiple_iframes(self):
        """Test processing multiple iframes."""
        def mock_fetch_side_effect(url, kwargs):
            if "external1.com" in url:
                return SimpleNamespace(html_content="<html><body>Content 1</body></html>", status=200)
            elif "external2.com" in url:
                return SimpleNamespace(html_content="<html><body>Content 2</body></html>", status=200)
            else:
                raise Exception("Unexpected URL")

        self.mock_fetch_client.fetch.side_effect = mock_fetch_side_effect

        html = '''
        <html>
            <body>
                <iframe src="https://external1.com/content1"></iframe>
                <iframe src="https://external2.com/content2"></iframe>
            </body>
        </html>
        '''
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 2
        # Order may vary due to processing, so check both values exist
        srcs = [r["src"] for r in results]
        assert "https://external1.com/content1" in srcs
        assert "https://external2.com/content2" in srcs
        assert "Content 1" in result_html
        assert "Content 2" in result_html
        assert self.mock_fetch_client.fetch.call_count == 2

    def test_extract_iframes_with_attributes(self):
        """Test iframe with various attributes is processed correctly."""
        mock_page = SimpleNamespace(
            html_content="<html><body>Content</body></html>",
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        html = '<iframe src="https://external.com/content" width="100%" height="400" style="border:none"></iframe>'
        base_url = "https://example.com"

        result_html, results = self.extractor.extract_iframes(html, base_url, {})

        assert len(results) == 1
        # The original attributes should be preserved except src which is replaced with content
        assert "<iframe><html><body>Content</body></html></iframe>" in result_html

    def test_extract_iframes_with_custom_fetch_kwargs(self):
        """Test that custom fetch kwargs are passed through correctly."""
        mock_page = SimpleNamespace(
            html_content="<html><body>Content</body></html>",
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        html = '<iframe src="https://external.com/content"></iframe>'
        base_url = "https://example.com"
        custom_kwargs = {'custom_header': 'value', 'timeout_seconds': 20}

        result_html, results = self.extractor.extract_iframes(html, base_url, custom_kwargs)

        self.mock_fetch_client.fetch.assert_called_once()
        fetch_call = self.mock_fetch_client.fetch.call_args
        params = fetch_call.args[1]
        assert isinstance(params, FetchParams)
        assert params.get("network_idle") is False
        assert params.get("timeout") == 10000
        assert params.get("custom_header") == 'value'
        assert "timeout_seconds" not in params

    def test_extract_iframes_with_fetch_params_instance_preserves_original(self):
        """Passing FetchParams should not mutate the original mapping."""
        mock_page = SimpleNamespace(
            html_content="<html><body>Frame Content</body></html>",
            status=200
        )
        self.mock_fetch_client.fetch.return_value = mock_page

        original_params = FetchParams({"timeout": 45000, "network_idle": True, "proxy": "http://proxy"})
        html = '<iframe src="https://external.com/content"></iframe>'
        base_url = "https://example.com"

        self.extractor.extract_iframes(html, base_url, original_params)

        fetch_call = self.mock_fetch_client.fetch.call_args
        iframe_params = fetch_call.args[1]
        assert isinstance(iframe_params, FetchParams)
        assert iframe_params.get("timeout") == 10000
        assert iframe_params.get("network_idle") is False
        assert iframe_params.get("proxy") == "http://proxy"

        # Ensure the original params remain unchanged
        assert original_params.get("timeout") == 45000
        assert original_params.get("network_idle") is True

    def test_get_iframe_summary(self):
        """Test iframe summary generation."""
        iframe_results = [
            {"src": "https://example1.com", "content": "content1"},
            {"src": "https://example2.com", "content": ""},
            {"src": "https://example3.com", "content": "content3"}
        ]

        summary = self.extractor.get_iframe_summary(iframe_results)

        assert summary["total_iframes"] == 3
        assert summary["processed_iframes"] == 2
        assert summary["failed_iframes"] == 1
        assert len(summary["iframe_sources"]) == 3
        assert "https://example1.com" in summary["iframe_sources"]
