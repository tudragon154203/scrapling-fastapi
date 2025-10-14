from fastapi import APIRouter

import re

from app.schemas.browse import BrowseRequest, BrowseResponse
from app.services.browser.browse import BrowseCrawler
from fastapi.responses import JSONResponse

router = APIRouter()


def browse(request: BrowseRequest) -> BrowseResponse:
    """Browse handler used by the API route."""
    try:
        crawler = BrowseCrawler(browser_engine=request.engine)
        return crawler.run(request)
    except ImportError as e:
        # Handle ImportError during BrowseCrawler initialization
        from app.schemas.browse import BrowseResponse
        error_msg = (
            f"Chromium dependencies are not available: {str(e)}\n"
            "To resolve this issue:\n"
            "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
            "2. Ensure Playwright browsers are installed: playwright install chromium\n"
            "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
        )
        return BrowseResponse(
            status="failure",
            message=error_msg
        )


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
        if _is_profile_lock_conflict(result.message):
            return JSONResponse(content=result.model_dump(), status_code=409)
        return JSONResponse(content=result.model_dump(), status_code=500)

    # Fallback for patched/mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))


def _is_profile_lock_conflict(message: str | None) -> bool:
    """Detect whether a failure message indicates a profile lock conflict."""

    normalized = (message or "").lower()
    if not normalized:
        return False

    targeted_terms = (
        "already in use",
        "exclusive lock",
        "lock file",
        "profile lock",
    )
    if any(term in normalized for term in targeted_terms):
        return True

    return bool(
        re.search(r"\block\b", normalized)
        or re.search(r"\blocked\b", normalized)
    )
