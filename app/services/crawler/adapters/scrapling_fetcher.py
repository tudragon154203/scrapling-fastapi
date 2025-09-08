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
            supports_page_action=_ok("page_action"),
            supports_geoip=_ok("geoip"),
            supports_extra_headers=_ok("extra_headers"),
            supports_user_data_dir=_ok("user_data_dir"),
            supports_profile_dir=_ok("profile_dir"),
            supports_profile_path=_ok("profile_path"),
            supports_user_data=_ok("user_data"),
        )
        return self._capabilities
    
    def fetch(self, url: str, args: Dict[str, Any]) -> Any:
        """Fetch the given URL using StealthyFetcher with thread safety."""
        logger.info(f"Launching browser for URL: {url}")
        try:
            from scrapling.fetchers import StealthyFetcher
        except ImportError:
            raise ImportError("Scrapling library not available")

        StealthyFetcher.adaptive = True

        # Handle asyncio event loop conflicts
        if self._has_running_loop():
            return self._fetch_in_thread(url, args)

        return self._fetch_with_geoip_fallback(url, args)
    
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
        logger.info(f"Launching browser in thread for URL: {url}")

        holder: Dict[str, Any] = {}

        def _runner():
            try:
                result = self._fetch_with_geoip_fallback(url, args)
                holder["result"] = result
            except Exception as e:
                holder["exc"] = e

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()

        if "exc" in holder:
            raise holder["exc"]
        return holder.get("result")

    def _fetch_with_geoip_fallback(self, url: str, args: Dict[str, Any]) -> Any:
        """Fetch with GeoIP fallback: try with geoip, retry without if DB error."""
        try:
            from scrapling.fetchers import StealthyFetcher
            return StealthyFetcher.fetch(url, **args)
        except Exception as e:
            # Check for known GeoIP database errors
            error_str = str(e)
            error_type = str(type(e))
            if ("InvalidDatabaseError" in error_type or
                "GeoLite2-City.mmdb" in error_str):
                logger.warning(f"GeoIP database error: {e}. Retrying without geoip.")
                # Remove geoip from args and retry
                retry_args = args.copy()
                retry_args.pop("geoip", None)
                return StealthyFetcher.fetch(url, **retry_args)
            else:
                # Re-raise if not a GeoIP error
                raise


class FetchArgComposer:
    """Composer for fetch arguments that handles capabilities safely."""
    
    @staticmethod
    def compose(options: Dict[str, Any], caps: FetchCapabilities, selected_proxy: Optional[str], 
                additional_args: Dict[str, Any], extra_headers: Optional[Dict[str, str]], 
                settings: Any, page_action: Optional[Any] = None) -> Dict[str, Any]:
        """Compose fetch arguments from components in a capability-safe way."""
        proxy = selected_proxy  # Alias for compatibility

        def _ok(name: str) -> bool:
            # For capabilities not in FetchCapabilities, we check directly
            return getattr(caps, f"supports_{name}", False)

        fetch_kwargs: Dict[str, Any] = dict(
            headless=options.get("headless", True),
            network_idle=options.get("network_idle", False),
            wait=0,  # Fixed wait time, wait_ms removed from new schema
        )

        # Timeout handling: allow effectively disabling in write mode by using a very large value
        if options.get("disable_timeout") is True:
            # Use a very large timeout (defaults to 24h) to emulate no-timeout without passing null
            large_timeout_ms = getattr(settings, "write_mode_timeout_ms", 86_400_000)
            fetch_kwargs["timeout"] = large_timeout_ms
        else:
            fetch_kwargs["timeout"] = (
                (options.get("timeout_seconds") * 1000)
                if options.get("timeout_seconds")
                else options.get("timeout_ms", 20000)
            )  # Use converted seconds or default ms

        # Only add selector-related args if selector is provided
        if options.get("wait_for_selector"):
            fetch_kwargs["wait_selector"] = options["wait_for_selector"]
            fetch_kwargs["wait_selector_state"] = options.get("wait_for_selector_state", "visible")

        if caps.supports_proxy and proxy:
            fetch_kwargs["proxy"] = proxy
            redacted_proxy = _redact_proxy(proxy)
            logger.debug(f"Using proxy: {redacted_proxy}")
        else:
            logger.debug("No proxy used for this request")

        # Note: geoip, extra_headers, and page_action support need to be handled differently
        # since they're not in the basic FetchCapabilities class
        if _ok("geoip"):
            fetch_kwargs["geoip"] = True

        if caps.supports_additional_args and additional_args:
            # Filter out internal cleanup function
            filtered_additional_args = {k: v for k, v in additional_args.items() if not k.startswith('_')}
            if filtered_additional_args:
                fetch_kwargs["additional_args"] = filtered_additional_args

        if _ok("extra_headers") and extra_headers:
            fetch_kwargs["extra_headers"] = extra_headers

        if _ok("page_action") and page_action is not None:
            fetch_kwargs["page_action"] = page_action

        # Enable Cloudflare solving when supported by StealthyFetcher
        # if caps.supports_solve_cloudflare:
        #     fetch_kwargs["solve_cloudflare"] = True

        return fetch_kwargs
