"""
Comprehensive tests for core logging to achieve 80%+ coverage.
"""

import logging
import re
from unittest.mock import MagicMock, patch

from app.core.logging import (
    RefererScrubbingFormatter,
    RefererScrubbingFilter,
    _ensure_filter,
    _ensure_global_filters,
    get_log_level,
    setup_logger,
    get_logger,
    _SCRUBBING_FILTER,
)


class TestRefererScrubbingFormatter:
    """Test RefererScrubbingFormatter."""

    def test_format_with_referer(self):
        """Test formatting with referer information."""
        formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed (referer: https://example.com)",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert "https://example.com" not in result
        assert "(referer:" not in result
        assert "Request completed" in result

    def test_format_without_referer(self):
        """Test formatting without referer information."""
        formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert result == "INFO - Request completed"

    def test_format_case_insensitive_referer(self):
        """Test formatting with different case referer."""
        formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed (REFERER: https://example.com)",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert "https://example.com" not in result
        assert "(REFERER:" not in result

    def test_format_with_multiple_referers(self):
        """Test formatting with multiple referer mentions."""
        formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="First request (referer: https://example1.com) and second request (referer: https://example2.com)",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert "https://example1.com" not in result
        assert "https://example2.com" not in result
        assert "(referer:" not in result
        assert "First request" in result
        assert "and second request" in result

    def test_format_with_complex_referer(self):
        """Test formatting with complex referer string."""
        formatter = RefererScrubbingFormatter("%(levelname)s - %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed (referer: https://example.com/path?query=value&other=test)",
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert "https://example.com" not in result
        assert "Request completed" in result


class TestRefererScrubbingFilter:
    """Test RefererScrubbingFilter."""

    def test_filter_init(self):
        """Test filter initialization."""
        filter_instance = RefererScrubbingFilter()
        assert hasattr(filter_instance, '_seen_warnings')
        assert isinstance(filter_instance._seen_warnings, set)

    def test_filter_with_referer(self):
        """Test filtering log with referer."""
        filter_instance = RefererScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed (referer: https://example.com)",
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)

        assert result is True
        assert "https://example.com" not in record.msg
        assert "(referer:" not in record.msg
        assert record.args == ()

    def test_filter_without_referer(self):
        """Test filtering log without referer."""
        filter_instance = RefererScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed",
            args=(),
            exc_info=None
        )

        original_msg = record.msg
        result = filter_instance.filter(record)

        assert result is True
        assert record.msg == original_msg

    def test_filter_with_call_log_debug_level(self):
        """Test filtering call log at debug level."""
        filter_instance = RefererScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Request completed\nCall log:\n  - item 1\n  - item 2\n",
            args=(),
            exc_info=None
        )

        # Mock logger effective level as DEBUG
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.getEffectiveLevel.return_value = logging.DEBUG
            mock_get_logger.return_value = mock_logger

            result = filter_instance.filter(record)

            # Should not filter call log at debug level
            assert result is True
            assert "Call log:" in record.msg

    def test_filter_with_call_log_info_level(self):
        """Test filtering call log at info level."""
        filter_instance = RefererScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Request completed\nCall log:\n  - item 1\n  - item 2\n",
            args=(),
            exc_info=None
        )

        # Mock logger effective level as INFO (higher than DEBUG)
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.getEffectiveLevel.return_value = logging.INFO
            mock_get_logger.return_value = mock_logger

            result = filter_instance.filter(record)

            # Should filter call log at info level
            assert result is True
            assert "Call log:" not in record.msg
            assert "Request completed" in record.msg

    def test_filter_warning_deduplication(self):
        """Test warning deduplication."""
        filter_instance = RefererScrubbingFilter()

        # First warning should pass
        record1 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None
        )

        result1 = filter_instance.filter(record1)
        assert result1 is True

        # Second identical warning should be filtered
        record2 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None
        )

        result2 = filter_instance.filter(record2)
        assert result2 is False

    def test_filter_warning_different_messages(self):
        """Test warning filtering with different messages."""
        filter_instance = RefererScrubbingFilter()

        # First warning
        record1 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message 1",
            args=(),
            exc_info=None
        )

        result1 = filter_instance.filter(record1)
        assert result1 is True

        # Different warning should pass
        record2 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message 2",
            args=(),
            exc_info=None
        )

        result2 = filter_instance.filter(record2)
        assert result2 is True

    def test_filter_warning_different_levels(self):
        """Test warning deduplication with different levels."""
        filter_instance = RefererScrubbingFilter()

        # Warning level
        record1 = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Same message",
            args=(),
            exc_info=None
        )

        result1 = filter_instance.filter(record1)
        assert result1 is True

        # Error level should not be deduplicated with warning
        record2 = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Same message",
            args=(),
            exc_info=None
        )

        result2 = filter_instance.filter(record2)
        assert result2 is True

    def test_filter_info_no_deduplication(self):
        """Test that info messages are not deduplicated."""
        filter_instance = RefererScrubbingFilter()

        # First info message
        record1 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Info message",
            args=(),
            exc_info=None
        )

        result1 = filter_instance.filter(record1)
        assert result1 is True

        # Second identical info message should also pass
        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Info message",
            args=(),
            exc_info=None
        )

        result2 = filter_instance.filter(record2)
        assert result2 is True

    def test_filter_non_string_message(self):
        """Test filtering non-string messages."""
        filter_instance = RefererScrubbingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg=123,  # Non-string message
            args=(),
            exc_info=None
        )

        result = filter_instance.filter(record)

        # Should pass through non-string messages unchanged
        assert result is True
        assert record.msg == 123

    def test_filter_message_get_exception(self):
        """Test filtering when getMessage() raises exception."""
        filter_instance = RefererScrubbingFilter()
        record = MagicMock()
        record.getMessage.side_effect = Exception("Message failed")
        record.msg = "Original message"
        record.levelno = logging.INFO
        record.name = "test_logger"  # Add proper string name for logging.getLogger()

        result = filter_instance.filter(record)

        # Should handle exception gracefully
        assert result is True

    def test_filter_multiple_processing(self):
        """Test filter handles multiple processing passes correctly."""
        filter_instance = RefererScrubbingFilter()

        # Create record with referer
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Request completed (referer: https://example.com)",
            args=(),
            exc_info=None
        )

        # First pass - should sanitize
        result1 = filter_instance.filter(record)
        assert result1 is True
        assert "referer:" not in record.msg

        # Second pass - should not change further
        original_msg = record.msg
        result2 = filter_instance.filter(record)
        assert result2 is True
        assert record.msg == original_msg


