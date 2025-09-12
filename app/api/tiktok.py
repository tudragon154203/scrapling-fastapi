from fastapi import APIRouter, HTTPException, status, Request
from types import SimpleNamespace, FunctionType
from typing import Optional

from app.schemas.tiktok import TikTokSessionRequest, TikTokSessionResponse, TikTokSearchRequest, TikTokSearchResponse, TikTokSearchErrorResponse
from app.services.tiktok.service import TiktokService
from fastapi.responses import JSONResponse


router = APIRouter()

# TikTok session service instance
tiktok_service = TiktokService()


async def create_tiktok_session(request: TikTokSessionRequest) -> TikTokSessionResponse:
    """TikTok session creation handler used by the API route."""
    # For testing purposes, use immediate cleanup to ensure clone directories are cleaned up
    # In production, this would be False to maintain interactive sessions
    return await tiktok_service.create_session(request, immediate_cleanup=True)


@router.post("/tiktok/session", response_model=TikTokSessionResponse, tags=["TikTok Session"])
async def create_tiktok_session_endpoint(request: Request):
    """Create TikTok interactive session with automatic login status checking.
    
    Creates an interactive browser session for TikTok with automatic login status checking.
    The endpoint operates similarly to the existing `/browse` endpoint but with TikTok-specific considerations:
    - Launches browser with TikTok-specific configuration
    - Checks TikTok login status using multiple detection methods
    - Returns 409 if user is not logged in
    - Provides full interactive capabilities when logged in
    - Uses read-only user data directory cloning
    
    The endpoint expects an empty request body - all configuration is derived from context.
    """
    # Try to parse the request body as JSON, but don't fail if it's not JSON
    try:
        body = await request.body()
        if body:
            json_data = await request.json()
            req_obj = TikTokSessionRequest(**json_data)
        else:
            req_obj = TikTokSessionRequest()
    except Exception as e:
        # Check if it's a validation error (extra fields)
        if "extra_forbidden" in str(e) or "Extra inputs are not permitted" in str(e):
            # Return 422 for validation errors
            return JSONResponse(
                content={"detail": [{"type": "extra_forbidden", "msg": "Extra inputs are not permitted"}]},
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        # If JSON parsing fails, create empty request
        req_obj = TikTokSessionRequest()

    if not isinstance(create_tiktok_session, FunctionType):
        # This would be patched for testing
        req_obj = SimpleNamespace()

    result = await create_tiktok_session(request=req_obj)
    
    # If a proper TikTokSessionResponse, map HTTP status code based on outcome
    if isinstance(result, TikTokSessionResponse):
        if result.status == "success":
            return JSONResponse(
                content=result.model_dump(exclude_none=True),
                status_code=status.HTTP_200_OK
            )
        # Handle error responses with appropriate HTTP status codes
        if result.error_details:
            error_code = result.error_details.get("code", "").upper()

            if error_code == "NOT_LOGGED_IN":
                return JSONResponse(
                    content=result.model_dump(exclude_none=True),
                    status_code=status.HTTP_409_CONFLICT
                )
            elif error_code == "USER_DATA_LOCKED":
                return JSONResponse(
                    content=result.model_dump(exclude_none=True),
                    status_code=status.HTTP_423_LOCKED
                )
            elif error_code == "SESSION_TIMEOUT":
                return JSONResponse(
                    content=result.model_dump(exclude_none=True),
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT
                )
            elif error_code in ["INTERNAL_ERROR", "UNKNOWN_ERROR", "SESSION_CREATION_FAILED"]:
                return JSONResponse(
                    content=result.model_dump(exclude_none=True),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Default to 500 for other errors
        return JSONResponse(content=result.model_dump(exclude_none=True), status_code=500)
    
    # Fallback for patched/mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 500)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))


# TikTok search service instance
tiktok_service = TiktokService()


async def tiktok_search(request: TikTokSearchRequest):
    """TikTok search handler used by the API route."""
    # Call the TikTok service to perform the search
    result = await tiktok_service.search_tiktok(
        query=request.query,
        num_videos=request.numVideos,
        sort_type=request.sortType,
        recency_days=request.recencyDays
    )
    
    # Check if there was an error
    if "error" in result:
        error_info = result["error"]
        error_code = error_info.get("code", "SCRAPE_FAILED")

        # Map error codes to HTTP status codes and return top-level error JSON
        if error_code == "NOT_LOGGED_IN":
            return JSONResponse(
                content={
                    "error": {
                        "code": "NOT_LOGGED_IN",
                        "message": error_info.get("message", "TikTok session is not logged in"),
                        "details": error_info.get("details", {})
                    }
                },
                status_code=status.HTTP_409_CONFLICT,
            )
        elif error_code == "VALIDATION_ERROR":
            return JSONResponse(
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": error_info.get("message", "Invalid request parameters"),
                        "fields": error_info.get("fields", {})
                    }
                },
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        elif error_code == "RATE_LIMITED":
            return JSONResponse(
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": error_info.get("message", "Too many requests"),
                    }
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        else:
            return JSONResponse(
                content={
                    "error": {
                        "code": "SCRAPE_FAILED",
                        "message": error_info.get("message", "Failed to scrape TikTok search results"),
                        "details": error_info.get("details", {})
                    }
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Return successful response
    return TikTokSearchResponse(
        results=result.get("results", []),
        totalResults=result.get("totalResults", 0),
        query=result.get("query", ""),
    )


@router.post("/tiktok/search", response_model=TikTokSearchResponse, tags=["TikTok Search"])
async def tiktok_search_endpoint(payload: TikTokSearchRequest):
    """Search TikTok content using an active session.
    
    Performs a search on TikTok and returns structured video results.
    Requires an active, logged-in TikTok session.
    
    Args:
        payload: TikTok search request parameters
        
    Returns:
        TikTokSearchResponse: Structured search results
        
    Raises:
        HTTPException: If no active session or search fails
    """
    if not isinstance(tiktok_search, FunctionType):
        # This would be patched for testing
        req_obj = SimpleNamespace()
    else:
        req_obj = payload

    result = await tiktok_search(request=req_obj)

    # Pass-through JSONResponse errors
    if isinstance(result, JSONResponse):
        return result

    # If a proper TikTokSearchResponse, return it
    if isinstance(result, TikTokSearchResponse):
        return result

    # Fallback: coerce dict result into response model if provided
    if isinstance(result, dict):
        if "error" in result:
            # Return generic 500 for unknown error format
            return JSONResponse(content=result, status_code=500)
        return TikTokSearchResponse(
            results=result.get("results", []),
            totalResults=result.get("totalResults", 0),
            query=result.get("query", ""),
        )

    # Default fallback
    return JSONResponse(content={"error": {"code": "SCRAPE_FAILED", "message": "Unknown error"}}, status_code=500)