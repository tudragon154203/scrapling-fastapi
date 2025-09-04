import os
from typing import Optional, Tuple, Dict, Any

from app.schemas.crawl import CrawlRequest


def _parse_window_size(value: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse a window size string into (width, height)."""
    if not value:
        return None
    raw = value.strip().lower().replace(" ", "")
    sep = "x" if "x" in raw else "," if "," in raw else None
    if not sep:
        return None
    try:
        w_str, h_str = raw.split(sep, 1)
        w, h = int(w_str), int(h_str)
        if w > 0 and h > 0:
            return (w, h)
    except Exception:
        return None
    return None


def _resolve_effective_options(payload: CrawlRequest, settings) -> Dict[str, Any]:
    """Resolve crawl options from payload with sensible defaults and legacy compat."""
    wait_selector = payload.wait_selector or payload.x_wait_for_selector

    timeout_ms: int = (
        payload.timeout_ms if payload.timeout_ms is not None else settings.default_timeout_ms
    )

    wait_ms: Optional[int] = None
    if payload.x_wait_time is not None:
        wait_ms = int(payload.x_wait_time * 1000)

    headless: bool = payload.headless if payload.headless is not None else settings.default_headless
    if payload.x_force_headful is True:
        headless = False

    network_idle: bool = (
        payload.network_idle if payload.network_idle is not None else settings.default_network_idle
    )

    return dict(
        wait_selector=wait_selector,
        timeout_ms=timeout_ms,
        wait_ms=wait_ms,
        headless=headless,
        network_idle=network_idle,
        wait_selector_state=payload.wait_selector_state,
    )


def _build_camoufox_args(payload: CrawlRequest, settings, caps: Dict[str, bool]) -> Tuple[Dict[str, Any], Optional[Dict[str, str]]]:
    """Build Camoufox additional_args and optional extra headers from settings/payload."""
    additional_args: Dict[str, Any] = {}

    # User data directory with parameter detection
    if payload.x_force_user_data is True and settings.camoufox_user_data_dir:
        user_data_param = None
        for param in ("user_data_dir", "profile_dir", "profile_path", "user_data"):
            if caps.get(param, False):
                user_data_param = param
                break
        if user_data_param:
            try:
                os.makedirs(settings.camoufox_user_data_dir, exist_ok=True)
            except Exception:
                pass
            else:
                additional_args[user_data_param] = settings.camoufox_user_data_dir

    if getattr(settings, "camoufox_disable_coop", False):
        additional_args["disable_coop"] = True
    if getattr(settings, "camoufox_virtual_display", None):
        additional_args["virtual_display"] = settings.camoufox_virtual_display

    # Solve Cloudflare is provided via additional_args when supported by StealthyFetcher
    # Gatekeeping happens later when passing additional_args based on capabilities
    additional_args["solve_cloudflare"] = True

    extra_headers: Optional[Dict[str, str]] = None
    if getattr(settings, "camoufox_locale", None):
        additional_args["locale"] = settings.camoufox_locale
        extra_headers = {"Accept-Language": settings.camoufox_locale}

    win = _parse_window_size(getattr(settings, "camoufox_window", None))
    if win:
        additional_args["window"] = win

    return additional_args, extra_headers
