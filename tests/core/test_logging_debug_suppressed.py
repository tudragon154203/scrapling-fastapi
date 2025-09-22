import logging
import io
from unittest.mock import patch
from app.core.logging import setup_logger, get_log_level


def test_debug_messages_suppressed_at_info_level():
    """Test that debug messages are suppressed when logging level is INFO."""

    # Capture log output
    log_capture = io.StringIO()

    # Create logger with INFO level
    logger = logging.getLogger("test_debug_suppression")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add our capture handler
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

    # Log at different levels
    logger.debug("This is a sensitive debug message")
    logger.info("This is a public info message")
    logger.warning("This is a warning message")

    # Check output
    output = log_capture.getvalue()

    # Debug message should NOT appear
    assert "sensitive debug message" not in output

    # Info and warning messages should appear
    assert "public info message" in output
    assert "warning message" in output


def test_log_level_returns_info_by_default():
    """Test that get_log_level returns INFO when not configured otherwise."""

    # Mock settings to return INFO level
    with patch('app.core.logging.get_settings') as mock_settings:
        mock_settings.return_value.log_level = "INFO"

        level = get_log_level()
        assert level == logging.INFO

        # Test that debug messages would be suppressed
        assert level > logging.DEBUG


def test_debug_not_logged_when_level_is_info():
    """Test that debug messages are not logged when logging level is INFO."""

    # Create a string buffer to capture logs
    log_buffer = io.StringIO()

    # Create logger with INFO level
    logger = setup_logger("test_debug", level=logging.INFO)

    # Replace handler with our buffer
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    test_handler = logging.StreamHandler(log_buffer)
    test_handler.setLevel(logging.INFO)
    test_handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(test_handler)

    # Log debug and info messages
    logger.debug("This debug content should NOT appear")
    logger.info("This info content should appear")

    # Check what was actually logged
    logged_content = log_buffer.getvalue()

    # Debug content should not be there
    assert "This debug content should NOT appear" not in logged_content

    # Info content should be there
    assert "This info content should appear" in logged_content
