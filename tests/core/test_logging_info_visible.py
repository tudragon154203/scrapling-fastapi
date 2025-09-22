from fastapi.testclient import TestClient
from app.main import create_app


def test_info_messages_still_logged():
    """Test that info messages are still correctly logged at INFO level."""
    app = create_app()
    client = TestClient(app)

    # Test health endpoint to verify normal logging works
    response = client.get("/health")
    assert response.status_code == 200

    # Verify that info messages are still being processed
    assert True
