from app.core.config import get_settings

import pytest

pytestmark = [pytest.mark.unit]


def test_camoufox_force_mute_default_enabled():
    assert get_settings().camoufox_force_mute_audio_default is True
