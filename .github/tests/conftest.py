from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

import pytest

MODULE_PATH = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    / "workflows"
    / "scripts"
    / "common"
    / "python"
    / "dispatcher_filter.py"
)


@pytest.fixture(scope="session")
def dispatcher_module():
    spec = importlib.util.spec_from_file_location("dispatcher_filter", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_dispatcher(
    dispatcher_module, monkeypatch, tmp_path
) -> Callable[..., dict[str, str]]:
    def _run(
        *,
        event_name: str,
        payload: dict[str, Any],
        active_var: str | None = "",
        active_env: str | None = "",
    ) -> dict[str, str]:
        github_output = tmp_path / "out.txt"
        if github_output.exists():
            github_output.unlink()

        monkeypatch.setenv("GITHUB_OUTPUT", str(github_output))

        if active_var is None:
            monkeypatch.delenv("ACTIVE_BOTS_VAR", raising=False)
        else:
            monkeypatch.setenv("ACTIVE_BOTS_VAR", active_var)

        if active_env is None:
            monkeypatch.delenv("ACTIVE_BOTS_ENV", raising=False)
        else:
            monkeypatch.setenv("ACTIVE_BOTS_ENV", active_env)

        monkeypatch.setenv("EVENT_NAME", event_name)
        monkeypatch.setenv("EVENT_PAYLOAD", json.dumps(payload))

        dispatcher_module.decide()

        output = github_output.read_text(encoding="utf-8").strip()
        if not output:
            return {}

        return dict(line.split("=", 1) for line in output.splitlines())

    return _run
