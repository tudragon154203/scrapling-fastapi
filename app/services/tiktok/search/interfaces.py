"""Interface definitions for TikTok search services."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, Union, runtime_checkable


@runtime_checkable
class TikTokSearchInterface(Protocol):
    """Contract for asynchronous TikTok search implementations.

    Implementations encapsulate the concrete logic for performing a TikTok
    search (network calls, parsing, retries, etc.) and return a normalized
    payload that the rest of the application can consume.  The interface is kept
    intentionally small so different search backends (mock services, offline
    fixtures, live scrapers, etc.) can be injected interchangeably wherever a
    TikTok search capability is required.

    Args:
        query: Either a single query string or a list of query strings to
            execute sequentially.
        num_videos: Target number of videos to collect from the search
            operation.

    Returns:
        A dictionary containing the normalized TikTok search results.
    """

    async def search(
        self,
        query: Union[str, List[str]],
        num_videos: int,
    ) -> Dict[str, Any]:
        """Execute a TikTok search and return the structured results."""
        ...
