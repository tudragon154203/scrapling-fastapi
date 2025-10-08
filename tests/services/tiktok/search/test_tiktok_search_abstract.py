"""Tests for shared TikTok search helpers."""

from typing import Any

import pytest

pytestmark = [pytest.mark.unit]


from app.services.tiktok.search.multistep import TikTokMultiStepSearchService


class DummyFetcher:
    def detect_capabilities(self) -> Any:
        return {}


class DummyComposer:
    pass


class DummyBuilder:
    def __init__(self, captured):
        self._captured = captured

    def build(self, payload, settings, caps):
        self._captured.append(payload)
        return {}, None


def test_prepare_context_sets_force_mute_audio(monkeypatch):
    """_prepare_context should always request muted audio from Camoufox."""

    service = TikTokMultiStepSearchService()
    captured_payloads = []

    monkeypatch.setattr(
        "app.services.common.adapters.scrapling_fetcher.ScraplingFetcherAdapter",
        lambda: DummyFetcher(),
    )
    monkeypatch.setattr(
        "app.services.common.adapters.scrapling_fetcher.FetchArgComposer",
        lambda: DummyComposer(),
    )
    monkeypatch.setattr(
        "app.services.common.browser.camoufox.CamoufoxArgsBuilder",
        lambda: DummyBuilder(captured_payloads),
    )

    context = service._prepare_context(in_tests=False)

    assert captured_payloads, "Camoufox builder should be invoked"
    assert all(
        getattr(payload, "force_mute_audio", False)
        for payload in captured_payloads
    )
    assert context["fetcher"].detect_capabilities() == {}
