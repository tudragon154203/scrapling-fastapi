import random
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.browser.actions.humanize import (
    human_pause,
    move_mouse_to_locator,
    jitter_mouse,
    click_like_human,
    type_like_human,
    scroll_noise,
)


class TestHumanizeActions:
    """Unit tests for humanization functions in humanize.py."""

    def setup_method(self):
        """Set up deterministic random seed for all tests."""
        random.seed(42)  # Fixed seed for reproducible tests

    def test_human_pause(self):
        """Test human_pause uses random delay within specified range."""
        with patch('time.sleep') as mock_sleep:
            human_pause(0.5, 1.5)
            delay = mock_sleep.call_args[0][0]
            assert 0.5 <= delay <= 1.5

    def test_move_mouse_to_locator_with_bounding_box(self):
        """Test move_mouse_to_locator moves to center of locator with random steps."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.bounding_box.return_value = {'x': 100, 'y': 200, 'width': 50, 'height': 30}

        # Mock settings for steps range
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.auspost_mouse_steps_min = 12
            mock_settings.return_value.auspost_mouse_steps_max = 28

            move_mouse_to_locator(mock_page, mock_locator)

            # Verify hover was called (pre_hover=True by default)
            mock_locator.hover.assert_called_once()

            # Verify mouse.move was called with center coordinates and steps in range
            mock_page.mouse.move.assert_called_once()
            args, kwargs = mock_page.mouse.move.call_args
            assert args[0] == 125  # x + width/2
            assert args[1] == 215  # y + height/2
            steps = kwargs['steps']
            assert 12 <= steps <= 28

    def test_move_mouse_to_locator_no_bounding_box(self):
        """Test move_mouse_to_locator skips when no bounding box."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.bounding_box.return_value = None

        move_mouse_to_locator(mock_page, mock_locator)

        # Should not call hover or mouse.move
        mock_locator.hover.assert_not_called()
        mock_page.mouse.move.assert_not_called()

    def test_jitter_mouse(self):
        """Test jitter_mouse moves mouse by small random amounts."""
        mock_page = MagicMock()
        mock_page.mouse._x = 100
        mock_page.mouse._y = 200

        jitter_mouse(mock_page)

        mock_page.mouse.move.assert_called_once()
        args, kwargs = mock_page.mouse.move.call_args
        # Should move within radius 3 of current position
        assert 97 <= args[0] <= 103  # 100 ± 3
        assert 197 <= args[1] <= 203  # 200 ± 3
        assert kwargs['steps'] == 2

    def test_click_like_human(self):
        """Test click_like_human hovers and clicks."""
        mock_locator = MagicMock()

        click_like_human(mock_locator)

        mock_locator.hover.assert_called_once()
        mock_locator.click.assert_called_once()

    def test_click_like_human_no_hover(self):
        """Test click_like_human without hover."""
        mock_locator = MagicMock()

        click_like_human(mock_locator, hover_first=False)

        mock_locator.hover.assert_not_called()
        mock_locator.click.assert_called_once()

    def test_type_like_human(self):
        """Test type_like_human fills and types with delay."""
        mock_locator = MagicMock()

        # Mock settings for delay range
        with patch('app.core.config.get_settings') as mock_settings:
            mock_settings.return_value.auspost_typing_delay_ms_min = 60
            mock_settings.return_value.auspost_typing_delay_ms_max = 140

            type_like_human(mock_locator, "test text")

            # Verify fill was called to clear
            mock_locator.fill.assert_called_once_with("")

            # Verify type was called with text and delay in range
            mock_locator.type.assert_called_once()
            args, kwargs = mock_locator.type.call_args
            assert args[0] == "test text"
            delay = kwargs['delay']
            assert 60 <= delay <= 140

    def test_scroll_noise(self):
        """Test scroll_noise performs random wheel movements."""
        mock_page = MagicMock()

        with patch('time.sleep'):  # Mock sleep to speed up test
            scroll_noise(mock_page)

            # Should call mouse.wheel multiple times
            assert mock_page.mouse.wheel.call_count >= 1
            assert mock_page.mouse.wheel.call_count <= 3  # cycles_range=(1,3)

            # Each call should have dy in range (120, 480) or negative
            for call in mock_page.mouse.wheel.call_args_list:
                args = call[0]
                dy = args[1]
                assert -480 <= dy <= -120 or 120 <= dy <= 480

    def test_scroll_noise_with_custom_ranges(self):
        """Test scroll_noise with custom ranges."""
        mock_page = MagicMock()

        with patch('time.sleep'):
            scroll_noise(mock_page, cycles_range=(2, 2), dy_range=(100, 200))

            # Should call exactly 2 times
            assert mock_page.mouse.wheel.call_count == 2

            for call in mock_page.mouse.wheel.call_args_list:
                args = call[0]
                dy = args[1]
                assert -200 <= dy <= -100 or 100 <= dy <= 200

    def test_move_mouse_to_locator_custom_steps_range(self):
        """Test move_mouse_to_locator with custom steps range."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.bounding_box.return_value = {'x': 0, 'y': 0, 'width': 10, 'height': 10}

        move_mouse_to_locator(mock_page, mock_locator, steps_range=(5, 10))

        mock_page.mouse.move.assert_called_once()
        args, kwargs = mock_page.mouse.move.call_args
        steps = kwargs['steps']
        assert 5 <= steps <= 10

    def test_type_like_human_custom_delay_range(self):
        """Test type_like_human with custom delay range."""
        mock_locator = MagicMock()

        type_like_human(mock_locator, "test", delay_ms_range=(50, 100))

        mock_locator.type.assert_called_once()
        args, kwargs = mock_locator.type.call_args
        delay = kwargs['delay']
        assert 50 <= delay <= 100
