"""Unit tests for :mod:`specify_src.services.tiktok_search_service`."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import Any, Dict, List
import sys

import pytest

scrapling_stub = ModuleType("scrapling")


class _DummyScrapling:  # pragma: no cover - not used directly but satisfies import side effects
    """Minimal placeholder for :mod:`scrapling` import resolution."""


scrapling_stub.Scrapling = _DummyScrapling
sys.modules["scrapling"] = scrapling_stub

from specify_src.models.browser_mode import BrowserMode
from specify_src.services import browser_mode_service
from specify_src.services.tiktok_search_service import TikTokSearchService


@dataclass
class _FakeBrowserMode:
    """Simple stand-in for :class:`BrowserMode` with a controllable value."""

    value: str


@pytest.mark.parametrize("force_headful", [False, True])
def test_search_uses_stubbed_browser_mode(monkeypatch: pytest.MonkeyPatch, force_headful: bool) -> None:
    """Ensure the search payload reflects the mocked browser mode selection."""

    captured_arguments: Dict[str, Any] = {}

    def _mock_determine_mode(force_headful_arg: bool) -> _FakeBrowserMode:
        captured_arguments["force_headful"] = force_headful_arg
        return _FakeBrowserMode(value=f"mocked-{force_headful_arg}")

    monkeypatch.setattr(
        browser_mode_service.BrowserModeService,
        "determine_mode",
        staticmethod(_mock_determine_mode),
    )

    response: Dict[str, Any] = TikTokSearchService.search("cats", force_headful=force_headful)

    expected_results: List[Dict[str, str]] = [
        {"title": "Funny Cat Video 1", "url": "https://tiktok.com/video1", "thumbnail": "thumbnail1.jpg"},
        {"title": "Funny Cat Video 2", "url": "https://tiktok.com/video2", "thumbnail": "thumbnail2.jpg"},
    ]

    assert captured_arguments["force_headful"] == force_headful
    assert response == {
        "results": expected_results,
        "execution_mode": f"mocked-{force_headful}",
        "message": "Search completed successfully",
    }


def test_search_handles_alternate_browser_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure alternate enum values such as ``HEADFUL`` are respected."""

    def _mock_determine_mode(force_headful: bool) -> BrowserMode:  # noqa: ARG001 - signature mirrors production
        return BrowserMode.HEADFUL

    monkeypatch.setattr(
        browser_mode_service.BrowserModeService,
        "determine_mode",
        staticmethod(_mock_determine_mode),
    )

    response: Dict[str, Any] = TikTokSearchService.search("dogs", force_headful=True)

    assert response["execution_mode"] == BrowserMode.HEADFUL.value
