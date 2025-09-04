import logging
import random
import time
from typing import Optional, Dict, Any, List

import app.core.config as app_config
from app.schemas.crawl import CrawlRequest, CrawlResponse

from ..utils.options import _resolve_effective_options, _build_camoufox_args
from ..utils.fetch import _detect_fetch_capabilities, _compose_fetch_kwargs
from ..utils.proxy import (
    health_tracker,
    _redact_proxy,
    _load_public_proxies,
    _build_attempt_plan,
)


logger = logging.getLogger(__name__)


def _calculate_backoff_delay(attempt_idx: int, settings) -> float:
    base = settings.retry_backoff_base_ms
    cap = settings.retry_backoff_max_ms
    jitter = settings.retry_jitter_ms
    delay_ms = min(cap, base * (2 ** attempt_idx)) + random.randint(0, jitter)
    return delay_ms / 1000.0


def execute_crawl_with_retries(payload: CrawlRequest) -> CrawlResponse:
    """Execute crawl with retry and proxy strategy."""
    settings = app_config.get_settings()
    public_proxies = _load_public_proxies(settings.proxy_list_file_path)

    candidates = public_proxies.copy()
    if getattr(settings, "private_proxy_url", None):
        candidates.append(settings.private_proxy_url)

    options = _resolve_effective_options(payload, settings)
    additional_args, extra_headers = _build_camoufox_args(payload, settings)

    last_error = None

    try:
        from scrapling.fetchers import StealthyFetcher  # type: ignore

        StealthyFetcher.adaptive = True
        caps = _detect_fetch_capabilities(StealthyFetcher.fetch)
        if not caps.get("proxy"):
            logger.warning(
                "StealthyFetcher.fetch does not support proxy parameter, continuing without proxy"
            )

        attempt_count = 0
        last_used_proxy: Optional[str] = None
        attempt_plan = _build_attempt_plan(settings, public_proxies)

        while attempt_count < settings.max_retries:
            selected_proxy: Optional[str] = None
            mode = "direct"

            if getattr(settings, "proxy_rotation_mode", "sequential") != "random" or not candidates:
                found_healthy_attempt = False
                while attempt_count < settings.max_retries:
                    attempt_config = attempt_plan[attempt_count]
                    candidate_proxy = attempt_config["proxy"]
                    candidate_mode = attempt_config["mode"]

                    if candidate_proxy and health_tracker.get(candidate_proxy, {}).get("unhealthy_until", 0) > time.time():
                        logger.info(
                            f"Attempt {attempt_count+1} skipped - {candidate_mode} proxy {_redact_proxy(candidate_proxy)} is unhealthy"
                        )
                        attempt_count += 1
                        continue

                    selected_proxy = candidate_proxy
                    mode = candidate_mode
                    found_healthy_attempt = True
                    break

                if not found_healthy_attempt:
                    break
            else:
                healthy_proxies = [
                    p for p in candidates if health_tracker.get(p, {}).get("unhealthy_until", 0) <= time.time()
                ]
                if healthy_proxies:
                    if len(healthy_proxies) > 1 and last_used_proxy in healthy_proxies:
                        healthy_proxies.remove(last_used_proxy)
                    selected_proxy = random.choice(healthy_proxies)
                    if selected_proxy == getattr(settings, "private_proxy_url", None):
                        mode = "private"
                    else:
                        mode = "public"
                else:
                    if getattr(settings, "private_proxy_url", None) and health_tracker.get(settings.private_proxy_url, {}).get(
                        "unhealthy_until", 0
                    ) <= time.time():
                        selected_proxy = settings.private_proxy_url
                        mode = "private"
                    else:
                        selected_proxy = None
                        mode = "direct"

            redacted_proxy = _redact_proxy(selected_proxy)
            logger.info(f"Attempt {attempt_count+1} using {mode} connection, proxy: {redacted_proxy}")

            try:
                fetch_kwargs = _compose_fetch_kwargs(
                    options=options,
                    caps=caps,
                    selected_proxy=selected_proxy,
                    additional_args=additional_args,
                    extra_headers=extra_headers,
                    settings=settings,
                )

                page = StealthyFetcher.fetch(str(payload.url), **fetch_kwargs)

                if getattr(page, "status", None) == 200:
                    html = getattr(page, "html_content", None)
                    if selected_proxy:
                        health_tracker[selected_proxy] = {"failures": 0, "unhealthy_until": 0}
                        logger.info(f"Proxy {redacted_proxy} recovered")
                    logger.info(f"Attempt {attempt_count+1} outcome: success")
                    return CrawlResponse(status="success", url=payload.url, html=html)
                else:
                    last_status = getattr(page, "status", None)
                    last_error = f"Non-200 status: {last_status}"
                    if selected_proxy:
                        ht = health_tracker.setdefault(selected_proxy, {"failures": 0, "unhealthy_until": 0})
                        ht["failures"] += 1
                        if ht["failures"] >= settings.proxy_health_failure_threshold:
                            ht["unhealthy_until"] = time.time() + settings.proxy_unhealthy_cooldown_ms / 1000
                            logger.info(f"Proxy {redacted_proxy} marked unhealthy")
                    logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                if selected_proxy:
                    ht = health_tracker.setdefault(selected_proxy, {"failures": 0, "unhealthy_until": 0})
                    ht["failures"] += 1
                    if ht["failures"] >= settings.proxy_health_failure_threshold:
                        ht["unhealthy_until"] = time.time() + settings.proxy_unhealthy_cooldown_ms / 1000
                        logger.info(f"Proxy {redacted_proxy} marked unhealthy")
                logger.info(f"Attempt {attempt_count+1} outcome: failure - {last_error}")

            attempt_count += 1
            last_used_proxy = selected_proxy

            if attempt_count < settings.max_retries:
                delay = _calculate_backoff_delay(attempt_count - 1, settings)
                time.sleep(delay)

        return CrawlResponse(status="failure", url=payload.url, html=None, message=last_error or "exhausted retries")
    except ImportError:
        return CrawlResponse(
            status="failure",
            url=payload.url,
            html=None,
            message="Scrapling library not available",
        )
