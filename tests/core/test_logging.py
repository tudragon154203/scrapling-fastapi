import logging
from types import SimpleNamespace

import pytest

from app.core.logging import get_log_level, setup_logger, get_logger


@pytest.mark.parametrize(
    "level_str,expected",
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
    ],
)
def test_get_log_level(monkeypatch, level_str, expected):
    """Ensure get_log_level maps string levels to logging constants."""
    dummy_settings = SimpleNamespace(log_level=level_str)
    monkeypatch.setattr("app.core.logging.get_settings", lambda: dummy_settings)
    assert get_log_level() == expected


def test_setup_logger_creates_stream_handler(capsys):
    """setup_logger should create a single StreamHandler with expected format."""
    logger = setup_logger("test_logger")
    logger.info("hello")
    captured = capsys.readouterr()
    assert "hello" in captured.out
    # logger should have exactly one StreamHandler
    assert len(logger.handlers) == 1
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    expected_fmt = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )
    assert handler.formatter._fmt == expected_fmt


def test_setup_logger_replaces_handlers():
    """Calling setup_logger twice should remove old handlers."""
    logger = setup_logger("another_logger")
    first_handler = logger.handlers[0]
    logger = setup_logger("another_logger")
    assert len(logger.handlers) == 1
    assert logger.handlers[0] is not first_handler


def test_get_logger_delegates(monkeypatch):
    """get_logger should delegate to setup_logger."""
    called = {}

    def fake_setup(name):
        called["name"] = name
        return logging.getLogger(name)

    monkeypatch.setattr("app.core.logging.setup_logger", fake_setup)
    logger = get_logger("delegated")
    assert called["name"] == "delegated"
    assert logger.name == "delegated"
