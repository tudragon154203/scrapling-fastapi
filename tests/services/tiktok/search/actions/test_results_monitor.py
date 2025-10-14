"""Tests for search results monitoring helper."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.services.tiktok.search.actions.results_monitor import SearchResultsMonitor


@pytest.fixture()
def monitor():
    return SearchResultsMonitor(
        logger=Mock(),
        result_selectors=[".result"],
        result_scan_timeout=0.1,
        result_scan_interval=0.01,
        ui_ready_pause=0,
    )


def test_await_search_results_triggers_fallback(monkeypatch, monitor):
    page = Mock()
    monkeypatch.setattr(
        "app.services.tiktok.search.actions.results_monitor.human_pause",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.tiktok.search.actions.results_monitor.wait_for_network_idle",
        lambda *_args, **_kwargs: None,
    )
    monitor._wait_for_results_url = Mock()  # type: ignore[attr-defined]
    monitor._scan_result_selectors = Mock(return_value=False)  # type: ignore[attr-defined]
    monitor._fallback_result_detection = Mock()  # type: ignore[attr-defined]

    monitor.await_search_results(page)

    monitor._wait_for_results_url.assert_called_once_with(page)
    monitor._scan_result_selectors.assert_called_once_with(page)
    monitor._fallback_result_detection.assert_called_once_with(page)


def test_scan_result_selectors_returns_true_on_first_match(monkeypatch, monitor):
    page = Mock()
    page.query_selector.return_value = object()
    monkeypatch.setattr(
        "app.services.tiktok.search.actions.results_monitor.time.sleep",
        lambda *_args, **_kwargs: None,
    )

    assert monitor._scan_result_selectors(page) is True
    page.query_selector.assert_called_once_with(".result")
