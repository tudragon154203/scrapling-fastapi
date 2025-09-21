
import os
from pathlib import Path

import pytest

from app.services.tiktok.search.multistep import TikTokMultiStepSearchService
from app.services.tiktok.search.service import TikTokSearchService
from app.services.tiktok.search.url_param import TikTokURLParamSearchService


@pytest.fixture
def service():
    return TikTokSearchService()


def _restore_user_data_dir(settings, original):
    settings.camoufox_user_data_dir = original


def test_build_search_falls_back_when_user_data_missing(service, caplog):
    settings = service.settings
    original = getattr(settings, "camoufox_user_data_dir", None)
    settings.camoufox_user_data_dir = None
    try:
        with caplog.at_level("WARNING"):
            impl = service._build_search_implementation()
        assert isinstance(impl, TikTokMultiStepSearchService)
        assert any(
            "camoufox_user_data_dir not configured" in message
            for message in caplog.messages
        )
    finally:
        _restore_user_data_dir(settings, original)


def test_build_search_falls_back_when_master_missing(service, tmp_path, caplog):
    settings = service.settings
    original = getattr(settings, "camoufox_user_data_dir", None)
    settings.camoufox_user_data_dir = str(tmp_path)
    try:
        with caplog.at_level("WARNING"):
            impl = service._build_search_implementation()
        assert isinstance(impl, TikTokMultiStepSearchService)
        assert any(
            "camoufox master profile missing or empty; running with ephemeral user data" in message
            for message in caplog.messages
        )
    finally:
        _restore_user_data_dir(settings, original)


def test_build_search_uses_multistep_when_master_present(service, tmp_path):
    settings = service.settings
    original = getattr(settings, "camoufox_user_data_dir", None)
    master_dir = tmp_path / "master"
    master_dir.mkdir(parents=True)
    (master_dir / "prefs.js").write_text("user_pref('media.volume_scale', 1.0);")
    settings.camoufox_user_data_dir = str(tmp_path)
    try:
        impl = service._build_search_implementation()
        assert isinstance(impl, TikTokMultiStepSearchService)
    finally:
        _restore_user_data_dir(settings, original)
