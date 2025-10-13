import types
from unittest.mock import MagicMock, call as mock_call

import pytest

from app.services.crawler.actions.auspost import AuspostTrackAction


class DummySettings:
    def __init__(self, enabled: bool, pause_min: float = 0.1, pause_max: float = 0.2) -> None:
        self.auspost_humanize_enabled = enabled
        self.auspost_micro_pause_min_s = pause_min
        self.auspost_micro_pause_max_s = pause_max


@pytest.fixture
def page_mock() -> MagicMock:
    page = MagicMock()
    page.url = ""
    locator = MagicMock()
    locator.first = MagicMock()
    locator.first.wait_for = MagicMock()
    locator.first.is_visible = MagicMock(return_value=False)
    page.locator.return_value = locator
    page.wait_for_url = MagicMock(side_effect=Exception("no match"))
    page.wait_for_load_state = MagicMock()
    page.keyboard.press = MagicMock()
    return page


@pytest.fixture
def humanize_mocks(monkeypatch):
    module = pytest.importorskip("app.services.crawler.actions.auspost")
    human_pause = MagicMock()
    scroll_noise = MagicMock()
    move_mouse_to_locator = MagicMock()
    jitter_mouse = MagicMock()
    click_like_human = MagicMock()
    type_like_human = MagicMock()

    monkeypatch.setattr(module, "human_pause", human_pause)
    monkeypatch.setattr(module, "scroll_noise", scroll_noise)
    monkeypatch.setattr(module, "move_mouse_to_locator", move_mouse_to_locator)
    monkeypatch.setattr(module, "jitter_mouse", jitter_mouse)
    monkeypatch.setattr(module, "click_like_human", click_like_human)
    monkeypatch.setattr(module, "type_like_human", type_like_human)

    return types.SimpleNamespace(
        human_pause=human_pause,
        scroll_noise=scroll_noise,
        move_mouse_to_locator=move_mouse_to_locator,
        jitter_mouse=jitter_mouse,
        click_like_human=click_like_human,
        type_like_human=type_like_human,
    )


def _configure_settings(monkeypatch, enabled: bool, pause_min: float = 0.1, pause_max: float = 0.2) -> None:
    settings = DummySettings(enabled=enabled, pause_min=pause_min, pause_max=pause_max)
    monkeypatch.setattr(
        "app.services.crawler.actions.auspost.app_config.get_settings",
        lambda: settings,
    )


def test_execute_with_humanization(monkeypatch, page_mock, humanize_mocks):
    _configure_settings(monkeypatch, enabled=True, pause_min=0.3, pause_max=0.6)
    action = AuspostTrackAction(tracking_code="TRACK123")

    close_search = MagicMock()
    fill_tracking = MagicMock()
    submit_form = MagicMock()
    handle_verification = MagicMock()
    retry_if_needed = MagicMock(return_value=True)

    monkeypatch.setattr(action, "_close_global_search", close_search)
    monkeypatch.setattr(action, "_fill_tracking_code", fill_tracking)
    monkeypatch.setattr(action, "_submit_form", submit_form)
    monkeypatch.setattr(action, "_handle_verification", handle_verification)
    monkeypatch.setattr(action, "_retry_if_needed", retry_if_needed)

    result = action._execute(page_mock)

    assert result is page_mock
    close_search.assert_called_once_with(page_mock)
    fill_tracking.assert_called_once_with(page_mock, True)
    submit_form.assert_called_once_with(page_mock, True)
    handle_verification.assert_called_once_with(page_mock)
    retry_if_needed.assert_called_once_with(page_mock, True)

    human_pause_calls = [call_record.args for call_record in humanize_mocks.human_pause.call_args_list]
    assert (0.25, 0.8) in human_pause_calls
    assert (0.3, 0.6) in human_pause_calls
    humanize_mocks.scroll_noise.assert_has_calls(
        [mock_call(page_mock, cycles_range=(1, 2)), mock_call(page_mock, cycles_range=(1, 2))]
    )


