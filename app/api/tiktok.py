"""Tiktok
=========

Expose the unified Tiktok API surface that covers session management and
search capabilities. Both endpoints are grouped under the same documentation
section to keep the generated OpenAPI docs concise.
"""

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from app.schemas.tiktok.models import TikTokVideo
from app.schemas.tiktok.search import TikTokSearchRequest, TikTokSearchResponse
from app.schemas.tiktok.session import TikTokSessionRequest, TikTokSessionResponse
from app.services.tiktok.session import TiktokService
from app.services.tiktok.search.service import TikTokSearchService
from src.services.browser_mode_service import BrowserModeService


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
    # Determine browser mode based on force_headful parameter
    browser_mode = BrowserModeService.determine_mode(payload.force_headful)

    # Log the force_headful parameter and determined mode for debugging
    print(f"DEBUG: force_headful={payload.force_headful}, browser_mode={browser_mode.value}")

    search_service = TikTokSearchService(strategy=payload.strategy, force_headful=payload.force_headful)
    fields_set = getattr(payload, "model_fields_set", set())
    sort_type_param = payload.sortType if "sortType" in fields_set else None
    recency_days_param = payload.recencyDays if "recencyDays" in fields_set else None

    result = await search_service.search(
        query=payload.query,
        num_videos=payload.numVideos,
        sort_type=sort_type_param,
        recency_days=recency_days_param,
    )

    if "error" in result:
        err = result["error"] or {}
        # Handle both string error messages and structured error objects
        if isinstance(err, str):
            # Convert string error to structured error format
            code = "SCRAPE_FAILED"
            lower_err = err.lower()
            if "not logged" in lower_err or "session" in lower_err:
                code = "NOT_LOGGED_IN"
            elif "validation" in lower_err:
                code = "VALIDATION_ERROR"
            elif "too many request" in lower_err or "rate limit" in lower_err:
                code = "RATE_LIMITED"
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

    raw_results = result.get("results", []) or []
    normalized_results = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        like_count = item.get("likeCount", item.get("likes"))
        try:
            like_count_int = int(like_count)
        except (TypeError, ValueError):
            like_count_int = 0

        author = item.get("authorHandle") or item.get("author") or ""
        if isinstance(author, str):
            author = author.lstrip("@")
        else:
            author = str(author or "")

        video_payload = {
            "id": str(item.get("id") or ""),
            "caption": str(item.get("caption") or item.get("title") or ""),
            "authorHandle": author,
            "likeCount": like_count_int,
            "uploadTime": str(item.get("uploadTime") or item.get("createTime") or ""),
            "webViewUrl": str(item.get("webViewUrl") or item.get("url") or ""),
        }

        try:
            normalized_results.append(TikTokVideo(**video_payload).model_dump())
        except Exception:  # pragma: no cover - defensive against schema updates
            continue

    total_results_raw = result.get("totalResults")
    try:
        total_results = int(total_results_raw)
    except (TypeError, ValueError):
        total_results = len(normalized_results)

    if isinstance(result.get("query"), str):
        normalized_query = result["query"]
    elif isinstance(payload.query, list):
        normalized_query = ", ".join(str(q).strip() for q in payload.query if str(q).strip())
    else:
        normalized_query = str(payload.query)

    response_payload = TikTokSearchResponse(
        results=normalized_results,
        totalResults=total_results,
        query=normalized_query,
        execution_mode=browser_mode.value,
    )
    return response_payload
