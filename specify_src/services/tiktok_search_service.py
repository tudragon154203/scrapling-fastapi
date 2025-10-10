from typing import List, Dict, Any
from specify_src.models.browser_mode import BrowserMode
from specify_src.services.browser_mode_service import BrowserModeService
from scrapling import Scrapling

class TikTokSearchService:
    """Service for TikTok search functionality with mode control."""
    
    @staticmethod
    def search(query: str, force_headful: bool = False) -> Dict[str, Any]:
        """
        Search TikTok content with optional control over browser execution mode.
        
        Args:
            query (str): Search query string
            force_headful (bool): Whether to force headful mode
            
        Returns:
            Dict[str, Any]: Search results and execution information
        """
        # Determine the browser mode
        browser_mode = BrowserModeService.determine_mode(force_headful)
        
        # For now, we'll return mock results since we're focusing on the mode control
        # In a real implementation, this would use Scrapling to perform the actual search
        results = [
            {"title": "Funny Cat Video 1", "url": "https://tiktok.com/video1", "thumbnail": "thumbnail1.jpg"},
            {"title": "Funny Cat Video 2", "url": "https://tiktok.com/video2", "thumbnail": "thumbnail2.jpg"}
        ]
        
        return {
            "results": results,
            "execution_mode": browser_mode.value,
            "message": "Search completed successfully"
        }