class TestEnsureFilter:
    """Test _ensure_filter function."""

    def test_ensure_filter_on_logger(self):
        """Test ensuring filter on logger."""
        logger = MagicMock()
        logger.filters = []

        _ensure_filter(logger)

        logger.addFilter.assert_called_once_with(_SCRUBBING_FILTER)

    def test_ensure_filter_on_handler(self):
        """Test ensuring filter on handler."""
        handler = MagicMock()
        handler.filters = []

        _ensure_filter(handler)

        handler.addFilter.assert_called_once_with(_SCRUBBING_FILTER)

    def test_ensure_filter_already_exists(self):
        """Test ensuring filter when it already exists."""
        logger = MagicMock()
        logger.filters = [_SCRUBBING_FILTER]

        _ensure_filter(logger)

        logger.addFilter.assert_not_called()

    def test_ensure_filter_no_filters_attribute(self):
        """Test ensuring filter when target has no filters attribute."""
        target = MagicMock()
        delattr(target, 'filters')

        # Should not raise exception
        _ensure_filter(target)


class TestEnsureGlobalFilters:
    """Test _ensure_global_filters function."""

    def test_ensure_global_filters(self):
        """Test ensuring global filters."""
        with patch('app.core.logging._ensure_filter') as mock_ensure_filter:
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = [MagicMock(), MagicMock()]
            mock_scrapling_logger = MagicMock()
            mock_scrapling_logger.handlers = [MagicMock()]

            with patch('logging.getLogger') as mock_get_logger:
                mock_get_logger.side_effect = [mock_root_logger, mock_scrapling_logger]

                _ensure_global_filters()

                # Should be called for both loggers and all their handlers
                assert mock_ensure_filter.call_count == 5  # 2 loggers + 3 handlers


