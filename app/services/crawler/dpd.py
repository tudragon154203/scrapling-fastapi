import logging
from typing import Dict, Any
from urllib.parse import quote

import app.core.config as app_config
from app.schemas.dpd import DPDCrawlRequest, DPDCrawlResponse
from app.schemas.crawl import CrawlRequest, CrawlResponse

from .executors.retry import execute_crawl_with_retries
from .executors.single import crawl_single_attempt

logger = logging.getLogger(__name__)

# DPD direct status URL base (no form automation required)
DPD_STATUS_BASE = "https://tracking.dpd.de/status/en_US/parcel/"


def build_dpd_url(tracking_code: str) -> str:
    """Build direct DPD status URL for the given tracking code.

    Example: https://tracking.dpd.de/status/en_US/parcel/<code>
    """
    encoded = quote(tracking_code, safe="")
    return f"{DPD_STATUS_BASE}{encoded}"


def _convert_dpd_to_crawl_request(dpd_request: DPDCrawlRequest) -> CrawlRequest:
    """Convert DPD request to generic crawl request.
    
    Args:
        dpd_request: The DPD-specific request
        
    Returns:
        Generic crawl request with DPD URL and converted options
    """
    dpd_url = build_dpd_url(dpd_request.tracking_code)
    
    return CrawlRequest(
        url=dpd_url,
        x_force_headful=dpd_request.x_force_headful,
        x_force_user_data=dpd_request.x_force_user_data,
        # Use reasonable defaults for DPD tracking pages
        timeout_ms=None,  # Use system default
        headless=None,    # Use system default with x_force_headful override
        network_idle=True # For dynamic results after search
    )


def _convert_crawl_to_dpd_response(
    crawl_response: CrawlResponse, 
    tracking_code: str
) -> DPDCrawlResponse:
    """Convert generic crawl response to DPD-specific response.
    
    Args:
        crawl_response: The generic crawl response
        tracking_code: Original tracking code for echo
        
    Returns:
        DPD-specific response with tracking code echo
    """
    return DPDCrawlResponse(
        status=crawl_response.status,
        tracking_code=tracking_code,
        html=crawl_response.html,
        message=crawl_response.message
    )


def crawl_dpd(request: DPDCrawlRequest) -> DPDCrawlResponse:
    """Crawl DPD tracking page for the given tracking code.
    
    This function reuses the existing generic crawl infrastructure with retry
    and proxy support, converting the DPD-specific request to a generic one.
    
    Args:
        request: DPD crawl request containing tracking code and options
        
    Returns:
        DPD crawl response with status, tracking code, and HTML/error message
    """
    settings = app_config.get_settings()
    
    # Log the tracking request (with redacted tracking code for privacy)
    redacted_code = request.tracking_code[:4] + "***" if len(request.tracking_code) > 4 else "***"
    logger.info(f"DPD tracking request for code: {redacted_code}")
    
    # Log headless decision reasoning
    if request.x_force_headful:
        import platform
        if platform.system().lower() == "windows":
            logger.info("x_force_headful=true honored on Windows platform")
        else:
            logger.info("x_force_headful=true ignored on non-Windows platform")
    
    # Log user data decision
    if request.x_force_user_data:
        if settings.camoufox_user_data_dir:
            logger.info("x_force_user_data=true enabled with configured user data directory")
        else:
            logger.info("x_force_user_data=true requested but no user data directory configured")
    
    try:
        # Convert to generic crawl request (parcelstatus?query=...)
        crawl_request = _convert_dpd_to_crawl_request(request)

        # Use the same retry/single strategy as the generic endpoint, no page_action needed
        if settings.max_retries <= 1:
            crawl_response = crawl_single_attempt(crawl_request)
        else:
            crawl_response = execute_crawl_with_retries(crawl_request)
        
        # Convert back to DPD-specific response
        dpd_response = _convert_crawl_to_dpd_response(crawl_response, request.tracking_code)

        # Log outcome
        if dpd_response.status == "success":
            html_length = len(dpd_response.html) if dpd_response.html else 0
            logger.info(f"DPD tracking successful, HTML length: {html_length}")
            # Heuristic error detection based on known messages
            try:
                text = (dpd_response.html or "").lower()
                error_markers = [
                    "nicht finden",  # couldn't find
                    "keine sendung",  # no shipment
                    "bitte prüfen",   # please check your entry
                    "no shipment found",
                    "could not find",
                    "invalid tracking",
                ]
                if any(m in text for m in error_markers):
                    dpd_response = DPDCrawlResponse(
                        status="failure",
                        tracking_code=request.tracking_code,
                        html=dpd_response.html,
                        message="DPD page indicates tracking not found or invalid code",
                    )
            except Exception:
                pass
        else:
            logger.info(f"DPD tracking failed: {dpd_response.message}")
        
        return dpd_response
        
    except Exception as e:
        error_msg = f"Exception during DPD crawl: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return DPDCrawlResponse(
            status="failure",
            tracking_code=request.tracking_code,
            html=None,
            message=error_msg
        )
