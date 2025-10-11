import inspect
import logging
import threading
from typing import Any, Dict, Optional, Union
from app.services.common.interfaces import IFetchClient
from app.services.common.adapters.fetch_params import FetchParams
from app.services.common.types import FetchCapabilities
import asyncio
import sys
from urllib.request import Request, urlopen

import types
import importlib

logger = logging.getLogger(__name__)


class ScraplingFetcherAdapter(IFetchClient):
    """Adapter for Scrapling's StealthyFetcher that bridges to OOP interfaces."""

    def __init__(self):
        self._capabilities: Optional[FetchCapabilities] = None
        self._user_data_cleanup = None

    def detect_capabilities(self) -> FetchCapabilities:
        """Detect fetch capabilities by introspecting StealthyFetcher.fetch signature."""
        if self._capabilities is not None:
            return self._capabilities
        try:
            StealthyFetcher = self._get_stealthy_fetcher()
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
            supports_custom_config=_ok("custom_config"),
        )
        return self._capabilities

    def fetch(self, url: str, args: Union[FetchParams, Dict[str, Any], None]) -> Any:
        """Fetch the given URL using StealthyFetcher with thread safety."""
        logger.debug(f"Launching browser for URL: {url}")
        StealthyFetcher = self._get_stealthy_fetcher()
        StealthyFetcher.adaptive = True
        params = args if isinstance(args, FetchParams) else FetchParams(args or {})
        return self._run_with_event_loop(url, params)

    def _run_with_event_loop(self, url: str, params: FetchParams) -> Any:
        """Execute fetch directly or delegate to a background thread when needed."""
        if self._has_running_loop():
            return self._fetch_in_thread(url, params)
        return self._fetch_with_retry(url, params)

    def _has_running_loop(self) -> bool:
        """Check if there's a running asyncio event loop in the current thread."""
        try:
            asyncio.get_running_loop()
            return True
        except Exception:
            return False

    def _fetch_in_thread(self, url: str, params: FetchParams) -> Any:
        """Execute fetch in a dedicated thread if event loop is running."""
        logger.debug(f"Launching browser in thread for URL: {url}")
        holder: Dict[str, Any] = {}

        def _runner():
            try:
                import asyncio
                # Set proper event loop policy for Windows in the thread
                if sys.platform == "win32":
                    try:
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    except Exception:
                        pass
                holder["result"] = self._fetch_with_retry(url, params)
            except Exception as e:
                holder["exc"] = e
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()
        if "exc" in holder:
            raise holder["exc"]
        return holder.get("result")

    def _fetch_with_retry(self, url: str, params: FetchParams) -> Any:
        """Attempt fetch, retrying without GeoIP or via HTTP fallback when needed."""
        try:
            return self._execute_fetch(url, params)
        except Exception as exc:
            if params.geoip_enabled and self._is_geoip_error(exc):
                logger.warning(f"GeoIP database error: {exc}. Retrying without geoip.")
                return self._execute_fetch(url, params.without_geoip())
            if self._should_http_fallback(exc, params):
                try:
                    return self._http_fallback(url)
                except Exception:
                    pass
            raise

    def _execute_fetch(self, url: str, params: FetchParams) -> Any:
        StealthyFetcher = self._get_stealthy_fetcher()
        return StealthyFetcher.fetch(url, **params.as_kwargs())

    @staticmethod
    def _is_geoip_error(exc: Exception) -> bool:
        error_str = str(exc)
        error_type = type(exc).__name__
        return "InvalidDatabaseError" in error_type or "GeoLite2-City.mmdb" in error_str

    @staticmethod
    def _should_http_fallback(exc: Exception, params: FetchParams) -> bool:
        error_str = str(exc)
        error_type = type(exc).__name__
        timeout_error = (
            "Timeout" in error_type
            or "Timeout" in error_str
            or "Page.goto" in error_str
        )
        if not timeout_error:
            return False
        return params.allows_http_fallback

    def _http_fallback(self, url: str) -> Any:
        """Simple HTTP fallback returning a minimal response-like object.
        Used as a best-effort escape hatch when Playwright navigation waits fail,
        especially on pages that still serve static HTML. Not a full replacement
        for browser fetch; only used when Scrapling navigation times out.
        """
        try:
            # Use a desktop UA to avoid trivial bot blocks
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                },
            )
            with urlopen(req, timeout=30) as resp:
                html_bytes = resp.read() or b""
                html = html_bytes.decode("utf-8", errors="ignore")
                holder = types.SimpleNamespace()
                holder.status = getattr(resp, "status", 200) or 200
                holder.html_content = html
                return holder
        except Exception as e:
            logger.debug(f"HTTP fallback failed: {type(e).__name__}: {e}")
            raise

    def get_user_data_cleanup(self) -> Optional[callable]:
        """Get the user data cleanup function for cleanup after fetch."""
        cleanup_func = self._user_data_cleanup
        # Reset the cleanup function after getting it
        self._user_data_cleanup = None
        return cleanup_func

    def _get_stealthy_fetcher(self):
        """Resolve and return the current StealthyFetcher class.

        This method supports tests that monkeypatch `sys.modules` with fake
        `scrapling` or `scrapling.fetchers` modules by checking those entries
        first before attempting a real import. Raises ImportError if not found.
        """
        # Prefer explicitly injected module in sys.modules (common in tests)
        fetchers_mod = sys.modules.get("scrapling.fetchers")
        if fetchers_mod is not None and hasattr(fetchers_mod, "StealthyFetcher"):
            return getattr(fetchers_mod, "StealthyFetcher")
        scrapling_mod = sys.modules.get("scrapling")
        if scrapling_mod is not None:
            fetchers = getattr(scrapling_mod, "fetchers", None)
            if fetchers is not None and hasattr(fetchers, "StealthyFetcher"):
                return getattr(fetchers, "StealthyFetcher")
        # Fallback to dynamic import
        try:
            scrapling_mod = importlib.import_module("scrapling")
            fetchers_mod = getattr(scrapling_mod, "fetchers", None) or importlib.import_module("scrapling.fetchers")
            return getattr(fetchers_mod, "StealthyFetcher")
        except Exception as e:
            raise ImportError("Scrapling library not available") from e
