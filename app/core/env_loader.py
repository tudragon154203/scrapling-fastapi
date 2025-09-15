"""Manual environment loader used when ``pydantic-settings`` is unavailable."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, Iterable

from .config_base import Settings


def _iter_env_keys(field_name: str, field) -> Iterable[str]:
    """Yield environment variable names to check for a field."""

    seen: set[str] = set()
    alias = getattr(field, "validation_alias", None)
    if alias:
        if isinstance(alias, str):
            seen.add(alias)
            yield alias
        else:
            choices = getattr(alias, "choices", None)
            if choices:
                for candidate in choices:
                    if isinstance(candidate, str) and candidate not in seen:
                        seen.add(candidate)
                        yield candidate
    extra = field.json_schema_extra or {}
    env_setting = extra.get("env")
    if env_setting:
        if isinstance(env_setting, (tuple, list, set)):
            for candidate in env_setting:
                if isinstance(candidate, str) and candidate not in seen:
                    seen.add(candidate)
                    yield candidate
        elif isinstance(env_setting, str) and env_setting not in seen:
            seen.add(env_setting)
            yield env_setting
    upper_name = field_name.upper()
    if upper_name not in seen:
        yield upper_name


def _collect_env_overrides() -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for field_name, field in Settings.model_fields.items():
        for env_key in _iter_env_keys(field_name, field):
            value = os.getenv(env_key)
            if value is not None:
                overrides[field_name] = value
                break
    return overrides


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings built from raw environment variables."""

    overrides = _collect_env_overrides()
    return Settings(**overrides)


__all__ = ["get_settings"]

