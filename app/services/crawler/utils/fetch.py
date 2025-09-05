import inspect
import threading
from typing import Dict, Any, Optional, Callable
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError


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
        solve_cloudflare=_ok("solve_cloudflare"),
        page_action=_ok("page_action"),
        user_data_dir=_ok("user_data_dir"),
        profile_dir=_ok("profile_dir"),
        profile_path=_ok("profile_path"),
        user_data=_ok("user_data"),
    )


def _compose_fetch_kwargs(
    options: Dict[str, Any],
    caps: Dict[str, bool],
    selected_proxy: Optional[str],
    additional_args: Dict[str, Any],
    extra_headers: Optional[Dict[str, str]],
    settings,
    page_action: Optional[Callable] = None,
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
    if caps.get("page_action") and page_action is not None:
        fetch_kwargs["page_action"] = page_action

    # Enable Cloudflare solving when supported by StealthyFetcher
    # if caps.get("solve_cloudflare"):
    #     fetch_kwargs["solve_cloudflare"] = True

    return fetch_kwargs



def _call_stealthy_fetch(fetch_callable: Callable[..., Any], url: str, **kwargs) -> Any:
    """Call StealthyFetcher.fetch safely when an asyncio loop is running.

    Playwright's sync API cannot run in a thread that already has a running
    asyncio event loop. If we detect a running loop in the current thread,
    execute the blocking sync fetch in a dedicated thread and return the result.
    """
    try:
        # Python 3.7+: raises RuntimeError when no running loop
        import asyncio
        asyncio.get_running_loop()
        running = True
    except Exception:
        running = False

    if not running:
        return fetch_callable(url, **kwargs)

    holder: Dict[str, Any] = {}

    def _runner():
        try:
            holder["result"] = fetch_callable(url, **kwargs)
        except Exception as e:  # store exception to re-raise in caller thread
            holder["exc"] = e

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join()

    if "exc" in holder:
        raise holder["exc"]
    return holder.get("result")
