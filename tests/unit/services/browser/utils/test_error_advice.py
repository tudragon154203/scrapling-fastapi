from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.browser.utils.error_advice import (
    ChromiumErrorAdvisor,
    ErrorAdvice,
    chromium_dependency_missing_advice,
)


@dataclass
class DummySettings:
    chromium_runtime_effective_user_data_dir: str | None = None


def test_chromium_dependency_missing_advice_matches_existing_message():
    advice = chromium_dependency_missing_advice(ImportError("missing playwright"))

    expected = (
        "Chromium dependencies are not available: missing playwright\n"
        "To resolve this issue:\n"
        "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
        "2. Ensure Playwright browsers are installed: playwright install chromium\n"
        "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
    )

    assert isinstance(advice, ErrorAdvice)
    assert advice.log_level == "error"
    assert advice.message == expected


def test_chromium_runtime_lock_error_returns_warning_and_message():
    advisor = ChromiumErrorAdvisor(
        settings=DummySettings(),
        user_data_dir="/profiles",
        lock_file="/profiles/lockfile",
    )

    advice = advisor.handle_runtime_error(RuntimeError("profile already in use"))

    assert isinstance(advice, ErrorAdvice)
    assert advice.log_level == "warning"
    assert "Chromium profile is already in use" in advice.message
    assert "/profiles/lockfile" in advice.message


def test_chromium_runtime_corruption_error_uses_effective_dir():
    settings = DummySettings(chromium_runtime_effective_user_data_dir="/tmp/effective")
    advisor = ChromiumErrorAdvisor(settings=settings, user_data_dir="/profiles")

    advice = advisor.handle_runtime_error(RuntimeError("database is corrupted"))

    assert isinstance(advice, ErrorAdvice)
    assert advice.log_level == "error"
    assert "/tmp/effective" in advice.message


def test_chromium_runtime_error_returns_none_when_unknown():
    advisor = ChromiumErrorAdvisor(settings=DummySettings(), user_data_dir="/profiles")

    advice = advisor.handle_runtime_error(RuntimeError("something else"))

    assert advice is None


@pytest.mark.parametrize(
    "exc,expected_substring",
    [
        (OSError("no space left on device"), "Disk space or filesystem error"),
        (PermissionError("permission denied"), "Permission error accessing Chromium user data"),
        (TimeoutError("timed out"), "Timeout occurred during Chromium browse session"),
        (ConnectionError("connection reset"), "Network/connection error during Chromium browse"),
        (MemoryError("out of memory"), "Insufficient memory for Chromium browse"),
        (ImportError("playwright not installed"), "Chromium browser engine is not available"),
    ],
)
def test_chromium_advisor_handles_known_exceptions(exc: Exception, expected_substring: str):
    advisor = ChromiumErrorAdvisor(settings=DummySettings(), user_data_dir="/profiles")

    advice = advisor.handle_known_exception(exc)

    assert isinstance(advice, ErrorAdvice)
    assert expected_substring in advice.message


def test_chromium_advisor_known_exception_falls_back_to_generic():
    advisor = ChromiumErrorAdvisor(settings=DummySettings(), user_data_dir="/profiles")

    advice = advisor.handle_known_exception(ValueError("boom"))

    assert isinstance(advice, ErrorAdvice)
    assert advice.message.startswith("Chromium browse session failed: boom")


def test_chromium_advisor_generic_exception_message_matches_original():
    advisor = ChromiumErrorAdvisor(settings=DummySettings(), user_data_dir="/profiles")

    advice = advisor.generic_failure(Exception("boom"))

    expected = (
        "Chromium browse session failed: boom\n"
        "Troubleshooting steps:\n"
        "1. Check that Chromium/Chrome is properly installed\n"
        "2. Verify display settings if running in headful mode\n"
        "3. Check available disk space for user data directory\n"
        "4. Try running with Camoufox engine as an alternative"
    )

    assert isinstance(advice, ErrorAdvice)
    assert advice.log_level == "error"
    assert advice.message == expected
