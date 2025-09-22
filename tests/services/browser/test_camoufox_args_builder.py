import os
import platform
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.services.common.types import FetchCapabilities


def _expected_path(raw_path: str) -> str:
    """Normalize a filesystem path in the same way as CamoufoxArgsBuilder."""
    if platform.system() == "Windows":
        return str(Path(raw_path).resolve())
    return os.path.abspath(raw_path)


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
        return SimpleNamespace(
            force_user_data=False,
            url='https://example.com',
            force_mute_audio=None,
        )

    @pytest.fixture
    def mock_settings(self, tmp_path_factory):
        return SimpleNamespace(
            camoufox_user_data_dir=str(tmp_path_factory.mktemp("camoufox_profiles")),
            camoufox_locale=None,
            camoufox_window=None,
            camoufox_disable_coop=False,
            camoufox_virtual_display=None,
            camoufox_force_mute_audio_default=True,
            camoufox_runtime_force_mute_audio=False,
            camoufox_runtime_user_data_mode=None,
            camoufox_runtime_effective_user_data_dir=None,
        )

    def test_build_no_user_data(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = False

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert 'user_data_dir' not in additional_args
        prefs = additional_args.get('firefox_user_prefs')
        assert prefs is not None
        assert prefs['dom.audiochannel.mutedByDefault'] is True
        assert extra_headers is None

    def test_build_with_user_data_read_mode(
        self, builder, mock_request, mock_settings, mock_caps, tmp_path
    ):
        # Arrange
        mock_request.force_user_data = True
        mock_settings.camoufox_runtime_user_data_mode = None  # Read mode default

        mock_context = MagicMock()
        mock_cleanup = Mock()
        clone_dir = tmp_path / "clone"
        mock_context.__enter__.return_value = (str(clone_dir), mock_cleanup)
        mock_context.__exit__.return_value = False

        with patch('app.services.common.browser.user_data.user_data_context', return_value=mock_context):
            # Act
            additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

            # Assert
            assert additional_args['user_data_dir'] == _expected_path(str(clone_dir))
            assert '_user_data_cleanup' in additional_args
            assert additional_args['_user_data_cleanup'] == mock_cleanup
            assert extra_headers is None

    def test_build_with_user_data_write_mode(
        self, builder, mock_request, mock_settings, mock_caps, tmp_path
    ):
        # Arrange
        mock_request.force_user_data = True
        mock_settings.camoufox_runtime_user_data_mode = 'write'
        master_dir = tmp_path / "master"
        mock_settings.camoufox_runtime_effective_user_data_dir = str(master_dir)

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert additional_args['user_data_dir'] == _expected_path(str(master_dir))
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

    def test_build_force_mute_from_payload(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_mute_audio = True

        # Act
        additional_args, _ = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        prefs = additional_args.get('firefox_user_prefs')
        assert prefs is not None
        assert prefs['dom.audiochannel.mutedByDefault'] is True
        assert prefs['media.default_volume'] == 0.0
        assert prefs['media.volume_scale'] == 0.0

    def test_build_respects_config_default(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_force_mute_audio_default = False
        mock_request.force_mute_audio = None

        # Act
        additional_args, _ = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        prefs = additional_args.get('firefox_user_prefs')
        assert prefs is None

    def test_build_force_mute_from_settings(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_settings.camoufox_force_mute_audio_default = False
        mock_settings.camoufox_runtime_force_mute_audio = True
        mock_request.force_mute_audio = False

        # Act
        additional_args, _ = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        prefs = additional_args.get('firefox_user_prefs')
        assert prefs is not None
        assert prefs['dom.audiochannel.mutedByDefault'] is True
        assert prefs['media.default_volume'] == 0.0
        assert prefs['media.volume_scale'] == 0.0

    def test_build_no_camoufox_user_data_dir(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings.camoufox_user_data_dir = None

        # Act
        additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

        # Assert
        assert 'user_data_dir' not in additional_args
        prefs = additional_args.get('firefox_user_prefs')
        assert prefs is not None
        assert prefs['dom.audiochannel.mutedByDefault'] is True
        assert prefs['media.default_volume'] == 0.0
        assert prefs['media.volume_scale'] == 0.0

    def test_build_user_data_dir_permission_error(self, builder, mock_request, mock_settings, mock_caps):
        # Arrange
        mock_request.force_user_data = True
        mock_settings.camoufox_runtime_user_data_mode = None
        unwritable_dir = Path(tempfile.gettempdir()) / "non" / "writable" / "dir"
        mock_settings.camoufox_user_data_dir = str(unwritable_dir)

        with patch('os.access', return_value=False):
            with pytest.warns(UserWarning):
                # Act
                additional_args, extra_headers = builder.build(mock_request, mock_settings, mock_caps)

                # Assert
                assert 'user_data_dir' not in additional_args
                prefs = additional_args.get('firefox_user_prefs')
                assert prefs is not None
                assert prefs['dom.audiochannel.mutedByDefault'] is True
                assert prefs['media.default_volume'] == 0.0
                assert prefs['media.volume_scale'] == 0.0
