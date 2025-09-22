import logging
import io
import sys
from app.core.logging import setup_logger, RefererScrubbingFilter, RefererScrubbingFormatter


class LogCaptureHandler(logging.Handler):
    """Custom handler that captures log records for testing."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def get_messages(self, level=None):
        """Get formatted messages, optionally filtered by level."""
        if level:
            return [self.format(record) for record in self.records if record.levelno == level]
        return [self.format(record) for record in self.records]


def test_sensitive_debug_messages_hidden_with_real_setup():
    """Test that sensitive debug messages are hidden using real logging setup."""

    # Use the actual setup_logger function from the app
    logger = setup_logger("test_sensitive_debug", level=logging.INFO)

    # Replace the handler with our capture handler
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    capture_handler = LogCaptureHandler()
    capture_handler.setFormatter(RefererScrubbingFormatter("%(levelname)s - %(message)s"))

    # Add the real scrubbing filter
    scrub_filter = RefererScrubbingFilter()
    capture_handler.addFilter(scrub_filter)

    logger.addHandler(capture_handler)

    # Log messages with potentially sensitive information
    debug_message = "DEBUG: Sensitive user data from session abc123"
    info_message = "INFO: Normal application operation"
    warning_message = "WARNING: Something happened (referer: https://example.com/sensitive/path)"

    logger.debug(debug_message)
    logger.info(info_message)
    logger.warning(warning_message)

    # Check captured records
    records = capture_handler.records

    # Only INFO and WARNING should be captured (DEBUG filtered out)
    debug_records = [r for r in records if r.levelno == logging.DEBUG]
    info_records = [r for r in records if r.levelno == logging.INFO]
    warning_records = [r for r in records if r.levelno == logging.WARNING]

    assert len(debug_records) == 0, f"Debug messages should be filtered out: {debug_records}"
    assert len(info_records) > 0, "Info messages should be captured"
    assert len(warning_records) > 0, "Warning messages should be captured"

    # Check formatted output for sensitive data scrubbing
    formatted_messages = capture_handler.get_messages()

    # Sensitive referer information should be scrubbed from warnings
    referer_found = any("referer:" in msg for msg in formatted_messages)
    url_found = any("https://example.com/sensitive/path" in msg for msg in formatted_messages)

    assert not referer_found, f"Sensitive referer information found in logs: {formatted_messages}"
    assert not url_found, f"Sensitive URL found in logs: {formatted_messages}"


def test_call_logs_hidden_at_info_level_with_real_setup():
    """Test that verbose call logs are hidden with real logging setup."""

    logger = setup_logger("test_call_logs_hidden", level=logging.INFO)

    # Replace handler with capture handler
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    capture_handler = LogCaptureHandler()
    capture_handler.setFormatter(RefererScrubbingFormatter("%(message)s"))

    # Add the real scrubbing filter
    scrub_filter = RefererScrubbingFilter()
    capture_handler.addFilter(scrub_filter)

    logger.addHandler(capture_handler)

    # Log a message with call logs that might be filtered
    message_with_call_log = "INFO: Operation completed successfully\nCall log:\n  - navigate(url)\n  - click(element)\n  - extract_data()"

    logger.info(message_with_call_log)

    formatted_messages = capture_handler.get_messages()

    # At INFO level, call logs should be filtered out
    call_log_found = any("Call log:" in msg for msg in formatted_messages)
    element_click_found = any("element.click()" in msg for msg in formatted_messages)

    assert not call_log_found, f"Call logs should be hidden at INFO level: {formatted_messages}"
    assert not element_click_found, f"Specific call log details should be hidden: {formatted_messages}"

    # Main message should still be present
    assert any("Operation completed successfully" in msg for msg in formatted_messages), "Main operation message should be present"


def test_warning_deduplication_with_real_setup():
    """Test that duplicate warnings are deduplicated using real setup."""

    logger = setup_logger("test_deduplication", level=logging.WARNING)

    # Replace handler with capture handler
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    capture_handler = LogCaptureHandler()
    capture_handler.setFormatter(RefererScrubbingFormatter("%(levelname)s - %(message)s"))

    # Add the real scrubbing filter (this handles deduplication)
    scrub_filter = RefererScrubbingFilter()
    capture_handler.addFilter(scrub_filter)

    logger.addHandler(capture_handler)

    # Log the same warning multiple times
    warning_message = "WARNING: Duplicate test warning"

    logger.warning(warning_message)
    logger.warning(warning_message)  # This should be filtered out
    logger.warning(warning_message)  # This should be filtered out

    formatted_messages = capture_handler.get_messages()

    # Should only see the warning once
    warning_count = sum(1 for msg in formatted_messages if warning_message in msg)
    assert warning_count == 1, f"Warning should appear only once, but appeared {warning_count} times"

    # Total messages should be limited due to deduplication
    assert len(formatted_messages) <= 5, f"Too many messages after deduplication: {formatted_messages}"


def test_debug_messages_suppressed_by_default():
    """Test that debug messages are suppressed by default in real setup."""

    # Capture stdout since that's where setup_logger writes
    original_stdout = sys.stdout
    stdout_capture = io.StringIO()
    sys.stdout = stdout_capture

    try:
        # Use the real setup_logger as the app does (INFO level by default)
        logger = setup_logger("test_default_suppression")

        # Log at different levels
        logger.debug("This debug should NOT be visible")
        logger.info("This info SHOULD be visible")
        logger.warning("This warning SHOULD be visible")

        # Check what was actually written
        output = stdout_capture.getvalue()

        # Debug should not appear
        assert "This debug should NOT be visible" not in output

        # At least one log level should appear
        assert any(level in output for level in ["INFO", "WARNING", "ERROR", "CRITICAL"]), \
            f"No logs found in output: {output}"

    finally:
        sys.stdout = original_stdout
