from enum import Enum

class BrowserMode(Enum):
    """Enumeration representing browser execution modes."""
    HEADLESS = "headless"
    HEADFUL = "headful"