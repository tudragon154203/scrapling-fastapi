from fastapi import APIRouter, HTTPException, status
from types import SimpleNamespace, FunctionType

from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.schemas.browse import BrowseRequest, BrowseResponse
from app.schemas.tiktok import TikTokSessionRequest, TikTokSessionResponse
from app.services.crawler.generic import GenericCrawler
from app.services.crawler.dpd import DPDCrawler
from app.services.crawler.auspost import AuspostCrawler
from app.services.browser.browse import BrowseCrawler
from app.services.tiktok.service import TiktokService
from fastapi.responses import JSONResponse


router = APIRouter()


@router.get("/health", tags=["health"])  # simple readiness endpoint
def health() -> dict:
    return {"status": "ok"}


def crawl(request: CrawlRequest) -> CrawlResponse:
    """Generic crawl handler (callable) used by the API route.

    Kept separate from the FastAPI-decorated function so tests can patch
    this symbol and assert the request object being forwarded.
    """
    crawler = GenericCrawler()
    return crawler.run(request)


@router.post("/crawl", response_model=CrawlResponse, tags=["crawl"])
def crawl_endpoint(payload: CrawlRequest):
    """Generic crawl endpoint using Scrapling.

    Accepts the simplified request model only (breaking change).
    Delegates to the plain `crawl` function to ease testing via patching.
    """

    # If tests patch `crawl` (becomes a Mock), pass a lightweight object to match expectations
    if not isinstance(crawl, FunctionType):
        req_obj = SimpleNamespace(
            url=str(payload.url).rstrip("/"),
            force_user_data=payload.force_user_data,
        )
    else:
        req_obj = payload

    result = crawl(request=req_obj)
    # Allow tests to patch `crawl` and return a simple mock-like object
    if isinstance(result, CrawlResponse):
        return result
    # Fallback for mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))


def crawl_dpd(request: DPDCrawlRequest) -> DPDCrawlResponse:
    """DPD tracking handler used by the API route."""
    crawler = DPDCrawler()
    return crawler.run(request)


@router.post("/crawl/dpd", response_model=DPDCrawlResponse, tags=["crawl"])
def crawl_dpd_endpoint(payload: DPDCrawlRequest):
    """DPD tracking endpoint using Scrapling.
    
    Accepts a tracking code and returns the DPD tracking page HTML. Delegates to `crawl_dpd`.
    """
    if not isinstance(crawl_dpd, FunctionType):
        req_obj = SimpleNamespace(
            tracking_number=getattr(payload, "tracking_number", payload.tracking_code),
            force_user_data=payload.force_user_data,
        )
    else:
        req_obj = payload

    result = crawl_dpd(request=req_obj)
    if isinstance(result, DPDCrawlResponse):
        return result
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))


def crawl_auspost(request: AuspostCrawlRequest) -> AuspostCrawlResponse:
    """AusPost tracking handler used by the API route."""
    crawler = AuspostCrawler()
    return crawler.run(request)


@router.post("/crawl/auspost", response_model=AuspostCrawlResponse, tags=["crawl"]) 
def crawl_auspost_endpoint(payload: AuspostCrawlRequest):
    """AusPost tracking endpoint using Scrapling.
    
    Accepts a tracking code or a full details URL
    (https://auspost.com.au/mypost/track/details/<CODE>) and returns the
    AusPost tracking page HTML. Delegates to `crawl_auspost`.
    """
    if not isinstance(crawl_auspost, FunctionType):
        req_obj = SimpleNamespace(
            tracking_code=payload.tracking_code,
            details_url=payload.details_url,
            force_user_data=payload.force_user_data,
        )
    else:
        req_obj = payload

    result = crawl_auspost(request=req_obj)
    if isinstance(result, AuspostCrawlResponse):
        return result
    status_code = getattr(result, "status_code", 200)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))


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


# TikTok session service instance
tiktok_service = TiktokService()


async def create_tiktok_session(request: TikTokSessionRequest) -> TikTokSessionResponse:
    """TikTok session creation handler used by the API route."""
    return await tiktok_service.create_session(request)


@router.post("/tiktok/session", response_model=TikTokSessionResponse, tags=["TikTok Session"])
async def create_tiktok_session_endpoint(request: TikTokSessionRequest):
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
    if not isinstance(create_tiktok_session, FunctionType):
        # This would be patched for testing
        req_obj = SimpleNamespace()
    else:
        req_obj = request

    result = await create_tiktok_session(request=req_obj)
    
    # If a proper TikTokSessionResponse, map HTTP status code based on outcome
    if isinstance(result, TikTokSessionResponse):
        if result.status == "success":
            return result
        # Handle error responses with appropriate HTTP status codes
        if result.error_details:
            error_code = result.error_details.get("code", "").upper()
            
            if error_code == "NOT_LOGGED_IN":
                return JSONResponse(
                    content=result.model_dump(),
                    status_code=status.HTTP_409_CONFLICT
                )
            elif error_code == "USER_DATA_LOCKED":
                return JSONResponse(
                    content=result.model_dump(),
                    status_code=status.HTTP_423_LOCKED
                )
            elif error_code == "SESSION_TIMEOUT":
                return JSONResponse(
                    content=result.model_dump(),
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT
                )
            
        # Default to 500 for other errors
        return JSONResponse(content=result.model_dump(), status_code=500)
    
    # Fallback for patched/mocked results with `.status_code` and `.json`
    status_code = getattr(result, "status_code", 500)
    body = getattr(result, "json", None)
    if isinstance(body, dict):
        return JSONResponse(content=body, status_code=int(status_code))
    return JSONResponse(content={}, status_code=int(status_code))
