"""Tests for the TikTokAutoSearchAction orchestrator."""

from __future__ import annotations

from unittest.mock import Mock

from app.services.tiktok.search.actions.auto_search import TikTokAutoSearchAction


def test_auto_search_action_orchestrates_helpers(monkeypatch):
    action = TikTokAutoSearchAction("cats")
    action.ui_controller = Mock()
    action.ui_controller.encode_search_query.return_value = "cats"  # type: ignore[attr-defined]
    action.results_monitor = Mock()
    action.scroller = Mock()
    action.snapshot_capturer = Mock()
    action.snapshot_capturer.capture_html.return_value = "<html>"  # type: ignore[attr-defined]

    page = Mock()
    page.is_closed.return_value = True

    result = action(page)

    assert result is page
    action.ui_controller.wait_for_initial_load.assert_called_once_with(page)
    action.ui_controller.prepare_search_ui.assert_called_once_with(page)
    action.ui_controller.encode_search_query.assert_called_once_with("cats")
    action.ui_controller.enter_search_query.assert_called_once_with(page, None, "cats")
    action.ui_controller.submit_search.assert_called_once_with(page)
    action.results_monitor.await_search_results.assert_called_once_with(page)
    action.scroller.scroll_results.assert_called_once_with(page, None)
    action.snapshot_capturer.capture_html.assert_called_once_with(page)
    assert action.html_content == "<html>"
    assert action._cleanup_functions == []


def test_set_target_videos_updates_expected_values():
    action = TikTokAutoSearchAction("cats")

    action.set_target_videos(5)
    assert action.target_videos == 5

    action.set_target_videos(None)
    assert action.target_videos is None

    action.set_target_videos(0)
    assert action.target_videos is None


def test_auto_search_action_supports_dependency_injection():
    ui_controller = Mock()
    ui_controller.encode_search_query.return_value = "cats"

    results_monitor = Mock()
    scroller = Mock()
    snapshot_capturer = Mock()
    snapshot_capturer.capture_html.return_value = "<html>"

    action = TikTokAutoSearchAction(
        "cats",
        ui_controller=ui_controller,
        results_monitor=results_monitor,
        scroller=scroller,
        snapshot_capturer=snapshot_capturer,
    )

    page = Mock()
    page.is_closed.return_value = True

    action(page)

    assert action.ui_controller is ui_controller
    assert action.results_monitor is results_monitor
    assert action.scroller is scroller
    assert action.snapshot_capturer is snapshot_capturer
    ui_controller.wait_for_initial_load.assert_called_once_with(page)
    ui_controller.prepare_search_ui.assert_called_once_with(page)
    ui_controller.encode_search_query.assert_called_once_with("cats")
    ui_controller.enter_search_query.assert_called_once_with(page, None, "cats")
    ui_controller.submit_search.assert_called_once_with(page)
    results_monitor.await_search_results.assert_called_once_with(page)
    scroller.scroll_results.assert_called_once_with(page, None)
    snapshot_capturer.capture_html.assert_called_once_with(page)
