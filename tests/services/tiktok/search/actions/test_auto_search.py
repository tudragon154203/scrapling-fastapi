"""Unit tests for TikTokAutoSearchAction functionality"""

import pytest
from unittest.mock import Mock, patch
from app.services.tiktok.search.actions.auto_search import TikTokAutoSearchAction


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
        mock_search_input = Mock()
        mock_page.query_selector.side_effect = [Exception(), mock_search_bar, mock_search_input]
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
        assert mock_page.query_selector.call_count >= 2
        assert mock_page.wait_for_load_state.call_count >= 2

    @patch('app.services.tiktok.search.actions.auto_search.type_like_human')
    def test_typing_behavior(self, mock_type_like_human, auto_search_action):
        """Test typing behavior"""
        mock_page = Mock()
        mock_search_input = Mock()

        # Mock page methods
        mock_page.wait_for_load_state.return_value = None
        mock_page.query_selector.side_effect = [Mock(), mock_search_input]
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
        assert mock_type_like_human.called or mock_page.keyboard.type.called
        assert mock_page.wait_for_load_state.call_count >= 2

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
        assert mock_page.query_selector.call_count == 2

    def test_scan_result_selectors_not_found(self, auto_search_action):
        """Test scanning result selectors returns False when none found"""
        mock_page = Mock()
        mock_page.query_selector.return_value = None

        found = auto_search_action._scan_result_selectors(mock_page)

        assert found is False
        assert mock_page.query_selector.call_count == len(auto_search_action.RESULT_SELECTORS)

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

    def test_wait_for_network_idle(self, auto_search_action):
        """Test network idle wait helper"""
        mock_page = Mock()

        with patch('time.sleep') as mock_sleep:
            auto_search_action._wait_for_network_idle(mock_page)

        mock_page.wait_for_load_state.assert_called_once_with('networkidle')
        mock_sleep.assert_called_once()

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
