"""Settings loader backed by ``pydantic-settings``."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .config_base import Settings as SettingsModel


class Settings(BaseSettings, SettingsModel):
    """Settings implementation that loads from the environment/.env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        populate_by_name=True,
    )


@lru_cache()
def get_settings() -> SettingsModel:
    """Return cached settings loaded via ``pydantic-settings``."""

    return Settings()


__all__ = ["Settings", "get_settings"]

