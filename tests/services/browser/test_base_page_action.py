import pytest

from app.services.browser.actions.base import BasePageAction


class DummyAction(BasePageAction):
    def _execute(self, page):
        return None


class FakeLocator:
    def __init__(self, selector: str, should_raise: bool = False):
        self.selector = selector
        self.should_raise = should_raise
        self.wait_calls: list[tuple[str, int]] = []

    @property
    def first(self):
        return self

    def wait_for(self, state: str, timeout: int):
        self.wait_calls.append((state, timeout))
        if self.should_raise:
            raise RuntimeError(f"{self.selector} is not visible")
        return self


class FakePage:
    def __init__(self, locator_behaviour: dict[str, bool]):
        self._locators = {
            selector: FakeLocator(selector, should_raise=should_raise)
            for selector, should_raise in locator_behaviour.items()
        }
        self.calls: list[str] = []

    def locator(self, selector: str):
        self.calls.append(selector)
        return self._locators[selector]


@pytest.fixture
def action():
    return DummyAction()


def test_first_visible_returns_first_locator(action):
    page = FakePage({"#first": False, "#second": False})

    locator = action._first_visible(page, ["#first", "#second"], timeout=1234)

    assert locator is page._locators["#first"]
    assert page.calls == ["#first"]
    assert page._locators["#first"].wait_calls == [("visible", 1234)]


def test_first_visible_falls_back_to_last_selector_when_all_fail(action):
    selectors = ["#one", "#two", "#three"]
    page = FakePage({selector: True for selector in selectors})

    locator = action._first_visible(page, selectors, timeout=777)

    assert locator is page._locators[selectors[-1]]
    assert page.calls == selectors + [selectors[-1]]
    for selector in selectors:
        assert page._locators[selector].wait_calls == [("visible", 777)]
