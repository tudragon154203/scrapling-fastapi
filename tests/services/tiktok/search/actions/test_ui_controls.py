"""Tests for the TikTok search UI controller helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.services.tiktok.search.actions.ui_controls import SearchUIController


@pytest.fixture()
def controller():
    return SearchUIController(
        logger=Mock(),
        search_button_selectors=["button"],
        ui_ready_pause=0,
    )


def test_prepare_search_ui_focuses_body_when_click_fails(controller):
    page = Mock()
    controller._click_search_button = Mock(return_value=False)  # type: ignore[attr-defined]
    controller.wait_for_search_ui = Mock()  # type: ignore[attr-defined]

    controller.prepare_search_ui(page)

    page.focus.assert_called_once_with("body")
    controller.wait_for_search_ui.assert_called_once_with(page)


def test_enter_search_query_types_into_input(monkeypatch, controller):
    page = Mock()
    search_input = Mock()
    type_like_human = Mock()
    monkeypatch.setattr(
        "app.services.tiktok.search.actions.ui_controls.type_like_human",
        type_like_human,
    )

    controller.enter_search_query(page, search_input, "query")

    type_like_human.assert_called_once()
    page.keyboard.type.assert_not_called()


def test_enter_search_query_keyboard_fallback_when_no_input(monkeypatch, controller):
    page = Mock()
    monkeypatch.setattr(
        "app.services.tiktok.search.actions.ui_controls.human_pause",
        lambda *_args, **_kwargs: None,
    )

    controller.enter_search_query(page, None, "query")

    page.keyboard.type.assert_called_once_with("query")
