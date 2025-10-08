from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.unit]


import pytest

from app.services.browser.actions.wait_for_close import WaitForUserCloseAction


class DummyCloseError(Exception):
    """Dummy exception to simulate failures from wait_for_event."""


@pytest.fixture
def mocked_page():
    page = MagicMock()
    page.bring_to_front = MagicMock()
    page.wait_for_event = MagicMock(side_effect=DummyCloseError("boom"))
    page.configure_mock(context=None)
    return page


def test_wait_for_user_close_action_returns_page_on_exception(mocked_page):
    action = WaitForUserCloseAction()

    result = action(mocked_page)

    mocked_page.bring_to_front.assert_called_once_with()
    mocked_page.wait_for_event.assert_called_once_with("close")
    assert result is mocked_page
