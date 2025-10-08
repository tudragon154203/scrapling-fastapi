from specify_src.models.browser_mode import BrowserMode
from specify_src.services.browser_mode_service import BrowserModeService
from specify_src.services.execution_context_service import ExecutionContextService

import pytest

pytestmark = [pytest.mark.unit]



def test_browser_mode_enum():
    """Test that BrowserMode enum has the correct values."""
    assert BrowserMode.HEADLESS.value == "headless"
    assert BrowserMode.HEADFUL.value == "headful"


def test_execution_context_service_not_test_env(monkeypatch):
    """Test that ExecutionContextService correctly identifies non-test environment."""
    # Remove test environment variables
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    assert not ExecutionContextService.is_test_environment()


def test_execution_context_service_test_env_pytest(monkeypatch):
    """Test that ExecutionContextService correctly identifies pytest environment."""
    # Set pytest environment variable
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_execution.py::test_something")

    assert ExecutionContextService.is_test_environment()


def test_execution_context_service_test_env_testing(monkeypatch):
    """Test that ExecutionContextService correctly identifies TESTING environment."""
    # Set TESTING environment variable
    monkeypatch.setenv("TESTING", "true")

    assert ExecutionContextService.is_test_environment()


def test_execution_context_service_test_env_ci(monkeypatch):
    """Test that ExecutionContextService correctly identifies CI environment."""
    # Set CI environment variable
    monkeypatch.setenv("CI", "true")

    assert ExecutionContextService.is_test_environment()


def test_browser_mode_service_headless_in_test_env(monkeypatch):
    """Test that BrowserModeService returns headless mode in test environment."""
    # Set test environment
    monkeypatch.setenv("TESTING", "true")

    # Even with force_headful=True, should return headless in test environment
    mode = BrowserModeService.determine_mode(force_headful=True)
    assert mode == BrowserMode.HEADLESS


def test_browser_mode_service_headless_by_default(monkeypatch):
    """Test that BrowserModeService returns headless mode by default."""
    # Remove test environment variables
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    # With force_headful=False or not provided, should return headless
    mode = BrowserModeService.determine_mode()
    assert mode == BrowserMode.HEADLESS

    mode = BrowserModeService.determine_mode(force_headful=False)
    assert mode == BrowserMode.HEADLESS


def test_browser_mode_service_headful_when_requested(monkeypatch):
    """Test that BrowserModeService returns headful mode when requested."""
    # Remove test environment variables
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    # With force_headful=True, should return headful
    mode = BrowserModeService.determine_mode(force_headful=True)
    assert mode == BrowserMode.HEADFUL
