from typing import Optional
import os
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    # Preferred: pydantic-settings for .env loading
    class Settings(BaseSettings):
        """Application settings loaded from environment variables (.env).
        This keeps the first sprint simple while allowing future expansion
        (proxies, advanced stealth configs, metrics toggles, etc.).
        """
        # Server
        app_name: str = Field(default="Scrapling FastAPI Service")
        host: str = Field(default="0.0.0.0")
        port: int = Field(default=8000)
        reload: bool = Field(default=False)
        # Logging
        log_level: str = Field(default="INFO")
        # Scraping defaults
        default_headless: bool = Field(default=True)
        default_network_idle: bool = Field(default=False)
        default_timeout_ms: int = Field(default=20_000)
        # Retry and Proxy settings
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
        # Camoufox user data directory (single profile dir)
        camoufox_user_data_dir: Optional[str] = Field(default=None)
        # Chromium user data directory (master/clone profile structure)
        chromium_user_data_dir: Optional[str] = Field(default="data/chromium_profiles")
        # Camoufox stealth extras (optional, no API changes)
        camoufox_locale: Optional[str] = Field(default=None)  # e.g., "en-US,en;q=0.9"
        camoufox_window: Optional[str] = Field(default="1280x720")  # e.g., "1366x768"
        camoufox_disable_coop: bool = Field(default=False)
        camoufox_geoip: bool = Field(default=True)
        camoufox_virtual_display: Optional[str] = Field(default=None)
        camoufox_force_mute_audio_default: bool = Field(default=True)
        # Runtime-only Camoufox toggles managed by services (never persisted)
        camoufox_runtime_force_mute_audio: bool = Field(
            default=False, exclude=True, repr=False
        )
        camoufox_runtime_user_data_mode: Optional[str] = Field(
            default=None, exclude=True, repr=False
        )
        camoufox_runtime_effective_user_data_dir: Optional[str] = Field(
            default=None, exclude=True, repr=False
        )
        # Runtime-only Chromium toggles managed by services (never persisted)
        chromium_runtime_user_data_mode: Optional[str] = Field(
            default=None, exclude=True, repr=False
        )
        chromium_runtime_effective_user_data_dir: Optional[str] = Field(
            default=None, exclude=True, repr=False
        )
        # AusPost humanization settings
        auspost_humanize_enabled: bool = Field(default=True, env="AUSPOST_HUMANIZE_ENABLED")
        auspost_humanize_scroll: bool = Field(default=True, env="AUSPOST_HUMANIZE_SCROLL")
        auspost_typing_delay_ms_min: int = Field(default=60, env="AUSPOST_TYPING_DELAY_MS_MIN")
        auspost_typing_delay_ms_max: int = Field(default=140, env="AUSPOST_TYPING_DELAY_MS_MAX")
        auspost_mouse_steps_min: int = Field(default=12, env="AUSPOST_MOUSE_STEPS_MIN")
        auspost_mouse_steps_max: int = Field(default=28, env="AUSPOST_MOUSE_STEPS_MAX")
        auspost_jitter_radius_px: int = Field(default=3, env="AUSPOST_JITTER_RADIUS_PX")
        auspost_jitter_steps: int = Field(default=2, env="AUSPOST_JITTER_STEPS")
        auspost_micro_pause_min_s: float = Field(default=0.15, env="AUSPOST_MICRO_PAUSE_MIN_S")
        auspost_micro_pause_max_s: float = Field(default=0.40, env="AUSPOST_MICRO_PAUSE_MAX_S")
        # Intensity and probability
        auspost_mouse_move_prob: float = Field(default=1.0, env="AUSPOST_MOUSE_MOVE_PROB")
        auspost_mouse_jitter_prob: float = Field(default=1.0, env="AUSPOST_MOUSE_JITTER_PROB")
        auspost_scroll_prob: float = Field(default=1.0, env="AUSPOST_SCROLL_PROB")
        auspost_scroll_cycles_min: int = Field(default=1, env="AUSPOST_SCROLL_CYCLES_MIN")
        auspost_scroll_cycles_max: int = Field(default=1, env="AUSPOST_SCROLL_CYCLES_MAX")
        auspost_scroll_dy_min: int = Field(default=80, env="AUSPOST_SCROLL_DY_MIN")
        auspost_scroll_dy_max: int = Field(default=180, env="AUSPOST_SCROLL_DY_MAX")
        # AusPost endpoint behavior
        auspost_use_proxy: bool = Field(default=False, env="AUSPOST_USE_PROXY")
        # TikTok session configuration
        tiktok_write_mode_enabled: bool = Field(default=False, env="TIKTOK_WRITE_MODE_ENABLED")
        tiktok_login_detection_timeout: int = Field(default=8, env="TIKTOK_LOGIN_DETECTION_TIMEOUT")
        tiktok_max_session_duration: int = Field(default=300, env="TIKTOK_MAX_SESSION_DURATION")
        tiktok_url: str = Field(default="https://www.tiktok.com/", env="TIKTOK_URL")
        # TikTok download configuration
        tiktok_download_strategy: str = Field(default="chromium", env="TIKTOK_DOWNLOAD_STRATEGY")
        # TikTok download resolver configuration
        tikvid_base: str = Field(default="https://tikvid.io/vi", env="TIKVID_BASE")

        @field_validator('chromium_user_data_dir', mode='before')
        def _sanitize_chromium_user_data_dir(cls, v: Optional[str]) -> Optional[str]:
            if v is None:
                return None
            if isinstance(v, str):
                s = v.strip()
                if not s:
                    return None
                try:
                    return os.path.abspath(s)
                except Exception:
                    return s
            return v

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @lru_cache()
    def get_settings() -> "Settings":
        return Settings()
