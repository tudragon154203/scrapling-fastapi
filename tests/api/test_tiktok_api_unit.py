import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.tiktok.search import TikTokSearchResponse, TikTokSearchRequest
from app.services.tiktok.search.service import TikTokSearchService
from src.services.browser_mode_service import BrowserModeService
from src.models.browser_mode import BrowserMode

client = TestClient(app)


@pytest.fixture
def mock_tiktok_search_service():
    with patch("app.api.tiktok.TikTokSearchService", autospec=True) as MockService:
        instance = MockService.return_value
        instance.search = AsyncMock()
        yield instance


@pytest.fixture
def mock_browser_mode_service():
    with patch("app.api.tiktok.BrowserModeService", autospec=True) as MockService:
        MockService.determine_mode.return_value = BrowserMode.HEADLESS
        yield MockService


@pytest.fixture(autouse=True)
def mock_tiktok_service_init():
    """
    Mocks the TikTokService.__init__ to prevent actual service initialization
    and potential side effects during testing.
    """
    with patch("app.api.tiktok.TiktokService.__init__", return_value=None) as mock_init:
        yield mock_init


def test_tiktok_search_endpoint_success(mock_tiktok_search_service, mock_browser_mode_service):
    mock_tiktok_search_service.search.return_value = {
        "results": [{"id": "123", "title": "video1"}],
        "totalResults": 1,
        "query": "test query",
    }

    response = client.post(
        "/tiktok/search",
        json={"query": "test query", "numVideos": 1, "force_headful": False}
    )

    assert response.status_code == 200
    data = TikTokSearchResponse(**response.json())
    assert data.query == "test query"
    assert data.totalResults == 1
    assert len(data.results) == 1
    assert data.execution_mode == BrowserMode.HEADLESS.value

    mock_browser_mode_service.determine_mode.assert_called_once_with(False)
    mock_tiktok_search_service.search.assert_called_once_with(
        query="test query",
        num_videos=1,
        sort_type=None,
        recency_days=None,
    )


@pytest.mark.parametrize(
    "error_code, expected_status_code",
    [
        ("NOT_LOGGED_IN", 409),
        ("VALIDATION_ERROR", 422),
        ("RATE_LIMITED", 429),
        ("SCRAPE_FAILED", 500),
        ("UNKNOWN_ERROR", 500),
    ],
)
def test_tiktok_search_endpoint_error_handling_structured_error(
    mock_tiktok_search_service, mock_browser_mode_service, error_code, expected_status_code
):
    mock_tiktok_search_service.search.return_value = {
        "error": {"code": error_code, "message": f"Error message for {error_code}"}
    }

    response = client.post(
        "/tiktok/search",
        json={"query": "test query", "numVideos": 1, "force_headful": False}
    )

    assert response.status_code == expected_status_code
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == error_code
    assert data["error"]["message"] == f"Error message for {error_code}"


@pytest.mark.parametrize(
    "error_message, expected_code, expected_status_code",
    [
        ("User not logged in", "NOT_LOGGED_IN", 409),
        ("Session expired", "NOT_LOGGED_IN", 409),
        ("Validation failed for parameter", "VALIDATION_ERROR", 422),
        ("Too many requests", "RATE_LIMITED", 429),
        ("Scraping failed unexpectedly", "SCRAPE_FAILED", 500),
        ("Some other error", "SCRAPE_FAILED", 500),  # Default for unknown string errors
    ],
)
def test_tiktok_search_endpoint_error_handling_string_error(
    mock_tiktok_search_service, mock_browser_mode_service, error_message, expected_code, expected_status_code
):
    mock_tiktok_search_service.search.return_value = {"error": error_message}

    response = client.post(
        "/tiktok/search",
        json={"query": "test query", "numVideos": 1, "force_headful": False}
    )

    assert response.status_code == expected_status_code
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == expected_code
    assert data["error"]["message"] == error_message


def test_tiktok_search_endpoint_invalid_force_headful():
    """Test that invalid values for force_headful result in validation errors."""
    response = client.post("/tiktok/search", json={"query": "test", "force_headful": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert len(data["detail"]) > 0
    assert data["detail"][0]["loc"] == ["body", "force_headful"]
    assert "bool_parsing" in data["detail"][0]["type"]
