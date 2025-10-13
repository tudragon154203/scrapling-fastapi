from app.services.crawler.executors.single_executor import SingleAttemptExecutor
from app.schemas.crawl import CrawlRequest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


def _settings_factory():
    return SimpleNamespace(min_html_content_length=5, private_proxy_url=None)


def test_single_executor_uses_single_clone_and_cleans_up(monkeypatch):
    monkeypatch.setattr(
        'app.services.crawler.executors.single_executor.app_config.get_settings',
        _settings_factory,
    )
    executor = SingleAttemptExecutor()
    request = CrawlRequest(url="https://example.com")

    cleanup = MagicMock()

    with patch.object(executor.options_resolver, 'resolve', return_value={}), \
            patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
            patch.object(executor.camoufox_builder, 'build') as mock_build, \
            patch.object(executor.arg_composer, 'compose', return_value={}), \
            patch.object(executor.fetch_client, 'fetch') as mock_fetch:

        caps = MagicMock()
        caps.supports_proxy = True
        mock_caps.return_value = caps
        mock_build.return_value = ({'_user_data_cleanup': cleanup}, {})
        mock_fetch.return_value = SimpleNamespace(status=200, html_content='x' * 20)

        response = executor.execute(request)

    assert response.status == 'success'
    assert mock_build.call_count == 1
    cleanup.assert_called_once()


def test_single_executor_cleanup_runs_on_exception(monkeypatch):
    monkeypatch.setattr(
        'app.services.crawler.executors.single_executor.app_config.get_settings',
        _settings_factory,
    )
    executor = SingleAttemptExecutor()
    request = CrawlRequest(url="https://example.com")

    cleanup = MagicMock()

    with patch.object(executor.options_resolver, 'resolve', return_value={}), \
            patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
            patch.object(executor.camoufox_builder, 'build') as mock_build, \
            patch.object(executor.arg_composer, 'compose', return_value={}), \
            patch.object(executor.fetch_client, 'fetch') as mock_fetch:

        caps = MagicMock()
        caps.supports_proxy = True
        mock_caps.return_value = caps
        mock_build.return_value = ({'_user_data_cleanup': cleanup}, {})
        mock_fetch.side_effect = Exception('network error')

        response = executor.execute(request)

    assert response.status == 'error'
    assert 'network error' in response.message
    assert mock_build.call_count == 1
    cleanup.assert_called_once()


def test_single_executor_processes_iframes(monkeypatch):
    """Test that single executor processes iframes in HTML content."""
    monkeypatch.setattr(
        'app.services.crawler.executors.single_executor.app_config.get_settings',
        _settings_factory,
    )
    executor = SingleAttemptExecutor()
    request = CrawlRequest(url="https://example.com")

    cleanup = MagicMock()
    html_with_iframe = '<html><body><iframe src="https://external.com/content"></iframe></body></html>'
    processed_html = '<iframe><html><body>iframe content</body></html></iframe>'

    with patch.object(executor.options_resolver, 'resolve', return_value={}), \
            patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
            patch.object(executor.camoufox_builder, 'build') as mock_build, \
            patch.object(executor.arg_composer, 'compose', return_value={}), \
            patch.object(executor.fetch_client, 'fetch') as mock_fetch, \
            patch.object(executor.iframe_extractor, 'extract_iframes') as mock_extract:

        caps = MagicMock()
        caps.supports_proxy = True
        mock_caps.return_value = caps
        mock_build.return_value = ({'_user_data_cleanup': cleanup}, {})
        mock_fetch.return_value = SimpleNamespace(status=200, html_content=html_with_iframe)
        mock_extract.return_value = (processed_html, [{"src": "https://external.com/content"}])

        response = executor.execute(request)

    assert response.status == 'success'
    assert response.html == processed_html
    mock_extract.assert_called_once_with(html_with_iframe, "https://example.com/", {})
    cleanup.assert_called_once()


def test_single_executor_handles_iframe_processing_failure(monkeypatch):
    """Test that single executor continues when iframe processing fails."""
    monkeypatch.setattr(
        'app.services.crawler.executors.single_executor.app_config.get_settings',
        _settings_factory,
    )
    executor = SingleAttemptExecutor()
    request = CrawlRequest(url="https://example.com")

    cleanup = MagicMock()
    original_html = '<html><body><p>Content</p></body></html>'

    with patch.object(executor.options_resolver, 'resolve', return_value={}), \
            patch.object(executor.fetch_client, 'detect_capabilities') as mock_caps, \
            patch.object(executor.camoufox_builder, 'build') as mock_build, \
            patch.object(executor.arg_composer, 'compose', return_value={}), \
            patch.object(executor.fetch_client, 'fetch') as mock_fetch, \
            patch.object(executor.iframe_extractor, 'extract_iframes') as mock_extract:

        caps = MagicMock()
        caps.supports_proxy = True
        mock_caps.return_value = caps
        mock_build.return_value = ({'_user_data_cleanup': cleanup}, {})
        mock_fetch.return_value = SimpleNamespace(status=200, html_content=original_html)
        mock_extract.side_effect = Exception("Iframe processing failed")

        response = executor.execute(request)

    assert response.status == 'success'
    # Should continue with original HTML when iframe processing fails
    assert response.html == original_html
    mock_extract.assert_called_once()
    cleanup.assert_called_once()
