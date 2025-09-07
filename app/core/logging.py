import logging
import os
import sys
from typing import Optional

from app.core.config import get_settings


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
    """Set up logger with proper formatting and level.
    
    Args:
        name: Logger name, typically __name__
        level: Log level, if not provided uses settings
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set level
    if level is not None:
        logger.setLevel(level)
    else:
        logger.setLevel(get_log_level())
    
    # Remove existing handlers to avoid duplication
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(get_log_level())
    
    # Set formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return setup_logger(name)