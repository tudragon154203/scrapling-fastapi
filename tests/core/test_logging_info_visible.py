import logging
import io
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.logging import setup_logger


def test_info_messages_still_logged():
    """Test that info messages are still correctly logged and visible."""

    # Test that the health endpoint works and logs info messages
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_info_messages_preserved_through_logging_setup():
    """Test that info messages are preserved throughout the logging setup."""

    # Create a string buffer to capture logs
    log_buffer = io.StringIO()

    # Create logger with INFO level
    logger = setup_logger("test_info_preservation", level=logging.INFO)

    # Replace handler with our buffer
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    test_handler = logging.StreamHandler(log_buffer)
    test_handler.setLevel(logging.INFO)
    test_handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
    logger.addHandler(test_handler)

    # Log at different levels
    logger.debug("This debug message should NOT appear")
    logger.info("This info message should appear")
    logger.warning("This warning message should appear")
    logger.error("This error message should appear")

    # Check what was actually logged
    logged_content = log_buffer.getvalue()

    # Info message should be there
    assert "INFO:This info message should appear" in logged_content

    # Warning and error messages should be there
    assert "WARNING:This warning message should appear" in logged_content
    assert "ERROR:This error message should appear" in logged_content

    # Debug message should NOT be there
    assert "DEBUG:This debug message should NOT appear" not in logged_content


def test_info_messages_with_referer_scrubbing():
    """Test that info messages with referers are properly scrubbed but still visible."""

    logger = logging.getLogger("test_info_referer")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    from app.core.logging import RefererScrubbingFormatter, RefererScrubbingFilter

    formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log info message with referer
    info_message_with_referer = "INFO: Page loaded successfully (referer: https://example.com/user/profile)"

    logger.info(info_message_with_referer)

    logged_content = log_capture.getvalue()

    # Info message should be visible without sensitive referer (formatter adds prefix)
    assert "INFO - Page loaded successfully" in logged_content or "INFO: Page loaded successfully" in logged_content

    # Sensitive referer should be scrubbed
    assert "referer:" not in logged_content
    assert "https://example.com/user/profile" not in logged_content


def test_info_messages_survive_call_log_filtering():
    """Test that info messages survive call log filtering at INFO level."""

    logger = logging.getLogger("test_info_call_log")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    from app.core.logging import RefererScrubbingFormatter, RefererScrubbingFilter

    formatter = RefererScrubbingFormatter("%(message)s")
    handler.setFormatter(formatter)
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Create info message with call logs that might be filtered
    info_message_with_call_log = "INFO: Operation completed successfully\nCall log:\n  - navigate(url)\n  - click(element)\n  - extract_data()"

    logger.info(info_message_with_call_log)

    logged_content = log_capture.getvalue()

    # Main info message should survive
    assert "INFO: Operation completed successfully" in logged_content

    # Call logs should be filtered out at INFO level
    assert "Call log:" not in logged_content
    assert "navigate(url)" not in logged_content
    assert "click(element)" not in logged_content


def test_info_messages_not_deduplicated():
    """Test that info messages are not subject to warning deduplication."""
    import logging

    logger = logging.getLogger("test_info_dedup")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    from app.core.logging import RefererScrubbingFormatter, RefererScrubbingFilter

    formatter = RefererScrubbingFormatter("%(message)s")
    handler.setFormatter(formatter)
    scrub_filter = RefererScrubbingFilter()
    handler.addFilter(scrub_filter)

    logger.addHandler(handler)

    # Log the same info message multiple times
    info_message = "INFO: Normal system operation"

    logger.info(info_message)
    logger.info(info_message)  # This should NOT be filtered out
    logger.info(info_message)  # This should NOT be filtered out

    logged_content = log_capture.getvalue()

    # All info messages should appear (no deduplication for INFO)
    lines = logged_content.strip().split('\n')
    info_count = sum(1 for line in lines if info_message in line)
    assert info_count == 3, f"Expected 3 info messages, got {info_count}"
