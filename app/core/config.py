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
        )