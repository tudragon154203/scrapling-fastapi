
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock, ANY
from pathlib import Path

from app.services.browser.browse import BrowseCrawler
from app.schemas.browse import BrowseRequest
from app.services.common.engine import CrawlerEngine
from app.schemas.crawl import CrawlRequest


@pytest.fixture
def mock_engine():
    engine = Mock(spec=CrawlerEngine)
    engine.run.return_value = None
    return engine


@pytest.fixture
def mock_settings():
    settings = Mock()
    settings.camoufox_user_data_dir = '/tmp/camoufox_profiles'
    return settings


class TestBrowseCrawler:
    def test_browse_crawler_sets_write_mode_and_master_dir(self, mock_engine, mock_settings):
        # Arrange
        crawler = BrowseCrawler(engine=mock_engine)
        request = BrowseRequest(url='https://example.com')

        mock_ctx = MagicMock()
        mock_cleanup = Mock()
        mock_ctx.__enter__.return_value = ('/mock/master', mock_cleanup)
        mock_ctx.__exit__.return_value = False

        with patch('app.services.browser.browse.app_config.get_settings', return_value=mock_settings), \
                patch('app.services.browser.browse.user_data_mod.user_data_context', return_value=mock_ctx):
            # Act
            result = crawler.run(request)

            # Assert
            mock_ctx.assert_called_once_with('/tmp/camoufox_profiles', 'write')
            mock_engine.run.assert_called_once()
            crawl_req = mock_engine.run.call_args.args[0]
