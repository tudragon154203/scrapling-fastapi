import inspect
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
    if caps.get("solve_cloudflare"):
        fetch_kwargs["solve_cloudflare"] = True

    return fetch_kwargs



def _simple_http_fetch(url: str, timeout_ms: int, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Very small fallback HTTP fetcher using stdlib urllib.

    Returns a dict with keys: status (int) and html_content (str|None).
    Intended only as a last-resort when Playwright/StealthyFetcher cannot run
    (e.g., sync API used inside an asyncio loop).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    if extra_headers:
        headers.update({k: v for k, v in extra_headers.items() if isinstance(k, str) and isinstance(v, str)})

    req = urllib_request.Request(url, headers=headers, method="GET")
    timeout = max(1.0, float(timeout_ms) / 1000.0)

    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            status = getattr(resp, "status", 200)
            content_type = resp.headers.get("Content-Type", "")
            charset = None
            try:
                # email.message.Message supports get_content_charset in 3.10
                charset = resp.headers.get_content_charset()  # type: ignore[attr-defined]
            except Exception:
                charset = None
            data = resp.read()
            if not charset:
                if "charset=" in content_type:
                    charset = content_type.split("charset=", 1)[-1].split(";")[0].strip()
                else:
                    charset = "utf-8"
            try:
                html = data.decode(charset, errors="ignore")
            except Exception:
                html = data.decode("utf-8", errors="ignore")
            return {"status": int(status or 200), "html_content": html}
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = None
        return {"status": int(e.code), "html_content": body}
    except URLError:
        return {"status": 0, "html_content": None}
    except Exception:
        return {"status": 0, "html_content": None}
