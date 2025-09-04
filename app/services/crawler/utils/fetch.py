import inspect
from typing import Dict, Any, Optional


def _detect_fetch_capabilities(fetch_callable) -> Dict[str, bool]:
    """Introspect StealthyFetcher.fetch signature to learn supported kwargs."""
    try:
        _sig = inspect.signature(fetch_callable)
        _fetch_params = set(_sig.parameters.keys())
        _has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in _sig.parameters.values())
    except Exception:
        _fetch_params = set()
        _has_varkw = False

    def _ok(name: str) -> bool:
        return (name in _fetch_params) or _has_varkw

    return dict(
        proxy=_ok("proxy"),
        geoip=_ok("geoip"),
        extra_headers=_ok("extra_headers"),
        additional_args=_ok("additional_args"),
    )


def _compose_fetch_kwargs(
    options: Dict[str, Any],
    caps: Dict[str, bool],
    selected_proxy: Optional[str],
    additional_args: Dict[str, Any],
    extra_headers: Optional[Dict[str, str]],
    settings,
) -> Dict[str, Any]:
    """Compose kwargs for StealthyFetcher.fetch in a capability-safe way."""
    geoip_enabled = bool(getattr(settings, "camoufox_geoip", True) and selected_proxy)

    fetch_kwargs: Dict[str, Any] = dict(
        headless=options["headless"],
        network_idle=options["network_idle"],
        wait_selector=options["wait_selector"],
        wait_selector_state=options.get("wait_selector_state") or None,
        timeout=options["timeout_ms"],
        wait=options["wait_ms"] or 0,
    )

    if caps.get("proxy") and selected_proxy:
        fetch_kwargs["proxy"] = selected_proxy
    if caps.get("geoip") and geoip_enabled:
        fetch_kwargs["geoip"] = True
    if caps.get("additional_args") and additional_args:
        fetch_kwargs["additional_args"] = additional_args
    if caps.get("extra_headers") and extra_headers:
        fetch_kwargs["extra_headers"] = extra_headers

    return fetch_kwargs

