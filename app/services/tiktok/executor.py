"""
TikTok-specific browsing executor
"""
import asyncio
from typing import Dict, Any, Optional
import scrapling

from app.services.common.executor import AbstractBrowsingExecutor
from app.schemas.tiktok import TikTokSessionConfig


class TiktokExecutor(AbstractBrowsingExecutor):
    """TikTok-specific browsing executor"""
    
    def __init__(self, config: TikTokSessionConfig, proxy: Optional[Dict[str, str]] = None):
        super().__init__(user_data_dir=config.user_data_clones_dir, proxy=proxy)
        self.config = config
        
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
        
        # Initialize Scrapling browser
        self.browser = scrapling.DynamicFetcher(
            browser_type="chrome",
            headless=config["headless"],
            stealth=config["stealth"],
            user_data_dir=config["user_data_dir"],
            proxy=config["proxy"],
            timeout=config["timeout"],
            network_idle_timeout=config["network_idle_timeout"]
        )
        
        # Navigate to TikTok
        await self.browser.get(config["url"])
        
    async def detect_login_state(self, timeout: int = 8) -> str:
        """Detect TikTok login state"""
        from app.services.tiktok.utils.login_detection import LoginDetector
        
        detector = LoginDetector(self.browser, self.config)
        return await detector.detect_login_state(timeout=timeout)
    
    async def navigate_to_profile(self) -> None:
        """Navigate to user profile page"""
        profile_url = f"{self.config.tiktok_url.rstrip('/')}/@me"
        await self.browser.get(profile_url)
        
    async def search_hashtag(self, hashtag: str) -> None:
        """Search for a hashtag"""
        # Find search bar
        search_bar = await self.browser.find('input[type="search"]', timeout=5000)
        if not search_bar:
            # Alternative: find by placeholder text
            search_bar = await self.browser.find('input[placeholder*="search"]', timeout=5000)
            
        if search_bar:
            await search_bar.type(hashtag)
            await search_bar.press('Enter')
            
    async def watch_video(self, video_url: str) -> None:
        """Watch a specific video"""
        await self.browser.get(video_url)
        # Wait for video to load
        await asyncio.sleep(2)
        
    async def like_post(self) -> bool:
        """Like the current post"""
        try:
            like_button = await self.browser.find('button[aria-label*="like"]', timeout=3000)
            if like_button:
                await like_button.click()
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception:
            return False
            
    async def follow_user(self, username: str) -> bool:
        """Follow a user"""
        try:
            profile_url = f"{self.config.tiktok_url.rstrip('/')}/@{username}"
            await self.browser.get(profile_url)
            
            follow_button = await self.browser.find('button[aria-label*="Follow"]', timeout=3000)
            if follow_button:
                await follow_button.click()
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception:
            return False
            
    async def get_video_info(self) -> Dict[str, Any]:
        """Get information about the currently viewed video"""
        try:
            # Get video title
            title = await self.browser.find('h1[data-e2e="video-title"]')
            title_text = await title.text() if title else ""
            
            # Get video description
            description = await self.browser.find('div[data-e2e="video-description"]')
            desc_text = await description.text() if description else ""
            
            # Get author information
            author = await self.browser.find('a[role="link"] span[dir="auto"]')
            author_text = await author.text() if author else ""
            
            # Get like count
            likes = await self.browser.find('span[dir="auto"]')
            likes_text = await likes.text() if likes else "0"
            
            return {
                "title": title_text,
                "description": desc_text,
                "author": author_text,
                "likes": likes_text,
                "url": self.browser.url if self.browser else ""
            }
        except Exception as e:
            return {"error": str(e)}
            
    async def interact_with_page(self, action: str, **kwargs) -> Any:
        """Perform various interactive actions"""
        actions = {
            "scroll_down": self._scroll_down,
            "scroll_up": self._scroll_up,
            "refresh": self._refresh,
            "wait": self._wait,
            "click_element": self._click_element,
            "type_text": self._type_text
        }
        
        if action not in actions:
            raise ValueError(f"Unknown action: {action}")
            
        return await actions[action](**kwargs)
        
    async def _scroll_down(self, pixels: int = 300) -> None:
        """Scroll down by specified pixels"""
        await self.browser.execute(f"window.scrollBy(0, {pixels})")
        await asyncio.sleep(1)
        
    async def _scroll_up(self, pixels: int = 300) -> None:
        """Scroll up by specified pixels"""
        await self.browser.execute(f"window.scrollBy(0, {-pixels})")
        await asyncio.sleep(1)
        
    async def _refresh(self) -> None:
        """Refresh the current page"""
        await self.browser.reload()
        
    async def _wait(self, seconds: float = 2) -> None:
        """Wait for specified seconds"""
        await asyncio.sleep(seconds)
        
    async def _click_element(self, selector: str, timeout: int = 5000) -> bool:
        """Click element matching selector"""
        try:
            element = await self.browser.find(selector, timeout=timeout)
            if element:
                await element.click()
                return True
            return False
        except Exception:
            return False
            
    async def _type_text(self, selector: str, text: str, timeout: int = 5000) -> bool:
        """Type text into element matching selector"""
        try:
            element = await self.browser.find(selector, timeout=timeout)
            if element:
                await element.type(text)
                return True
            return False
        except Exception:
            return False
            
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                
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
        try:
            return self.browser is not None and await self.browser.is_visible('body')
        except Exception:
            return False