from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Tuple

import pytest

from app.services.common.browser import camoufox
from app.services.common.browser.camoufox import CamoufoxArgsBuilder


pytestmark = pytest.mark.unit


class DummyPayload:
    def __init__(self, force_user_data: bool, headers: Dict[str, str] | None = None) -> None:
        self.force_user_data = force_user_data
        self.headers = headers or {}


def test_build_uses_read_clone_and_merges_headers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"
    cleanup_called = {"value": False}
    clone_dir = base_dir / "clones" / "clone1"
    clone_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def fake_user_data_context(requested_dir: str, mode: str) -> Tuple[str, Any]:
        assert requested_dir == str(base_dir)
        assert mode == "read"

        def cleanup() -> None:
            cleanup_called["value"] = True

        yield str(clone_dir), cleanup

    payload = DummyPayload(force_user_data=True, headers={"X-Test": "1"})
    settings = SimpleNamespace(
        testing=True,
        camoufox_user_data_dir=str(base_dir),
        camoufox_disable_coop=True,
        camoufox_virtual_display={"width": 800, "height": 600},
        camoufox_locale="en-US",
        camoufox_window="1280x720",
    )

    monkeypatch.setattr(camoufox.user_data_mod, "user_data_context", fake_user_data_context)
    monkeypatch.setattr(camoufox, "_CAMOUFOX_READY", False)

    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, {})

    assert Path(additional_args["user_data_dir"]) == clone_dir.resolve()
    assert callable(additional_args["_user_data_cleanup"])
    additional_args["_user_data_cleanup"]()
    assert cleanup_called["value"] is True
    assert additional_args["disable_coop"] is True
    assert additional_args["virtual_display"] == {"width": 800, "height": 600}
    assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True
    assert additional_args["locale"] == "en-US"
    assert additional_args["window"] == (1280, 720)

    assert extra_headers == {"Accept-Language": "en-US", "X-Test": "1"}


def test_build_respects_write_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "profiles"
    override_dir = base_dir / "master"
    payload = DummyPayload(force_user_data=True)
    settings = SimpleNamespace(
        testing=True,
        camoufox_user_data_dir=str(base_dir),
        _camoufox_user_data_mode="write",
        _camoufox_effective_user_data_dir=str(override_dir),
        camoufox_disable_coop=False,
        camoufox_virtual_display=None,
        camoufox_locale="fr-FR",
        camoufox_window="1600x900",
    )

    def fail_context(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("user_data_context should not be used when overrides are present")

    monkeypatch.setattr(camoufox.user_data_mod, "user_data_context", fail_context)
    monkeypatch.setattr(camoufox, "_CAMOUFOX_READY", False)

    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, {})

    assert Path(additional_args["user_data_dir"]) == override_dir.resolve()
    assert "_user_data_cleanup" not in additional_args
    assert additional_args["firefox_user_prefs"]["dom.audiochannel.mutedByDefault"] is True
    assert additional_args["locale"] == "fr-FR"
    assert additional_args["window"] == (1600, 900)
    assert extra_headers == {"Accept-Language": "fr-FR"}


def test_build_triggers_ready_check_when_not_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    call_counter = {"count": 0}

    def fake_ready() -> None:
        call_counter["count"] += 1

    payload = DummyPayload(force_user_data=False)
    settings = SimpleNamespace(
        testing=False,
        camoufox_user_data_dir=None,
        camoufox_disable_coop=False,
        camoufox_virtual_display=None,
        camoufox_locale=None,
        camoufox_window=None,
    )

    monkeypatch.setattr(camoufox, "_CAMOUFOX_READY", False)
    monkeypatch.setattr(CamoufoxArgsBuilder, "_ensure_camoufox_ready", staticmethod(fake_ready))
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("CAMOUFOX_SKIP_READY_CHECK", raising=False)

    additional_args, extra_headers = CamoufoxArgsBuilder.build(payload, settings, {})

    assert call_counter["count"] == 1
    assert "user_data_dir" not in additional_args
    assert extra_headers is None
