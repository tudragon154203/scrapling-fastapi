import importlib
import sys
from pathlib import Path
import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core.config import get_settings
import logging

# Ensure project root is on sys.path for imports like `app.*`
# Ensure project root is on sys.path for imports like `app.*`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add specify_src to sys.path for tests
SPECIFY_SRC = ROOT / "specify_src"
if str(SPECIFY_SRC) not in sys.path:
    sys.path.insert(0, str(SPECIFY_SRC))

app = importlib.import_module("app.main").app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="function")
def test_app_with_logging_level(request):
    # Get the desired log level from the test marker
    log_level = request.node.get_closest_marker("log_level")
    if log_level:
        log_level_value = log_level.args[0]
    else:
        log_level_value = "INFO"  # Default if no marker

    # Set the environment variable for LOG_LEVEL
    original_log_level_env = os.environ.get("LOG_LEVEL")
    os.environ["LOG_LEVEL"] = log_level_value

    # Clear settings cache to ensure new LOG_LEVEL is picked up
    get_settings.cache_clear()

    # Re-create the app instance
    app = create_app()
    with TestClient(app) as client:
        # Ensure app.main logger propagates messages for caplog
        app_main_logger = logging.getLogger("app.main")
        original_propagate = app_main_logger.propagate
        app_main_logger.propagate = True

        yield client, app_main_logger  # Yield client and the app.main logger

        # Teardown: Reset environment variable, clear cache, reset logger propagation
        if original_log_level_env is not None:
            os.environ["LOG_LEVEL"] = original_log_level_env
        else:
            del os.environ["LOG_LEVEL"]
        get_settings.cache_clear()  # Clear cache again for cleanup
        app_main_logger.propagate = original_propagate
