"""Tests for search results scrolling helper."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.services.tiktok.search.actions.scrolling import SearchResultsScroller


@pytest.fixture()
def scroller():
    return SearchResultsScroller(
        logger=Mock(),
        scroll_max_attempts=3,
        scroll_no_change_limit=2,
        scroll_interval_seconds=0,
    )


def test_scroll_results_skips_when_target_met(scroller):
    page = Mock()
    scroller._count_video_results = Mock(return_value=5)  # type: ignore[attr-defined]

    scroller.scroll_results(page, target_videos=3)

    page.mouse.wheel.assert_not_called()


def test_scroll_results_uses_timed_scroll_when_no_target(monkeypatch, scroller):
    page = Mock()
    scroller._timed_scroll = Mock()  # type: ignore[attr-defined]

    scroller.scroll_results(page, target_videos=None)

    scroller._timed_scroll.assert_called_once_with(page)


def test_count_video_results_returns_max(scroller):
    page = Mock()
    page.eval_on_selector_all.side_effect = [1, 5, 3]

    assert scroller._count_video_results(page) == 5
    assert page.eval_on_selector_all.call_count == 3
