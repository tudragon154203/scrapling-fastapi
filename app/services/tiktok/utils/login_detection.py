"""
TikTok login detection utilities
"""
import asyncio
from typing import Dict, Any, Optional, Literal
from enum import Enum

import scrapling

from app.schemas.tiktok import TikTokLoginState, TikTokSessionConfig


class LoginDetectionMethod(str, Enum):
    """Login detection methods"""
    DOM_ELEMENT = "dom_element"
    API_REQUEST = "api_request"
    FALLBACK_REFRESH = "fallback_refresh"
    COMBO = "combo"


class LoginDetector:
    """TikTok login state detector"""
    
    def __init__(self, browser: scrapling.DynamicFetcher, config: TikTokSessionConfig):
        self.browser = browser
        self.config = config
        self.selectors = config.selectors
        self.api_endpoints = config.api_endpoints
        
    async def detect_login_state(self, timeout: int = 8) -> TikTokLoginState:
        """
        Detect TikTok login state using multiple methods with fallback
        
        Args:
            timeout: Maximum time to spend on detection
            
        Returns:
            TikTokLoginState: LOGGED_IN, LOGGED_OUT, or UNCERTAIN
        """
        start_time = asyncio.get_event_loop().time()
        
        # Try primary methods first
        result = await self._try_combo_detection(timeout - (asyncio.get_event_loop().time() - start_time))
        
        if result != TikTokLoginState.UNCERTAIN:
            return result
            
        # If uncertain, try fallback refresh if enabled
        if self.config.login_detection_refresh:
            return await self._try_fallback_refresh(timeout - (asyncio.get_event_loop().time() - start_time))
            
        return TikTokLoginState.UNCERTAIN
    
    async def _try_combo_detection(self, timeout: float) -> TikTokLoginState:
        """Try multiple detection methods in parallel"""
        start_time = asyncio.get_event_loop().time()
        
        # Run DOM detection and API detection in parallel
        dom_task = asyncio.create_task(self._detect_dom_elements(timeout/2))
        api_task = asyncio.create_task(self._detect_api_requests(timeout/2))
        
        try:
            dom_result, api_result = await asyncio.wait_for(
                asyncio.gather(dom_task, api_task),
                timeout=timeout
            )
            
            # If both methods agree, return that result
            if dom_result == api_result:
                return dom_result
                
            # If they disagree, prefer DOM detection
            if dom_result != TikTokLoginState.UNCERTAIN:
                return dom_result
                
            return api_result
            
        except asyncio.TimeoutError:
            return TikTokLoginState.UNCERTAIN
        except Exception:
            return TikTokLoginState.UNCERTAIN
    
    async def _detect_dom_elements(self, timeout: float) -> TikTokLoginState:
        """Detect login state using DOM elements"""
        try:
            # Check for logged-in elements
            logged_in_element = await self.browser.find(
                self.selectors.get("logged_in", "[data-e2e='profile-avatar']"),
                timeout=int(timeout * 1000)
            )
            
            if logged_in_element and await logged_in_element.is_visible():
                return TikTokLoginState.LOGGED_IN
                
            # Check for logged-out elements
            logged_out_element = await self.browser.find(
                self.selectors.get("logged_out", "[data-e2e='login-button']"),
                timeout=int(timeout * 1000)
            )
            
            if logged_out_element and await logged_out_element.is_visible():
                return TikTokLoginState.LOGGED_OUT
                
            return TikTokLoginState.UNCERTAIN
            
        except Exception:
            return TikTokLoginState.UNCERTAIN
    
    async def _detect_api_requests(self, timeout: float) -> TikTokLoginState:
        """Detect login state using API request interception"""
        try:
            # This is a simplified implementation
            # In a real implementation, this would intercept network requests
            # to check for user info endpoints
            
            # Try to access user info page
            user_info_url = f"{self.config.tiktok_url}api/user/info"
            response = await self.browser.request("GET", user_info_url)
            
            # Check response status and content
            if response.status_code == 200:
                # Try to parse JSON response
                try:
                    json_data = response.json()
                    if json_data.get("code") == 0 or json_data.get("status") == "success":
                        return TikTokLoginState.LOGGED_IN
                except Exception:
                    pass
                    
            return TikTokLoginState.LOGGED_OUT
            
        except Exception:
            return TikTokLoginState.UNCERTAIN
    
    async def _try_fallback_refresh(self, timeout: float) -> TikTokLoginState:
        """Try refresh and retry detection method"""
        try:
            # Refresh the page
            await self.browser.reload()
            
            # Wait for page to load
            await asyncio.sleep(1)
            
            # Try detection again with remaining timeout
            return await self._detect_dom_elements(timeout)
            
        except Exception:
            return TikTokLoginState.UNCERTAIN
    
    async def get_detection_details(self) -> Dict[str, Any]:
        """Get detailed information about the detection process"""
        return {
            "selectors_used": self.selectors,
            "api_endpoints_checked": self.api_endpoints,
            "login_detection_enabled": self.config.login_detection_refresh,
            "detection_timeout": self.config.login_detection_timeout
        }
    
    async def update_selectors(self, new_selectors: Dict[str, str]) -> None:
        """Update the CSS selectors used for login detection"""
        self.selectors.update(new_selectors)
        
    async def validate_selectors(self) -> Dict[str, bool]:
        """Validate that all required selectors are present"""
        required_selectors = ["logged_in", "logged_out", "uncertain"]
        validation_results = {}
        
        for selector_name in required_selectors:
            selector = self.selectors.get(selector_name)
            validation_results[selector_name] = selector is not None and len(selector) > 0
            
        return validation_results
    
    async def test_selector(self, selector_name: str) -> bool:
        """Test if a specific selector works on current page"""
        try:
            selector = self.selectors.get(selector_name)
            if not selector:
                return False
                
            element = await self.browser.find(selector, timeout=2000)
            return element is not None
            
        except Exception:
            return False
    
    async def get_login_state_details(self) -> Dict[str, Any]:
        """Get comprehensive login state information"""
        dom_detection = None
        api_detection = None
        
        try:
            dom_detection = await self._detect_dom_elements(2)
        except Exception:
            pass
            
        try:
            api_detection = await self._detect_api_requests(2)
        except Exception:
            pass
            
        return {
            "dom_detection": dom_detection,
            "api_detection": api_detection,
            "browser_url": self.browser.url if self.browser else None,
            "page_title": await self.browser.title() if self.browser else None,
            "detection_method": "combo" if dom_detection and api_detection else "unknown"
        }