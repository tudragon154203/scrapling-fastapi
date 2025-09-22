import logging
from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


@pytest.mark.log_level("INFO")
def test_sensitive_debug_not_visible_at_info_level(caplog, test_app_with_logging_level):
    client, app_main_logger = test_app_with_logging_level
    caplog.set_level(logging.INFO)  # Set caplog to INFO to only capture INFO and above

    response = client.get("/test-logging")
    assert response.status_code == 200

    assert "This is a sensitive debug message from endpoint." not in caplog.text
    assert "This is a public info message from endpoint." in caplog.text
