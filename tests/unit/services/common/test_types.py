import pytest
from types import SimpleNamespace

from app.services.common.types import Attempt, CrawlOptions, FetchCapabilities


ALL_CAPABILITIES = (
    "supports_proxy",
    "supports_network_idle",
    "supports_timeout",
    "supports_additional_args",
    "supports_page_action",
    "supports_geoip",
    "supports_extra_headers",
    "supports_user_data_dir",
    "supports_profile_dir",
    "supports_profile_path",
    "supports_user_data",
    "supports_custom_config",
)


def _make_capabilities(**overrides) -> FetchCapabilities:
    base_kwargs = {name: False for name in ALL_CAPABILITIES}
    base_kwargs.update(overrides)
    return FetchCapabilities(**base_kwargs)


def test_attempt_invalid_mode_raises_value_error():
    with pytest.raises(ValueError):
        Attempt(index=1, proxy=None, mode="invalid")


def test_fetch_capabilities_false_when_all_disabled():
    capabilities = _make_capabilities()
    assert bool(capabilities) is False


@pytest.mark.parametrize("enabled_capability", ALL_CAPABILITIES)
def test_fetch_capabilities_true_with_enabled_flag(enabled_capability):
    capabilities = _make_capabilities(**{enabled_capability: True})
    assert bool(capabilities) is True


def test_crawl_options_from_request_defaults_and_overrides():
    default_options = CrawlOptions.from_request(SimpleNamespace())
    assert default_options == CrawlOptions()

    request = SimpleNamespace(
        headless=False,
        network_idle=False,
        timeout=120,
        wait_for_selector="#content",
    )

    overridden_options = CrawlOptions.from_request(request)
    assert overridden_options.headless is False
    assert overridden_options.network_idle is False
    assert overridden_options.timeout == 120
    assert overridden_options.wait_for_selector == "#content"
