"""Tests for application settings configuration validators."""

from __future__ import annotations

import os

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "raw_value", ["  ", "\t", "\n"],
    ids=["spaces", "tab", "newline"],
)
def test_chromium_user_data_dir_blank_is_none(raw_value: str) -> None:
    """Providing blank values should coerce to ``None``."""

    settings = Settings(chromium_user_data_dir=raw_value)

    assert settings.chromium_user_data_dir is None


def test_chromium_user_data_dir_relative_path_becomes_absolute() -> None:
    """Relative paths should be normalized to absolute paths."""

    relative_path = "profiles/test"
    expected = os.path.abspath(relative_path)

    settings = Settings(chromium_user_data_dir=relative_path)

    assert settings.chromium_user_data_dir == expected


def test_chromium_user_data_dir_abspath_error_returns_original(monkeypatch: pytest.MonkeyPatch) -> None:
    """If ``os.path.abspath`` raises ``OSError`` the original path should be used."""

    def raising_abspath(_: str) -> str:
        raise OSError("boom")

    monkeypatch.setattr("app.core.config.os.path.abspath", raising_abspath)

    raw_value = "profiles/test"
    settings = Settings(chromium_user_data_dir=raw_value)

    assert settings.chromium_user_data_dir == raw_value
