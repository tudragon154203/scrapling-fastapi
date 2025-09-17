"""Tiktok
=========

Expose the unified Tiktok API surface that covers session management and
search capabilities. Both endpoints are grouped under the same documentation
section to keep the generated OpenAPI docs concise.
"""

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from app.schemas.tiktok.search import TikTokSearchRequest, TikTokSearchResponse
from app.schemas.tiktok.session import TikTokSessionRequest, TikTokSessionResponse
from app.services.tiktok.session import TiktokService
from app.services.tiktok.search.service import TikTokSearchService


router = APIRouter()
# Keep the conventional name so tests can patch it
tiktok_service = TiktokService()


@router.post("/tiktok/session", response_model=TikTokSessionResponse, tags=["Tiktok"])
async def create_tiktok_session_endpoint(request: Request):
    """Handle the Tiktok session workflow, accepting empty JSON bodies gracefully."""
    # Accept empty body or JSON; if invalid JSON, fallback to empty request
    try:
        body = await request.body()
        if body:
            data = await request.json()
            req_obj = TikTokSessionRequest(**data)
        else:
            req_obj = TikTokSessionRequest()
    except Exception as e:
        # Return 422 when extra fields provided
        msg = str(e)
        if "extra_forbidden" in msg or "Extra inputs are not permitted" in msg:
            return JSONResponse(
                content={"detail": [{
                    "type": "extra_forbidden",
                    "msg": "Extra inputs are not permitted"
                }]},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        # Fallback: treat as empty request
        req_obj = TikTokSessionRequest()

    result = await tiktok_service.create_session(req_obj, immediate_cleanup=False)

    if result.status == "success":
        return JSONResponse(content=result.model_dump(exclude_none=True), status_code=status.HTTP_200_OK)

    # Map known error codes to HTTP status
    code = (result.error_details or {}).get("code", "").upper() if result.error_details else ""
    status_map = {
        "NOT_LOGGED_IN": status.HTTP_409_CONFLICT,
        "USER_DATA_LOCKED": status.HTTP_423_LOCKED,
        "SESSION_TIMEOUT": status.HTTP_504_GATEWAY_TIMEOUT,
        "SESSION_CREATION_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "UNKNOWN_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return JSONResponse(content=result.model_dump(exclude_none=True), status_code=status_map.get(code, 500))


@router.post("/tiktok/search", response_model=TikTokSearchResponse, tags=["Tiktok"])
async def tiktok_search_endpoint(payload: TikTokSearchRequest):
    """Handle the Tiktok search workflow by delegating to the service layer."""
    search_service = TikTokSearchService(strategy=payload.strategy)
    result = await search_service.search(
        query=payload.query,
        num_videos=payload.numVideos,
        sort_type=payload.sortType,
        recency_days=payload.recencyDays,
    )

    if "error" in result:
        err = result["error"] or {}
        # Handle both string error messages and structured error objects
        if isinstance(err, str):
            # Convert string error to structured error format
            code = "SCRAPE_FAILED"
            if "not logged" in err.lower() or "session" in err.lower():
                code = "NOT_LOGGED_IN"
            elif "validation" in err.lower():
                code = "VALIDATION_ERROR"
            err = {"code": code, "message": err}

        code = (err.get("code") or "").upper()
        status_map = {
            "NOT_LOGGED_IN": status.HTTP_409_CONFLICT,
            "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
            "SCRAPE_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        http_status = status_map.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(content={"error": err}, status_code=http_status)

    return TikTokSearchResponse(
        results=result.get("results", []),
        totalResults=result.get("totalResults", 0),
        query=result.get("query", ""),
    )