class TestGetLogLevel:
    """Test get_log_level function."""

    @patch('app.core.logging.get_settings')
    def test_get_log_level_debug(self, mock_get_settings):
        """Test getting debug log level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "DEBUG"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.DEBUG

    @patch('app.core.logging.get_settings')
    def test_get_log_level_info(self, mock_get_settings):
        """Test getting info log level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.INFO

    @patch('app.core.logging.get_settings')
    def test_get_log_level_warning(self, mock_get_settings):
        """Test getting warning log level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "WARNING"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.WARNING

    @patch('app.core.logging.get_settings')
    def test_get_log_level_error(self, mock_get_settings):
        """Test getting error log level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "ERROR"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.ERROR

    @patch('app.core.logging.get_settings')
    def test_get_log_level_critical(self, mock_get_settings):
        """Test getting critical log level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "CRITICAL"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.CRITICAL

    @patch('app.core.logging.get_settings')
    def test_get_log_level_case_insensitive(self, mock_get_settings):
        """Test getting log level case insensitive."""
        mock_settings = MagicMock()
        mock_settings.log_level = "debug"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.DEBUG

    @patch('app.core.logging.get_settings')
    def test_get_log_level_invalid_defaults_to_info(self, mock_get_settings):
        """Test getting log level defaults to info for invalid level."""
        mock_settings = MagicMock()
        mock_settings.log_level = "INVALID"
        mock_get_settings.return_value = mock_settings

        result = get_log_level()

        assert result == logging.INFO


class TestSetupLogger:
    """Test setup_logger function."""

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_with_level(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger with explicit level."""
        mock_get_log_level.return_value = logging.INFO

        logger = setup_logger("test_logger", logging.DEBUG)

        assert logger.level == logging.DEBUG
        mock_ensure_filters.assert_called_once()

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_without_level(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger without explicit level."""
        mock_get_log_level.return_value = logging.WARNING

        logger = setup_logger("test_logger")

        assert logger.level == logging.WARNING
        mock_ensure_filters.assert_called_once()

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_removes_existing_handlers(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger removes existing handlers."""
        mock_get_log_level.return_value = logging.INFO

        existing_handler = MagicMock()
        logger = logging.getLogger("test_logger")
        logger.addHandler(existing_handler)

        setup_logger("test_logger")

        assert len(logger.handlers) == 1
        assert existing_handler not in logger.handlers

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_adds_stream_handler(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger adds stream handler."""
        mock_get_log_level.return_value = logging.INFO

        logger = setup_logger("test_logger")

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_handler_configuration(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger configures handler correctly."""
        mock_get_log_level.return_value = logging.DEBUG

        logger = setup_logger("test_logger")

        handler = logger.handlers[0]
        assert handler.level == logging.DEBUG
        assert isinstance(handler.formatter, RefererScrubbingFormatter)

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_no_propagation(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger disables propagation."""
        mock_get_log_level.return_value = logging.INFO

        logger = setup_logger("test_logger")

        assert logger.propagate is False

    @patch('app.core.logging.get_log_level')
    @patch('app.core.logging._ensure_global_filters')
    def test_setup_logger_none_name(self, mock_ensure_filters, mock_get_log_level):
        """Test setting up logger with None name."""
        mock_get_log_level.return_value = logging.INFO

        logger = setup_logger(None)

        assert logger.name == "root"  # Default logger name


class TestGetLogger:
    """Test get_logger function."""

    @patch('app.core.logging.setup_logger')
    def test_get_logger(self, mock_setup_logger):
        """Test getting logger."""
        mock_logger = MagicMock()
        mock_setup_logger.return_value = mock_logger

        result = get_logger("test_logger")

        mock_setup_logger.assert_called_once_with("test_logger")
        assert result is mock_logger


class TestIntegration:
    """Integration tests for logging system."""

    @patch('app.core.logging.get_settings')
    def test_full_logging_setup_integration(self, mock_get_settings):
        """Test full logging setup integration."""
        mock_settings = MagicMock()
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        # Setup logger
        logger = setup_logger("integration_test")

        # Test that logger is properly configured
        assert logger.name == "integration_test"
        assert len(logger.handlers) == 1
        assert logger.propagate is False

        # Test logging with referer (should not crash)
        logger.info("Request completed (referer: https://example.com)")

        # Test logging with call log (should not crash)
        logger.warning("Operation failed\nCall log:\n  - step 1 failed\n  - step 2 skipped")

        # If we got here without exceptions, the integration works

    def test_filter_patterns_match_real_cases(self):
        """Test filter patterns match real-world cases."""
        formatter = RefererScrubbingFormatter()

        # Test real UVicorn access log format
        test_cases = [
            'POST /api/test HTTP/1.1" 200 1234 (referer: https://example.com)',
            'GET /api/other HTTP/1.1" 404 567 (REFERER: https://test.org/path)',
            'Request completed with info (referer: http://localhost:8000/page)',
        ]

        for test_case in test_cases:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg=test_case,
                args=(),
                exc_info=None
            )

            result = formatter.format(record)
            assert "referer:" not in result.lower()
            assert not re.search(r'https?://[^\s)]+', result)

    def test_call_log_pattern_real_cases(self):
        """Test call log pattern matches real cases."""
        filter_instance = RefererScrubbingFilter()

        test_cases = [
            "Error occurred\nCall log:\n  - First operation\n  - Second operation\n  - Third operation",
            "Operation failed\nCall log:\n\t- item 1\n\t- item 2\n",
            "Request processed\nCall log:\n  + step 1\n  + step 2\n",
        ]

        # Mock logger with INFO level (higher than DEBUG)
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.getEffectiveLevel.return_value = logging.INFO
            mock_get_logger.return_value = mock_logger

            for test_case in test_cases:
                record = logging.LogRecord(
                    name="test",
                    level=logging.WARNING,
                    pathname="test.py",
                    lineno=10,
                    msg=test_case,
                    args=(),
                    exc_info=None
                )

                filter_instance.filter(record)

                # Call log should be removed
                assert "Call log:" not in record.msg
