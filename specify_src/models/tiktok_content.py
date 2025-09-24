from typing import Optional

from pydantic import BaseModel, Field


class TikTokContentItem(BaseModel):
    """Documentation model mirroring the public TikTok video schema."""

    id: str = Field(
        ...,
        description="Video ID",
        example="7200000000000000000",
    )
    caption: str = Field(
        default="",
        description="Video caption",
        example="Funniest cats of 2024",
    )
    authorHandle: str = Field(
        ...,
        description="Author handle without the leading @",
        example="catlover",
    )
    likeCount: int = Field(
        ...,
        description="Total like count as an integer",
        example=1280,
    )
    uploadTime: str = Field(
        ...,
        description="Upload timestamp represented as a string",
        example="2024-01-02T12:34:56Z",
    )
    webViewUrl: str = Field(
        ...,
        description="Public URL to the TikTok video",
        example="https://www.tiktok.com/@catlover/video/7200000000000000000",
    )
    thumbnailUrl: Optional[str] = Field(
        None,
        description="Optional thumbnail URL if available",
    )
