import logging
import io
from app.core.logging import RefererScrubbingFilter, RefererScrubbingFormatter


def test_sensitive_debug_messages_hidden():
    """Test that sensitive debug messages are hidden from public view."""

    # Create a logger with DEBUG level to capture all messages
    logger = logging.getLogger("test_sensitive_debug")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a handler that captures logs
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # Use the scrubbing formatter and filter
    formatter = RefererScrubbingFormatter("%(message)s")
    handler.setFormatter(formatter)

    # Add the scrubbing filter
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log messages with potentially sensitive information
    debug_message = "DEBUG: Sensitive user data from session abc123"
    info_message = "INFO: Normal application operation"
    warning_message = "WARNING: Something happened (referer: https://example.com/sensitive/path)"

    logger.debug(debug_message)
    logger.info(info_message)
    logger.warning(warning_message)

    # Get logged content
    logged_content = log_capture.getvalue()

    # Check that debug messages are present in raw logs but not in public output
    assert debug_message in logged_content, "Debug messages should be captured"
    assert info_message in logged_content, "Info messages should be present"
    assert "WARNING: Something happened" in logged_content, "Warning message should be present after referer scrubbing"

    # Check that sensitive referer information is NOT in the final output
    assert "referer:" not in logged_content, "Sensitive referer information should be scrubbed"
    assert "https://example.com/sensitive/path" not in logged_content, "URL should not be in logs"


def test_call_logs_hidden_at_info_level():
    """Test that verbose call logs are hidden when logging level is not DEBUG."""

    logger = logging.getLogger("test_call_logs_hidden")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    formatter = RefererScrubbingFormatter("%(message)s")
    handler.setFormatter(formatter)
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log a message with call logs
    message_with_call_log = "Some operation\nCall log:\n  - element.click()\n  - page.wait()\n  - screenshot.take()"

    logger.info(message_with_call_log)

    logged_content = log_capture.getvalue()

    # At INFO level, call logs should be filtered out
    assert "Call log:" not in logged_content, "Call logs should be hidden at INFO level"
    assert "element.click()" not in logged_content, "Specific call log details should be hidden"
    assert "Some operation" in logged_content, "Original message should still be present"


def test_warning_deduplication():
    """Test that duplicate warnings are deduplicated."""

    logger = logging.getLogger("test_deduplication")
    logger.setLevel(logging.WARNING)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    formatter = RefererScrubbingFormatter("%(message)s")
    handler.setFormatter(formatter)
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log the same warning multiple times
    warning_message = "WARNING: Duplicate test warning"

    logger.warning(warning_message)
    logger.warning(warning_message)  # This should be filtered out
    logger.warning(warning_message)  # This should be filtered out

    logged_content = log_capture.getvalue()

    # Should only see the warning once
    lines = logged_content.strip().split('\n')
    log_lines = [line for line in lines if line.strip()]

    # Only one instance of the warning should appear
    warning_count = sum(1 for line in log_lines if warning_message in line)
    assert warning_count == 1, f"Warning should appear only once, but appeared {warning_count} times"
    assert len(log_lines) == 1, f"Expected only 1 log line, got {len(log_lines)}"
