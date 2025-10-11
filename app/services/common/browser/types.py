"""Type definitions and schema models for Chromium user data management."""

from typing import Dict, Any, List, Optional, TypedDict, Union


class CookieData(TypedDict, total=False):
    """Schema for individual cookie data."""

    name: str
    value: str
    domain: str
    path: str
    expires: int
    httpOnly: bool
    secure: bool
    sameSite: str
    creationTime: Optional[int]
    lastAccessTime: Optional[int]
    persistent: Optional[bool]


class CookieExportResult(TypedDict, total=False):
    """Schema for exported cookie data."""

    format: str
    cookies: List[CookieData]
    profile_metadata: Optional[Dict[str, Any]]
    cookies_available: bool
    master_profile_path: str
    export_timestamp: float


class StorageStateCookies(TypedDict, total=False):
    """Schema for Playwright storage_state format cookies."""

    name: str
    value: str
    domain: str
    path: str
    expires: int
    httpOnly: bool
    secure: bool
    sameSite: str


class StorageStateResult(TypedDict):
    """Schema for Playwright storage_state format."""

    cookies: List[StorageStateCookies]
    origins: List[Any]


class ProfileMetadata(TypedDict, total=False):
    """Schema for Chromium profile metadata."""

    version: str
    created_at: float
    last_updated: float
    browserforge_version: Optional[str]
    profile_type: str
    browserforge_fingerprint_generated: Optional[bool]
    browserforge_fingerprint_file: Optional[str]
    browserforge_fingerprint_source: Optional[str]
    last_cookie_import: Optional[float]
    cookie_import_count: Optional[int]
    cookie_import_status: Optional[str]
    last_cleanup: Optional[float]
    last_cleanup_count: Optional[int]
    last_cleanup_size_saved: Optional[float]
    remaining_clones: Optional[int]


class DiskUsageStats(TypedDict, total=False):
    """Schema for disk usage statistics."""

    enabled: bool
    master_size_mb: float
    clones_size_mb: float
    total_size_mb: float
    clone_count: int
    master_dir: str
    clones_dir: str
    last_cleanup: Optional[float]
    last_cleanup_count: int
    last_cleanup_size_saved: float
    error: Optional[str]


class CleanupResult(TypedDict):
    """Schema for cleanup operation results."""

    cleaned: int
    remaining: int
    errors: int
    size_saved_mb: Optional[float]


class BrowserForgeFingerprint(TypedDict, total=False):
    """Schema for BrowserForge fingerprint data."""

    userAgent: str
    viewport: Dict[str, int]
    screen: Dict[str, Union[int, float]]


# Type aliases for common patterns
CookieList = List[CookieData]
CookieDict = Dict[str, Any]
MetadataUpdates = Dict[str, Any]


def convert_samesite(samesite_int: int) -> str:
    """Convert Chromium samesite integer to string.

    Args:
        samesite_int: Chromium samesite integer value

    Returns:
        String representation of SameSite value
    """
    mapping = {
        0: "None",
        1: "Lax",
        2: "Strict",
        -1: "None"  # Unspecified
    }
    return mapping.get(samesite_int, "None")


def convert_samesite_to_db(samesite_str: str) -> int:
    """Convert samesite string to Chromium database integer.

    Args:
        samesite_str: String representation of SameSite value

    Returns:
        Chromium database integer value
    """
    mapping = {
        "None": 0,
        "Lax": 1,
        "Strict": 2,
        "none": 0,
        "lax": 1,
        "strict": 2
    }
    return mapping.get(samesite_str, 0)
