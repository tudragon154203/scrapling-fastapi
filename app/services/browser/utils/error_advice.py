"""Error-to-message mapping utilities for browser sessions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional


LogLevel = Literal["warning", "error"]


@dataclass
class ErrorAdvice:
    """Structured error advice for browse responses."""

    message: str
    log_level: LogLevel = "error"
    log_message: Optional[str] = None


def chromium_dependency_missing_advice(error: ImportError) -> ErrorAdvice:
    message = (
        f"Chromium dependencies are not available: {str(error)}\n"
        "To resolve this issue:\n"
        "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
        "2. Ensure Playwright browsers are installed: playwright install chromium\n"
        "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
    )
    return ErrorAdvice(message=message, log_level="error", log_message=f"Chromium dependencies missing: {error}")


class ChromiumErrorAdvisor:
    """Generate troubleshooting messages for Chromium browse failures."""

    def __init__(self, *, settings, user_data_dir: str, lock_file: Optional[str] = None) -> None:
        self._settings = settings
        self._user_data_dir = user_data_dir
        self._lock_file = lock_file

    def handle_runtime_error(self, error: RuntimeError) -> Optional[ErrorAdvice]:
        message = str(error).lower()

        if any(keyword in message for keyword in ("already in use", "lock", "exclusive")):
            error_msg = (
                "Chromium profile is already in use by another session. "
                "To resolve this issue:\n"
                "1. Wait for the current session to complete\n"
                "2. Check if another browser instance is running\n"
                f"3. If no session is active, manually remove the lock file: {self._lock_file}\n"
                "4. Consider using a different user data directory via CHROMIUM_USER_DATA_DIR environment variable"
            )
            return ErrorAdvice(
                message=error_msg,
                log_level="warning",
                log_message=f"Chromium profile locked: {error}",
            )

        if any(keyword in message for keyword in ("corrupt", "corrupted", "database is corrupted")):
            profile_path = (
                getattr(self._settings, "chromium_runtime_effective_user_data_dir", None)
                or os.path.abspath(self._user_data_dir)
            )
            error_msg = (
                f"Chromium user profile appears corrupted: {str(error)}\n"
                "Recovery steps:\n"
                "1. Close all Chromium/Chrome instances\n"
                f"2. Backup and then delete the corrupted profile directory\n   Path: {profile_path}\n"
                "3. Re-run the browse session to rebuild a fresh profile\n"
                "4. If issues persist, reinstall Playwright browsers: playwright install chromium"
            )
            return ErrorAdvice(
                message=error_msg,
                log_message=f"Chromium profile corruption detected: {error}",
            )

        if "version" in message or "compatib" in message:
            error_msg = (
                f"Chromium/Playwright version compatibility issue: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Update Playwright and browsers: pip install -U playwright && playwright install chromium\n"
                "2. Ensure system Chromium matches Playwright's expected version\n"
                "3. Consider using the Camoufox engine as a temporary workaround"
            )
            return ErrorAdvice(
                message=error_msg,
                log_message=f"Chromium version compatibility issue: {error}",
            )

        return None

    def handle_known_exception(self, error: Exception) -> ErrorAdvice:
        if isinstance(error, PermissionError):
            target_dir = (
                getattr(self._settings, "chromium_runtime_effective_user_data_dir", None)
                or os.path.abspath(self._user_data_dir)
            )
            message = (
                f"Permission error accessing Chromium user data: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Ensure the process has access permissions to the user data directory\n"
                f"2. Check directory path: {target_dir}\n"
                "3. Run the service with sufficient privileges or adjust directory ACLs"
            )
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium permission/access error: {error}",
            )

        if isinstance(error, TimeoutError):
            message = (
                f"Timeout occurred during Chromium browse session: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Verify display availability for headful sessions\n"
                "2. Check system resource utilization (CPU/RAM) and reduce load\n"
                "3. Try again after restarting the browser or use Camoufox engine"
            )
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium browse timeout: {error}",
            )

        if isinstance(error, ConnectionError):
            message = (
                f"Network/connection error during Chromium browse: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Check internet connectivity and proxy settings\n"
                "2. Ensure firewall or VPN isn't blocking Chromium/Playwright\n"
                "3. Retry the session after network is stable"
            )
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium browse network connectivity error: {error}",
            )

        if isinstance(error, MemoryError):
            message = (
                f"Insufficient memory for Chromium browse: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Close other applications to free memory\n"
                "2. Reduce concurrent workloads and try again\n"
                "3. Consider using Camoufox engine which may have lower memory footprint"
            )
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium browse memory error: {error}",
            )

        if isinstance(error, ImportError):
            message = (
                f"Chromium browser engine is not available: {str(error)}\n"
                "To resolve this issue:\n"
                "1. Install the required dependencies: pip install 'scrapling[chromium]'\n"
                "2. Ensure Playwright browsers are installed: playwright install chromium\n"
                "3. Alternatively, use the Camoufox engine by setting 'engine': 'camoufox' in your request"
            )
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium dependencies missing: {error}",
            )

        if isinstance(error, OSError):
            target_dir = (
                getattr(self._settings, "chromium_runtime_effective_user_data_dir", None)
                or os.path.abspath(self._user_data_dir)
            )
            message = (
                f"Disk space or filesystem error during Chromium browse: {str(error)}\n"
                "Troubleshooting:\n"
                "1. Free up disk space for the Chromium user data directory\n"
                f"2. Verify write permissions to: {target_dir}\n"
                "3. Consider changing CHROMIUM_USER_DATA_DIR to a drive with more space"
            )
            if "no space" in str(error).lower():
                message = "Disk space issue detected (No space left on device).\n" + message
            return ErrorAdvice(
                message=message,
                log_message=f"Chromium disk space/filesystem error: {error}",
            )

        return self.generic_failure(error)

    def generic_failure(self, error: Exception) -> ErrorAdvice:
        message = (
            f"Chromium browse session failed: {str(error)}\n"
            "Troubleshooting steps:\n"
            "1. Check that Chromium/Chrome is properly installed\n"
            "2. Verify display settings if running in headful mode\n"
            "3. Check available disk space for user data directory\n"
            "4. Try running with Camoufox engine as an alternative"
        )
        return ErrorAdvice(
            message=message,
            log_message=f"Chromium browse session failed: {error}",
        )
