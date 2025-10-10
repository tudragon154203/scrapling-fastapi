from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol
from app.schemas.crawl import CrawlRequest, CrawlResponse


class PageAction(Protocol):
    """Protocol for page actions that can be applied to a page."""

    def apply(self, page: Any) -> Any:
        """Apply the page action to the given page."""
        ...


class IExecutor(ABC):
    """Interface for crawl executors."""

    @abstractmethod
    def execute(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Execute a crawl request with optional page action."""
        ...


class IFetchClient(ABC):
    """Interface for fetch clients."""

    @abstractmethod
    def fetch(self, url: str, args: Dict[str, Any]) -> Any:
        """Fetch the given URL with provided arguments."""
        ...

    @abstractmethod
    def detect_capabilities(self) -> Dict[str, Any]:
        """Detect fetch capabilities."""
        ...


class IBackoffPolicy(ABC):
    """Interface for backoff policies."""

    @abstractmethod
    def delay_for_attempt(self, attempt_idx: int) -> float:
        """Calculate delay for the given attempt index."""
        ...


class IAttemptPlanner(ABC):
    """Interface for attempt planners."""

    @abstractmethod
    def build_plan(self, settings: Any, public_proxies: list) -> list[Dict[str, Any]]:
        """Build a plan of crawl attempts."""
        ...


class IProxyListSource(ABC):
    """Interface for proxy list sources."""

    @abstractmethod
    def load(self) -> list[str]:
        """Load proxy list from source."""
        ...


class IProxyHealthTracker(ABC):
    """Interface for proxy health tracking."""

    @abstractmethod
    def mark_failure(self, proxy: str) -> None:
        """Mark a proxy as failed."""
        ...

    @abstractmethod
    def mark_success(self, proxy: str) -> None:
        """Mark a proxy as successful."""
        ...

    @abstractmethod
    def is_unhealthy(self, proxy: str) -> bool:
        """Check if a proxy is currently unhealthy."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset all proxy health states."""
        ...


class IFetchArgComposer(ABC):
    """Interface for fetch argument composition."""

    @abstractmethod
    def compose(self, options: Any, caps: Dict[str, Any], proxy: Optional[str],
                additional_args: Dict[str, Any], extra_headers: Dict[str, str],
                settings: Any, page_action: Optional[PageAction] = None) -> Dict[str, Any]:
        """Compose fetch arguments from components."""
        ...


class IOptionsResolver(ABC):
    """Interface for options resolution."""

    @abstractmethod
    def resolve(self, request: CrawlRequest, settings: Any) -> Any:
        """Resolve effective options from request and settings."""
        ...


class ICrawlerEngine(ABC):
    """Interface for the main crawler engine."""

    @abstractmethod
    def run(self, request: CrawlRequest, page_action: Optional[PageAction] = None) -> CrawlResponse:
        """Run a crawl request with optional page action."""
        ...
