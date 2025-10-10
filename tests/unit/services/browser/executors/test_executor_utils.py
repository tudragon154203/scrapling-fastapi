import asyncio
import shutil
from pathlib import Path
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


class FailingCleanupExecutor(DummyBrowsingExecutor):
    """Executor whose browser attribute raises when reassigned after init."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._allow_browser_assignment = True
        super().__init__(*args, **kwargs)
        self._allow_browser_assignment = False
        self._browser = object()

    @property
    def browser(self) -> Any:
        return self._browser

    @browser.setter
    def browser(self, value: Any) -> None:
        if getattr(self, "_allow_browser_assignment", False):
            self._browser = value
        else:
            raise RuntimeError("Unable to reassign browser instance")


class StubLogger:
    def __init__(self) -> None:
        self.error_messages: list[str] = []

    async def error(self, message: str) -> None:
        self.error_messages.append(message)


@pytest.mark.asyncio
async def test_prepare_user_data_dir_without_initial_dir():
    executor = DummyBrowsingExecutor()

    temp_dir = await executor._prepare_user_data_dir()

    temp_path = Path(temp_dir)
    assert temp_path.exists()
    assert temp_path.name.startswith("scrapling_")

    shutil.rmtree(temp_path)


@pytest.mark.asyncio
async def test_prepare_user_data_dir_clones_from_master(tmp_path: Path):
    base_dir = tmp_path
    master_dir = base_dir / "master"
    master_dir.mkdir()
    (master_dir / "config.json").write_text("configuration")

    clone_dir = base_dir / "clones" / "profile1"
    executor = DummyBrowsingExecutor(user_data_dir=str(clone_dir))
    settings = executor.settings
    original_dir = settings.camoufox_user_data_dir

    try:
        settings.camoufox_user_data_dir = str(base_dir)

        prepared_dir = await executor._prepare_user_data_dir()

        assert prepared_dir == str(clone_dir)
        assert (clone_dir / "config.json").read_text() == "configuration"
    finally:
        settings.camoufox_user_data_dir = original_dir


@pytest.mark.asyncio
async def test_clone_user_data_dir_missing_master_raises(tmp_path: Path):
    executor = DummyBrowsingExecutor(user_data_dir=str(tmp_path / "target"))

    with pytest.raises(FileNotFoundError):
        await executor._clone_user_data_dir(tmp_path / "missing", str(tmp_path / "clone"))


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
async def test_validate_user_data_dir_existing(tmp_path: Path):
    executor = DummyBrowsingExecutor(user_data_dir=str(tmp_path))

    assert await executor.validate_user_data_dir() is True


@pytest.mark.asyncio
async def test_validate_user_data_dir_missing(tmp_path: Path):
    missing_dir = tmp_path / "missing"
    executor = DummyBrowsingExecutor(user_data_dir=str(missing_dir))

    assert await executor.validate_user_data_dir() is False


@pytest.mark.asyncio
async def test_cleanup_on_error_clears_state():
    executor = DummyBrowsingExecutor()
    executor.browser = object()
    executor.user_data_dir = "some-dir"

    await executor._cleanup_on_error()

    assert executor.browser is None
    assert executor.user_data_dir is None


@pytest.mark.asyncio
async def test_cleanup_on_error_logs_when_assignment_fails():
    executor = FailingCleanupExecutor()
    executor.user_data_dir = "persistent"
    stub_logger = StubLogger()
    executor.logger = stub_logger

    await executor._cleanup_on_error()

    assert stub_logger.error_messages
    assert "Error during cleanup" in stub_logger.error_messages[0]
