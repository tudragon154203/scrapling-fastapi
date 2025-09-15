"""Session management utilities for TikTok service."""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.schemas.tiktok import (
    TikTokLoginState,
    TikTokSessionConfig,
    TikTokSessionRequest,
    TikTokSessionResponse,
)
from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.tiktok.utils.login_detection import LoginDetector


@dataclass
class TikTokSessionMetadata:
    """Structured metadata describing an active TikTok session."""

    user_data_dir: Optional[str]
    config: TikTokSessionConfig
    login_state: TikTokLoginState
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Update the last-activity timestamp for keep-alive events."""
        self.last_activity = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to a dictionary for external consumers."""
        return {
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "user_data_dir": self.user_data_dir,
            "config": self.config,
            "login_state": self.login_state,
        }

    def timeout_remaining(self) -> int:
        """Return remaining session duration in seconds."""
        time_reference = max(self.created_at, self.last_activity)
        timeout_at = time_reference + timedelta(seconds=self.config.max_session_duration)
        now = datetime.now()
        return max(0, int((timeout_at - now).total_seconds()))


class TikTokSessionManager:
    """Encapsulates lifecycle management for TikTok sessions."""

    def __init__(self, settings: Any, logger: Optional[logging.Logger] = None):
        self.settings = settings
        self.logger = logger or logging.getLogger(__name__)
        self.active_sessions: Dict[str, TiktokExecutor] = {}
        self.session_metadata: Dict[str, TikTokSessionMetadata] = {}

    async def create_session(
        self,
        request: TikTokSessionRequest,
        user_data_dir: Optional[str] = None,
        immediate_cleanup: bool = False,
    ) -> TikTokSessionResponse:
        """Create a TikTok session and register it as active."""
        _ = request  # Request body currently unused; kept for future extensions.
        session_id = str(uuid.uuid4())
        try:
            config = await self._load_tiktok_config(user_data_dir)
            executor = TiktokExecutor(config)
            await executor.start_session()
            login_state = await self._detect_login_state(executor, config)
            if login_state == TikTokLoginState.LOGGED_OUT:
                await executor.cleanup()
                return TikTokSessionResponse(
                    status="error",
                    message="Not logged in to TikTok",
                    error_details={
                        "code": "NOT_LOGGED_IN",
                        "details": "User is not logged in to TikTok",
                        "method": "dom_api_combo",
                        "timeout": config.login_detection_timeout,
                    },
                )

            if not immediate_cleanup:
                executor.session_id = session_id
                self.active_sessions[session_id] = executor
                self.session_metadata[session_id] = TikTokSessionMetadata(
                    user_data_dir=executor.user_data_dir,
                    config=config,
                    login_state=login_state,
                )

            response = TikTokSessionResponse(
                status="success",
                message="TikTok session established successfully",
            )

            if immediate_cleanup:
                await executor.cleanup()

            return response
        except Exception as exc:  # pragma: no cover - safeguard for unexpected failures
            await self._cleanup_session(session_id)
            return TikTokSessionResponse(
                status="error",
                message="Failed to create TikTok session",
                error_details={
                    "code": "SESSION_CREATION_FAILED",
                    "details": str(exc),
                    "method": "internal_error",
                },
            )

    def has_active_session(self) -> bool:
        """Return True when at least one active session exists."""
        return bool(self.active_sessions)

    def get_active_session(self) -> Optional[TiktokExecutor]:
        """Return the first available active session executor, if any."""
        if self.active_sessions:
            session_id = next(iter(self.active_sessions))
            self.logger.debug(
                f"[TikTokSessionManager] Returning active session with id: {session_id}"
            )
            return self.active_sessions[session_id]
        return None

    async def close_session(self, session_id: str) -> bool:
        """Close and unregister an active session."""
        try:
            executor = self.active_sessions.pop(session_id, None)
            if not executor:
                self.logger.warning(
                    f"[TikTokSessionManager] Session {session_id} not found in active sessions"
                )
                self.session_metadata.pop(session_id, None)
                return False

            await executor.cleanup()
            self.session_metadata.pop(session_id, None)
            self.logger.debug(
                f"[TikTokSessionManager] Successfully closed session: {session_id}"
            )
            return True
        except Exception as exc:
            self.logger.error(
                f"[TikTokSessionManager] Error closing session {session_id}: {exc}",
                exc_info=True,
            )
            return False

    async def keep_alive(self, session_id: str) -> bool:
        """Refresh metadata for an active session to prevent timeouts."""
        executor = self.active_sessions.get(session_id)
        metadata = self.session_metadata.get(session_id)
        if not executor or not metadata:
            return False

        if not await executor.is_still_active():
            await self.close_session(session_id)
            return False

        metadata.touch()
        return True

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return merged metadata and executor info for a session."""
        executor = self.active_sessions.get(session_id)
        metadata = self.session_metadata.get(session_id)
        if not executor or not metadata:
            return None

        session_info = await executor.get_session_info()
        details = metadata.to_dict()
        details["timeout_remaining"] = metadata.timeout_remaining()
        return {**details, **session_info}

    async def check_session_timeout(self, session_id: str) -> bool:
        """Return True if the session has expired based on inactivity."""
        metadata = self.session_metadata.get(session_id)
        if not metadata:
            return True
        return metadata.timeout_remaining() <= 0

    async def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Return details for all active sessions."""
        sessions: Dict[str, Dict[str, Any]] = {}
        for session_id in list(self.active_sessions.keys()):
            info = await self.get_session_info(session_id)
            if info:
                sessions[session_id] = info
            else:
                await self._cleanup_session(session_id)
        return sessions

    async def cleanup_all_sessions(self) -> None:
        """Cleanup every registered session."""
        for session_id in list(self.active_sessions.keys()):
            await self._cleanup_session(session_id)

    async def cleanup_session(self, session_id: str) -> None:
        """Expose cleanup helper for selective session teardown."""
        await self._cleanup_session(session_id)

    async def _cleanup_session(self, session_id: str) -> None:
        """Internal helper ensuring a session is torn down."""
        try:
            executor = self.active_sessions.pop(session_id, None)
            if executor:
                try:
                    await executor.cleanup()
                finally:
                    self.session_metadata.pop(session_id, None)
        except Exception as exc:
            self.logger.error(
                f"[TikTokSessionManager] Error cleaning up session {session_id}: {exc}",
                exc_info=True,
            )

    async def _load_tiktok_config(
        self, user_data_dir: Optional[str] = None
    ) -> TikTokSessionConfig:
        """Recreate configuration logic for TikTok sessions."""
        base_user_data_dir = self.settings.camoufox_user_data_dir or "./user_data"
        headless = bool(getattr(self.settings, "default_headless", True))
        try:
            current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
            norm = current_test.replace("\\", "/").lower()
            if "/tests/unit/" in norm or "tests/unit/" in norm:
                headless = True
        except Exception:
            headless = bool(getattr(self.settings, "default_headless", True))

        del user_data_dir  # User data directories currently share the same base path.
        return TikTokSessionConfig(
            user_data_master_dir=base_user_data_dir,
            user_data_clones_dir=base_user_data_dir,
            write_mode_enabled=self.settings.tiktok_write_mode_enabled,
            acquire_lock_timeout=30,
            login_detection_timeout=self.settings.tiktok_login_detection_timeout,
            max_session_duration=self.settings.tiktok_max_session_duration,
            tiktok_url=self.settings.tiktok_url,
            headless=headless,
        )

    async def _detect_login_state(
        self, executor: TiktokExecutor, config: TikTokSessionConfig
    ) -> TikTokLoginState:
        """Detect login state using the executor and provided config."""
        if not executor.browser:
            return TikTokLoginState.UNCERTAIN
        detector = LoginDetector(executor.browser, config)
        return await detector.detect_login_state(config.login_detection_timeout)
