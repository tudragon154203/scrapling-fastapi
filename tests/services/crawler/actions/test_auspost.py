import types
from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple

import pytest

import app.services.crawler.actions.auspost as auspost


class FakeKeyboard:
    def __init__(self) -> None:
        self.presses: List[str] = []

    def press(self, key: str) -> None:
        self.presses.append(key)


class FakeLocator:
    def __init__(
        self,
        name: str,
        visible: bool = True,
        on_click: Optional[Callable[[], None]] = None,
        on_fill: Optional[Callable[[str], None]] = None,
        wait_behaviors: Optional[Dict[str, Callable[[], None]]] = None,
    ) -> None:
        self.name = name
        self.visible = visible
        self.on_click = on_click
        self.on_fill = on_fill
        self.wait_behaviors = wait_behaviors or {}
        self.wait_calls: List[Tuple[Optional[str], Optional[int]]] = []
        self.click_calls = 0
        self.fill_calls: List[str] = []
        self.first = self

    def wait_for(self, state: Optional[str] = None, timeout: Optional[int] = None) -> None:
        self.wait_calls.append((state, timeout))
        if state in self.wait_behaviors:
            self.wait_behaviors[state]()
            return
        if state == "visible":
            if not self.visible:
                raise TimeoutError(f"Locator {self.name} not visible")
        elif state == "hidden":
            if self.visible:
                # simulate transition to hidden
                self.visible = False
        # other states are ignored for simplicity

    def is_visible(self) -> bool:
        return self.visible

    def click(self) -> None:
        self.click_calls += 1
        if self.on_click:
            self.on_click()

    def fill(self, value: str) -> None:
        self.fill_calls.append(value)
        if self.on_fill:
            self.on_fill(value)


class FakePage:
    def __init__(self) -> None:
        self.locators: Dict[str, FakeLocator] = {}
        self.keyboard = FakeKeyboard()
        self.url = "https://auspost.com.au/mypost/track/search"
        self.wait_for_url_calls: List[Tuple[str, Optional[int]]] = []
        self.load_state_calls: List[Tuple[str, Optional[int]]] = []

    def locator(self, selector: str) -> FakeLocator:
        if selector not in self.locators:
            self.locators[selector] = FakeLocator(selector)
        return self.locators[selector]

    def wait_for_url(self, pattern: str, timeout: Optional[int] = None) -> None:
        self.wait_for_url_calls.append((pattern, timeout))
        if "/mypost/track/details/" not in self.url:
            raise TimeoutError("details page not reached")

    def wait_for_load_state(self, state: str = "load", timeout: Optional[int] = None) -> None:
        self.load_state_calls.append((state, timeout))


@pytest.fixture
def fake_settings() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        auspost_humanize_enabled=True,
        auspost_micro_pause_min_s=0.1,
        auspost_micro_pause_max_s=0.2,
    )


@pytest.fixture
def action(monkeypatch: pytest.MonkeyPatch, fake_settings: types.SimpleNamespace) -> auspost.AuspostTrackAction:
    monkeypatch.setattr(auspost.app_config, "get_settings", lambda: fake_settings)
    return auspost.AuspostTrackAction("TRACK123")


def _setup_common_locators(page: FakePage) -> Dict[str, FakeLocator]:
    locators: Dict[str, FakeLocator] = {}

    tracking_input = FakeLocator("tracking-input")
    locators["tracking-input"] = tracking_input
    page.locators['input[placeholder="Enter tracking number(s)"]'] = tracking_input

    header_search = FakeLocator("header-search", visible=True)
    locators["header-search"] = header_search
    page.locators['input[placeholder="Search our site"]'] = header_search

    def close_overlay() -> None:
        header_search.visible = False

    close_button = FakeLocator("close-button", on_click=close_overlay)
    locators["close-button"] = close_button
    page.locators["button[aria-label*='Close']"] = close_button

    def mark_details() -> None:
        page.url = "https://auspost.com.au/mypost/track/details/TRACK123"

    track_button = FakeLocator("track-button", on_click=mark_details)
    locators["track-button"] = track_button
    page.locators['button:has-text("Track")'] = track_button

    verifying_locator = FakeLocator("verifying", visible=False)
    locators["verifying"] = verifying_locator
    page.locators["text=Verifying the device"] = verifying_locator

    header_locator = FakeLocator("details-header", visible=True)
    locators["details-header"] = header_locator
    page.locators["h3#trackingPanelHeading"] = header_locator

    return locators


