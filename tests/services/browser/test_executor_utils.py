import asyncio
from typing import Any, Dict

import pytest

from app.services.common.executor import AbstractBrowsingExecutor


class DummyBrowsingExecutor(AbstractBrowsingExecutor):
    """Minimal concrete implementation of AbstractBrowsingExecutor for testing."""

    async def get_config(self) -> Dict[str, Any]:
        return {}

    async def setup_browser(self) -> None:
        self.browser = object()

    async def cleanup(self) -> None:
        self.browser = None


@pytest.mark.asyncio
async def test_redact_proxy_values():
    executor = DummyBrowsingExecutor(proxy={"value": "http://user:pass@proxy:8080"})
    message = "Connecting via http://user:pass@proxy:8080"

    redacted = await executor._redact_proxy_values(message)

    assert redacted == "Connecting via ***"
    assert "http://user:pass@proxy:8080" not in redacted


@pytest.mark.asyncio
async def test_check_session_timeout_exceeded():
    executor = DummyBrowsingExecutor()
    loop = asyncio.get_event_loop()
    executor.start_time = loop.time() - 10

    assert await executor.check_session_timeout(max_duration=5) is True


@pytest.mark.asyncio
async def test_validate_user_data_dir_existing(tmp_path):
    executor = DummyBrowsingExecutor(user_data_dir=str(tmp_path))

    assert await executor.validate_user_data_dir() is True


@pytest.mark.asyncio
async def test_validate_user_data_dir_missing(tmp_path):
    missing_dir = tmp_path / "missing"
    executor = DummyBrowsingExecutor(user_data_dir=str(missing_dir))

    assert await executor.validate_user_data_dir() is False
