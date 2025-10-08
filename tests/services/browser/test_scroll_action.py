from app.services.browser.actions.scroll import ScrollDownAction
import app.services.browser.actions.scroll as scroll_module
import itertools
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit]


def _make_page(wheel=True, evaluate=True, keyboard=True):
    wheel_mock = MagicMock()
    if not wheel:
        wheel_mock.side_effect = Exception("wheel fail")
    eval_mock = MagicMock()
    if not evaluate:
        eval_mock.side_effect = Exception("evaluate fail")
    keyboard_mock = MagicMock()
    if not keyboard:
        keyboard_mock.side_effect = Exception("keyboard fail")

    return SimpleNamespace(
        mouse=SimpleNamespace(wheel=wheel_mock),
        evaluate=eval_mock,
        keyboard=SimpleNamespace(press=keyboard_mock),
    )


class TestScrollDownAction:
    def test_scroll_once_mouse_primary(self):
        page = _make_page(wheel=True)
        action = ScrollDownAction()

        assert action._scroll_once(page, 100) is True
        page.mouse.wheel.assert_called_once_with(0, 100)
        page.evaluate.assert_not_called()
        page.keyboard.press.assert_not_called()

    def test_scroll_once_evaluate_fallback(self):
        page = _make_page(wheel=False, evaluate=True)
        action = ScrollDownAction()

        assert action._scroll_once(page, 100) is True
        page.mouse.wheel.assert_called_once_with(0, 100)
        page.evaluate.assert_called_once_with(
            "window.scrollBy(0, arguments[0]);", 100
        )
        page.keyboard.press.assert_not_called()

    def test_scroll_once_keyboard_fallback(self):
        page = _make_page(wheel=False, evaluate=False, keyboard=True)
        action = ScrollDownAction()

        assert action._scroll_once(page, 100) is True
        page.mouse.wheel.assert_called_once_with(0, 100)
        page.evaluate.assert_called_once_with(
            "window.scrollBy(0, arguments[0]);", 100
        )
        page.keyboard.press.assert_called_once_with("End")

    def test_scroll_once_all_fail(self):
        page = _make_page(wheel=False, evaluate=False, keyboard=False)
        action = ScrollDownAction()

        assert action._scroll_once(page, 100) is False
        page.mouse.wheel.assert_called_once_with(0, 100)
        page.evaluate.assert_called_once_with(
            "window.scrollBy(0, arguments[0]);", 100
        )
        page.keyboard.press.assert_called_once_with("End")

    def test_execute_respects_timing(self, monkeypatch):
        page = object()
        action = ScrollDownAction(
            duration_s=0.05, step_px=10, interval_s=0.01, settle_s=0.02
        )

        scroll_mock = MagicMock(return_value=True)
        monkeypatch.setattr(action, "_scroll_once", scroll_mock)

        times = itertools.chain([0, 0, 0.02, 0.04, 0.06], itertools.repeat(0.06))
        monkeypatch.setattr(scroll_module, "time", lambda: next(times))

        sleep_calls = []

        def fake_sleep(duration):
            sleep_calls.append(duration)

        monkeypatch.setattr(scroll_module, "sleep", fake_sleep)

        action._execute(page)

        assert scroll_mock.call_count == 3
        assert sleep_calls == [0.01, 0.01, 0.01, 0.02]
