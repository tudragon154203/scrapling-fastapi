import logging
import re
import sys
from typing import Optional, Union

from app.core.config import get_settings


class RefererScrubbingFormatter(logging.Formatter):
    """Formatter that strips referer details from log output."""

    _referer_pattern = re.compile(r"\s*\(referer: [^)]*\)", re.IGNORECASE)

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return self._referer_pattern.sub("", formatted)


class RefererScrubbingFilter(logging.Filter):
    """Log filter that removes referer fragments, hides verbose call logs, and deduplicates warnings."""

    _referer_pattern = RefererScrubbingFormatter._referer_pattern
    _call_log_pattern = re.compile(r"(?:^|\n)Call log:\n(?:\s+-.*(?:\n|$))+", re.IGNORECASE)

    def __init__(self) -> None:
        super().__init__()
        self._seen_warnings: set[str] = set()

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = record.msg

        if not isinstance(message, str):
            return True

        first_pass = not hasattr(record, "_scrubbing_processed")
        if first_pass:
            record._scrubbing_processed = True

        sanitized = message
        changed = False

        if self._referer_pattern.search(sanitized):
            sanitized = self._referer_pattern.sub("", sanitized)
            changed = True

        effective_level = logging.getLogger(record.name).getEffectiveLevel()
        if (
            effective_level > logging.DEBUG
            and record.levelno > logging.DEBUG
            and self._call_log_pattern.search(sanitized)
        ):
            sanitized = self._call_log_pattern.sub("", sanitized).rstrip()
            changed = True

        if changed:
            record.msg = sanitized
            record.args = ()

        if first_pass and record.levelno >= logging.WARNING:
            key = f"{record.levelno}:{sanitized}"
            if key in self._seen_warnings:
                return False
            self._seen_warnings.add(key)

        return True


_SCRUBBING_FILTER = RefererScrubbingFilter()


def _ensure_filter(target: Union[logging.Logger, logging.Handler]) -> None:
    """Attach the scrubbing filter to loggers/handlers once."""
    existing_filters = getattr(target, "filters", [])
    if not any(isinstance(f, RefererScrubbingFilter) for f in existing_filters):
        target.addFilter(_SCRUBBING_FILTER)


def _ensure_global_filters() -> None:
    """Ensure root and scrapling loggers scrub sensitive data."""
    for logger_name in (None, "scrapling"):
        logger = logging.getLogger(logger_name)
        _ensure_filter(logger)
        for handler in list(logger.handlers):
            _ensure_filter(handler)


def get_log_level() -> int:
    """Get log level from settings or environment."""
    settings = get_settings()
    log_level_str = settings.log_level.upper()
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return log_levels.get(log_level_str, logging.INFO)


def setup_logger(name: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """Set up logger with proper formatting, level, and scrubbing."""
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(get_log_level())

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(get_log_level())
    _ensure_filter(handler)

    formatter = RefererScrubbingFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)

    _ensure_filter(logger)
    logger.addHandler(handler)
    logger.propagate = False

    _ensure_global_filters()
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return setup_logger(name)
