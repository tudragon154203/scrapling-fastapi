import pytest
from unittest.mock import patch
import os
from src.models.browser_mode import BrowserMode
from src.services.browser_mode_service import BrowserModeService


@patch('src.services.execution_context_service.ExecutionContextService.is_test_environment')
def test_determine_mode_force_headful_true(mock_is_test_environment):
    """Test that determine_mode returns HEADFUL when force_headful is True and not in test environment."""
    mock_is_test_environment.return_value = False
    mode = BrowserModeService.determine_mode(force_headful=True)
    assert mode == BrowserMode.HEADFUL


@patch('src.services.execution_context_service.ExecutionContextService.is_test_environment')
def test_determine_mode_force_headful_false(mock_is_test_environment):
    """Test that determine_mode returns HEADLESS when force_headful is False and not in test environment."""
    mock_is_test_environment.return_value = False
    mode = BrowserModeService.determine_mode(force_headful=False)
    assert mode == BrowserMode.HEADLESS


@patch('src.services.execution_context_service.ExecutionContextService.is_test_environment')
def test_determine_mode_test_environment(mock_is_test_environment):
    """Test that determine_mode returns HEADLESS when in test environment, regardless of force_headful."""
    mock_is_test_environment.return_value = True
    mode = BrowserModeService.determine_mode(force_headful=True)
    assert mode == BrowserMode.HEADLESS
    mode = BrowserModeService.determine_mode(force_headful=False)
    assert mode == BrowserMode.HEADLESS


@patch.dict(os.environ, {"TESTING": "true"})
def test_determine_mode_testing_env_force_headful_true():
    """Test that determine_mode returns HEADLESS when TESTING env var is 'true' and force_headful is True."""
    mode = BrowserModeService.determine_mode(force_headful=True)
    assert mode == BrowserMode.HEADLESS
