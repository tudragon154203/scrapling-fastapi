import importlib
import sys
import types

from app.core import config


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
