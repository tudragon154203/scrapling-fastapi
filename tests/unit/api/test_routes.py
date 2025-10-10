from app.api.routes import router
from fastapi.routing import APIRoute

import pytest

pytestmark = [pytest.mark.unit]


EXPECTED_PATHS = {
    "/health",
    "/crawl",
    "/crawl/dpd",
    "/crawl/auspost",
    "/browse",
    "/tiktok/session",
    "/tiktok/search",
}


def test_routes_include_expected_paths():
    registered_paths = {
        route.path for route in router.routes if isinstance(route, APIRoute)
    }

    missing = EXPECTED_PATHS - registered_paths
    assert not missing, f"Missing expected routes: {sorted(missing)}"


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
