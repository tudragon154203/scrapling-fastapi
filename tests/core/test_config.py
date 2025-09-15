import importlib
import sys
import types

from app.core import config


def test_get_settings_env_vars(monkeypatch):
    """Ensure environment variables override defaults using pydantic settings."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PORT", "1234")
    monkeypatch.setenv("HEADLESS", "0")
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.log_level == "DEBUG"
    assert settings.port == 1234
    assert settings.default_headless is False


def test_get_settings_fallback(monkeypatch):
    """Simulate missing pydantic_settings to trigger fallback Settings class."""
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    real_ps = sys.modules.get("pydantic_settings")
    real_loader = sys.modules.get("app.core.pydantic_loader")
    dummy = types.ModuleType("pydantic_settings")
    dummy.BaseSettings = None
    dummy.SettingsConfigDict = dict
    monkeypatch.setitem(sys.modules, "pydantic_settings", dummy)
    if real_loader is not None:
        monkeypatch.delitem(sys.modules, "app.core.pydantic_loader", raising=False)
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert config.get_settings.__module__ == "app.core.env_loader"
    assert settings.log_level == "INFO"
    assert settings.port == 8000
    if real_ps is not None:
        sys.modules["pydantic_settings"] = real_ps
    else:
        sys.modules.pop("pydantic_settings", None)
    if real_loader is not None:
        sys.modules["app.core.pydantic_loader"] = real_loader
    importlib.reload(config)
    config.get_settings.cache_clear()


def test_env_loader_supports_legacy_aliases(monkeypatch):
    """Ensure fallback loader still honors historical environment names."""

    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("NETWORK_IDLE", "1")
    monkeypatch.setenv("TIMEOUT_MS", "15000")
    real_ps = sys.modules.get("pydantic_settings")
    real_loader = sys.modules.get("app.core.pydantic_loader")
    dummy = types.ModuleType("pydantic_settings")
    dummy.BaseSettings = None
    dummy.SettingsConfigDict = dict
    monkeypatch.setitem(sys.modules, "pydantic_settings", dummy)
    if real_loader is not None:
        monkeypatch.delitem(sys.modules, "app.core.pydantic_loader", raising=False)
    importlib.reload(config)
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert config.get_settings.__module__ == "app.core.env_loader"
    assert settings.default_headless is False
    assert settings.default_network_idle is True
    assert settings.default_timeout_ms == 15_000
    if real_ps is not None:
        sys.modules["pydantic_settings"] = real_ps
    else:
        sys.modules.pop("pydantic_settings", None)
    if real_loader is not None:
        sys.modules["app.core.pydantic_loader"] = real_loader
    importlib.reload(config)
    config.get_settings.cache_clear()
