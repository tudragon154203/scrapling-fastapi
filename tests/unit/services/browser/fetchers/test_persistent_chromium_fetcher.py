import os
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import Mock

import pytest

from app.services.browser.fetchers import persistent_chromium


class FakePage:
    def __init__(self, html: str = "<html></html>", goto_error: Optional[Exception] = None):
        self._html = html
        self.goto_error = goto_error
        self.goto_calls: list[Dict[str, Any]] = []
        self.wait_for_load_state_calls: list[Dict[str, Any]] = []
        self.wait_for_timeout_calls: list[int] = []
        self.closed = False
        self.url = ""

    def goto(self, url: str, timeout: int) -> None:
        self.goto_calls.append({"url": url, "timeout": timeout})
        self.url = url
        if self.goto_error:
            raise self.goto_error

    def wait_for_load_state(self, state: str, timeout: int) -> None:
        self.wait_for_load_state_calls.append({"state": state, "timeout": timeout})

    def wait_for_timeout(self, wait: int) -> None:
        self.wait_for_timeout_calls.append(wait)

    def content(self) -> str:
        return self._html

    def close(self) -> None:
        self.closed = True


class FakeContext:
    def __init__(self, page: FakePage):
        self.page = page
        self.closed = False
        self.new_page_called = 0

    def new_page(self) -> FakePage:
        self.new_page_called += 1
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext):
        self.context = context
        self.new_context_kwargs: Optional[Dict[str, Any]] = None

    def new_context(self, **kwargs: Any) -> FakeContext:
        self.new_context_kwargs = kwargs
        return self.context


class FakeSyncManager:
    def __init__(self, playwright: Any):
        self.playwright = playwright

    def __enter__(self) -> Any:
        return self.playwright

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.fixture(autouse=True)
def enable_playwright(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(persistent_chromium, "PLAYWRIGHT_AVAILABLE", True)


def test_fetch_with_persistent_context(monkeypatch: pytest.MonkeyPatch) -> None:
    page_action_invocations: list[FakePage] = []

    def page_action(page: FakePage) -> None:
        page_action_invocations.append(page)

    fake_page = FakePage(html="<html>persistent</html>")
    fake_context = FakeContext(page=fake_page)
    persistent_kwargs: Dict[str, Any] = {}

    def launch_persistent_context(**kwargs: Any) -> FakeContext:
        persistent_kwargs.update(kwargs)
        return fake_context

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=launch_persistent_context,
            launch=Mock(name="unused_launch"),
        )
    )

    monkeypatch.setattr(
        persistent_chromium,
        "sync_playwright",
        lambda: FakeSyncManager(fake_playwright),
    )

    fetcher = persistent_chromium.PersistentChromiumFetcher(user_data_dir="profile")
    result = fetcher.fetch(
        "https://example.com",
        page_action=page_action,
        extra_headers={"X-Test": "1"},
        useragent="ScraplingBot/1.0",
    )

    assert persistent_kwargs["user_data_dir"] == os.path.abspath("profile")
    assert persistent_kwargs["headless"] is True
    assert persistent_kwargs["args"] == []
    assert persistent_kwargs["extra_http_headers"] == {"X-Test": "1"}
    assert persistent_kwargs["user_agent"] == "ScraplingBot/1.0"
    assert page_action_invocations == [fake_page]
    assert result.url == "https://example.com"
    assert result.html_content == "<html>persistent</html>"
    assert fake_context.new_page_called == 1


def test_fetch_reuses_profile_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    persistent_calls: list[dict[str, Any]] = []
    created_contexts: list[FakeContext] = []

    def launch_persistent_context(**kwargs: Any) -> FakeContext:
        persistent_calls.append(dict(kwargs))
        context = FakeContext(page=FakePage(html="<html>call</html>"))
        created_contexts.append(context)
        return context

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=launch_persistent_context,
            launch=Mock(name="unused_launch"),
        )
    )

    monkeypatch.setattr(
        persistent_chromium,
        "sync_playwright",
        lambda: FakeSyncManager(fake_playwright),
    )

    fetcher = persistent_chromium.PersistentChromiumFetcher(user_data_dir=str(tmp_path))

    results = [
        fetcher.fetch(f"https://example.com/{idx}")
        for idx in range(2)
    ]

    expected_user_data_dir = os.path.abspath(tmp_path)
    assert [call["user_data_dir"] for call in persistent_calls] == [
        expected_user_data_dir,
        expected_user_data_dir,
    ]
    assert len(created_contexts) == 2
    assert all(context.new_page_called == 1 for context in created_contexts)

    for result in results:
        result.page.close()


