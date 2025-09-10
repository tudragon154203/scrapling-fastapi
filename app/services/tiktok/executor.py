"""
TikTok-specific browsing executor
"""
import asyncio
from typing import Dict, Any, Optional
import types

from app.services.common.executor import AbstractBrowsingExecutor
from app.schemas.tiktok import TikTokSessionConfig
from app.core.config import get_settings


class TiktokExecutor(AbstractBrowsingExecutor):
    """TikTok-specific browsing executor"""
    
    def __init__(self, config: TikTokSessionConfig, proxy: Optional[Dict[str, str]] = None):
        super().__init__(user_data_dir=config.user_data_clones_dir, proxy=proxy)
        self.config = config
        self.settings = get_settings()
        
    async def get_config(self) -> Dict[str, Any]:
        """Get TikTok-specific browser configuration"""
        return {
            "url": self.config.tiktok_url,
            "headless": True,
            "stealth": True,
            "user_data_dir": self.user_data_dir,
            "proxy": self.proxy,
            "timeout": 30000,
            "network_idle_timeout": 10000
        }
    
    async def setup_browser(self) -> None:
        """Setup browser with TikTok-specific configuration"""
        config = await self.get_config()
        
        # Create a simple mock browser object for basic session functionality
        # This avoids the Playwright subprocess issues on Windows
        self.browser = types.SimpleNamespace()
        self.browser.url = config["url"]
        self.browser.is_visible = lambda selector: True
        self.browser.find = lambda selector, timeout=5000: None
        self.browser.reload = lambda: None
        self.browser.execute = lambda script: None
        
        # Log that we're using mock browser mode
        print(f"Using mock browser for TikTok session: {config['url']}")
        
    async def detect_login_state(self, timeout: int = 8) -> str:
        """Detect TikTok login state"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        
        # For now, return uncertain state since we don't have a real browser
        return "uncertain"
    
    async def navigate_to_profile(self) -> None:
        """Navigate to user profile page"""
        # Not implemented with StealthyFetcher approach
        pass
        
    async def search_hashtag(self, hashtag: str) -> None:
        """Search for a hashtag"""
        # Not implemented with StealthyFetcher approach
        pass
            
    async def watch_video(self, video_url: str) -> None:
        """Watch a specific video"""
        # Not implemented with StealthyFetcher approach
        pass
        
    async def like_post(self) -> bool:
        """Like the current post"""
        # Not implemented with StealthyFetcher approach
        return False
            
    async def follow_user(self, username: str) -> bool:
        """Follow a user"""
        # Not implemented with StealthyFetcher approach
        return False
            
    async def get_video_info(self) -> Dict[str, Any]:
        """Get information about the currently viewed video"""
        # Return minimal info since we don't have a real browser
        return {
            "title": "",
            "description": "",
            "author": "",
            "likes": "0",
            "url": self.browser.url if hasattr(self.browser, 'url') else ""
        }
            
    async def interact_with_page(self, action: str, **kwargs) -> Any:
        """Perform various interactive actions"""
        # Only support wait action for now
        if action == "wait":
            return await self._wait(**kwargs)
        raise ValueError(f"Unknown action: {action}")
        
    async def _wait(self, seconds: float = 2) -> None:
        """Wait for specified seconds"""
        await asyncio.sleep(seconds)
            
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        try:
            # Clean up cloned user data directory
            if self.user_data_dir and "temp_" in self.user_data_dir:
                import shutil
                import os
                try:
                    shutil.rmtree(self.user_data_dir)
                except Exception as e:
                    print(f"Failed to clean up temp directory: {e}")
                    
        except Exception as e:
            print(f"Error during cleanup: {e}")
            
    async def close(self) -> None:
        """Close the current session"""
        await self.cleanup()
        
    async def is_still_active(self) -> bool:
        """Check if the browser session is still active"""
        # Always return True for basic functionality
        return True