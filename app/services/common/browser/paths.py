"""Chromium user data path management utilities."""

from pathlib import Path
from typing import Optional


class ChromiumPathManager:
    """Manages Chromium user data directory structure and path calculations."""

    def __init__(self, user_data_dir: Optional[str] = None):
        """Initialize the Chromium path manager.

        Args:
            user_data_dir: Root directory for Chromium profiles. If None,
                          user data management is disabled.
        """
        self.user_data_dir = user_data_dir
        self.enabled = user_data_dir is not None

        if self.enabled:
            self.base_path = Path(user_data_dir)
            self.master_dir = self.base_path / 'master'
            self.clones_dir = self.base_path / 'clones'
            self.lock_file = self.base_path / 'chromium_profile.lock'
            self.metadata_file = self.master_dir / 'metadata.json'
            self.fingerprint_file = self.master_dir / 'browserforge_fingerprint.json'

    def get_master_dir(self) -> Optional[str]:
        """Get the master directory path if enabled."""
        return str(self.master_dir) if self.enabled else None

    def ensure_directories_exist(self) -> None:
        """Ensure all required directories exist."""
        if not self.enabled:
            return

        self.base_path.mkdir(parents=True, exist_ok=True)
        self.master_dir.mkdir(parents=True, exist_ok=True)
        self.clones_dir.mkdir(parents=True, exist_ok=True)

    def generate_clone_path(self) -> Path:
        """Generate a unique clone directory path."""
        import uuid
        return self.clones_dir / str(uuid.uuid4())

    def get_cookies_db_path(self) -> Path:
        """Get path to Chromium cookies database."""
        return self.master_dir / "Default" / "Cookies"

    def validate_paths(self) -> bool:
        """Validate that required paths are accessible."""
        if not self.enabled:
            return True

        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            return self.base_path.exists() and self.base_path.is_dir()
        except (OSError, PermissionError):
            return False
