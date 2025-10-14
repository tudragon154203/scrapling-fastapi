"""Unit coverage for the TikTok auto-search action orchestration."""

from unittest.mock import Mock

import pytest

from app.services.tiktok.search.actions.auto_search import TikTokAutoSearchAction
from app.services.tiktok.search.actions.results_monitor import SearchResultsMonitor
from app.services.tiktok.search.actions.scrolling import SearchResultsScroller
from app.services.tiktok.search.actions.snapshot import SearchSnapshotCapturer
from app.services.tiktok.search.actions.ui_controls import SearchUIController

pytestmark = [pytest.mark.unit]


def test_initializes_with_default_helpers() -> None:
    """The action should construct helper instances when none are provided."""
    action = TikTokAutoSearchAction("some query")

    assert isinstance(action.ui_controller, SearchUIController)
    assert isinstance(action.results_monitor, SearchResultsMonitor)
    assert isinstance(action.scroller, SearchResultsScroller)
    assert isinstance(action.snapshot_capturer, SearchSnapshotCapturer)


def test_set_target_videos_validation() -> None:
    """Target configuration accepts positive integers and ignores invalid inputs."""
    action = TikTokAutoSearchAction("query")

    action.set_target_videos(5)
    assert action.target_videos == 5

    action.set_target_videos(0)
    assert action.target_videos is None

    action.set_target_videos(None)
    assert action.target_videos is None


def test_cleanup_browser_resources_closes_open_page() -> None:
    """Cleanup helper should close the active page when it remains open."""
    action = TikTokAutoSearchAction("query")
    page = Mock()
    page.is_closed.return_value = False

    action.page = page
    action._cleanup_browser_resources()

    page.close.assert_called_once_with()


def test_execute_orchestrates_helpers_and_captures_html() -> None:
    """The action should delegate the search flow to the injected helpers."""
    page = Mock()
    page.is_closed.return_value = True

    ui_controller = Mock(spec=SearchUIController)
    ui_controller.encode_search_query.return_value = "encoded"

    results_monitor = Mock(spec=SearchResultsMonitor)
    scroller = Mock(spec=SearchResultsScroller)
    snapshot_capturer = Mock(spec=SearchSnapshotCapturer)
    snapshot_capturer.capture_html.return_value = "<html />"

    action = TikTokAutoSearchAction(
        "query",
        ui_controller=ui_controller,
        results_monitor=results_monitor,
        scroller=scroller,
        snapshot_capturer=snapshot_capturer,
    )
    action.set_target_videos(3)

    result = action(page)

    ui_controller.wait_for_initial_load.assert_called_once_with(page)
    ui_controller.prepare_search_ui.assert_called_once_with(page)
    ui_controller.encode_search_query.assert_called_once_with("query")
    ui_controller.enter_search_query.assert_called_once_with(page, None, "encoded")
    ui_controller.submit_search.assert_called_once_with(page)

    results_monitor.await_search_results.assert_called_once_with(page)
    scroller.scroll_results.assert_called_once_with(page, 3)
    snapshot_capturer.capture_html.assert_called_once_with(page)
    assert action.html_content == "<html />"
    assert result is page


def test_execute_propagates_errors_and_cleans_up() -> None:
    """Errors raised by helpers should trigger cleanup before re-raising."""
    page = Mock()
    page.is_closed.return_value = False

    ui_controller = Mock(spec=SearchUIController)
    ui_controller.prepare_search_ui.side_effect = RuntimeError("boom")

    action = TikTokAutoSearchAction("query", ui_controller=ui_controller)

    with pytest.raises(RuntimeError):
        action(page)

    page.close.assert_called_once_with()
    ui_controller.prepare_search_ui.assert_called_once_with(page)


def test_cleanup_handles_faulty_callables() -> None:
    """Cleanup should attempt all registered functions even when some fail."""
    action = TikTokAutoSearchAction("query")
    good_cleanup = Mock()

    def bad_cleanup() -> None:
        raise ValueError("nope")

    action._cleanup_functions = [good_cleanup, bad_cleanup, "not-callable"]  # type: ignore[list-item]

    action._cleanup()

    good_cleanup.assert_called_once_with()
    assert action._cleanup_functions == []
