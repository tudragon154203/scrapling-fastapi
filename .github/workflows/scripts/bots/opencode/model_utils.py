"""Utilities shared across opencode workflow scripts."""

from __future__ import annotations

import re


_WHITESPACE_RE = re.compile(r"\s+")


def canonicalize_model(model: str) -> str:
    """Normalize model identifiers to the format expected by the CLI."""

    if not isinstance(model, str):
        return ""

    normalized = _WHITESPACE_RE.sub("", model).lower()

    if not normalized:
        return ""

    if "/" not in normalized and ":" not in normalized:
        return normalized

    slug = normalized
    if slug.startswith("openrouter/"):
        slug = slug[len("openrouter/") :]

    if "/" in slug:
        slug = slug.rsplit("/", 1)[-1]

    slug = slug.replace("/", "-").replace(":", "-")

    slug = slug.strip("- ")
    if not slug:
        return "openrouter"

    return f"openrouter.{slug}"


__all__ = ["canonicalize_model"]

