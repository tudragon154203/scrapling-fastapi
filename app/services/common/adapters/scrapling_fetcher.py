import inspect
import logging
import threading
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Optional, Union
from app.services.common.interfaces import IFetchClient
from app.services.common.types import FetchCapabilities
from app.services.crawler.proxy.redact import redact_proxy as _redact_proxy
import asyncio
import sys
from urllib.request import Request, urlopen

import types
import importlib

logger = logging.getLogger(__name__)


@dataclass
class FetchParams(MutableMapping[str, Any]):
    """Stateful mapping of Scrapling fetch keyword arguments."""

    _values: Dict[str, Any] = field(default_factory=dict)
    geoip_enabled: bool = field(init=False)
    wait_selector: Optional[str] = field(init=False)
    network_idle_enabled: bool = field(init=False)

    def __post_init__(self) -> None:
        # Always copy user-provided mappings so mutations stay local.
        self._values = dict(self._values or {})
        self._refresh_state()

    # -- MutableMapping protocol -------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        return self._values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._values[key] = value
        self._refresh_state()

    def __delitem__(self, key: str) -> None:
        del self._values[key]
        self._refresh_state()

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    # -- Convenience helpers -----------------------------------------------------
    def _refresh_state(self) -> None:
        self.geoip_enabled = bool(self._values.get("geoip"))
        self.wait_selector = self._values.get("wait_selector")
        self.network_idle_enabled = bool(self._values.get("network_idle", False))

    def as_kwargs(self) -> Dict[str, Any]:
        """Return a shallow copy suitable for **kwargs expansion."""
        return dict(self._values)

    def copy(self) -> "FetchParams":
        """Clone the current parameters for safe mutation."""
        return FetchParams(self._values)

    def without_geoip(self) -> "FetchParams":
        """Produce a copy with geoip removed."""
        if "geoip" not in self._values:
            return self.copy()
        clone = dict(self._values)
        clone.pop("geoip", None)
        return FetchParams(clone)

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        return self._values.get(key, default)

    def setdefault(self, key: str, default: Any = None) -> Any:
        result = self._values.setdefault(key, default)
        self._refresh_state()
        return result

    def update(self, mapping: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        if mapping:
            self._values.update(mapping)
        if kwargs:
            self._values.update(kwargs)
        self._refresh_state()

    def items(self):
        return self._values.items()

    def __contains__(self, item: object) -> bool:
        return item in self._values

    @property
    def allows_http_fallback(self) -> bool:
        """Return True when HTTP fallback is viable for timeout errors."""
        return self.wait_selector is not None and not self.network_idle_enabled


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

    async def fetch_async(self, url: str, args: Union[FetchParams, Dict[str, Any], None]) -> Any:
        """Fetch the given URL using StealthyFetcher asynchronously."""
        logger.debug(f"Launching browser asynchronously for URL: {url}")
        StealthyFetcher = self._get_stealthy_fetcher()
        StealthyFetcher.adaptive = True
        params = args if isinstance(args, FetchParams) else FetchParams(args or {})
        return await self._execute_fetch_async(url, params)

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

    async def _execute_fetch_async(self, url: str, params: FetchParams) -> Any:
        """Execute fetch asynchronously using StealthyFetcher's async methods."""
        StealthyFetcher = self._get_stealthy_fetcher()
        # Check if StealthyFetcher has async_fetch method
        if hasattr(StealthyFetcher, 'async_fetch'):
            return await StealthyFetcher.async_fetch(url, **params.as_kwargs())
        else:
            # Fallback: use asyncio.to_thread for the sync fetch method
            return await asyncio.to_thread(self._execute_fetch, url, params)

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


class FetchArgComposer:
    """Composer for fetch arguments that handles capabilities safely."""

    _USER_DATA_KEYS: tuple[str, ...] = (
        "user_data_dir",
        "profile_dir",
        "profile_path",
        "user_data",
        "firefox_user_prefs",
    )

    @classmethod
    def compose(
        cls,
        options: Dict[str, Any],
        caps: FetchCapabilities,
        selected_proxy: Optional[str],
        additional_args: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]],
        settings: Any,
        page_action: Optional[Any] = None,
    ) -> FetchParams:
        """Compose fetch arguments from components in a capability-safe way."""
        proxy = selected_proxy  # Alias for compatibility
        # Handle None options gracefully
        options = options or {}
        fetch_kwargs = FetchParams(
            {
                "headless": options.get("headless", True),
                "network_idle": options.get("network_idle", False),
                "wait": int(options.get("wait_ms", 0) or 0),
            }
        )
        cls._apply_timeouts(fetch_kwargs, options, settings)

        if options.get("wait_for_selector"):
            fetch_kwargs["wait_selector"] = options["wait_for_selector"]
            fetch_kwargs["wait_selector_state"] = options.get("wait_for_selector_state", "attached")

        if getattr(caps, "supports_proxy", False) and proxy:
            fetch_kwargs["proxy"] = proxy
            redacted_proxy = _redact_proxy(proxy)
            logger.debug(f"Using proxy: {redacted_proxy}")
        else:
            logger.debug("No proxy used for this request")

        if getattr(caps, "supports_geoip", False):
            fetch_kwargs["geoip"] = True

        cls._apply_user_data(fetch_kwargs, caps, additional_args or {})
        cls._apply_headers(fetch_kwargs, caps, extra_headers)

        if cls._supports(caps, "page_action") and page_action is not None:
            fetch_kwargs["page_action"] = page_action

        if options.get("prefer_domcontentloaded") and cls._supports(caps, "custom_config"):
            cfg = fetch_kwargs.get("custom_config") or {}
            cfg.setdefault("wait_until", "domcontentloaded")
            cfg.setdefault("goto_wait_until", "domcontentloaded")
            fetch_kwargs["custom_config"] = cfg

        return fetch_kwargs

    @staticmethod
    def _apply_timeouts(fetch_kwargs: FetchParams, options: Dict[str, Any], settings: Any) -> None:
        """Apply timeout configuration based on options/settings."""
        if options.get("disable_timeout") is True:
            large_timeout_ms = getattr(settings, "write_mode_timeout_ms", 86_400_000)
            fetch_kwargs["timeout"] = large_timeout_ms
            return
        timeout_ms = (
            (options.get("timeout_seconds") * 1000)
            if options.get("timeout_seconds")
            else options.get("timeout_ms", 30000)
        )
        fetch_kwargs["timeout"] = timeout_ms

    @classmethod
    def _apply_user_data(
        cls,
        fetch_kwargs: FetchParams,
        caps: FetchCapabilities,
        additional_args: Dict[str, Any],
    ) -> None:
        """Filter and attach additional args with user-data awareness."""
        if not additional_args or not cls._supports(caps, "additional_args"):
            return
        try:
            safe_additional_args: Dict[str, Any] = {}
            for key, value in additional_args.items():
                if str(key).startswith("_"):
                    continue
                if cls._supports(caps, key):
                    safe_additional_args[key] = value
                    continue
                if key in cls._USER_DATA_KEYS:
                    safe_additional_args[key] = value
            if safe_additional_args:
                fetch_kwargs["additional_args"] = safe_additional_args
        except Exception:
            fetch_kwargs["additional_args"] = dict(additional_args)

    @classmethod
    def _apply_headers(
        cls,
        fetch_kwargs: FetchParams,
        caps: FetchCapabilities,
        extra_headers: Optional[Dict[str, str]],
    ) -> None:
        """Attach extra headers when supported by the fetcher."""
        if extra_headers and cls._supports(caps, "extra_headers"):
            fetch_kwargs["extra_headers"] = extra_headers

    @staticmethod
    def _supports(caps: FetchCapabilities, name: str) -> bool:
        return getattr(caps, f"supports_{name}", False)

    @classmethod
    def _supports_any(cls, caps: FetchCapabilities, names: Iterable[str]) -> bool:
        return any(cls._supports(caps, name) for name in names)
