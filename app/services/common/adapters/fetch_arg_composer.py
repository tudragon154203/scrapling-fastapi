"""Fetch argument composer for building Scrapling fetch parameters."""

import logging
from typing import Any, Dict, Iterable, Optional
from app.services.common.adapters.fetch_params import FetchParams
from app.services.common.types import FetchCapabilities
from app.services.crawler.proxy.redact import redact_proxy as _redact_proxy

logger = logging.getLogger(__name__)


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
