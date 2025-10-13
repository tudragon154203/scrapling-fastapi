"""Unit tests for :mod:`specify_src.services.tiktok_search_service`."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any, TYPE_CHECKING

import pytest

if TYPE_CHECKING:  # pragma: no cover - imports only for type checking
    from specify_src.models.browser_mode import BrowserMode
    from specify_src.services.tiktok_search_service import TikTokSearchService


@dataclass
class _FakeBrowserMode:
    """Simple stand-in for :class:`BrowserMode` with a controllable value."""

    value: str


@pytest.fixture(name="tiktok_components")
def _tiktok_components(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[type["BrowserMode"], ModuleType, type["TikTokSearchService"]]:
    """Provide TikTok service dependencies with a stubbed :mod:`scrapling` module."""

    scrapling_stub = ModuleType("scrapling")

    class _DummyScrapling:  # pragma: no cover - placeholder for import side effect
        """Minimal placeholder class used to satisfy :mod:`scrapling` import."""

    scrapling_stub.Scrapling = _DummyScrapling
    monkeypatch.setitem(sys.modules, "scrapling", scrapling_stub)

    browser_mode_module = importlib.import_module("specify_src.models.browser_mode")
    browser_mode_service_module = importlib.import_module("specify_src.services.browser_mode_service")
    tiktok_service_module = importlib.import_module("specify_src.services.tiktok_search_service")

    return (
        browser_mode_module.BrowserMode,
        browser_mode_service_module,
        tiktok_service_module.TikTokSearchService,
    )


@pytest.mark.parametrize("force_headful", [False, True])
def test_search_uses_stubbed_browser_mode(
    monkeypatch: pytest.MonkeyPatch,
    force_headful: bool,
    tiktok_components: tuple[type["BrowserMode"], ModuleType, type["TikTokSearchService"]],
) -> None:
    """Ensure the search payload reflects the mocked browser mode selection."""

    _, browser_mode_service_module, tiktok_service = tiktok_components
    captured_arguments: dict[str, Any] = {}

    def _mock_determine_mode(force_headful_arg: bool) -> _FakeBrowserMode:
        captured_arguments["force_headful"] = force_headful_arg
        return _FakeBrowserMode(value=f"mocked-{force_headful_arg}")

    monkeypatch.setattr(
        browser_mode_service_module.BrowserModeService,
        "determine_mode",
        staticmethod(_mock_determine_mode),
    )

    response: dict[str, Any] = tiktok_service.search("cats", force_headful=force_headful)

    expected_results: list[dict[str, str]] = [
        {
            "title": "Funny Cat Video 1",
            "url": "https://tiktok.com/video1",
            "thumbnail": "thumbnail1.jpg",
        },
        {
            "title": "Funny Cat Video 2",
            "url": "https://tiktok.com/video2",
            "thumbnail": "thumbnail2.jpg",
        },
    ]

    assert captured_arguments["force_headful"] == force_headful
    assert response == {
        "results": expected_results,
        "execution_mode": f"mocked-{force_headful}",
        "message": "Search completed successfully",
    }


def test_search_handles_alternate_browser_mode(
    monkeypatch: pytest.MonkeyPatch,
    tiktok_components: tuple[type["BrowserMode"], ModuleType, type["TikTokSearchService"]],
) -> None:
    """Ensure alternate enum values such as ``HEADFUL`` are respected."""

    browser_mode, browser_mode_service_module, tiktok_service = tiktok_components

    def _mock_determine_mode(force_headful: bool) -> browser_mode:  # type: ignore[valid-type]
        return browser_mode.HEADFUL

    monkeypatch.setattr(
        browser_mode_service_module.BrowserModeService,
        "determine_mode",
        staticmethod(_mock_determine_mode),
    )

    response: dict[str, Any] = tiktok_service.search("dogs", force_headful=True)

    assert response["execution_mode"] == browser_mode.HEADFUL.value
