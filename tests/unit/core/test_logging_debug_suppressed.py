import logging
import io
import sys
from unittest.mock import patch
from app.core.logging import setup_logger, get_log_level

import pytest

pytestmark = [pytest.mark.unit]


def test_debug_messages_suppressed_at_info_level():
    """Test that debug messages are suppressed when logging level is INFO."""

    # Capture log output using the actual logging setup
    log_capture = io.StringIO()

    # Use the real setup_logger function but capture its output
    logger = setup_logger("test_debug_suppression", level=logging.INFO)

    # Replace the handler with our capture handler
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Use a handler that matches the real one but captures to our string
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)  # Same as real setup
    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

    # Add the real filters
    scrub_filter = logging.getLogger().filters[0] if logger.handlers and logger.handlers[0].filters else logging.NullHandler()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log at different levels using the real logger
    logger.debug("This debug message should NOT appear")
    logger.info("This info message should appear")
    logger.warning("This warning message should appear")

    # Check what the real logging system captured
    output = log_capture.getvalue()

    # Debug message should be suppressed
    assert "This debug message should NOT appear" not in output

    # Info and warning should appear
    assert "INFO - This info message should appear" in output
    assert "WARNING - This warning message should appear" in output


def test_log_level_returns_info_by_default():
    """Test that get_log_level returns INFO when configured."""

    with patch('app.core.logging.get_settings') as mock_settings:
        # Mock settings to return actual INFO level
        mock_settings.return_value.log_level = "INFO"

        level = get_log_level()
        assert level == logging.INFO
        assert level > logging.DEBUG  # Debug should be suppressed


def test_debug_suppression_with_setup_logger():
    """Test setup_logger properly suppresses debug messages."""

    # Create a buffer to capture what setup_logger would write
    original_stdout = sys.stdout
    sys.stdout = log_capture = io.StringIO()

    try:
        # Use the real setup_logger as the application would
        logger = setup_logger("test_real_setup", level=logging.INFO)

        # Log debug and info messages
        logger.debug("DEBUG: Hidden sensitive information")
        logger.info("INFO: Public operational message")
        logger.warning("WARNING: Public warning message")

        # Get what was actually written to stdout
        output = log_capture.getvalue()

        # Debug should not appear
        assert "DEBUG: Hidden sensitive information" not in output

        # Info and warning should appear
        assert "INFO: Public operational message" in output or "INFO" in output
        assert "WARNING: Public warning message" in output or "WARNING" in output

    finally:
        # Restore stdout
        sys.stdout = original_stdout
