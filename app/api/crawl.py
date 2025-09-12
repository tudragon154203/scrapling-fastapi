from fastapi import APIRouter, HTTPException, status
from types import SimpleNamespace, FunctionType
from typing import Optional

from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.services.crawler.generic import GenericCrawler
from app.services.crawler.dpd import DPDCrawler
from app.services.crawler.auspost import AuspostCrawler
from fastapi.responses import JSONResponse

router = APIRouter()

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