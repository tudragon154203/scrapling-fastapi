import logging
import app.core.config as app_config
from app.schemas.crawl import CrawlRequest
from app.schemas.toplogistics import TopLogisticsCrawlRequest, TopLogisticsCrawlResponse
from app.services.common.engine import CrawlerEngine
from urllib.parse import quote

logger = logging.getLogger(__name__)
TOPLOGISTICS_BASE = "https://imshk.toplogistics.com.au/customerService/imparcelTracking"


def extract_tracking_code(raw: str) -> str:
    """Extract tracking code from either a bare code or search URL.

    Args:
        raw: Raw input string, either a tracking code or search URL

    Returns:
        Normalized tracking code

    Raises:
        ValueError: If tracking code cannot be extracted
    """
    if not raw or not isinstance(raw, str):
        raise ValueError('tracking_code must be a non-empty string')

    raw_stripped = raw.strip()
    if not raw_stripped:
        raise ValueError('tracking_code must be a non-empty string')

    # If a URL is provided, extract the 's' parameter
    if raw_stripped.startswith("http://") or raw_stripped.startswith("https://"):
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(raw_stripped)
            query_params = parse_qs(parsed.query or "")
            s_params = query_params.get('s', [])
            if s_params and s_params[0].strip():
                return s_params[0].strip()
            raise ValueError("Invalid TopLogistics search URL: could not extract 's' parameter")
        except Exception as e:
            raise ValueError(str(e))

    return raw_stripped


def build_tracking_url(code: str) -> str:
    """Build the canonical TopLogistics tracking URL from a tracking code.

    Args:
        code: The tracking code

    Returns:
        The canonical tracking URL
    """
    encoded_code = quote(code.strip())
    return f"{TOPLOGISTICS_BASE}?s={encoded_code}"


class TopLogisticsCrawler:
    """TopLogistics-specific crawler that uses the CrawlerEngine."""

    def __init__(self, engine: CrawlerEngine = None):
        self.engine = engine or CrawlerEngine.from_settings(app_config.get_settings())

    def run(self, request: TopLogisticsCrawlRequest) -> TopLogisticsCrawlResponse:
        """Run a TopLogistics crawl request."""
        logger.info(f"Running TopLogistics crawl for tracking code: {request.tracking_code}")

        # Convert TopLogisticsCrawlRequest to CrawlRequest
        crawl_request = self._convert_toplogistics_to_crawl_request(request)

        logger.info(f"Built canonical URL: {crawl_request.url}")

        # Execute crawl with engine
        crawl_response = self.engine.run(crawl_request)

        # Normalize 'error' status to 'failure' to match schema expectations
        normalized_status = "failure" if crawl_response.status == "error" else crawl_response.status

        logger.info(
            f"TopLogistics crawl completed with status: {normalized_status}, "
            f"headful: {request.force_headful}, "
            f"user_data: {request.force_user_data}"
        )

        return TopLogisticsCrawlResponse(
            status=normalized_status,
            tracking_code=request.tracking_code,
            html=crawl_response.html,
            message=crawl_response.message,
        )

    def _convert_toplogistics_to_crawl_request(self, toplogistics_request: TopLogisticsCrawlRequest) -> CrawlRequest:
        """Convert TopLogistics request to generic crawl request."""
        # Build canonical tracking URL
        tracking_url = build_tracking_url(toplogistics_request.tracking_code)

        return CrawlRequest(
            url=tracking_url,
            network_idle=True,
            force_headful=toplogistics_request.force_headful,
            force_user_data=toplogistics_request.force_user_data,
            timeout_seconds=25,  # As specified in PRD
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )