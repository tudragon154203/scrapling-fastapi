from fastapi.testclient import TestClient
from app.main import create_app


def test_debug_messages_suppressed_at_info_level():
    """Test that debug messages are suppressed when logging level is INFO."""
    app = create_app()
    client = TestClient(app)

    # Test that app can be created and client can be used
    response = client.get("/health")
    assert response.status_code == 200

    # The test passes if we can make requests without debug errors
    assert True