def test_fetch_with_proxy_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    persistent_kwargs: Dict[str, Any] = {}

    def launch_persistent_context(**kwargs: Any) -> FakeContext:
        persistent_kwargs.update(kwargs)
        return FakeContext(page=FakePage(html="<html>proxy</html>"))

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=launch_persistent_context,
            launch=Mock(name="unused_launch"),
        )
    )

    monkeypatch.setattr(
        persistent_chromium,
        "sync_playwright",
        lambda: FakeSyncManager(fake_playwright),
    )

    fetcher = persistent_chromium.PersistentChromiumFetcher(user_data_dir="profile")
    proxy_arg = "--proxy-server=http://127.0.0.1:8080"

    fetcher.fetch(
        "https://example.com/proxy",
        browser_args=[proxy_arg],
    )

    assert persistent_kwargs["args"] == [proxy_arg]
    assert persistent_kwargs["user_data_dir"] == os.path.abspath("profile")


def test_fetch_ephemeral_context_cleans_up_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    goto_error = RuntimeError("navigation failed")
    fake_page = FakePage(html="<html>boom</html>", goto_error=goto_error)
    fake_context = FakeContext(page=fake_page)
    fake_browser = FakeBrowser(context=fake_context)
    launch_kwargs: Dict[str, Any] = {}

    def launch(**kwargs: Any) -> FakeBrowser:
        launch_kwargs.update(kwargs)
        return fake_browser

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch=launch,
            launch_persistent_context=Mock(name="unused_persistent"),
        )
    )

    monkeypatch.setattr(
        persistent_chromium,
        "sync_playwright",
        lambda: FakeSyncManager(fake_playwright),
    )

    fetcher = persistent_chromium.PersistentChromiumFetcher()

    with pytest.raises(RuntimeError):
        fetcher.fetch(
            "https://example.com/ephemeral",
            headless=False,
            browser_args=["--flag"],
            extra_headers={"Accept-Language": "en"},
            useragent="ScraplingBot/2.0",
        )

    assert launch_kwargs == {"headless": False, "args": ["--flag"]}
    assert fake_browser.new_context_kwargs == {
        "extra_http_headers": {"Accept-Language": "en"},
        "user_agent": "ScraplingBot/2.0",
    }
    assert fake_page.closed is True
    assert fetcher.context is fake_context


def test_fetch_ephemeral_launch_failure_logs_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def launch(**kwargs: Any) -> FakeBrowser:
        raise RuntimeError("launch failed")

    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch=launch,
            launch_persistent_context=Mock(name="unused_persistent"),
        )
    )

    monkeypatch.setattr(
        persistent_chromium,
        "sync_playwright",
        lambda: FakeSyncManager(fake_playwright),
    )

    logger_mock = Mock()
    monkeypatch.setattr(persistent_chromium, "logger", logger_mock)

    fetcher = persistent_chromium.PersistentChromiumFetcher()

    with pytest.raises(RuntimeError):
        fetcher.fetch("https://example.com/launch-error")

    assert fetcher.context is None
    logger_mock.error.assert_called_once()


def test_cleanup_methods_close_resources() -> None:
    fetcher = persistent_chromium.PersistentChromiumFetcher()
    context_mock = Mock()
    fetcher.context = context_mock

    fetcher.close()
    context_mock.close.assert_called_once_with()
    assert fetcher.context is None

    fake_page = Mock()
    result = persistent_chromium.PageResult(page=fake_page, html_content="<html></html>")
    result.__del__()
    fake_page.close.assert_called_once_with()
