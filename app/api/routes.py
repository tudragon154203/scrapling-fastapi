from fastapi import APIRouter

from app.schemas.crawl import CrawlRequest, CrawlResponse
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.services.crawler.generic import GenericCrawler
from app.services.crawler.dpd import DPDCrawler
from app.services.crawler.auspost import AuspostCrawler


router = APIRouter()


@router.get("/health", tags=["health"])  # simple readiness endpoint
def health() -> dict:
    return {"status": "ok"}


@router.post("/crawl", response_model=CrawlResponse, tags=["crawl"])
def crawl(payload: CrawlRequest) -> CrawlResponse:
    """Generic crawl endpoint using Scrapling.

    Accepts the simplified request model only (breaking change).
    """
    crawler = GenericCrawler()
    return crawler.run(payload)


@router.post("/crawl/dpd", response_model=DPDCrawlResponse, tags=["crawl"])
def crawl_dpd_endpoint(payload: DPDCrawlRequest) -> DPDCrawlResponse:
    """DPD tracking endpoint using Scrapling.
    
    Accepts a tracking code and returns the DPD tracking page HTML.
    """
    crawler = DPDCrawler()
    return crawler.run(payload)


@router.post("/crawl/auspost", response_model=AuspostCrawlResponse, tags=["crawl"]) 
def crawl_auspost_endpoint(payload: AuspostCrawlRequest) -> AuspostCrawlResponse:
    """AusPost tracking endpoint using Scrapling.
    
    Accepts a tracking code and returns the AusPost tracking page HTML.
    """
    crawler = AuspostCrawler()
    return crawler.run(payload)

