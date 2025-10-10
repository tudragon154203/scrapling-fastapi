from specify_src.models.browser_mode import BrowserMode
from specify_src.services.execution_context_service import ExecutionContextService

class BrowserModeService:
    """Service for determining browser execution mode."""
    
    @staticmethod
    def determine_mode(force_headful: bool = False) -> BrowserMode:
        """
        Determine the browser execution mode based on parameters and context.
        
        Args:
            force_headful (bool): Whether to force headful mode
            
        Returns:
            BrowserMode: The determined browser mode
        """
        # If we're in a test environment, always use headless mode
        if ExecutionContextService.is_test_environment():
            return BrowserMode.HEADLESS
            
        # Otherwise, use the force_headful parameter to determine mode
        if force_headful:
            return BrowserMode.HEADFUL
        else:
            return BrowserMode.HEADLESS