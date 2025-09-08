import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas.crawl import CrawlRequest
from app.services.crawler.options.resolver import OptionsResolver
from app.services.crawler.adapters.scrapling_fetcher import FetchArgComposer
from app.services.crawler.core.types import FetchCapabilities


class DummySettings:
    default_headless = True
    default_network_idle = False
    default_timeout_ms = 20000


def test_disable_timeout_in_write_mode():
    req = CrawlRequest(
        url="https://example.com",
        force_user_data=True,
        user_data_mode="write",
        force_headful=True,
    )
    settings = DummySettings()

    opts = OptionsResolver().resolve(req, settings)
    assert opts.get("disable_timeout") is True

    caps = FetchCapabilities(
        supports_proxy=False,
        supports_network_idle=True,
        supports_timeout=True,
        supports_additional_args=True,
        supports_page_action=True,
        supports_geoip=False,
        supports_extra_headers=False,
    )

    kwargs = FetchArgComposer.compose(
        options=opts,
        caps=caps,
        selected_proxy=None,
        additional_args={},
        extra_headers=None,
        settings=settings,
        page_action=None,
    )

    # We use a very large numeric timeout in write mode (not None)
    assert "timeout" in kwargs
    assert isinstance(kwargs["timeout"], int)
    assert kwargs["timeout"] >= 86_400_000  # at least 24h
