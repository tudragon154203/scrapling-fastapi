from specify_src.models.execution_context import ExecutionContext

import pytest

pytestmark = [pytest.mark.unit]


def test_execution_context_not_test_env(monkeypatch):
    """Test that ExecutionContext correctly identifies non-test environment."""
    # Remove test environment variables
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.delenv("CI", raising=False)

    assert not ExecutionContext.is_test_environment()


def test_execution_context_test_env_pytest(monkeypatch):
    """Test that ExecutionContext correctly identifies pytest environment."""
    # Set pytest environment variable
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_execution.py::test_something")

    assert ExecutionContext.is_test_environment()


def test_execution_context_test_env_testing(monkeypatch):
    """Test that ExecutionContext correctly identifies TESTING environment."""
    # Set TESTING environment variable
    monkeypatch.setenv("TESTING", "true")

    assert ExecutionContext.is_test_environment()


def test_execution_context_test_env_ci(monkeypatch):
    """Test that ExecutionContext correctly identifies CI environment."""
    # Set CI environment variable
    monkeypatch.setenv("CI", "true")

    assert ExecutionContext.is_test_environment()
