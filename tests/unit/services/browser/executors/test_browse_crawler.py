
from app.schemas.crawl import CrawlRequest
from app.services.common.engine import CrawlerEngine
from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.browser.browse import BrowseCrawler
import pytest
from unittest.mock import MagicMock, Mock, patch

pytestmark = [pytest.mark.unit]


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
                patch('app.services.browser.browse.user_data_mod.user_data_context') as user_data_ctx_mock:
            user_data_ctx_mock.return_value = mock_ctx
            # Act
            result = crawler.run(request)

            # Assert
            user_data_ctx_mock.assert_called_once_with('/tmp/camoufox_profiles', 'write')
            mock_engine.run.assert_called_once()
            crawl_req = mock_engine.run.call_args.args[0]
            assert isinstance(crawl_req, CrawlRequest)
            assert crawl_req.force_user_data is True
            assert isinstance(result, BrowseResponse)
            assert result.status == 'success'
