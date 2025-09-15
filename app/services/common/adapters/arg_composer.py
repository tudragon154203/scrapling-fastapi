import logging
from typing import Any, Dict, Optional

from app.services.common.types import FetchCapabilities
from app.services.crawler.proxy.redact import redact_proxy as _redact_proxy

logger = logging.getLogger(__name__)


class FetchArgComposer:
    """Composer for fetch arguments that handles capabilities safely."""

    @staticmethod
    def compose(
        options: Dict[str, Any],
        caps: FetchCapabilities,
        selected_proxy: Optional[str],
        additional_args: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]],
        settings: Any,
        page_action: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Compose fetch arguments from components in a capability-safe way."""
        proxy = selected_proxy  # Alias for compatibility

        def _ok(name: str) -> bool:
            # For capabilities not in FetchCapabilities, we check directly
            return getattr(caps, f"supports_{name}", False)

        fetch_kwargs: Dict[str, Any] = dict(
            headless=options.get("headless", True),
            network_idle=options.get("network_idle", False),
            wait=int(options.get("wait_ms", 0) or 0),
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
            )

        # Only add selector-related args if selector is provided
        if options.get("wait_for_selector"):
            fetch_kwargs["wait_selector"] = options["wait_for_selector"]
            fetch_kwargs["wait_selector_state"] = options.get(
                "wait_for_selector_state", "visible"
            )

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
                    elif k == "user_data_dir" and (
                        _ok("user_data_dir")
                        or _ok("profile_dir")
                        or _ok("profile_path")
                        or _ok("user_data")
                    ):
                        safe_additional_args[k] = v
                    elif k == "profile_dir" and (
                        _ok("profile_dir")
                        or _ok("user_data_dir")
                        or _ok("profile_path")
                        or _ok("user_data")
                    ):
                        safe_additional_args[k] = v
                    elif k == "profile_path" and (
                        _ok("profile_path")
                        or _ok("user_data_dir")
                        or _ok("profile_dir")
                        or _ok("user_data")
                    ):
                        safe_additional_args[k] = v
                    elif k == "user_data" and (
                        _ok("user_data")
                        or _ok("user_data_dir")
                        or _ok("profile_dir")
                        or _ok("profile_path")
                    ):
                        safe_additional_args[k] = v
            except Exception:
                safe_additional_args = additional_args or {}
            if safe_additional_args:
                fetch_kwargs["additional_args"] = safe_additional_args

        if _ok("extra_headers") and extra_headers:
            fetch_kwargs["extra_headers"] = extra_headers

        if _ok("page_action") and page_action is not None:
            fetch_kwargs["page_action"] = page_action

        if options.get("prefer_domcontentloaded") and _ok("custom_config"):
            cfg = fetch_kwargs.get("custom_config") or {}
            cfg.setdefault("wait_until", "domcontentloaded")
            cfg.setdefault("goto_wait_until", "domcontentloaded")
            fetch_kwargs["custom_config"] = cfg

        return fetch_kwargs
