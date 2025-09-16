"""Protocol and typed helper definitions for TikTok search services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Protocol, TypedDict, Union

if TYPE_CHECKING:  # pragma: no cover
    from app.services.common.adapters.scrapling_fetcher import (
        FetchArgComposer,
        ScraplingFetcherAdapter,
    )


CleanupCallable = Callable[[], None]


class FetcherProtocol(Protocol):
    """Minimal protocol for objects used to fetch TikTok search pages."""

    def detect_capabilities(self) -> Any:  # pragma: no cover - interface declaration
        ...

    def fetch(self, url: str, options: Dict[str, Any]) -> Any:  # pragma: no cover - interface declaration
        ...


class ComposerProtocol(Protocol):
    """Protocol describing the compose behaviour required by the service."""

    def compose(
        self,
        *,
        options: Dict[str, Any],
        caps: Any,
        selected_proxy: Optional[str],
        additional_args: Dict[str, Any],
        extra_headers: Optional[Dict[str, Any]],
        settings: Any,
        page_action: Optional[Any],
    ) -> Dict[str, Any]:  # pragma: no cover - interface declaration
        ...


class SearchContext(TypedDict):
    fetcher: Union["ScraplingFetcherAdapter", FetcherProtocol]
    composer: Union["FetchArgComposer", ComposerProtocol]
    caps: Any
    additional_args: Dict[str, Any]
    extra_headers: Optional[Dict[str, Any]]
    user_data_cleanup: Optional[CleanupCallable]
    options: Dict[str, Any]
