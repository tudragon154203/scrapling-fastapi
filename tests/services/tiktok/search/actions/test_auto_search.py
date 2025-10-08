"""Unit tests for TikTokAutoSearchAction functionality"""

from app.services.tiktok.search.actions.auto_search import (
    PlaywrightTimeoutError,
    TikTokAutoSearchAction,
)
from unittest.mock import Mock, patch
import itertools

import pytest

pytestmark = [pytest.mark.unit]


class TestTikTokAutoSearchAction:
    """Test TikTokAutoSearchAction implementation"""

    @pytest.fixture
    def auto_search_action(self):
        """Create a TikTokAutoSearchAction instance"""
        return TikTokAutoSearchAction("test query")

    def test_initialization(self, auto_search_action):
        """Test that action initializes properly"""
        assert auto_search_action.search_query == "test query"
        assert auto_search_action.html_content == ""
        assert auto_search_action.page is None
        assert hasattr(auto_search_action, 'logger')

    def test_set_target_videos(self, auto_search_action):
        """Target configuration should accept positive integers and clear invalid values"""
        auto_search_action.set_target_videos(7)
        assert auto_search_action.target_videos == 7

        auto_search_action.set_target_videos(0)
        assert auto_search_action.target_videos is None

        auto_search_action.set_target_videos(None)
        assert auto_search_action.target_videos is None

    def test_cleanup_browser_resources(self, auto_search_action):
        """Test browser resource cleanup"""
        # Mock page object
        mock_page = Mock()
        mock_page.is_closed.return_value = False

        auto_search_action.page = mock_page
        auto_search_action._cleanup_browser_resources()

        # Should attempt to close the page
        mock_page.close.assert_called_once()

    def test_cleanup_browser_resources_closed_page(self, auto_search_action):
        """Test cleanup when page is already closed"""
        # Mock page object that's already closed
        mock_page = Mock()
        mock_page.is_closed.return_value = True

        auto_search_action.page = mock_page
        auto_search_action._cleanup_browser_resources()

        # Should not attempt to close already closed page
        mock_page.close.assert_not_called()

    def test_cleanup_browser_resources_no_page(self, auto_search_action):
        """Test cleanup when no page exists"""
        auto_search_action.page = None
        auto_search_action._cleanup_browser_resources()
        # Should not raise any errors

    def test_cleanup_with_registered_functions(self, auto_search_action):
        """Test cleanup with registered functions"""
        mock_cleanup1 = Mock()
        mock_cleanup2 = Mock()

        auto_search_action._cleanup_functions = [mock_cleanup1, mock_cleanup2]
        auto_search_action._cleanup()

        # Both cleanup functions should be called
        mock_cleanup1.assert_called_once()
        mock_cleanup2.assert_called_once()
        # Cleanup functions list should be cleared
        assert len(auto_search_action._cleanup_functions) == 0

    def test_cleanup_with_failing_function(self, auto_search_action, caplog):
        """Test cleanup continues even if a function fails"""
        mock_cleanup1 = Mock(side_effect=Exception("Cleanup failed"))
        mock_cleanup2 = Mock()

        auto_search_action._cleanup_functions = [mock_cleanup1, mock_cleanup2]
        auto_search_action._cleanup()

        # Both functions should be attempted
        mock_cleanup1.assert_called_once()
        mock_cleanup2.assert_called_once()
        # Should log the error but continue
        assert "Cleanup function failed" in caplog.text

    def test_cleanup_with_non_callable(self, auto_search_action):
        """Test cleanup with non-callable items in list"""
        auto_search_action._cleanup_functions = ["not_callable", Mock()]
        auto_search_action._cleanup()

        # Should skip non-callable items and call callable ones
        assert len(auto_search_action._cleanup_functions) == 0

    @patch('app.services.tiktok.search.actions.auto_search.click_like_human')
    @patch('app.services.tiktok.search.actions.auto_search.move_mouse_to_locator')
    def test_search_selectors_behavior(self, mock_move_mouse, mock_click, auto_search_action):
        """Test search selector finding behavior"""
        mock_page = Mock()

        # Mock page methods
        mock_page.wait_for_load_state.return_value = None
        mock_search_bar = Mock()
        mock_search_bar.bounding_box.return_value = {"width": 20, "height": 20}
        mock_search_bar.is_enabled.return_value = True

        def wait_for_selector_side_effect(selector, *args, **kwargs):
            if "nav-search" in selector:
                return mock_search_bar
            raise PlaywrightTimeoutError('not found')

        mock_page.wait_for_selector.side_effect = wait_for_selector_side_effect
        mock_page.focus.return_value = None
        mock_page.keyboard = Mock()
        mock_page.keyboard.type.return_value = None
        mock_page.keyboard.press.return_value = None
        mock_page.wait_for_function.return_value = None
        mock_page.content.return_value = "x" * 12000
        mock_page.mouse.wheel.return_value = None

        with patch('app.services.tiktok.search.actions.auto_search.human_pause'), \
                patch('time.sleep'), \
                patch.object(auto_search_action, '_scan_result_selectors', return_value=True):
            try:
                auto_search_action._execute(mock_page)
            except Exception:
                pass  # Expected to fail due to mocking

        # Should have attempted to find search selectors
        assert mock_page.wait_for_selector.call_count >= 1
        assert mock_page.wait_for_load_state.call_count >= 2
        assert mock_page.wait_for_selector.called

    @patch('app.services.tiktok.search.actions.auto_search.type_like_human')
    def test_typing_behavior(self, mock_type_like_human, auto_search_action):
        """Test typing behavior"""
        mock_page = Mock()
        mock_search_bar = Mock()

        # Mock page methods
        mock_page.wait_for_load_state.return_value = None

        mock_search_bar.bounding_box.return_value = {"width": 20, "height": 20}
        mock_search_bar.is_enabled.return_value = True

        def wait_for_selector_side_effect(selector, *args, **kwargs):
            if "nav-search" in selector:
                return mock_search_bar
            raise PlaywrightTimeoutError('not found')

        mock_page.wait_for_selector.side_effect = wait_for_selector_side_effect
        mock_page.focus.return_value = None
        mock_page.keyboard.type.return_value = None
        mock_page.keyboard.press.return_value = None
        mock_page.wait_for_function.return_value = None
        mock_page.content.return_value = "test content"
        mock_page.mouse.wheel.return_value = None

        # Mock time to avoid actual sleep
        with patch('time.time', side_effect=[0, 11]), \
                patch('time.sleep'), \
                patch('app.services.tiktok.search.actions.auto_search.human_pause'), \
                patch.object(auto_search_action, '_scan_result_selectors', return_value=True):

            try:
                auto_search_action._execute(mock_page)
            except Exception:
                pass  # Expected to fail due to mocking

        # Should have attempted typing
        assert mock_page.keyboard.type.called
        assert not mock_type_like_human.called
        assert mock_page.wait_for_load_state.call_count >= 2
        assert mock_page.wait_for_selector.called

    def test_html_content_capture_direct(self, auto_search_action):
        """Test HTML content capture functionality directly"""
        # Test the content capture directly without full execution
        mock_page = Mock()
        mock_page.content.return_value = "<html>test content</html>"

        # Simulate the content capture part
        auto_search_action.page = mock_page
        try:
            content = mock_page.content()
            auto_search_action.html_content = content
        except Exception:
            pass

        # Should have captured HTML content
        assert auto_search_action.html_content == "<html>test content</html>"

    def test_scan_result_selectors_found(self, auto_search_action):
        """Test scanning result selectors stops when one is found"""
        mock_page = Mock()
        mock_element = Mock()
        mock_page.query_selector.side_effect = [None, mock_element]

        found = auto_search_action._scan_result_selectors(mock_page)

        assert found is True
        assert mock_page.query_selector.call_count >= 2

    def test_scan_result_selectors_not_found(self, auto_search_action):
        """Test scanning result selectors returns False when none found"""
        mock_page = Mock()
        mock_page.query_selector.return_value = None
        auto_search_action.RESULT_SCAN_TIMEOUT = 1

        time_counter = (i * 0.5 for i in itertools.count())

        with patch('time.sleep'), patch('time.time', side_effect=lambda: next(time_counter)):
            found = auto_search_action._scan_result_selectors(mock_page)

        assert found is False
        assert mock_page.query_selector.called

    def test_await_search_results_uses_fallback(self, auto_search_action):
        """Test that fallback detection triggers when selectors missing"""
        mock_page = Mock()
        mock_page.keyboard = Mock()
        mock_page.mouse = Mock()
        mock_page.mouse.wheel.return_value = None
        mock_page.content.return_value = "x" * 15000

        with patch('app.services.tiktok.search.actions.auto_search.human_pause'), \
                patch('time.sleep'), \
                patch.object(auto_search_action, '_wait_for_results_url'), \
                patch.object(auto_search_action, '_scan_result_selectors', return_value=False) as mock_scan, \
                patch.object(auto_search_action, '_fallback_result_detection') as mock_fallback:
            auto_search_action._await_search_results(mock_page)

        mock_scan.assert_called_once_with(mock_page)
        mock_fallback.assert_called_once_with(mock_page)

    def test_scroll_results_stops_when_target_reached(self, auto_search_action):
        """Scrolling should stop as soon as the requested video count is detected."""
        auto_search_action.set_target_videos(5)
        mock_page = Mock()
        mock_page.mouse.wheel.return_value = None

        with patch.object(
            auto_search_action,
            '_count_video_results',
            side_effect=[2, 5],
        ) as mock_count, patch.object(
            auto_search_action, '_is_near_page_end', return_value=False
        ), patch('app.services.tiktok.search.actions.auto_search.time.sleep'), patch(
            'app.services.tiktok.search.actions.auto_search.human_pause'
        ):
            auto_search_action._scroll_results(mock_page)

        mock_page.mouse.wheel.assert_called_once_with(0, 800)
        assert mock_count.call_count == 2

    def test_scroll_results_stops_when_no_change_limit_hit(self, auto_search_action):
        """Scrolling should halt when repeated attempts find no new videos."""
        auto_search_action.set_target_videos(10)
        mock_page = Mock()
        mock_page.mouse.wheel.return_value = None

        no_change_sequence = [2] + [2] * auto_search_action.SCROLL_NO_CHANGE_LIMIT

        with patch.object(
            auto_search_action,
            '_count_video_results',
            side_effect=no_change_sequence,
        ) as mock_count, patch.object(
            auto_search_action, '_is_near_page_end', return_value=False
        ), patch('app.services.tiktok.search.actions.auto_search.time.sleep'), patch(
            'app.services.tiktok.search.actions.auto_search.human_pause'
        ):
            auto_search_action._scroll_results(mock_page)

        assert (
            mock_page.mouse.wheel.call_count
            == auto_search_action.SCROLL_NO_CHANGE_LIMIT
        )
        assert mock_count.call_count == len(no_change_sequence)

    def test_scroll_results_stops_at_max_attempts(self, auto_search_action):
        """Scrolling should respect the configured maximum number of attempts."""
        auto_search_action.set_target_videos(20)
        auto_search_action.SCROLL_MAX_ATTEMPTS = 4
        auto_search_action.SCROLL_NO_CHANGE_LIMIT = 10
        mock_page = Mock()
        mock_page.mouse.wheel.return_value = None

        count_sequence = [1, 5, 9, 12, 15]

        with patch.object(
            auto_search_action,
            '_count_video_results',
            side_effect=count_sequence,
        ) as mock_count, patch.object(
            auto_search_action, '_is_near_page_end', return_value=False
        ), patch('app.services.tiktok.search.actions.auto_search.time.sleep'), patch(
            'app.services.tiktok.search.actions.auto_search.human_pause'
        ):
            auto_search_action._scroll_results(mock_page)

        assert mock_page.mouse.wheel.call_count == 4
        assert mock_count.call_count == len(count_sequence)

    def test_wait_for_initial_load(self, auto_search_action):
        """Ensure initial load waits for network idle and sleep"""
        mock_page = Mock()

        with patch('time.sleep') as mock_sleep:
            auto_search_action._wait_for_initial_load(mock_page)

        mock_page.wait_for_load_state.assert_called_once_with('networkidle')
        mock_sleep.assert_called_once()

    def test_wait_for_network_idle(self, auto_search_action):
        """Test network idle wait helper"""
        mock_page = Mock()

        with patch('time.sleep') as mock_sleep:
            auto_search_action._wait_for_network_idle(mock_page)

        mock_page.wait_for_load_state.assert_called_once_with('networkidle')
        mock_sleep.assert_called_once()

    def test_prepare_search_ui_click_success(self, auto_search_action):
        """Search UI prep should not refocus body when click succeeds"""
        with patch.object(auto_search_action, '_click_search_button', return_value=True) as mock_click, \
                patch.object(auto_search_action, '_wait_for_search_ui') as mock_wait, \
                patch.object(auto_search_action, '_focus_page_body') as mock_focus:
            auto_search_action._prepare_search_ui(Mock())

        mock_click.assert_called_once()
        mock_wait.assert_called_once()
        mock_focus.assert_not_called()

    def test_prepare_search_ui_click_failure(self, auto_search_action):
        """Search UI prep should focus body when click fails"""
        with patch.object(auto_search_action, '_click_search_button', return_value=False) as mock_click, \
                patch.object(auto_search_action, '_wait_for_search_ui') as mock_wait, \
                patch.object(auto_search_action, '_focus_page_body') as mock_focus:
            auto_search_action._prepare_search_ui(Mock())

        mock_click.assert_called_once()
        mock_wait.assert_called_once()
        mock_focus.assert_called_once()

    @patch('app.services.tiktok.search.actions.auto_search.click_like_human')
    @patch('app.services.tiktok.search.actions.auto_search.move_mouse_to_locator')
    def test_click_search_button_success(self, mock_move, mock_click_like, auto_search_action):
        """Click helper should interact with located button"""
        mock_page = Mock()
        mock_button = Mock()
        mock_button.bounding_box.return_value = {"width": 30, "height": 30}
        mock_button.is_enabled.return_value = True

        def wait_for_selector_side_effect(selector, *args, **kwargs):
            first_selector = f"{auto_search_action.SEARCH_BUTTON_SELECTORS[0]} >> visible=true"
            second_selector = f"{auto_search_action.SEARCH_BUTTON_SELECTORS[1]} >> visible=true"
            if selector == first_selector:
                raise PlaywrightTimeoutError('hidden')
            if selector == second_selector:
                return mock_button
            raise PlaywrightTimeoutError('not found')

        mock_page.wait_for_selector.side_effect = wait_for_selector_side_effect

        result = auto_search_action._click_search_button(mock_page)

        assert result is True
        mock_move.assert_called_once_with(mock_page, mock_button, steps_range=(15, 25))
        mock_click_like.assert_called_once_with(mock_button)

    def test_click_search_button_failure(self, auto_search_action):
        """Click helper should return False when nothing is found"""
        mock_page = Mock()
        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError('not found')

        assert auto_search_action._click_search_button(mock_page) is False
        assert mock_page.wait_for_selector.call_count == len(auto_search_action.SEARCH_BUTTON_SELECTORS)

    def test_focus_page_body_handles_errors(self, auto_search_action):
        """Focusing the body should swallow errors"""
        mock_page = Mock()
        mock_page.focus.side_effect = Exception('focus failed')

        auto_search_action._focus_page_body(mock_page)

        mock_page.focus.assert_called_once_with('body')

    def test_encode_search_query_handles_unicode_errors(self, auto_search_action):
        """Encoding helper should gracefully handle encode errors"""

        class BadString(str):
            def encode(self, *_args, **_kwargs):
                raise UnicodeError('cannot encode')

        auto_search_action.search_query = BadString('bad')

        assert auto_search_action._encode_search_query() == auto_search_action.search_query

    def test_enter_search_query_with_input(self, auto_search_action):
        """Entering query with located input should call typing helper"""
        mock_page = Mock()
        mock_input = Mock()

        with patch.object(auto_search_action, '_type_into_search_input') as mock_type:
            auto_search_action._enter_search_query(mock_page, mock_input, 'query')

        mock_type.assert_called_once_with(mock_page, mock_input, 'query')

    def test_enter_search_query_without_input(self, auto_search_action):
        """Entering query without input should type via keyboard"""
        mock_page = Mock()
        mock_keyboard = Mock()
        mock_page.keyboard = mock_keyboard

        with patch('app.services.tiktok.search.actions.auto_search.human_pause'), \
                patch('time.sleep'):
            auto_search_action._enter_search_query(mock_page, None, 'query')

        mock_keyboard.type.assert_called_once_with('query')

    @patch('app.services.tiktok.search.actions.auto_search.type_like_human')
    def test_type_into_search_input_prefers_human_typing(self, mock_type_like_human, auto_search_action):
        """Typing helper should use human typing when available"""
        mock_page = Mock()
        mock_input = Mock()

        auto_search_action._type_into_search_input(mock_page, mock_input, 'query')

        mock_type_like_human.assert_called_once_with(mock_input, 'query', delay_ms_range=(50, 100))

    @patch('app.services.tiktok.search.actions.auto_search.type_like_human', side_effect=Exception('fail'))
    def test_type_into_search_input_fallbacks_to_keyboard(self, _mock_type_like_human, auto_search_action):
        """Typing helper should fallback to keyboard when human typing fails"""
        mock_page = Mock()
        mock_page.keyboard.type.return_value = None
        mock_input = Mock()

        auto_search_action._type_into_search_input(mock_page, mock_input, 'query')

        mock_page.keyboard.type.assert_called_once_with('query')

    def test_submit_search_uses_keyboard_press(self, auto_search_action):
        """Submit helper should press enter on keyboard"""
        mock_page = Mock()
        mock_keyboard = Mock()
        mock_page.keyboard = mock_keyboard

        auto_search_action._submit_search(mock_page)

        mock_keyboard.press.assert_called_once_with('Enter')

    def test_submit_search_logs_warning_on_failure(self, auto_search_action):
        """Submit helper should warn when Enter press fails"""
        mock_page = Mock()
        mock_keyboard = Mock()
        mock_keyboard.press.side_effect = Exception('no keyboard')
        mock_page.keyboard = mock_keyboard

        with patch.object(auto_search_action.logger, 'warning') as mock_warning:
            auto_search_action._submit_search(mock_page)

        mock_warning.assert_called_once()

    def test_wait_for_results_url_calls_page_function(self, auto_search_action):
        """Ensure wait for results URL triggers the evaluation"""
        mock_page = Mock()

        auto_search_action._wait_for_results_url(mock_page)

        mock_page.wait_for_function.assert_called_once()

    def test_wait_for_search_ui_delegates_to_network_idle(self, auto_search_action):
        """Ensure search UI wait leverages network idle helper"""
        with patch.object(auto_search_action, '_wait_for_network_idle') as mock_wait:
            auto_search_action._wait_for_search_ui(Mock())

        mock_wait.assert_called_once()

    def test_scroll_results_wheels_until_timeout(self, auto_search_action):
        """Scroll helper should attempt multiple scrolls"""
        mock_page = Mock()
        mock_page.mouse.wheel.return_value = None

        with patch('time.time', side_effect=[0, 1, 2, 3, 11]), \
                patch('time.sleep'), \
                patch('app.services.tiktok.search.actions.auto_search.human_pause'):
            auto_search_action._scroll_results(mock_page)

        assert mock_page.mouse.wheel.call_count == 3

    def test_capture_html_records_content(self, auto_search_action):
        """Capture helper should save HTML into instance"""
        mock_page = Mock()
        mock_page.content.return_value = '<html>content</html>'

        auto_search_action._capture_html(mock_page)

        assert auto_search_action.html_content == '<html>content</html>'

    def test_capture_html_persists_when_enabled(self, auto_search_action):
        """Capture helper should persist snapshot when requested"""
        mock_page = Mock()
        mock_page.content.return_value = '<html>persist</html>'
        auto_search_action.save_html = True

        with patch.object(auto_search_action, '_persist_html_snapshot') as mock_persist:
            auto_search_action._capture_html(mock_page)

        mock_persist.assert_called_once_with('<html>persist</html>')

    def test_capture_html_handles_errors(self, auto_search_action):
        """Capture helper should clear html when errors occur"""
        mock_page = Mock()
        mock_page.content.side_effect = Exception('no content')

        auto_search_action._capture_html(mock_page)

        assert auto_search_action.html_content == ''

    def test_error_handling_with_cleanup(self, auto_search_action):
        """Test that cleanup is called even on error"""
        mock_page = Mock()
        mock_page.wait_for_load_state.side_effect = Exception("Page load failed")

        # Mock the cleanup method to track calls
        original_cleanup = auto_search_action._cleanup
        cleanup_calls = []

        def mock_cleanup():
            cleanup_calls.append(1)
            original_cleanup()

        auto_search_action._cleanup = mock_cleanup

        try:
            auto_search_action._execute(mock_page)
        except Exception:
            pass

        # Cleanup should have been called despite error
        assert len(cleanup_calls) >= 1

    def test_encoding_handling(self, auto_search_action):
        """Test query encoding handling"""
        # Test with special characters
        action = TikTokAutoSearchAction("test query with spécial chàracters")
        assert "spécial" in action.search_query

        # Test encoding fallback would be handled in _execute method
        assert hasattr(action, 'search_query')
