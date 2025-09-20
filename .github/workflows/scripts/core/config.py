"""Configuration for opencode workflow scripts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class Config:
    """Centralized configuration for opencode workflow scripts."""
    
    def __init__(self) -> None:
        """Initialize configuration from environment variables and .env file."""
        # Load .env file if it exists
        self._load_env_file()
        
        # API Keys
        self.openrouter_api_key: Optional[str] = os.environ.get("OPENROUTER_API_KEY")
        
        # Model Configuration
        self.test_model: str = os.environ.get("OPENCODE_TEST_MODEL", "openrouter/z-ai/glm-4.5-air:free")
        
    def _load_env_file(self) -> None:
        """Load environment variables from .env file if it exists."""
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration and return (is_valid, error_messages)."""
        errors = []
        
        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY is not set")
            
        return len(errors) == 0, errors
    
    @property
    def has_api_keys(self) -> bool:
        """Check if required API keys are available."""
        return bool(self.openrouter_api_key)


# Global configuration instance
config = Config()