except Exception:
    # Fallback: light-weight env loader without pydantic-settings
    class Settings(BaseModel):
        app_name: str = "Scrapling FastAPI Service"
        host: str = "0.0.0.0"
        port: int = 8000
        reload: bool = False
        log_level: str = "INFO"
        default_headless: bool = True
        default_network_idle: bool = False
        default_timeout_ms: int = 20_000
        # Retry and Proxy settings
        max_retries: int = 3
        retry_backoff_base_ms: int = 500
        retry_backoff_max_ms: int = 5_000
        retry_jitter_ms: int = 250
        proxy_list_file_path: Optional[str] = None
        private_proxy_url: Optional[str] = None
        proxy_rotation_mode: str = "sequential"
        proxy_health_failure_threshold: int = 2
        proxy_unhealthy_cooldown_minute: int = 30
        # Camoufox user data directory (single profile dir)
        camoufox_user_data_dir: Optional[str] = None
        # Chromium user data directory (master/clone profile structure)
        chromium_user_data_dir: Optional[str] = "data/chromium_profiles"
        # Camoufox stealth extras
        camoufox_locale: Optional[str] = None
        camoufox_window: Optional[str] = "1280x720"
        camoufox_disable_coop: bool = False
        camoufox_geoip: bool = True
        camoufox_virtual_display: Optional[str] = None
        camoufox_force_mute_audio_default: bool = True
        camoufox_runtime_force_mute_audio: bool = False
        camoufox_runtime_user_data_mode: Optional[str] = None
        camoufox_runtime_effective_user_data_dir: Optional[str] = None
        # Runtime-only Chromium toggles managed by services (never persisted)
        chromium_runtime_user_data_mode: Optional[str] = None
        chromium_runtime_effective_user_data_dir: Optional[str] = None
        # Content validation
        min_html_content_length: int = 500
        # AusPost humanization settings
        auspost_humanize_enabled: bool = True
        auspost_humanize_scroll: bool = True
        auspost_typing_delay_ms_min: int = 100
        auspost_typing_delay_ms_max: int = 300
        auspost_mouse_steps_min: int = 12
        auspost_mouse_steps_max: int = 28
        auspost_jitter_radius_px: int = 3
        auspost_jitter_steps: int = 2
        auspost_micro_pause_min_s: float = 0.15
        auspost_micro_pause_max_s: float = 0.40
        auspost_mouse_move_prob: float = 1.0
        auspost_mouse_jitter_prob: float = 1.0
        auspost_scroll_prob: float = 1.0
        auspost_scroll_cycles_min: int = 1
        auspost_scroll_cycles_max: int = 1
        auspost_scroll_dy_min: int = 80
        auspost_scroll_dy_max: int = 180
        auspost_use_proxy: bool = False
        # TikTok session configuration
        tiktok_write_mode_enabled: bool = False
        tiktok_login_detection_timeout: int = 8
        tiktok_max_session_duration: int = 300
        tiktok_url: str = "https://www.tiktok.com/"
        # TikTok download configuration
        tiktok_download_strategy: str = "chromium"
        # TikTok download resolver configuration
        tikvid_base: str = "https://tikvid.io/vi"

    @lru_cache()
    def get_settings() -> "Settings":
        return Settings(
            app_name=os.getenv("APP_NAME", "Scrapling FastAPI Service"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"},
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            default_headless=os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"},
            default_network_idle=os.getenv("NETWORK_IDLE", "false").lower() in {"1", "true", "yes"},
            default_timeout_ms=int(os.getenv("TIMEOUT_MS", "20000")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_backoff_base_ms=int(os.getenv("RETRY_BACKOFF_BASE_MS", "500")),
            retry_backoff_max_ms=int(os.getenv("RETRY_BACKOFF_MAX_MS", "5000")),
            retry_jitter_ms=int(os.getenv("RETRY_JITTER_MS", "250")),
            proxy_list_file_path=os.getenv("PROXY_LIST_FILE_PATH"),
            private_proxy_url=os.getenv("PRIVATE_PROXY_URL"),
            proxy_rotation_mode=os.getenv("PROXY_ROTATION_MODE", "sequential"),
            proxy_health_failure_threshold=int(os.getenv("PROXY_HEALTH_FAILURE_THRESHOLD", "2")),
            proxy_unhealthy_cooldown_minute=int(os.getenv("PROXY_UNHEALTHY_COOLDOWN_MINUTE", "30")),
            camoufox_user_data_dir=os.getenv("CAMOUFOX_USER_DATA_DIR"),
            chromium_user_data_dir=(
                os.path.abspath(os.getenv("CHROMIUM_USER_DATA_DIR").strip())
                if os.getenv("CHROMIUM_USER_DATA_DIR")
                and os.getenv("CHROMIUM_USER_DATA_DIR").strip()
                else "data/chromium_profiles"
            ),
            camoufox_locale=os.getenv("CAMOUFOX_LOCALE"),
            camoufox_window=os.getenv("CAMOUFOX_WINDOW"),
            camoufox_disable_coop=os.getenv("CAMOUFOX_DISABLE_COOP", "false").lower() in {"1", "true", "yes"},
            camoufox_geoip=os.getenv("CAMOUFOX_GEOIP", "true").lower() in {"1", "true", "yes"},
            camoufox_virtual_display=os.getenv("CAMOUFOX_VIRTUAL_DISPLAY"),
            min_html_content_length=int(os.getenv("MIN_HTML_CONTENT_LENGTH", "500")),
            auspost_humanize_enabled=os.getenv("AUSPOST_HUMANIZE_ENABLED", "true").lower() in {"1", "true", "yes"},
            auspost_humanize_scroll=os.getenv("AUSPOST_HUMANIZE_SCROLL", "true").lower() in {"1", "true", "yes"},
            auspost_typing_delay_ms_min=int(os.getenv("AUSPOST_TYPING_DELAY_MS_MIN", "60")),
            auspost_typing_delay_ms_max=int(os.getenv("AUSPOST_TYPING_DELAY_MS_MAX", "140")),
            auspost_mouse_steps_min=int(os.getenv("AUSPOST_MOUSE_STEPS_MIN", "12")),
            auspost_mouse_steps_max=int(os.getenv("AUSPOST_MOUSE_STEPS_MAX", "28")),
            auspost_jitter_radius_px=int(os.getenv("AUSPOST_JITTER_RADIUS_PX", "3")),
            auspost_jitter_steps=int(os.getenv("AUSPOST_JITTER_STEPS", "2")),
            auspost_micro_pause_min_s=float(os.getenv("AUSPOST_MICRO_PAUSE_MIN_S", "0.15")),
            auspost_micro_pause_max_s=float(os.getenv("AUSPOST_MICRO_PAUSE_MAX_S", "0.40")),
            auspost_mouse_move_prob=float(os.getenv("AUSPOST_MOUSE_MOVE_PROB", "1.0")),
            auspost_mouse_jitter_prob=float(os.getenv("AUSPOST_MOUSE_JITTER_PROB", "1.0")),
            auspost_scroll_prob=float(os.getenv("AUSPOST_SCROLL_PROB", "1.0")),
            auspost_scroll_cycles_min=int(os.getenv("AUSPOST_SCROLL_CYCLES_MIN", "1")),
            auspost_scroll_cycles_max=int(os.getenv("AUSPOST_SCROLL_CYCLES_MAX", "1")),
            auspost_scroll_dy_min=int(os.getenv("AUSPOST_SCROLL_DY_MIN", "80")),
            auspost_scroll_dy_max=int(os.getenv("AUSPOST_SCROLL_DY_MAX", "180")),
            auspost_use_proxy=os.getenv("AUSPOST_USE_PROXY", "false").lower() in {"1", "true", "yes"},
            tiktok_write_mode_enabled=os.getenv("TIKTOK_WRITE_MODE_ENABLED", "false").lower() in {"1", "true", "yes"},
            tiktok_login_detection_timeout=int(os.getenv("TIKTOK_LOGIN_DETECTION_TIMEOUT", "8")),
            tiktok_max_session_duration=int(os.getenv("TIKTOK_MAX_SESSION_DURATION", "300")),
            tiktok_url=os.getenv("TIKTOK_URL", "https://www.tiktok.com/"),
            tiktok_download_strategy=os.getenv("TIKTOK_DOWNLOAD_STRATEGY", "chromium"),
            tikvid_base=os.getenv("TIKVID_BASE", "https://tikvid.io/vi"),
        )
