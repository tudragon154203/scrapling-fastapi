from fastapi import APIRouter

from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.services.crawler.generic import crawl_generic


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



