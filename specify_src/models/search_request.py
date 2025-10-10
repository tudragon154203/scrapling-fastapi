from pydantic import BaseModel
from typing import Optional

class SearchRequest(BaseModel):
    """
    Represents a request to the TikTok search endpoint.
    
    Attributes:
        query (str): Search query string
        force_headful (Optional[bool]): Controls browser execution mode
            - When True: Run in headful mode
            - When False or None: Run in headless mode (default)
            - When not provided: Run in headless mode (default)
    """
    query: str
    force_headful: Optional[bool] = None