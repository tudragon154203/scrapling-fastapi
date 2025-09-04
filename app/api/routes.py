from fastapi import APIRouter

from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.services.crawler.generic import crawl_generic
from app.services.crawler.dpd import crawl_dpd


router = APIRouter()


@router.get("/health", tags=["health"])  # simple readiness endpoint
def health() -> dict:
    return {"status": "ok"}


@router.post("/crawl", response_model=CrawlResponse, tags=["crawl"])
def crawl(payload: CrawlRequest) -> CrawlResponse:
    """Generic crawl endpoint using Scrapling.

    Accepts both new and legacy field names to ease migration.
    """
    return crawl_generic(payload)


@router.post("/crawl/dpd", response_model=DPDCrawlResponse, tags=["crawl"])
def crawl_dpd_endpoint(payload: DPDCrawlRequest) -> DPDCrawlResponse:
    """DPD tracking endpoint using Scrapling.
    
    Accepts a tracking code and returns the DPD tracking page HTML.
    Supports legacy compatibility flags for headless and user data control.
    """
    return crawl_dpd(payload)



