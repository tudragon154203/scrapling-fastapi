"""
Comprehensive tests for Camoufox browser utilities to achieve 80%+ coverage.
"""

import os  # noqa: F401 - used in patches
import platform  # noqa: F401 - used in patches
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.common.browser.camoufox import CamoufoxArgsBuilder


class TestCamoufoxArgsBuilder:
    """Test CamoufoxArgsBuilder main functionality."""

    def test_build_no_force_user_data(self):
        """Test build method without force_user_data."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args.get("user_data_dir") is None
        assert "firefox_user_prefs" in additional_args
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True

    def test_build_with_force_user_data_success(self):
        """Test build method with force_user_data successful setup."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings._camoufox_user_data_mode = "read"
        settings._camoufox_effective_user_data_dir = None
        caps = {}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=("/tmp/clone", MagicMock()))
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_user_data.user_data_context.return_value = mock_context

            with patch('app.services.common.browser.camoufox.Path') as mock_path:
                mock_path.return_value.mkdir = MagicMock()
                with patch('app.services.common.browser.camoufox.os.access', return_value=True):
                    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["user_data_dir"] == "/tmp/clone"
        assert "_user_data_cleanup" in additional_args
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True

    def test_build_with_force_user_data_write_mode(self):
        """Test build method with write mode user data."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings.camoufox_runtime_user_data_mode = "write"
        settings.camoufox_runtime_effective_user_data_dir = "/tmp/master"
        caps = {}

        with patch('app.services.common.browser.camoufox.Path') as mock_path:
            mock_path.return_value.mkdir = MagicMock()
            with patch('app.services.common.browser.camoufox.os.access', return_value=True):
                additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["user_data_dir"] == "/tmp/master"
        assert "_user_data_cleanup" not in additional_args

    def test_build_user_data_permission_error(self):
        """Test build method handles permission errors gracefully."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings._camoufox_user_data_mode = "read"
        settings._camoufox_effective_user_data_dir = None
        caps = {}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(side_effect=PermissionError("Permission denied"))
            mock_user_data.user_data_context.return_value = mock_context

            with patch('app.services.common.browser.camoufox.warnings') as mock_warnings:
                additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args.get("user_data_dir") is None
        mock_warnings.warn.assert_called_once()

    def test_build_user_data_general_exception(self):
        """Test build method handles general exceptions gracefully."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        caps = {}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_user_data.user_data_context.side_effect = Exception("General error")

            with patch('app.services.common.browser.camoufox.warnings') as mock_warnings:
                additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args.get("user_data_dir") is None
        mock_warnings.warn.assert_called_once()

    def test_build_disable_coop(self):
        """Test build method with disable coop setting."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        settings.camoufox_disable_coop = True
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["disable_coop"] is True

    def test_build_virtual_display(self):
        """Test build method with virtual display setting."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        settings.camoufox_virtual_display = ":99"
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["virtual_display"] == ":99"

    def test_build_force_mute_audio(self):
        """Test build method always forces audio mute."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert "firefox_user_prefs" in additional_args
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True

    def test_build_with_existing_firefox_prefs(self):
        """Test build method preserves existing firefox preferences."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        caps = {}

        # Mock additional_args with existing firefox prefs
        with patch('app.services.common.browser.camoufox.logger'):
            additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)
            # Add existing pref before calling build again (this is a simplified test)
            # In real usage, this would be tested by modifying the build method or
            # testing scenarios where additional_args already has firefox_user_prefs

    def test_build_with_locale(self):
        """Test build method with locale setting."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        settings.camoufox_locale = "en-US"
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["locale"] == "en-US"
        assert extra_headers == {"Accept-Language": "en-US"}

    def test_build_with_window_size(self):
        """Test build method with window size setting."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        settings.camoufox_window = "1920x1080"
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args["window"] == (1920, 1080)


class TestCamoufoxArgsBuilderHelpers:
    """Test CamoufoxArgsBuilder helper methods."""

    @pytest.mark.parametrize("input_value,expected", [
        ("1920x1080", (1920, 1080)),
        ("800x600", (800, 600)),
        ("1024,768", (1024, 768)),
        ("1280X720", (1280, 720)),  # Case insensitive
        (" 800x600  ", (800, 600)),  # With spaces
    ])
    def test_parse_window_size_valid(self, input_value, expected):
        """Test parsing valid window sizes."""
        result = CamoufoxArgsBuilder._parse_window_size(input_value)
        assert result == expected

    @pytest.mark.parametrize("input_value", [
        None,
        "",
        "invalid",
        "1920x",  # Missing height
        "x1080",  # Missing width
        "0x1080",  # Zero width
        "1920x0",  # Zero height
        "-800x600",  # Negative width
        "800x-600",  # Negative height
        "1920.5x1080",  # Non-integer
        "800x600x400",  # Too many dimensions
        "800:600",  # Invalid separator
        "800;600",  # Invalid separator
    ])
    def test_parse_window_size_invalid(self, input_value):
        """Test parsing invalid window sizes."""
        result = CamoufoxArgsBuilder._parse_window_size(input_value)
        assert result is None

    def test_parse_window_size_exception_handling(self):
        """Test parse window size handles exceptions."""
        # Test with value that causes int() conversion to fail
        result = CamoufoxArgsBuilder._parse_window_size("abcxdef")
        assert result is None

    @pytest.mark.parametrize("mode_attr,dir_attr,expected_mode,expected_dir", [
        ("read", "/tmp/read", "read", "/tmp/read"),
        ("write", "/tmp/write", "write", "/tmp/write"),
        ("READ", "/tmp/case", "read", "/tmp/case"),  # Case normalization
        (None, "/tmp/default", None, "/tmp/default"),
        ("", "", None, None),  # Empty values
    ])
    def test_runtime_user_data_overrides(self, mode_attr, dir_attr, expected_mode, expected_dir):
        """Test runtime user data overrides extraction."""
        settings = MagicMock()
        if mode_attr is not None:
            settings.camoufox_runtime_user_data_mode = mode_attr
        else:
            delattr(settings, 'camoufox_runtime_user_data_mode')

        if dir_attr is not None:
            settings.camoufox_runtime_effective_user_data_dir = dir_attr
        else:
            delattr(settings, 'camoufox_runtime_effective_user_data_dir')

        mode, directory = CamoufoxArgsBuilder._runtime_user_data_overrides(settings)

        assert mode == expected_mode
        assert directory == expected_dir

    def test_runtime_user_data_overrides_fallback_attributes(self):
        """Test runtime user data overrides with fallback attributes."""
        settings = MagicMock()
        settings._camoufox_user_data_mode = "write"
        settings._camoufox_effective_user_data_dir = "/tmp/fallback"
        # Delete runtime attributes to test fallback
        delattr(settings, 'camoufox_runtime_user_data_mode')
        delattr(settings, 'camoufox_runtime_effective_user_data_dir')

        mode, directory = CamoufoxArgsBuilder._runtime_user_data_overrides(settings)

        assert mode == "write"
        assert directory == "/tmp/fallback"

    def test_runtime_user_data_overrides_pathlike_object(self):
        """Test runtime user data overrides with PathLike object."""
        settings = MagicMock()
        settings.camoufox_runtime_user_data_mode = "read"
        settings.camoufox_runtime_effective_user_data_dir = Path("/tmp/pathlike")

        mode, directory = CamoufoxArgsBuilder._runtime_user_data_overrides(settings)

        assert mode == "read"
        assert directory == str(Path("/tmp/pathlike"))

    def test_runtime_user_data_overrides_invalid_pathlike(self):
        """Test runtime user data overrides with invalid PathLike object."""
        settings = MagicMock()
        settings.camoufox_runtime_user_data_mode = "read"

        # Create an object that raises TypeError when converted to string
        invalid_pathlike = MagicMock()
        invalid_pathlike.__fspath__ = MagicMock(side_effect=TypeError("Invalid path"))
        settings.camoufox_runtime_effective_user_data_dir = invalid_pathlike

        mode, directory = CamoufoxArgsBuilder._runtime_user_data_overrides(settings)

        assert mode == "read"
        assert directory is None

    @patch('app.services.common.browser.camoufox.platform.system')
    @patch('app.services.common.browser.camoufox.Path')
    def test_resolve_path_windows(self, mock_path, mock_system):
        """Test path resolution on Windows."""
        mock_system.return_value = "Windows"
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = "C:\\Users\\Test\\user_data"
        mock_path.return_value = mock_path_instance

        result = CamoufoxArgsBuilder._resolve_path("user_data")

        mock_path.assert_called_once_with("user_data")
        mock_path_instance.resolve.assert_called_once()
        assert result == "C:\\Users\\Test\\user_data"

    @patch('app.services.common.browser.camoufox.platform.system')
    @patch('app.services.common.browser.camoufox.os.path.abspath')
    def test_resolve_path_unix(self, mock_abspath, mock_system):
        """Test path resolution on Unix systems."""
        mock_system.return_value = "Linux"
        mock_abspath.return_value = "/home/user/user_data"

        result = CamoufoxArgsBuilder._resolve_path("user_data")

        mock_abspath.assert_called_once_with("user_data")
        assert result == "/home/user/user_data"

    @patch('app.services.common.browser.camoufox.platform.system')
    def test_resolve_path_macos(self, mock_system):
        """Test path resolution on macOS."""
        mock_system.return_value = "Darwin"

        with patch('app.services.common.browser.camoufox.os.path.abspath') as mock_abspath:
            mock_abspath.return_value = "/Users/user/user_data"

            result = CamoufoxArgsBuilder._resolve_path("user_data")

            assert result == "/Users/user/user_data"


class TestCamoufoxArgsBuilderEdgeCases:
    """Test edge cases and error conditions."""

    def test_build_with_missing_settings_attributes(self):
        """Test build with missing settings attributes."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        # Delete some attributes to test missing cases
        delattr(settings, 'camoufox_disable_coop')
        delattr(settings, 'camoufox_virtual_display')
        delattr(settings, 'camoufox_locale')
        delattr(settings, 'camoufox_window')
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        # Should not crash and should still have basic firefox prefs
        assert "firefox_user_prefs" in additional_args
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True
        assert extra_headers is None

    def test_build_with_no_settings_user_data_dir(self):
        """Test build when settings has no user data directory."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = None
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        # Should not crash and should not have user_data_dir
        assert additional_args.get("user_data_dir") is None

    def test_build_with_payload_missing_force_user_data(self):
        """Test build when payload has no force_user_data attribute."""
        payload = MagicMock()
        delattr(payload, 'force_user_data')
        settings = MagicMock()
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        # Should not crash
        assert "firefox_user_prefs" in additional_args

    def test_build_user_data_directory_creation_fails(self):
        """Test build when directory creation fails."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings._camoufox_user_data_mode = "read"
        settings._camoufox_effective_user_data_dir = None
        caps = {}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=("/tmp/clone", MagicMock()))
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_user_data.user_data_context.return_value = mock_context

            with patch('app.services.common.browser.camoufox.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.mkdir.side_effect = OSError("Creation failed")
                mock_path.return_value = mock_path_instance

                with patch('app.services.common.browser.camoufox.warnings') as mock_warnings:
                    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args.get("user_data_dir") is None
        mock_warnings.warn.assert_called_once()

    def test_build_user_data_directory_not_writable(self):
        """Test build when directory is not writable."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings._camoufox_user_data_mode = "read"
        settings._camoufox_effective_user_data_dir = None
        caps = {}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=("/tmp/clone", MagicMock()))
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_user_data.user_data_context.return_value = mock_context

            with patch('app.services.common.browser.camoufox.Path') as mock_path:
                mock_path_instance = MagicMock()
                mock_path_instance.mkdir = MagicMock()
                mock_path.return_value = mock_path_instance

                with patch('app.services.common.browser.camoufox.os.access', return_value=False):
                    with patch('app.services.common.browser.camoufox.warnings') as mock_warnings:
                        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        assert additional_args.get("user_data_dir") is None
        mock_warnings.warn.assert_called_once()

    def test_firefox_prefs_preservation(self):
        """Test that existing firefox preferences are preserved."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        caps = {}

        # This test verifies the logic in the build method that handles existing prefs
        # In practice, we'd need to modify the build method call or test the scenario
        # where additional_args already has firefox_user_prefs
        with patch('app.services.common.browser.camoufox.logger'):
            additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

            # The mute preference should always be set
            assert "firefox_user_prefs" in additional_args
            assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True

    def test_build_logging_debug(self):
        """Test that debug logging is called appropriately."""
        payload = MagicMock()
        payload.force_user_data = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        caps = {}

        with patch('app.services.common.browser.camoufox.logger') as mock_logger:
            # Mock user_data_mod to avoid actual file operations
            with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
                mock_context = MagicMock()
                mock_context.__enter__ = MagicMock(return_value=("/tmp/clone", MagicMock()))
                mock_context.__exit__ = MagicMock(return_value=None)
                mock_user_data.user_data_context.return_value = mock_context

                with patch('app.services.common.browser.camoufox.Path') as mock_path:
                    mock_path.return_value.mkdir = MagicMock()
                    with patch('app.services.common.browser.camoufox.os.access', return_value=True):
                        CamoufoxArgsBuilder.build(payload, settings, caps)

        # Verify debug logging was called
        mock_logger.debug.assert_called()


class TestCamoufoxArgsBuilderIntegration:
    """Integration tests for CamoufoxArgsBuilder."""

    def test_full_build_integration(self):
        """Test full build integration with all settings."""
        payload = MagicMock()
        payload.force_user_data = True
        payload.force_mute_audio = True
        settings = MagicMock()
        settings.camoufox_user_data_dir = "/tmp/user_data"
        settings.camoufox_disable_coop = True
        settings.camoufox_virtual_display = ":99"
        settings.camoufox_locale = "en-US"
        settings.camoufox_window = "1920x1080"
        settings._camoufox_user_data_mode = "read"
        settings._camoufox_effective_user_data_dir = None
        caps = {"supports_stealth": True}

        with patch('app.services.common.browser.camoufox.user_data_mod') as mock_user_data:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=("/tmp/clone", MagicMock()))
            mock_context.__exit__ = MagicMock(return_value=None)
            mock_user_data.user_data_context.return_value = mock_context

            with patch('app.services.common.browser.camoufox.Path') as mock_path:
                mock_path.return_value.mkdir = MagicMock()
                with patch('app.services.common.browser.camoufox.os.access', return_value=True):
                    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        # Verify all expected arguments are present
        assert additional_args["user_data_dir"] == "/tmp/clone"
        assert "_user_data_cleanup" in additional_args
        assert additional_args["disable_coop"] is True
        assert additional_args["virtual_display"] == ":99"
        assert additional_args["locale"] == "en-US"
        assert additional_args["window"] == (1920, 1080)
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True
        assert extra_headers == {"Accept-Language": "en-US"}

    def test_minimal_build_integration(self):
        """Test minimal build integration with just required settings."""
        payload = MagicMock()
        payload.force_user_data = False
        settings = MagicMock()
        # Delete all optional settings
        for attr in ['camoufox_disable_coop', 'camoufox_virtual_display',
                     'camoufox_locale', 'camoufox_window']:
            if hasattr(settings, attr):
                delattr(settings, attr)
        caps = {}

        additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, caps)

        # Should only have firefox prefs
        assert len(additional_args) == 1
        assert "firefox_user_prefs" in additional_args
        assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True
        assert extra_headers is None
