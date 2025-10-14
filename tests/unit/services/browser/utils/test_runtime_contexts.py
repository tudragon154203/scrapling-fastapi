from __future__ import annotations

import os
from contextlib import contextmanager

from app.services.browser.utils.runtime_contexts import (
    CamoufoxRuntimeContext,
    ChromiumRuntimeContext,
)


class DummyCleanup:
    called = False

    def __call__(self) -> None:
        self.called = True


class DummySettings:
    def __init__(self) -> None:
        self.camoufox_runtime_force_mute_audio = False
        self.camoufox_runtime_user_data_mode = "read"
        self.camoufox_runtime_effective_user_data_dir = "/existing/camoufox"
        self.chromium_runtime_user_data_mode = "read"
        self.chromium_runtime_effective_user_data_dir = "/existing/chromium"


def test_camoufox_runtime_context_toggles_settings_and_cleans_up():
    cleanup = DummyCleanup()

    @contextmanager
    def fake_user_data_context(path: str, mode: str):
        assert path == "/profiles"
        assert mode == "write"
        yield "/effective", cleanup

    settings = DummySettings()

    with CamoufoxRuntimeContext(settings, "/profiles", user_data_context_fn=fake_user_data_context) as (
        effective_dir,
        provided_cleanup,
    ):
        assert effective_dir == "/effective"
        assert provided_cleanup is cleanup
        assert settings.camoufox_runtime_force_mute_audio is True
        assert settings.camoufox_runtime_user_data_mode == "write"
        assert settings.camoufox_runtime_effective_user_data_dir == "/effective"

    assert settings.camoufox_runtime_force_mute_audio is False
    assert settings.camoufox_runtime_user_data_mode == "read"
    assert settings.camoufox_runtime_effective_user_data_dir == "/existing/camoufox"
    assert cleanup.called is True


def test_chromium_runtime_context_sets_absolute_path_and_restores():
    cleanup = DummyCleanup()

    @contextmanager
    def fake_chromium_context(mode: str):
        assert mode == "write"
        yield "relative/path", cleanup

    class DummyManager:
        def get_user_data_context(self, mode: str):
            return fake_chromium_context(mode)

    settings = DummySettings()
    manager = DummyManager()

    with ChromiumRuntimeContext(settings, manager, mode="write") as (effective_dir, provided_cleanup):
        expected_suffix = os.path.join("relative", "path")
        assert effective_dir.endswith(expected_suffix)
        assert provided_cleanup is cleanup
        assert settings.chromium_runtime_user_data_mode == "write"
        assert settings.chromium_runtime_effective_user_data_dir.endswith(expected_suffix)

    assert settings.chromium_runtime_user_data_mode == "read"
    assert settings.chromium_runtime_effective_user_data_dir == "/existing/chromium"
    assert cleanup.called is True
