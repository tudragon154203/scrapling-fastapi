"""
TikTok-specific browsing executor using ScraplingFetcherAdapter like BrowseExecutor
"""
import sys
import asyncio
from typing import Optional, Dict, Any
from app.services.common.executor import AbstractBrowsingExecutor
from app.schemas.tiktok.session import TikTokSessionConfig
from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter
from app.services.common.adapters.fetch_arg_composer import FetchArgComposer
from app.core.config import get_settings
from app.services.common.browser.camoufox import CamoufoxArgsBuilder
from app.services.tiktok.utils.login_detection import LoginDetector


class TiktokExecutor(AbstractBrowsingExecutor):
    """TikTok-specific browsing executor using ScraplingFetcherAdapter"""

    def __init__(
        self, config: TikTokSessionConfig, proxy: Optional[Dict[str, str]] = None,
        camoufox_builder: Optional[CamoufoxArgsBuilder] = None
    ):
        super().__init__(user_data_dir=config.user_data_clones_dir, proxy=proxy)
        self.config = config
        self.fetcher = ScraplingFetcherAdapter()
        self.arg_composer = FetchArgComposer()
        self.camoufox_builder = camoufox_builder or CamoufoxArgsBuilder()
        self.settings = get_settings()
        self._user_data_cleanup = None

    async def get_config(self) -> Dict[str, Any]:
        """Get TikTok-specific browser configuration"""
        return {
            "url": self.config.tiktok_url,
            "headless": self.config.headless,
            "stealth": True,
            "user_data_dir": self.user_data_dir,
            "proxy": self.proxy,
            # Compose-friendly keys below help trigger HTTP fallback on launch/goto timeouts
            "timeout_seconds": 30,
            "network_idle": False,
            "wait_for_selector": "html",
            "wait_for_selector_state": "visible",
        }

    async def setup_browser(self) -> None:
        """Setup browser with TikTok-specific configuration using ScraplingFetcher"""
        config = await self.get_config()
        # Ensure proper event loop policy on Windows for Playwright
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        # Use ScraplingFetcherAdapter like BrowseExecutor does
        # Create a mock request object with force_user_data=True to trigger CamoufoxArgsBuilder

        class MockRequest:
            force_user_data = True
            force_mute_audio = True
        # Build additional args using CamoufoxArgsBuilder
        additional_args, extra_headers = self.camoufox_builder.build(
            MockRequest(), self.settings, self.fetcher.detect_capabilities()
        )
        # Get cleanup function before it gets filtered out
        self._user_data_cleanup = additional_args.get('_user_data_cleanup')
        fetch_kwargs = self.arg_composer.compose(
            options=config,
            caps=self.fetcher.detect_capabilities(),
            selected_proxy=config.get("proxy"),
            additional_args=additional_args,
            extra_headers=extra_headers,
            settings=self.settings,
            page_action=None
        )
        # Launch browser using ScraplingFetcher - it handles async/sync conflicts internally
        result = self.fetcher.fetch(config["url"], fetch_kwargs)
        # Create browser reference for compatibility
        self.browser = result
        print(f"Using ScraplingFetcher for TikTok session: {config['url']}")

    async def start_session(self) -> None:
        """Start TikTok session using ScraplingFetcher"""
        try:
            # Get browser configuration
            await self.get_config()
            # Setup browser (CamoufoxArgsBuilder will handle user data directory)
            await self.setup_browser()
            self.start_time = asyncio.get_event_loop().time()
            print("TikTok session started")
        except Exception:
            await self._cleanup_on_error()
            raise

    async def cleanup(self) -> None:
        """Cleanup browser resources and user data context"""
        try:
            # Clean up user data context if it exists (from CamoufoxArgsBuilder)
            if self._user_data_cleanup:
                try:
                    self._user_data_cleanup()
                except Exception as e:
                    print(f"Failed to cleanup user data context: {e}")
                self._user_data_cleanup = None
            # Clean up browser resources
            if self.browser:
                try:
                    # For StealthyFetcher result, we might not have a close method
                    # The cleanup is handled by the fetch operation itself
                    pass
                except Exception as e:
                    print(f"Failed to cleanup browser: {e}")
                self.browser = None
        except Exception as e:
            print(f"Error during cleanup: {e}")

    async def detect_login_state(self, timeout: int = 8) -> str:
        """Detect TikTok login state"""
        detector = LoginDetector(self.browser, self.config)
        return await detector.detect_login_state(timeout=timeout)

    async def navigate_to_profile(self) -> None:
        """Navigate to user profile page"""
        # profile_url = f"{self.config.tiktok_url.rstrip('/')}/@me"
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

    async def close(self) -> None:
        """Close the current session"""
        await self.cleanup()

    async def is_still_active(self) -> bool:
        """Check if the browser session is still active"""
        # For StealthyFetcher approach, we can't easily check if browser is still active
        # Return True as long as we have a browser reference
        return self.browser is not None
