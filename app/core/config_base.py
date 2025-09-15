"""Shared application settings schema.

This module holds the canonical ``Settings`` model so it can be reused by
different loaders (pydantic-settings when available and a light-weight
environment reader fallback).
"""

from __future__ import annotations

from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Application settings shared by every loader implementation."""

    model_config = ConfigDict(populate_by_name=True)

    # Server
    app_name: str = Field(default="Scrapling FastAPI Service")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)

    # Logging
    log_level: str = Field(default="INFO")

    # Scraping defaults
    default_headless: bool = Field(
        default=True,
        validation_alias=AliasChoices("DEFAULT_HEADLESS", "HEADLESS"),
    )
    default_network_idle: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEFAULT_NETWORK_IDLE", "NETWORK_IDLE"),
    )
    default_timeout_ms: int = Field(
        default=20_000,
        validation_alias=AliasChoices("DEFAULT_TIMEOUT_MS", "TIMEOUT_MS"),
    )

    # Retry and proxy settings
    max_retries: int = Field(default=3)
    retry_backoff_base_ms: int = Field(default=500)
    retry_backoff_max_ms: int = Field(default=5_000)
    retry_jitter_ms: int = Field(default=250)
    proxy_list_file_path: Optional[str] = Field(default=None)
    private_proxy_url: Optional[str] = Field(default=None)
    proxy_rotation_mode: str = Field(default="sequential")
    proxy_health_failure_threshold: int = Field(default=2)
    proxy_unhealthy_cooldown_minute: int = Field(default=30)

    # Content validation
    min_html_content_length: int = Field(default=500)

    # Camoufox configuration
    camoufox_user_data_dir: Optional[str] = Field(default=None)
    camoufox_locale: Optional[str] = Field(default=None)
    camoufox_window: Optional[str] = Field(default="1280x720")
    camoufox_disable_coop: bool = Field(default=False)
    camoufox_geoip: bool = Field(default=True)
    camoufox_virtual_display: Optional[str] = Field(default=None)

    # AusPost humanization behaviour
    auspost_humanize_enabled: bool = Field(
        default=True, validation_alias="AUSPOST_HUMANIZE_ENABLED"
    )
    auspost_humanize_scroll: bool = Field(
        default=True, validation_alias="AUSPOST_HUMANIZE_SCROLL"
    )
    auspost_typing_delay_ms_min: int = Field(
        default=60, validation_alias="AUSPOST_TYPING_DELAY_MS_MIN"
    )
    auspost_typing_delay_ms_max: int = Field(
        default=140, validation_alias="AUSPOST_TYPING_DELAY_MS_MAX"
    )
    auspost_mouse_steps_min: int = Field(
        default=12, validation_alias="AUSPOST_MOUSE_STEPS_MIN"
    )
    auspost_mouse_steps_max: int = Field(
        default=28, validation_alias="AUSPOST_MOUSE_STEPS_MAX"
    )
    auspost_jitter_radius_px: int = Field(
        default=3, validation_alias="AUSPOST_JITTER_RADIUS_PX"
    )
    auspost_jitter_steps: int = Field(
        default=2, validation_alias="AUSPOST_JITTER_STEPS"
    )
    auspost_micro_pause_min_s: float = Field(
        default=0.15, validation_alias="AUSPOST_MICRO_PAUSE_MIN_S"
    )
    auspost_micro_pause_max_s: float = Field(
        default=0.40, validation_alias="AUSPOST_MICRO_PAUSE_MAX_S"
    )
    auspost_mouse_move_prob: float = Field(
        default=1.0, validation_alias="AUSPOST_MOUSE_MOVE_PROB"
    )
    auspost_mouse_jitter_prob: float = Field(
        default=1.0, validation_alias="AUSPOST_MOUSE_JITTER_PROB"
    )
    auspost_scroll_prob: float = Field(
        default=1.0, validation_alias="AUSPOST_SCROLL_PROB"
    )
    auspost_scroll_cycles_min: int = Field(
        default=1, validation_alias="AUSPOST_SCROLL_CYCLES_MIN"
    )
    auspost_scroll_cycles_max: int = Field(
        default=1, validation_alias="AUSPOST_SCROLL_CYCLES_MAX"
    )
    auspost_scroll_dy_min: int = Field(
        default=80, validation_alias="AUSPOST_SCROLL_DY_MIN"
    )
    auspost_scroll_dy_max: int = Field(
        default=180, validation_alias="AUSPOST_SCROLL_DY_MAX"
    )
    auspost_use_proxy: bool = Field(
        default=False, validation_alias="AUSPOST_USE_PROXY"
    )

    # TikTok session configuration
    tiktok_write_mode_enabled: bool = Field(
        default=False, validation_alias="TIKTOK_WRITE_MODE_ENABLED"
    )
    tiktok_login_detection_timeout: int = Field(
        default=8, validation_alias="TIKTOK_LOGIN_DETECTION_TIMEOUT"
    )
    tiktok_max_session_duration: int = Field(
        default=300, validation_alias="TIKTOK_MAX_SESSION_DURATION"
    )
    tiktok_url: str = Field(
        default="https://www.tiktok.com/", validation_alias="TIKTOK_URL"
    )


__all__ = ["Settings"]

