"""Unit tests for :mod:`app.services.crawler.proxy.health.ProxyHealthTracker`."""

import pytest

from app.services.crawler.proxy.health import ProxyHealthTracker


@pytest.fixture
def tracker() -> ProxyHealthTracker:
    return ProxyHealthTracker()


def test_mark_failure_increments_failure_count(tracker: ProxyHealthTracker) -> None:
    proxy = "http://user:pass@example.com:8080"

    tracker.mark_failure(proxy)
    tracker.mark_failure(proxy)

    assert tracker.get_failure_count(proxy) == 2


def test_mark_success_resets_state(tracker: ProxyHealthTracker) -> None:
    proxy = "socks5://example.com:1080"

    tracker.mark_failure(proxy)
    tracker.set_unhealthy(proxy, cooldown_minutes=1)

    tracker.mark_success(proxy)

    assert tracker.get_failure_count(proxy) == 0
    assert tracker.is_unhealthy(proxy) is False


def test_set_unhealthy_respects_cooldown(monkeypatch: pytest.MonkeyPatch, tracker: ProxyHealthTracker) -> None:
    proxy = "http://cooldown.test:3128"
    current_time = 1_700_000_000.0

    def fake_time() -> float:
        return current_time

    monkeypatch.setattr("app.services.crawler.proxy.health.time.time", fake_time)

    tracker.set_unhealthy(proxy, cooldown_minutes=0.5)
    assert tracker.is_unhealthy(proxy) is True

    current_time += 31
    assert tracker.is_unhealthy(proxy) is False


def test_unknown_proxy_operations_are_safe(tracker: ProxyHealthTracker) -> None:
    unknown_proxy = "unknown"

    assert tracker.is_unhealthy(unknown_proxy) is False
    assert tracker.get_failure_count(unknown_proxy) == 0

    tracker.mark_success(unknown_proxy)
    assert tracker.get_failure_count(unknown_proxy) == 0


def test_reset_clears_state(tracker: ProxyHealthTracker) -> None:
    proxy = "http://reset-me:8080"

    tracker.mark_failure(proxy)
    tracker.set_unhealthy(proxy, cooldown_minutes=1)

    tracker.reset()

    assert tracker.get_failure_count(proxy) == 0
    assert tracker.is_unhealthy(proxy) is False


def test_reset_is_idempotent(tracker: ProxyHealthTracker) -> None:
    proxy = "http://idempotent:9000"

    tracker.mark_failure(proxy)

    tracker.reset()
    tracker.reset()

    assert tracker.get_failure_count(proxy) == 0
    assert tracker.is_unhealthy(proxy) is False
