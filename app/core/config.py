"""Application configuration entry-point."""

from __future__ import annotations

from .config_base import Settings

try:  # pragma: no cover - exercised via tests in both branches
    from .pydantic_loader import get_settings  # type: ignore F401
except Exception:  # noqa: BLE001 - fallback when dependency is missing
    from .env_loader import get_settings  # type: ignore F401


__all__ = ["Settings", "get_settings"]

