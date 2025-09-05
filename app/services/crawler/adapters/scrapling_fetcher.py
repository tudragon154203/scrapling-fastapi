import inspect
import logging
import threading
from typing import Any, Dict, Optional
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

from app.services.crawler.core.interfaces import IFetchClient
from app.services.crawler.core.types import FetchCapabilities
from app.services.crawler.proxy.redact import redact_proxy as _redact_proxy


logger = logging.getLogger(__name__)


class ScraplingFetcherAdapter(IFetchClient):
    """Adapter for Scrapling's StealthyFetcher that bridges to OOP interfaces."""
    
    def __init__(self):
        self._capabilities: Optional[FetchCapabilities] = None
        
    def detect_capabilities(self) -> FetchCapabilities:
        """Detect fetch capabilities by introspecting StealthyFetcher.fetch signature."""
        if self._capabilities is not None:
            return self._capabilities
            
        try:
            from scrapling.fetchers import StealthyFetcher
            _sig = inspect.signature(StealthyFetcher.fetch)
            _fetch_params = set(_sig.parameters.keys())
            _has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in _sig.parameters.values())
        except Exception:
            _fetch_params = set()
            _has_varkw = False

        def _ok(name: str) -> bool:
            return (name in _fetch_params) or _has_varkw

        self._capabilities = FetchCapabilities(
            supports_proxy=_ok("proxy"),
            supports_network_idle=_ok("network_idle"),
            supports_timeout=_ok("timeout"),
            supports_additional_args=_ok("additional_args"),
        )
        return self._capabilities
    
    def fetch(self, url: str, args: Dict[str, Any]) -> Any:
        """Fetch the given URL using StealthyFetcher with thread safety."""
        try:
            from scrapling.fetchers import StealthyFetcher
        except ImportError:
            raise ImportError("Scrapling library not available")
        
        StealthyFetcher.adaptive = True
        
        # Handle asyncio event loop conflicts
        if self._has_running_loop():
            return self._fetch_in_thread(url, args)
        
        return StealthyFetcher.fetch(url, **args)
    
    def _has_running_loop(self) -> bool:
        """Check if there's a running asyncio event loop in the current thread."""
        try:
            import asyncio
            asyncio.get_running_loop()
            return True
        except Exception:
            return False
    
    def _fetch_in_thread(self, url: str, args: Dict[str, Any]) -> Any:
        """Execute fetch in a dedicated thread if event loop is running."""
        
        def _runner():
            try:
                from scrapling.fetchers import StealthyFetcher
                return StealthyFetcher.fetch(url, **args)
            except Exception as e:
                # Store exception to re-raise in caller thread
                return {"exc": e}
        
        holder: Dict[str, Any] = {}
        
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        
        if "exc" in holder:
            raise holder["exc"]
        return holder.get("result")


class FetchArgComposer:
    """Composer for fetch arguments that handles capabilities safely."""
    
    @staticmethod
    def compose(options: Dict[str, Any], caps: FetchCapabilities, selected_proxy: Optional[str], 
                additional_args: Dict[str, Any], extra_headers: Optional[Dict[str, str]], 
                settings: Any, page_action: Optional[Any] = None) -> Dict[str, Any]:
        """Compose fetch arguments from components in a capability-safe way."""
        geoip_enabled = bool(getattr(settings, "camoufox_geoip", True) and selected_proxy)
        proxy = selected_proxy  # Alias for compatibility

        def _ok(name: str) -> bool:
            # For capabilities not in FetchCapabilities, we check directly
            return getattr(caps, f"supports_{name}", False)

        fetch_kwargs: Dict[str, Any] = dict(
            headless=options["headless"],
            network_idle=options["network_idle"],
            wait_selector=options["wait_selector"],
            wait_selector_state=options.get("wait_selector_state") or None,
            timeout=options["timeout_ms"],
            wait=options["wait_ms"] or 0,
        )

        if caps.supports_proxy and proxy:
            fetch_kwargs["proxy"] = proxy
            redacted_proxy = _redact_proxy(proxy)
            logger.info(f"Using proxy: {redacted_proxy}")
        else:
            logger.info("No proxy used for this request")

        # Note: geoip, extra_headers, and page_action support need to be handled differently
        # since they're not in the basic FetchCapabilities class
        if _ok("geoip") and geoip_enabled:
            fetch_kwargs["geoip"] = True

        if caps.supports_additional_args and additional_args:
            fetch_kwargs["additional_args"] = additional_args

        if _ok("extra_headers") and extra_headers:
            fetch_kwargs["extra_headers"] = extra_headers

        if _ok("page_action") and page_action is not None:
            fetch_kwargs["page_action"] = page_action

        # Enable Cloudflare solving when supported by StealthyFetcher
        # if caps.supports_solve_cloudflare:
        #     fetch_kwargs["solve_cloudflare"] = True

        return fetch_kwargs