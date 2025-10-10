from app.services.common.types import FetchCapabilities
from app.services.common.adapters.scrapling_fetcher import FetchArgComposer
from app.services.browser.options.resolver import OptionsResolver
from app.schemas.crawl import CrawlRequest
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit]


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DummySettings:
    default_headless = True
    default_network_idle = False
    default_timeout_ms = 20000


def test_crawl_timeout_respects_defaults():
    req = CrawlRequest(
        url="https://example.com",
        force_user_data=True,
        force_headful=True,
    )
    settings = DummySettings()

    opts = OptionsResolver().resolve(req, settings)
    # In new model, disable_timeout is not used for /crawl
    assert opts.get("disable_timeout") is False

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

    # Timeout should be set to default and not be extremely large
    assert "timeout" in kwargs
    assert isinstance(kwargs["timeout"], int)
    assert kwargs["timeout"] == settings.default_timeout_ms
