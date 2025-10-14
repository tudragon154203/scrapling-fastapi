"""Unit tests for Chromium TikTok download configuration helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.services.tiktok.download.strategies.chromium_args import (
    HEADLESS_ONLY_BROWSER_ARGS,
    apply_headless_modifiers,
    build_browser_args,
)
from app.services.tiktok.download.strategies.chromium_user_data import (
    ChromiumUserDataContextProvider,
)
from app.services.tiktok.download.strategies.fetcher_support import (
    fetch_method_supports_argument,
)


class DummyFetcher:
    """Minimal fetcher implementation for compatibility tests."""

    def fetch(
        self, url: str, user_data_dir: str | None = None
    ) -> None:  # pragma: no cover - interface only
        raise NotImplementedError


class VarKeywordFetcher:
    """Fetcher that accepts arbitrary keyword arguments."""

    def fetch(self, url: str, **kwargs) -> None:  # pragma: no cover - interface only
        raise NotImplementedError


class TestChromiumBrowserArgs:
    """Verify Chromium browser argument helpers."""

    def test_headless_args_extend_headful_configuration(self) -> None:
        headful_args = build_browser_args(headless=False)
        headless_args = build_browser_args(headless=True)

        assert len(headless_args) >= len(headful_args)
        assert set(headful_args).issubset(set(headless_args))
        assert any(flag not in headful_args for flag in HEADLESS_ONLY_BROWSER_ARGS)

    def test_headless_args_include_all_flags(self) -> None:
        args = build_browser_args(headless=True)
        for flag in HEADLESS_ONLY_BROWSER_ARGS:
            assert flag in args


class TestHeadlessModifiers:
    """Ensure headless modifiers adjust fetch kwargs."""

    def test_apply_headless_modifiers_returns_new_dict(self) -> None:
        base_kwargs = {"extra_headers": {"User-Agent": "test"}, "wait": 1000}
        result = apply_headless_modifiers(base_kwargs)

        assert result is not base_kwargs
        assert result["wait"] != base_kwargs["wait"]
        assert "Accept" in result["extra_headers"]
        assert base_kwargs["extra_headers"] == {"User-Agent": "test"}

    def test_apply_headless_modifiers_preserves_original_headers(self) -> None:
        base_kwargs = {"extra_headers": {"User-Agent": "existing"}}

        result = apply_headless_modifiers(base_kwargs)

        assert result["extra_headers"]["User-Agent"] == "existing"
        for header in ("Accept", "Accept-Language", "Accept-Encoding", "DNT"):
            assert header in result["extra_headers"]
        # Ensure the original dict is untouched
        assert base_kwargs == {"extra_headers": {"User-Agent": "existing"}}


class TestChromiumUserDataContextProvider:
    """Validate Chromium user data collaborator behaviour."""

    def test_acquire_read_context_returns_absolute_path(self, tmp_path: Path) -> None:
        manager = MagicMock()
        manager.is_enabled.return_value = True

        context = MagicMock()
        path = tmp_path / "chromium"
        path.mkdir()
        context.__enter__.return_value = (str(path), None)
        manager.get_user_data_context.return_value = context

        provider = ChromiumUserDataContextProvider(manager)
        result = provider.acquire_read_context()

        assert result.effective_dir == str(path)
        assert callable(result.cleanup)

        result.cleanup()
        context.__exit__.assert_called_once_with(None, None, None)

    def test_acquire_read_context_disabled_manager(self) -> None:
        manager = MagicMock()
        manager.is_enabled.return_value = False

        provider = ChromiumUserDataContextProvider(manager)
        result = provider.acquire_read_context()

        assert result.effective_dir is None
        assert result.cleanup is None

    def test_acquire_read_context_manager_failure(self, caplog) -> None:
        manager = MagicMock()
        manager.is_enabled.return_value = True
        manager.get_user_data_context.side_effect = RuntimeError("boom")

        provider = ChromiumUserDataContextProvider(manager)
        with caplog.at_level("WARNING"):
            result = provider.acquire_read_context()

        assert result.effective_dir is None
        assert result.cleanup is None
        assert "Failed to create Chromium user data context" in " ".join(caplog.messages)

    def test_cleanup_is_idempotent(self, tmp_path: Path) -> None:
        manager = MagicMock()
        manager.is_enabled.return_value = True

        context = MagicMock()
        directory = tmp_path / "profile"
        directory.mkdir()
        context.__enter__.return_value = (str(directory), None)
        manager.get_user_data_context.return_value = context

        provider = ChromiumUserDataContextProvider(manager)
        result = provider.acquire_read_context()

        assert callable(result.cleanup)

        result.cleanup()
        result.cleanup()

        context.__exit__.assert_called_once_with(None, None, None)


class TestFetcherSupport:
    """Validate fetcher compatibility helper."""

    def test_fetch_method_supports_named_argument(self) -> None:
        assert fetch_method_supports_argument(DummyFetcher, "user_data_dir") is True
        assert fetch_method_supports_argument(DummyFetcher, "additional_args") is False

    def test_fetch_method_supports_varkw(self) -> None:
        assert (
            fetch_method_supports_argument(VarKeywordFetcher, "user_data_dir") is True
        )
        assert (
            fetch_method_supports_argument(VarKeywordFetcher, "additional_args") is True
        )

    @pytest.mark.parametrize("fetcher", [object(), None])
    def test_fetch_method_supports_argument_for_invalid_fetcher(
        self, fetcher: object
    ) -> None:
        assert fetch_method_supports_argument(fetcher, "user_data_dir") is False
