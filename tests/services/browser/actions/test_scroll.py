from unittest.mock import Mock

import pytest

from app.services.browser.actions.scroll import ScrollDownAction


pytestmark = pytest.mark.unit


def test_execute_wait_selector_fallback():
    page = Mock()
    page.wait_for_selector.side_effect = Exception("selector missing")

    action = ScrollDownAction(
        duration_s=0,
        interval_s=0,
        settle_s=0,
        wait_selector=".results"
    )

    result = action._execute(page)

    assert result is page
    page.wait_for_selector.assert_called_once_with(".results", timeout=5000)


def test_scroll_once_uses_mouse_wheel_when_available():
    page = Mock()
    page.mouse = Mock()
    page.mouse.wheel = Mock()
    page.evaluate = Mock()
    page.keyboard = Mock()
    page.keyboard.press = Mock()

    action = ScrollDownAction()

    assert action._scroll_once(page, 120)
    page.mouse.wheel.assert_called_once_with(0, 120)
    page.evaluate.assert_not_called()
    page.keyboard.press.assert_not_called()


def test_scroll_once_falls_back_to_evaluate_when_mouse_wheel_fails():
    page = Mock()
    page.mouse = Mock()
    page.mouse.wheel = Mock(side_effect=Exception("wheel failed"))
    page.evaluate = Mock()
    page.keyboard = Mock()
    page.keyboard.press = Mock()

    action = ScrollDownAction()

    assert action._scroll_once(page, 200)
    page.mouse.wheel.assert_called_once_with(0, 200)
    page.evaluate.assert_called_once_with("window.scrollBy(0, arguments[0]);", 200)
    page.keyboard.press.assert_not_called()


def test_scroll_once_uses_keyboard_end_when_other_strategies_fail():
    page = Mock()
    page.mouse = Mock()
    page.mouse.wheel = Mock(side_effect=Exception("wheel failed"))
    page.evaluate = Mock(side_effect=Exception("evaluate failed"))
    page.keyboard = Mock()
    page.keyboard.press = Mock()

    action = ScrollDownAction()

    assert action._scroll_once(page, 300)
    page.mouse.wheel.assert_called_once_with(0, 300)
    page.evaluate.assert_called_once_with("window.scrollBy(0, arguments[0]);", 300)
    page.keyboard.press.assert_called_once_with('End')


def test_scroll_once_returns_false_when_all_strategies_fail():
    page = Mock()
    page.mouse = Mock()
    page.mouse.wheel = Mock(side_effect=Exception("wheel failed"))
    page.evaluate = Mock(side_effect=Exception("evaluate failed"))
    page.keyboard = Mock()
    page.keyboard.press = Mock(side_effect=Exception("keyboard failed"))

    action = ScrollDownAction()

    assert not action._scroll_once(page, 400)
    page.mouse.wheel.assert_called_once_with(0, 400)
    page.evaluate.assert_called_once_with("window.scrollBy(0, arguments[0]);", 400)
    page.keyboard.press.assert_called_once_with('End')
