"""
Abstract base class for browsing executors
"""
import shutil
import tempfile
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from app.core.config import get_settings


class AbstractBrowsingExecutor(ABC):
    """Abstract base class for common browsing functionality"""

    def __init__(self, user_data_dir: Optional[str] = None, proxy: Optional[Dict[str, str]] = None):
        self.settings = get_settings()
        self.user_data_dir = user_data_dir
        self.proxy = proxy
        self.browser: Optional[Any] = None
        self.session_id: Optional[str] = None
        self.start_time: Optional[float] = None

    @abstractmethod
    async def get_config(self) -> Dict[str, Any]:
        """Get executor-specific configuration"""
        pass

    @abstractmethod
    async def setup_browser(self) -> None:
        """Setup browser with specific configuration"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup browser resources"""
        pass

    async def _prepare_user_data_dir(self) -> str:
        """Prepare user data directory - clones from master if needed"""
        if not self.user_data_dir:
            # Generate temporary directory
            temp_dir = tempfile.mkdtemp(prefix="scrapling_")
            return temp_dir

        configured_dir = Path(self.settings.camoufox_user_data_dir or "./user_data")
        if configured_dir.name == "master":
            base_dir = configured_dir.parent
            master_dir = configured_dir
        else:
            base_dir = configured_dir
            master_dir = configured_dir / "master"

        clones_root = base_dir / "clones"
        user_data_path = Path(self.user_data_dir)

        if (
            (str(user_data_path).startswith(str(clones_root)) and user_data_path != clones_root)
            or not user_data_path.exists()
        ):
            # Clone from master directory
            return await self._clone_user_data_dir(master_dir, str(user_data_path))

        return str(user_data_path)

    async def _clone_user_data_dir(self, master_dir: Path, target_dir: str) -> str:
        """Clone master user data directory to target"""
        if not master_dir.exists():
            raise FileNotFoundError(f"Master user data directory not found: {master_dir}")

        # Create target directory
        target_path = Path(target_dir)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Clone the directory
        shutil.copytree(master_dir, target_path, dirs_exist_ok=True)

        return str(target_path)

    async def _redact_proxy_values(self, message: str) -> str:
        """Redact proxy values from log messages for security"""
        if self.proxy and "value" in self.proxy:
            redacted = message.replace(self.proxy["value"], "***")
            return redacted
        return message

    async def start_session(self) -> None:
        """Start browsing session"""
        try:
            # Prepare user data directory
            self.user_data_dir = await self._prepare_user_data_dir()

            # Get browser configuration
            await self.get_config()

            # Setup browser
            await self.setup_browser()

            self.start_time = asyncio.get_event_loop().time()
            logger = getattr(self, 'logger', None)
            if logger:
                await logger.debug(f"Browser session started with user data: {self.user_data_dir}")

        except Exception:
            await self._cleanup_on_error()
            raise

    async def _cleanup_on_error(self) -> None:
        """Cleanup on error"""
        try:
            if self.browser:
                # Just set browser to None instead of calling cleanup which might fail
                self.browser = None
            self.user_data_dir = None
        except Exception as cleanup_error:
            logger = getattr(self, 'logger', None)
            if logger:
                await logger.error(f"Error during cleanup: {cleanup_error}")

    async def check_session_timeout(self, max_duration: Optional[int] = None) -> bool:
        """Check if session has timed out"""
        if not self.start_time:
            return False

        duration = asyncio.get_event_loop().time() - self.start_time
        max_duration = max_duration or self.settings.tiktok_max_session_duration

        return duration > max_duration

    async def validate_user_data_dir(self) -> bool:
        """Validate user data directory"""
        if not self.user_data_dir or not Path(self.user_data_dir).exists():
            return False

        # Check if directory is readable
        try:
            test_file = Path(self.user_data_dir) / "test.txt"
            test_file.touch()
            test_file.unlink()
            return True
        except Exception:
            return False

    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "session_id": self.session_id,
            "user_data_dir": self.user_data_dir,
            "start_time": self.start_time,
            "duration": asyncio.get_event_loop().time() - self.start_time if self.start_time else 0,
            "browser_running": self.browser is not None
        }
