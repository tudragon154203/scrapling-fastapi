from typing import Optional
import os
from functools import lru_cache
from pydantic import Field

try:
    # Preferred: pydantic-settings for .env loading
    from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore

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
        
        # Allow HTTP-only fallback on non-200/short HTML
        http_fallback_on_failure: bool = Field(default=False)
        
        # Camoufox user data directory (single profile dir)
        camoufox_user_data_dir: Optional[str] = Field(default=None)

        # Camoufox stealth extras (optional, no API changes)
        # Locale string like "en-US,en;q=0.9" or a single locale like "en-US"
        camoufox_locale: Optional[str] = Field(default=None)
        # Window size, e.g. "1366x768" or "1366,768"; parsed at runtime
        camoufox_window: Optional[str] = Field(default=None)
        # When true, relaxes COOP to allow interactions within cross-origin iframes
        camoufox_disable_coop: bool = Field(default=False)
        # When true and a proxy is used, spoof geolocation/timezone/WebRTC via Camoufox
        camoufox_geoip: bool = Field(default=True)
        # When set on Linux, enables virtual display (e.g., "xvfb")
        camoufox_virtual_display: Optional[str] = Field(default=None)

        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    @lru_cache()
    def get_settings() -> "Settings":
        return Settings()

except Exception:
    # Fallback: light-weight env loader without pydantic-settings
    from pydantic import BaseModel

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
        # Camoufox stealth extras
        camoufox_locale: Optional[str] = None
        camoufox_window: Optional[str] = None
        camoufox_disable_coop: bool = False
        camoufox_geoip: bool = True
        camoufox_virtual_display: Optional[str] = None

        # Content validation
        min_html_content_length: int = 500
        # Allow HTTP-only fallback on non-200/short HTML
        http_fallback_on_failure: bool = False

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
            camoufox_locale=os.getenv("CAMOUFOX_LOCALE"),
            camoufox_window=os.getenv("CAMOUFOX_WINDOW"),
            camoufox_disable_coop=os.getenv("CAMOUFOX_DISABLE_COOP", "false").lower()
            in {"1", "true", "yes"},
            camoufox_geoip=os.getenv("CAMOUFOX_GEOIP", "true").lower() in {"1", "true", "yes"},
            camoufox_virtual_display=os.getenv("CAMOUFOX_VIRTUAL_DISPLAY"),
            min_html_content_length=int(os.getenv("MIN_HTML_CONTENT_LENGTH", "500")),
            http_fallback_on_failure=os.getenv("HTTP_FALLBACK_ON_FAILURE", "false").lower() in {"1", "true", "yes"},
        )
