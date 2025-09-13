import inspect
import logging
import threading
from typing import Any, Dict, Optional
from app.services.common.interfaces import IFetchClient
from app.services.common.types import FetchCapabilities
from app.services.crawler.proxy.redact import redact_proxy as _redact_proxy
import asyncio
import sys
from urllib.request import Request, urlopen

import types
from scrapling.fetchers import StealthyFetcher

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

    def fetch(self, url: str, args: Dict[str, Any]) -> Any:
        """Fetch the given URL using StealthyFetcher with thread safety."""
        logger.info(f"Launching browser for URL: {url}")
        try:
            pass  # Already imported at the top
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
                import asyncio
                # Set proper event loop policy for Windows in the thread
                if sys.platform == "win32":
                    try:
                        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    except Exception:
                        pass
                result = StealthyFetcher.fetch(url, **args)
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
                # Consider light-weight HTTP fallback for navigation timeouts on JS-heavy pages
                if ("Timeout" in error_type or "Timeout" in error_str or "Page.goto" in error_str) \
                   and (args.get("wait_selector") is not None) \
                   and (not bool(args.get("network_idle", False))):
                    try:
                        return self._http_fallback(url)
                    except Exception:
                        pass
                # Re-raise if not handled
                raise

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
            logger.info(f"HTTP fallback failed: {type(e).__name__}: {e}")
            raise

    def get_user_data_cleanup(self) -> Optional[callable]:
        """Get the user data cleanup function for cleanup after fetch."""
        cleanup_func = self._user_data_cleanup
        # Reset the cleanup function after getting it
        self._user_data_cleanup = None
        return cleanup_func


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
            wait=int(options.get("wait_ms", 0) or 0),  # allow small stabilization delay after waits
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
        if caps.supports_geoip:
            fetch_kwargs["geoip"] = True
        if caps.supports_additional_args and additional_args:
            # Filter out any private/sentinel keys (e.g., cleanup callbacks) so they are NOT
            # forwarded into browser launch kwargs (e.g., Playwright), which would error.
            # Also filter out keys that are not supported by the fetcher
            try:
                safe_additional_args = {}
                for k, v in (additional_args or {}).items():
                    # Skip private/sentinel keys
                    if str(k).startswith("_"):
                        continue
                    # Check if the key is supported by the fetcher
                    if _ok(k):
                        safe_additional_args[k] = v
                    # Special case: user_data_dir, profile_dir, profile_path, user_data are all related to user data
                    # If any of these are supported, we can pass user_data_dir
                    elif k == "user_data_dir" and (_ok("user_data_dir") or _ok("profile_dir") or _ok("profile_path") or _ok("user_data")):
                        safe_additional_args[k] = v
                    elif k == "profile_dir" and (_ok("profile_dir") or _ok("user_data_dir") or _ok("profile_path") or _ok("user_data")):
                        safe_additional_args[k] = v
                    elif k == "profile_path" and (_ok("profile_path") or _ok("user_data_dir") or _ok("profile_dir") or _ok("user_data")):
                        safe_additional_args[k] = v
                    elif k == "user_data" and (_ok("user_data") or
                                               _ok("user_data_dir") or
                                               _ok("profile_dir") or
                                               _ok("profile_path")):
                        safe_additional_args[k] = v
            except Exception:
                safe_additional_args = additional_args or {}
            if safe_additional_args:
                fetch_kwargs["additional_args"] = safe_additional_args
        if _ok("extra_headers") and extra_headers:
            fetch_kwargs["extra_headers"] = extra_headers
        if _ok("page_action") and page_action is not None:
            fetch_kwargs["page_action"] = page_action
        # Avoid strict 'load' navigation wait for selector-driven flows
        # When a selector is provided and network_idle is False, prefer a lighter wait
        # by hinting the engine via custom_config. This relies on Scrapling/Camoufox
        # honoring 'wait_until' for navigation.
        if options.get("prefer_domcontentloaded") and _ok("custom_config"):
            # Initialize or extend custom_config
            cfg = fetch_kwargs.get("custom_config") or {}
            # Use commonly recognized keys
            cfg.setdefault("wait_until", "domcontentloaded")
            cfg.setdefault("goto_wait_until", "domcontentloaded")
            fetch_kwargs["custom_config"] = cfg
        # Enable Cloudflare solving when supported by StealthyFetcher
        # if caps.supports_solve_cloudflare:
        #     fetch_kwargs["solve_cloudflare"] = True
        return fetch_kwargs
