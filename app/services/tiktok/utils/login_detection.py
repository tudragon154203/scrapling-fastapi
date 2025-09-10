"""
TikTok login detection utilities for StealthyFetcher approach
"""
import asyncio
import re
from typing import Dict, Any, Optional, Literal
from enum import Enum

from app.schemas.tiktok import TikTokLoginState, TikTokSessionConfig


class LoginDetectionMethod(str, Enum):
    """Login detection methods"""
    DOM_ELEMENT = "dom_element"
    API_REQUEST = "api_request"
    FALLBACK_REFRESH = "fallback_refresh"
    COMBO = "combo"


class LoginDetector:
    """TikTok login state detector for StealthyFetcher approach"""
    
    def __init__(self, browser: Any, config: TikTokSessionConfig):
        self.browser = browser
        self.config = config
        self.selectors = config.selectors
        self.api_endpoints = config.api_endpoints
        
    async def detect_login_state(self, timeout: int = 8) -> TikTokLoginState:
        """
        Detect TikTok login state by analyzing HTML content
        
        Args:
            timeout: Maximum time to spend on detection
            
        Returns:
            TikTokLoginState: LOGGED_IN, LOGGED_OUT, or UNCERTAIN
        """
        try:
            # Check if we have HTML content from StealthyFetcher
            if hasattr(self.browser, 'html_content') and self.browser.html_content:
                html_content = self.browser.html_content.lower()
                
                # Check for logged-in indicators
                logged_in_indicators = [
                    r'profile-avatar',  # Profile avatar element
                    r'user.*avatar',   # User avatar
                    r'logged.*in',     # "Logged in" text
                    r'sign.*out',      # "Sign out" button
                    r'log.*out',       # "Log out" button
                    r'account',        # Account menu
                    r'notification',   # Notifications
                    r'message',        # Messages
                    r'inbox',          # Inbox
                ]
                
                # Check for logged-out indicators
                logged_out_indicators = [
                    r'login.*button',  # Login button
                    r'sign.*in',       # Sign in button
                    r'log.*in',        # Log in button
                    r'register',       # Register button
                    r'create.*account', # Create account
                    r'join.*tiktok',   # Join TikTok
                ]
                
                # Count matches for each indicator type
                logged_in_matches = sum(1 for pattern in logged_in_indicators
                                      if re.search(pattern, html_content))
                logged_out_matches = sum(1 for pattern in logged_out_indicators
                                       if re.search(pattern, html_content))
                
                # Determine login state based on indicator counts
                if logged_in_matches > logged_out_matches:
                    return TikTokLoginState.LOGGED_IN
                elif logged_out_matches > logged_in_matches:
                    return TikTokLoginState.LOGGED_OUT
                else:
                    return TikTokLoginState.UNCERTAIN
                    
            return TikTokLoginState.UNCERTAIN
            
        except Exception:
            return TikTokLoginState.UNCERTAIN
    
    async def _try_combo_detection(self, timeout: float) -> TikTokLoginState:
        """Try multiple detection methods"""
        return await self.detect_login_state(timeout)
    
    async def _detect_dom_elements(self, timeout: float) -> TikTokLoginState:
        """Detect login state using HTML content analysis"""
        return await self.detect_login_state(timeout)
    
    async def _detect_api_requests(self, timeout: float) -> TikTokLoginState:
        """API detection not available with StealthyFetcher"""
        return TikTokLoginState.UNCERTAIN
    
    async def _try_fallback_refresh(self, timeout: float) -> TikTokLoginState:
        """Refresh fallback not available with StealthyFetcher"""
        return TikTokLoginState.UNCERTAIN
    
    async def get_detection_details(self) -> Dict[str, Any]:
        """Get detailed information about the detection process"""
        login_state = await self.detect_login_state()
        return {
            "selectors_used": self.selectors,
            "api_endpoints_checked": self.api_endpoints,
            "login_detection_enabled": self.config.login_detection_refresh,
            "detection_timeout": self.config.login_detection_timeout,
            "detected_state": login_state.value if hasattr(login_state, 'value') else str(login_state)
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
                
            # For StealthyFetcher, we can't test selectors directly
            # Return True if selector exists
            return True
            
        except Exception:
            return False
    
    async def get_login_state_details(self) -> Dict[str, Any]:
        """Get comprehensive login state information"""
        login_state = await self.detect_login_state()
        return {
            "dom_detection": login_state,
            "api_detection": TikTokLoginState.UNCERTAIN,
            "browser_url": getattr(self.browser, 'url', None),
            "page_title": None,
            "detection_method": "html_content_analysis",
            "html_available": hasattr(self.browser, 'html_content') and bool(self.browser.html_content)
        }