"""TikTok download request and response schemas."""

from __future__ import annotations

from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, field_serializer


class TikTokDownloadRequest(BaseModel):
    """Request schema for TikTok video download."""

    url: HttpUrl = Field(
        ...,
        description="Public TikTok video URL to download",
        examples=["https://www.tiktok.com/@username/video/1234567890"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://www.tiktok.com/@tieentiton/video/7530618987760209170"
                }
            ]
        },
        "extra": "forbid",  # Reject extra fields in the request
        "populate_by_name": True
    }


class TikTokVideoInfo(BaseModel):
    """Video metadata information."""

    id: str = Field(..., description="Video ID")
    title: Optional[str] = Field(None, description="Video title/caption")
    author: Optional[str] = Field(None, description="Video author handle")
    duration: Optional[float] = Field(None, description="Video duration in seconds")
    thumbnail_url: Optional[HttpUrl] = Field(None, description="Video thumbnail URL")

    model_config = {
        "exclude_none": True  # Exclude None values from serialization
    }


class TikTokDownloadResponse(BaseModel):
    """Response schema for TikTok video download."""

    status: Literal["success", "error"] = Field(..., description="Download status: 'success' or 'error'")
    message: str = Field(..., description="Status message")

    # Success fields
    download_url: Optional[HttpUrl] = Field(None, description="Direct download URL for the video")
    video_info: Optional[TikTokVideoInfo] = Field(None, description="Video metadata")
    file_size: Optional[int] = Field(None, description="File size in bytes (if available)")

    # Error fields
    error_code: Optional[str] = Field(None, description="Error code for debugging")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    # Metadata
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")

    model_config = {
        "exclude_none": True,  # Exclude None values from serialization
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "message": "Video download URL resolved successfully",
                    "download_url": "https://example.com/video.mp4",
                    "video_info": {
                        "id": "7530618987760209170",
                        "title": "Sample TikTok Video",
                        "author": "tieentiton"
                    },
                    "execution_time": 12.5
                }
            ]
        }
    }
