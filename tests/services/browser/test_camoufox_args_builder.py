import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.schemas.crawl import CrawlRequest
from app.services.common.types import FetchCapabilities


class TestCamoufoxArgsBuilder:
    @pytest.fixture
    def builder(self):
        return CamoufoxArgsBuilder()

    @pytest.fixture
    def mock_caps(self):
        caps = Mock(spec=FetchCapabilities)
        caps.supports_user_data_dir = True
        caps.supports_profile_dir = True
        caps.supports_profile_path = True
        caps.supports_user_data = True
        return caps

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=CrawlRequest)
        request.force_user_data = False
        request.url = 'https://example.com'
        return request

    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.camoufox_user_data_dir = '/tmp/camoufox_profiles'
        settings.camoufox_locale = None
        settings.camoufox_window = None
        settings.camoufox_disable_coop = False
        settings.camoufox_virtual_display = None
        return settings

    def test_build_no_user_data(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = False

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert 'user_data_dir' not in additional_args
        assert additional_args == {}
        assert extra_headers is None

    def test_build_with_user_data_read_mode(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings._camoufox_user_data_mode = None  # Read mode default

        mock_context = MagicMock()
        mock_cleanup = Mock()
        mock_context.__enter__.return_value = ('/tmp/clone', mock_cleanup)
        mock_context.__exit__.return_value = False

        with patch('app.services.common.browser.user_data.user_data_context', return_value=mock_context):
            # Act
            additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

            # Assert
            assert additional_args['user_data_dir'] == '/tmp/clone'
            assert '_user_data_cleanup' in additional_args
            assert additional_args['_user_data_cleanup'] == mock_cleanup
            assert extra_headers is None

    def test_build_with_user_data_write_mode(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings._camoufox_user_data_mode = 'write'
        mock_settings._camoufox_effective_user_data_dir = '/tmp/master'

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['user_data_dir'] == '/tmp/master'
        assert '_user_data_cleanup' not in additional_args
        assert extra_headers is None

    def test_build_window_size(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_window = '1280x720'

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['window'] == (1280, 720)

    def test_build_locale(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_locale = 'en-US'

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['locale'] == 'en-US'
        assert extra_headers == {"Accept-Language": 'en-US'}

    def test_build_disable_coop(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_disable_coop = True

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['disable_coop'] is True

    def test_build_virtual_display(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_virtual_display = 'xvfb:99'

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['virtual_display'] == 'xvfb:99'

    def test_build_no_camoufox_user_data_dir(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings.camoufox_user_data_dir = None

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert 'user_data_dir' not in additional_args
        assert additional_args == {}

    def test_build_user_data_dir_permission_error(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings._camoufox_user_data_mode = None
        mock_settings.camoufox_user_data_dir = '/non/writable/dir'

        with patch('os.access', return_value=False):
            with pytest.warns(UserWarning):
                # Act
                additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

                # Assert
                assert 'user_data_dir' not in additional_args
