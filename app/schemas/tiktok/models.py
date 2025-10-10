"""TikTok search data models."""

from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, Field


class TikTokVideo(BaseModel):
    """TikTok video data model."""

    id: str = Field(..., description="Video ID")
    caption: str = Field(default="", description="Video caption")
    authorHandle: str = Field(..., description="Author handle without @")
    likeCount: int = Field(..., description="Like count as integer")
    uploadTime: str = Field(..., description="Upload time as string")
    webViewUrl: str = Field(..., description="Absolute web view URL")


class TikTokSearchError(BaseModel):
    """Error response schema for TikTok search endpoint."""

    code: Literal["NOT_LOGGED_IN", "VALIDATION_ERROR", "RATE_LIMITED", "SCRAPE_FAILED"] = Field(
        ..., description="Error code"
    )
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class TikTokSearchErrorResponse(BaseModel):
    """Full error response schema for TikTok search endpoint."""

    error: TikTokSearchError = Field(..., description="Error details")
