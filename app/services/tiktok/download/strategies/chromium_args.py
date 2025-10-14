"""Chromium launch arguments and headless configuration helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Sequence

BASE_CHROMIUM_BROWSER_ARGS: Sequence[str] = (
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-accelerated-2d-canvas",
    "--no-first-run",
    "--disable-gpu",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI",
    "--disable-ipc-flooding-protection",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-images",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--hide-scrollbars",
    "--metrics-recording-only",
    "--mute-audio",
    "--safebrowsing-disable-auto-update",
    "--disable-infobars",
    "--window-position=0,0",
    "--window-size=1920,1080",
    "--blink-settings=imagesEnabled=false",
    "--disable-javascript-harmony-shipping",
    "--disable-features=IsolateOrigins,site-per-process",
)

HEADLESS_ONLY_BROWSER_ARGS: Sequence[str] = (
    "--disable-background-networking",
    "--no-default-browser-check",
    "--disable-features=TranslateUI,BlinkGenPropertyTrees",
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
    "--disable-ipc-flooding-protection",
    "--disable-component-update",
    "--disable-domain-reliability",
    "--disable-features=AudioServiceOutOfProcess",
)

HEADLESS_FETCH_OVERRIDES: Dict[str, Any] = {
    "network_idle": True,
    "wait": 5000,
    "timeout": 120000,
}

HEADLESS_HEADER_UPDATES: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def build_browser_args(headless: bool) -> List[str]:
    """Build Chromium browser arguments for the desired mode."""
    args = list(BASE_CHROMIUM_BROWSER_ARGS)
    if headless:
        args.extend(HEADLESS_ONLY_BROWSER_ARGS)
    return args


def apply_headless_modifiers(fetch_kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Return fetch kwargs updated with headless-specific overrides."""
    updated_kwargs = deepcopy(fetch_kwargs)
    updated_kwargs.update(HEADLESS_FETCH_OVERRIDES)

    extra_headers = dict(updated_kwargs.get("extra_headers", {}))
    extra_headers.update(HEADLESS_HEADER_UPDATES)
    updated_kwargs["extra_headers"] = extra_headers
    return updated_kwargs