def test_execute_humanize_enabled_uses_human_behaviors(
    action: auspost.AuspostTrackAction, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = FakePage()
    locators = _setup_common_locators(page)

    calls: Counter = Counter()

    def record(name: str) -> Callable[..., None]:
        def _inner(*args: Any, **kwargs: Any) -> None:
            calls[name] += 1

        return _inner

    def type_like(locator: FakeLocator, value: str) -> None:
        calls["type_like_human"] += 1
        locator.fill(value)

    monkeypatch.setattr(auspost, "human_pause", record("human_pause"))
    monkeypatch.setattr(auspost, "scroll_noise", record("scroll_noise"))
    monkeypatch.setattr(auspost, "move_mouse_to_locator", record("move_mouse_to_locator"))
    monkeypatch.setattr(auspost, "jitter_mouse", record("jitter_mouse"))

    def click_like(locator: FakeLocator) -> None:
        calls["click_like_human"] += 1
        locator.click()

    monkeypatch.setattr(auspost, "click_like_human", click_like)
    monkeypatch.setattr(auspost, "type_like_human", type_like)

    action(page)

    assert calls["human_pause"] == 3
    assert calls["scroll_noise"] == 2
    assert calls["move_mouse_to_locator"] == 1
    assert calls["jitter_mouse"] == 2  # once for input, once for button
    assert calls["click_like_human"] == 1
    assert calls["type_like_human"] == 1
    assert locators["track-button"].click_calls == 1
    assert locators["tracking-input"].fill_calls == ["TRACK123"]


def test_execute_humanize_disabled_skips_human_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    page = FakePage()
    locators = _setup_common_locators(page)

    settings = types.SimpleNamespace(
        auspost_humanize_enabled=False,
        auspost_micro_pause_min_s=0.1,
        auspost_micro_pause_max_s=0.2,
    )
    monkeypatch.setattr(auspost.app_config, "get_settings", lambda: settings)

    calls: Counter = Counter()

    def record(name: str) -> Callable[..., None]:
        def _inner(*args: Any, **kwargs: Any) -> None:
            calls[name] += 1

        return _inner

    monkeypatch.setattr(auspost, "human_pause", record("human_pause"))
    monkeypatch.setattr(auspost, "scroll_noise", record("scroll_noise"))
    monkeypatch.setattr(auspost, "move_mouse_to_locator", record("move_mouse_to_locator"))
    monkeypatch.setattr(auspost, "jitter_mouse", record("jitter_mouse"))
    monkeypatch.setattr(auspost, "click_like_human", record("click_like_human"))
    monkeypatch.setattr(auspost, "type_like_human", record("type_like_human"))

    action = auspost.AuspostTrackAction("TRACK456")
    action(page)

    assert calls == Counter()
    assert locators["track-button"].click_calls == 1
    assert locators["tracking-input"].fill_calls == ["", "TRACK456"]


def test_execute_closes_global_search_overlay(action: auspost.AuspostTrackAction) -> None:
    page = FakePage()
    locators = _setup_common_locators(page)
    locators["verifying"].visible = False

    action(page)

    header_search = locators["header-search"]
    close_button = locators["close-button"]
    assert close_button.click_calls == 1
    assert header_search.visible is False
    assert ("hidden", 2000) in header_search.wait_calls


def test_handle_verification_waits_for_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    page = FakePage()
    _setup_common_locators(page)

    verifying = page.locator("text=Verifying the device")
    verifying.visible = True

    transitions: List[str] = []

    def after_visible() -> None:
        transitions.append("visible")

    def after_hidden() -> None:
        transitions.append("hidden")
        verifying.visible = False

    verifying.wait_behaviors = {
        "visible": after_visible,
        "hidden": after_hidden,
    }

    action = auspost.AuspostTrackAction("TRACK789")
    settings = types.SimpleNamespace(
        auspost_humanize_enabled=True,
        auspost_micro_pause_min_s=0.1,
        auspost_micro_pause_max_s=0.2,
    )
    monkeypatch.setattr(auspost.app_config, "get_settings", lambda: settings)

    action._handle_verification(page)

    assert transitions == ["visible", "hidden"]
    assert ("domcontentloaded", None) in page.load_state_calls
    assert ("networkidle", None) in page.load_state_calls
