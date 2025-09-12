from fastapi import APIRouter, HTTPException, status
from types import SimpleNamespace, FunctionType
from typing import Optional

from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.browser.browse import BrowseCrawler
from fastapi.responses import JSONResponse

router = APIRouter()

def browse(request: BrowseRequest) -> BrowseResponse:
    """Browse handler used by the API route."""
    crawler = BrowseCrawler()
    return crawler.run(request)


@router.post("/browse", response_model=BrowseResponse, tags=["browse"])
def browse_endpoint(payload: BrowseRequest):
    """Browse endpoint for interactive user data population sessions.

    Launches a headful browser session for manual browsing to populate persistent user data.
    The browser remains open until manually closed by the user.
    """
    if not isinstance(browse, FunctionType):
        req_obj = SimpleNamespace(url=str(payload.url) if payload.url else None)
    else:
        req_obj = payload

    result = browse(request=req_obj)
    # If a proper BrowseResponse, map HTTP status code based on outcome
    if isinstance(result, BrowseResponse):
        if result.status == "success":
            return result
        # failure: map to specific HTTP status codes
        message = (result.message or "").lower()
        if "lock" in message or "exclusive" in message:
            return JSONResponse(content=result.model_dump(), status_code=409)
        return JSONResponse(content=result.model_dump(), status_code=500)

    # Fallback for patched/mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))