from fastapi import APIRouter
from types import SimpleNamespace, FunctionType

from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.browser.browse import BrowseCrawler
from fastapi.responses import JSONResponse

router = APIRouter()


def browse(request: BrowseRequest) -> BrowseResponse:
    """Browse handler used by the API route."""
    crawler = BrowseCrawler(browser_engine=request.engine)
    return crawler.run(request)


@router.post("/browse", response_model=BrowseResponse, tags=["browse"])
def browse_endpoint(payload: BrowseRequest):
    """Browse endpoint for interactive user data population sessions.

    Launches a headful browser session for manual browsing to populate persistent user data.
    The browser remains open until manually closed by the user.

    Supports both Camoufox (default) and Chromium engines via the engine parameter.
    """
    result = browse(payload)

    # If a proper BrowseResponse, map HTTP status code based on outcome
    if isinstance(result, BrowseResponse):
        if result.status == "success":
            return result
        # failure: map to specific HTTP status codes
        message = (result.message or "").lower()
        if "lock" in message or "exclusive" in message or "already in use" in message:
            return JSONResponse(content=result.model_dump(), status_code=409)
        return JSONResponse(content=result.model_dump(), status_code=500)

    # Fallback for patched/mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))
