import importlib
import os
import sys
import types

import pytest

from app.core import config
from app.core.config import Settings
pytestmark = [pytest.mark.unit]


def test_get_settings_env_vars(monkeypatch):
    """Ensure environment variables override defaults using pydantic settings."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "1234")
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.log_level == "DEBUG"
    assert settings.port == 1234


def test_get_settings_fallback(monkeypatch):
    """Simulate missing pydantic_settings to trigger fallback Settings class."""
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    real_ps = sys.modules.get("pydantic_settings")
    dummy = types.ModuleType("pydantic_settings")
    dummy.BaseSettings = None
    dummy.SettingsConfigDict = dict
    monkeypatch.setitem(sys.modules, "pydantic_settings", dummy)
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.log_level == "INFO"
    assert settings.port == 8000
    sys.modules["pydantic_settings"] = real_ps
    importlib.reload(config)


@pytest.mark.parametrize(
    "raw_value",
    ["  ", "\t", "\n"],
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
