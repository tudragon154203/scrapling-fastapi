"""Adapters used across crawler and browser services."""

from .arg_composer import FetchArgComposer
from .fetch_adapter import ScraplingFetcherAdapter

__all__ = ["FetchArgComposer", "ScraplingFetcherAdapter"]
