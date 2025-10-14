"""Unit tests for the attempt planner retry ordering."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from app.services.crawler.proxy.plan import AttemptPlanner


@dataclass
class FakeSettings:
    proxy_rotation_mode: str
    max_retries: int
    private_proxy_url: Optional[str] = None


@pytest.fixture()
def planner() -> AttemptPlanner:
    return AttemptPlanner()


def test_sequential_without_private_uses_direct_fallback(planner: AttemptPlanner) -> None:
    settings = FakeSettings(proxy_rotation_mode="sequential", max_retries=3)
    public_proxies = []

    plan = planner.build_plan(settings, public_proxies)

    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "direct", "proxy": None},
        {"mode": "direct", "proxy": None},
    ]


def test_sequential_with_private_inserts_private_before_final_direct(planner: AttemptPlanner) -> None:
    settings = FakeSettings(
        proxy_rotation_mode="sequential",
        max_retries=5,
        private_proxy_url="http://private",
    )
    public_proxies = ["pub-1", "pub-2", "pub-3"]

    plan = planner.build_plan(settings, public_proxies)

    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "public", "proxy": "pub-1"},
        {"mode": "public", "proxy": "pub-2"},
        {"mode": "private", "proxy": "http://private"},
        {"mode": "direct", "proxy": None},
    ]


def test_random_without_private_uses_shuffled_order(monkeypatch: pytest.MonkeyPatch, planner: AttemptPlanner) -> None:
    def reverse(sequence: list[str]) -> None:
        sequence[:] = list(reversed(sequence))

    monkeypatch.setattr("app.services.crawler.proxy.plan.random.shuffle", reverse)

    settings = FakeSettings(proxy_rotation_mode="random", max_retries=4)
    public_proxies = ["pub-1", "pub-2", "pub-3"]

    plan = planner.build_plan(settings, public_proxies)

    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "public", "proxy": "pub-3"},
        {"mode": "public", "proxy": "pub-2"},
        {"mode": "direct", "proxy": None},
    ]


def test_random_with_private_appends_private_before_direct(
    monkeypatch: pytest.MonkeyPatch, planner: AttemptPlanner
) -> None:
    def rotate(sequence: list[str]) -> None:
        sequence[:] = [sequence[-1], *sequence[:-1]]

    monkeypatch.setattr("app.services.crawler.proxy.plan.random.shuffle", rotate)

    settings = FakeSettings(
        proxy_rotation_mode="random",
        max_retries=4,
        private_proxy_url="http://private",
    )
    public_proxies = ["pub-1", "pub-2"]

    plan = planner.build_plan(settings, public_proxies)

    assert plan == [
        {"mode": "direct", "proxy": None},
        {"mode": "public", "proxy": "pub-2"},
        {"mode": "private", "proxy": "http://private"},
        {"mode": "direct", "proxy": None},
    ]
