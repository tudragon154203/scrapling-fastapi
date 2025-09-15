from fastapi.routing import APIRoute

from app.api.routes import router


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
