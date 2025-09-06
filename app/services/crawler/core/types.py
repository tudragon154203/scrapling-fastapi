from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.schemas.crawl import CrawlRequest


@dataclass
class CrawlOptions:
    """Options for crawling operations."""
    headless: bool = True
    network_idle: bool = True
    timeout: int = 30
    wait_for_selector: Optional[str] = None
    
    @classmethod
    def from_request(cls, request: CrawlRequest) -> 'CrawlOptions':
        """Create options from crawl request."""
        return cls(
            headless=getattr(request, 'headless', True),
            network_idle=getattr(request, 'network_idle', True),
            timeout=getattr(request, 'timeout', 30),
            wait_for_selector=getattr(request, 'wait_for_selector', None)
        )


@dataclass
class FetchArgs:
    """Arguments for fetch operations."""
    url: str
    options: CrawlOptions
    proxy: Optional[str] = None
    additional_args: Optional[Dict[str, Any]] = None
    extra_headers: Optional[Dict[str, str]] = None
    page_action: Optional[Any] = None


@dataclass
class Attempt:
    """Single crawl attempt configuration."""
    index: int
    proxy: Optional[str]
    mode: str  # 'direct', 'public', 'private'
    
    def __post_init__(self):
        if self.mode not in ('direct', 'public', 'private'):
            raise ValueError(f"Invalid mode: {self.mode}")


@dataclass
class FetchCapabilities:
    """Capabilities detected for fetch operations."""
    supports_proxy: bool = False
    supports_network_idle: bool = False
    supports_timeout: bool = False
    supports_additional_args: bool = False
    supports_page_action: bool = True  # Force enable since we know StealthyFetcher supports it
    supports_geoip: bool = False
    supports_extra_headers: bool = False
    
    def __bool__(self) -> bool:
        """Return True if any capabilities are supported."""
        return any([
            self.supports_proxy,
            self.supports_network_idle,
            self.supports_timeout,
            self.supports_additional_args,
            self.supports_page_action,
            self.supports_geoip,
            self.supports_extra_headers,
        ])
