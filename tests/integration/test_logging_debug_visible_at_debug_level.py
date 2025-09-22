import logging
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


@pytest.mark.log_level("DEBUG")
def test_sensitive_debug_visible_at_debug_level(caplog, test_app_with_logging_level):
    client, app_main_logger = test_app_with_logging_level
    caplog.set_level(logging.DEBUG)  # Set caplog to DEBUG to capture all messages

    response = client.get("/test-logging")
    assert response.status_code == 200

    assert "This is a sensitive debug message from endpoint." in caplog.text
    assert "This is a public info message from endpoint." in caplog.text