def test_execute_without_humanization(monkeypatch, page_mock, humanize_mocks):
    _configure_settings(monkeypatch, enabled=False)
    action = AuspostTrackAction(tracking_code="TRACK123")

    close_search = MagicMock()
    fill_tracking = MagicMock()
    submit_form = MagicMock()
    handle_verification = MagicMock()
    retry_if_needed = MagicMock(return_value=True)

    monkeypatch.setattr(action, "_close_global_search", close_search)
    monkeypatch.setattr(action, "_fill_tracking_code", fill_tracking)
    monkeypatch.setattr(action, "_submit_form", submit_form)
    monkeypatch.setattr(action, "_handle_verification", handle_verification)
    monkeypatch.setattr(action, "_retry_if_needed", retry_if_needed)

    result = action._execute(page_mock)

    assert result is page_mock
    close_search.assert_called_once_with(page_mock)
    fill_tracking.assert_called_once_with(page_mock, False)
    submit_form.assert_called_once_with(page_mock, False)
    handle_verification.assert_called_once_with(page_mock)
    retry_if_needed.assert_called_once_with(page_mock, False)

    humanize_mocks.human_pause.assert_not_called()
    humanize_mocks.scroll_noise.assert_not_called()


def test_retry_if_needed_detects_details_page(monkeypatch, humanize_mocks):
    action = AuspostTrackAction(tracking_code="CODE")
    page = MagicMock()
    page.url = "https://auspost.com.au/mypost/track/details/123"
    page.wait_for_url = MagicMock()
    page.locator.return_value.first.is_visible.return_value = False
    page.wait_for_load_state = MagicMock()

    result = action._retry_if_needed(page, humanize=True)

    assert result is True
    humanize_mocks.human_pause.assert_not_called()
    humanize_mocks.scroll_noise.assert_not_called()
    page.wait_for_url.assert_not_called()


def test_retry_if_needed_handles_retry(monkeypatch, page_mock, humanize_mocks):
    action = AuspostTrackAction(tracking_code="CODE")
    page_mock.url = "/mypost/track/search"
    page_mock.locator.return_value.first.is_visible.return_value = False

    result = action._retry_if_needed(page_mock, humanize=True)

    assert result is False
    humanize_mocks.human_pause.assert_called_once_with(0.25, 0.7)
    humanize_mocks.scroll_noise.assert_called_once_with(page_mock, cycles_range=(1, 1))
    page_mock.wait_for_load_state.assert_called_once_with("domcontentloaded", timeout=2_000)


def test_close_global_search_uses_close_button(monkeypatch):
    action = AuspostTrackAction(tracking_code="CODE")
    page = MagicMock()
    header_search = MagicMock()
    header_search.is_visible.return_value = True
    header_search.wait_for = MagicMock()
    page.locator.return_value.first = header_search
    page.keyboard.press = MagicMock()

    close_button = MagicMock()
    monkeypatch.setattr(action, "_first_visible", MagicMock(return_value=close_button))

    action._close_global_search(page)

    close_button.click.assert_called_once()
    header_search.wait_for.assert_called_once_with(state="hidden", timeout=2_000)
    page.keyboard.press.assert_not_called()


def test_close_global_search_esc_fallback(monkeypatch):
    action = AuspostTrackAction(tracking_code="CODE")
    page = MagicMock()
    header_search = MagicMock()
    header_search.is_visible.return_value = True
    header_search.wait_for = MagicMock()
    page.locator.return_value.first = header_search
    page.keyboard.press = MagicMock()

    monkeypatch.setattr(action, "_first_visible", MagicMock(side_effect=Exception("no button")))

    action._close_global_search(page)

    page.keyboard.press.assert_called_once_with("Escape")
    header_search.wait_for.assert_called_once_with(state="hidden", timeout=2_000)
