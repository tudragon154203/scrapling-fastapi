import logging
from typing import Dict, Any

import app.core.config as app_config
from app.schemas.auspost import AuspostCrawlRequest, AuspostCrawlResponse
from app.schemas.crawl import CrawlRequest, CrawlResponse

from .executors.retry import execute_crawl_with_retries
from .executors.single import crawl_single_attempt
 

logger = logging.getLogger(__name__)

# AusPost tracking search URL
AUSPOST_TRACKING_PAGE = "https://auspost.com.au/mypost/track/search"
# Selector that exists on the details page when result loads
AUSPOST_DETAILS_SELECTOR = "h3#trackingPanelHeading"


def _make_auspost_page_action(tracking_code: str):
    def _go_to_auspost_details(page):
        """Playwright page_action for AusPost tracking automation.

        - Waits for the tracking search input
        - Enters the tracking number and submits
        - Handles "Verifying the device..." interstitial if it appears
        - Waits for details URL and selector to appear
        """
        # Use stable data-testid values from the current markup
        input_locator = page.locator('input[data-testid="SearchBarInput"]').first

        # Ensure the search page is interactive
        input_locator.wait_for(state="visible")
        input_locator.click()
        input_locator.fill(tracking_code)

        # Prefer clicking the Track button using its data-testid
        try:
            track_btn = page.locator('button[data-testid="SearchButton"]').first
            track_btn.wait_for(state="visible", timeout=5_000)
            track_btn.click()
        except Exception:
            # Fallback: press Enter
            page.keyboard.press("Enter")

        # Handle AusPost "Verifying the device..." interstitial if it appears
        try:
            verifying = page.locator("text=Verifying the device")
            verifying.first.wait_for(state="visible", timeout=4_000)
            # Wait until verification finishes
            verifying.first.wait_for(state="hidden", timeout=20_000)
            page.wait_for_load_state(state="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle")
            except Exception:
                pass
        except Exception:
            pass

        # If the site navigates to a details URL, wait for it
        try:
            page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
        except Exception:
            # Some flows may require clicking a Track/Search button instead
            try:
                btn = page.locator('button:has-text("Track"), button:has-text("Search")').first
                btn.wait_for(state="visible", timeout=5_000)
                btn.click()
                try:
                    page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
                except Exception:
                    pass
            except Exception:
                pass

        # If still on search page after verification, try one more submit (cookie now set)
        try:
            if "/mypost/track/search" in (page.url or "") and not page.locator(AUSPOST_DETAILS_SELECTOR).first.is_visible():
                input_locator.fill(tracking_code)
                try:
                    track_btn = page.locator('button[data-testid="SearchButton"]').first
                    track_btn.wait_for(state="visible", timeout=5_000)
                    track_btn.click()
                except Exception:
                    page.keyboard.press("Enter")
                try:
                    page.wait_for_url("**/mypost/track/details/**", timeout=15_000)
                except Exception:
                    pass
        except Exception:
            pass

        # Safety wait for the details header to appear (in addition to engine wait_selector)
        try:
            page.locator(AUSPOST_DETAILS_SELECTOR).first.wait_for(state="visible", timeout=15_000)
        except Exception:
            pass

        return page
    return _go_to_auspost_details


def _convert_auspost_to_crawl_request(auspost_request: AuspostCrawlRequest) -> CrawlRequest:
    """Convert AusPost request to generic crawl request.
    
    Builds a CrawlRequest with the AusPost search URL and sensible defaults.
    Page automation (form fill/submit) is supplied at execution time via
    the `page_action` argument of the executors.
    """
    # Provide conservative defaults; executors will merge with settings
    return CrawlRequest(
        url=AUSPOST_TRACKING_PAGE,
        x_force_headful=auspost_request.x_force_headful,
        x_force_user_data=auspost_request.x_force_user_data,
        # Wait for the details header to ensure content loaded
        wait_selector=AUSPOST_DETAILS_SELECTOR,
        wait_selector_state="visible",
        # Prefer network idle to stabilize dynamic content
        network_idle=True,
        # Use service default timeout if not set in settings
        timeout_ms=None,
    )


def _convert_crawl_to_auspost_response(
    crawl_response: CrawlResponse, 
    tracking_code: str
) -> AuspostCrawlResponse:
    """Convert generic crawl response to AusPost-specific response.
    
    Args:
        crawl_response: The generic crawl response
        tracking_code: Original tracking code for echo
        
    Returns:
        AusPost-specific response with tracking code echo
    """
    return AuspostCrawlResponse(
        status=crawl_response.status,
        tracking_code=tracking_code,
        html=crawl_response.html,
        message=crawl_response.message
    )




def crawl_auspost(request: AuspostCrawlRequest) -> AuspostCrawlResponse:
    """Crawl AusPost tracking page for the given tracking code.
    
    This function reuses the existing generic crawl infrastructure with retry
    and proxy support, converting the AusPost-specific request to a generic one
    and performing the page action automation from the demo.
    
    Args:
        request: AusPost crawl request containing tracking code and options
        
    Returns:
        AusPost crawl response with status, tracking code, and HTML/error message
    """
    settings = app_config.get_settings()

    # Log the tracking request (with redacted tracking code for privacy)
    redacted_code = request.tracking_code[:4] + "***" if len(request.tracking_code) > 4 else "***"
    logger.info(f"AusPost tracking request for code: {redacted_code}")
    
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
        # Convert to generic crawl request
        crawl_request = _convert_auspost_to_crawl_request(request)

        # Execute with page_action to automate the AusPost flow
        def _run_with_executor() -> CrawlResponse:
            if settings.max_retries <= 1:
                return crawl_single_attempt(crawl_request, page_action=_make_auspost_page_action(request.tracking_code))
            else:
                return execute_crawl_with_retries(crawl_request, page_action=_make_auspost_page_action(request.tracking_code))

        try:
            crawl_response = _run_with_executor()
        except Exception as e:
            # Retry once disabling geoip if MaxMind DB not available
            if "InvalidDatabaseError" in str(type(e)) or "GeoLite2-City.mmdb" in str(e):
                logger.info("GeoIP database error, retrying without geoip")
                original_geoip = getattr(settings, "camoufox_geoip", True)
                try:
                    setattr(settings, "camoufox_geoip", False)
                    crawl_response = _run_with_executor()
                finally:
                    setattr(settings, "camoufox_geoip", original_geoip)
            else:
                raise

        # Convert back to AusPost-specific response
        auspost_response = _convert_crawl_to_auspost_response(crawl_response, request.tracking_code)

        # Log outcome
        if auspost_response.status == "success":
            html_length = len(auspost_response.html) if auspost_response.html else 0
            logger.info(f"AusPost tracking successful, HTML length: {html_length}")
            # Check if the details selector is actually present in the HTML
            if auspost_response.html:
                html_lower = auspost_response.html.lower()
                if ("id=\"trackingpanelheading\"" not in html_lower) and ("trackingpanelheading" not in html_lower):
                    auspost_response = AuspostCrawlResponse(
                        status="failure",
                        tracking_code=request.tracking_code,
                        html=auspost_response.html,
                        message="AusPost page loaded but details content missing",
                    )
        else:
            logger.info(f"AusPost tracking failed: {auspost_response.message}")
        
        return auspost_response
        
    except Exception as e:
        error_msg = f"Exception during AusPost crawl: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return AuspostCrawlResponse(
            status="failure",
            tracking_code=request.tracking_code,
            html=None,
            message=error_msg
        )
