"""
TikTok session service
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.schemas.tiktok.session import (
    TikTokLoginState,
    TikTokSessionConfig,
    TikTokSessionRequest,
    TikTokSessionResponse,
)
from app.services.tiktok.session.registry import SessionRecord, SessionRegistry
from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.tiktok.utils.login_detection import LoginDetector


class TiktokService:
    """TikTok session management service."""

    def __init__(
        self,
        *,
        session_registry: Optional[SessionRegistry] = None,
    ) -> None:
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.sessions = session_registry or SessionRegistry()

    async def create_session(
        self,
        request: TikTokSessionRequest,
        user_data_dir: Optional[str] = None,
        immediate_cleanup: bool = False,
    ) -> TikTokSessionResponse:
        """Create a new TikTok session with login detection."""
        del request  # Payload currently unused but kept for parity with signature
        session_id = str(uuid.uuid4())
        executor: Optional[TiktokExecutor] = None

        try:
            config = await self._load_tiktok_config(user_data_dir)
            executor = TiktokExecutor(config)
            await executor.start_session()

            login_state = await self._detect_login_state(executor, config, config.login_detection_timeout)
            if login_state == TikTokLoginState.LOGGED_OUT:
                await self._safe_cleanup_executor(executor)
                return self._error_response(
                    message="Not logged in to TikTok",
                    code="NOT_LOGGED_IN",
                    details={
                        "details": "User is not logged in to TikTok",
                        "method": "dom_api_combo",
                        "timeout": config.login_detection_timeout,
                    },
                )

            if immediate_cleanup:
                await self._safe_cleanup_executor(executor)
            else:
                record = SessionRecord(
                    id=session_id,
                    executor=executor,
                    config=config,
                    login_state=login_state,
                    user_data_dir=executor.user_data_dir,
                )
                self.sessions.register(record)

            return TikTokSessionResponse(status="success", message="TikTok session established successfully")
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("[TiktokService] Failed to create session: %s", exc, exc_info=True)
            if executor is not None:
                await self._safe_cleanup_executor(executor)
            self.sessions.remove(session_id)
            return self._error_response(
                message="Failed to create TikTok session",
                code="SESSION_CREATION_FAILED",
                details={"method": "internal_error", "details": str(exc)},
            )

    async def has_active_session(self) -> bool:
        """Return True when at least one logged-in session is available."""
        count = len(self.sessions)
        self.logger.debug(
            "[TiktokService] has_active_session called - current sessions: %s, result: %s",
            count,
            bool(count),
        )
        return bool(count)

    async def get_active_session(self) -> Optional[TiktokExecutor]:
        """Return the executor for the first active session, if any."""
        first_pair = next(self.sessions.items(), None)
        self.logger.debug(
            "[TiktokService] get_active_session called - available sessions: %s",
            len(self.sessions),
        )
        if first_pair is None:
            self.logger.debug("[TiktokService] No active session available")
            return None
        session_id, record = first_pair
        self.logger.debug("[TiktokService] Returning active session: %s", session_id)
        return record.executor

    async def close_session(self, session_id: str) -> bool:
        """Close and cleanup an active TikTok session."""
        self.logger.debug("[TiktokService] Attempting to close session: %s", session_id)
        record = self.sessions.remove(session_id)
        if record is None:
            self.logger.warning("[TiktokService] Session %s not found in active sessions", session_id)
            return False
        await self._safe_cleanup_executor(record.executor)
        self.logger.debug("[TiktokService] Successfully closed session: %s", session_id)
        return True

    async def keep_alive(self, session_id: str) -> bool:
        """Refresh the last-activity timestamp for a session if it is still active."""
        record = self.sessions.get(session_id)
        if record is None:
            return False
        if not await record.executor.is_still_active():
            await self._cleanup_session(session_id)
            return False
        record.touch()
        return True

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return combined metadata and executor info for the given session."""
        self.logger.debug("[TiktokService] Getting session info for: %s", session_id)
        record = self.sessions.get(session_id)
        if record is None:
            self.logger.warning("[TiktokService] Session %s not found", session_id)
            return None
        try:
            session_info = await record.executor.get_session_info()
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error(
                "[TiktokService] Error getting session info for %s: %s",
                session_id,
                exc,
                exc_info=True,
            )
            return None
        metadata = record.to_metadata()
        metadata.update(session_info)
        metadata["timeout_remaining"] = record.timeout_remaining()
        self.logger.debug("[TiktokService] Session %s info retrieved successfully", session_id)
        return metadata

    async def perform_action(self, session_id: str, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Perform an action using an active TikTok session."""
        self.logger.debug(
            "[TiktokService] Performing action '%s' on session '%s' with args: %s",
            action,
            session_id,
            kwargs,
        )
        record = self.sessions.get(session_id)
        if record is None:
            self.logger.warning("[TiktokService] Session %s not found for action '%s'", session_id, action)
            return {"error": "Session not found"}

        record.touch()
        executor = record.executor
        if hasattr(executor, action):
            try:
                method = getattr(executor, action)
                result = await method(**kwargs)
                self.logger.debug("[TiktokService] Action '%s' completed successfully", action)
                return {"success": True, "result": result}
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.error(
                    "[TiktokService] Exception performing action '%s' on session %s: %s",
                    action,
                    session_id,
                    exc,
                    exc_info=True,
                )
                return {"error": str(exc)}
        self.logger.warning("[TiktokService] Unknown action '%s' requested", action)
        return {"error": f"Unknown action: {action}"}

    async def check_session_timeout(self, session_id: str) -> bool:
        """Return True when the session has exceeded its allowed lifetime."""
        record = self.sessions.get(session_id)
        if record is None:
            return True
        return record.timeout_remaining() <= 0

    async def _load_tiktok_config(self, user_data_dir: Optional[str] = None) -> TikTokSessionConfig:
        """Load TikTok configuration from settings and optional overrides."""
        base_user_data_dir = user_data_dir or self.settings.camoufox_user_data_dir or "./user_data"
        headless = bool(getattr(self.settings, "default_headless", True))
        try:
            current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
            norm = current_test.replace("\\", "/").lower()
            if "/tests/unit/" in norm or "tests/unit/" in norm:
                headless = True
        except Exception:  # pragma: no cover - defensive fallback
            headless = bool(getattr(self.settings, "default_headless", True))

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
        self,
        executor: TiktokExecutor,
        config: TikTokSessionConfig,
        timeout: int,
    ) -> TikTokLoginState:
        """Detect login state using the executor."""
        if not executor.browser:
            return TikTokLoginState.UNCERTAIN
        detector = LoginDetector(executor.browser, config)
        return await detector.detect_login_state(timeout=timeout)

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources."""
        record = self.sessions.remove(session_id)
        if record is None:
            return
        await self._safe_cleanup_executor(record.executor)

    async def _safe_cleanup_executor(self, executor: TiktokExecutor) -> None:
        """Best-effort cleanup for executors, with defensive logging."""
        try:
            await executor.cleanup()
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.warning("[TiktokService] Executor cleanup failed: %s", exc, exc_info=True)

    def _error_response(self, *, message: str, code: str, details: Optional[Dict[str, Any]] = None) -> TikTokSessionResponse:
        """Helper for building error responses with consistent structure."""
        payload: Dict[str, Any] = {"code": code}
        if details:
            payload.update(details)
        return TikTokSessionResponse(status="error", message=message, error_details=payload)

    async def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Return information about all active sessions."""
        sessions_info: Dict[str, Dict[str, Any]] = {}
        for session_id in list(self.sessions.ids()):
            session_info = await self.get_session_info(session_id)
            if session_info:
                sessions_info[session_id] = session_info
            else:
                await self._cleanup_session(session_id)
        return sessions_info

    async def cleanup_all_sessions(self) -> None:
        """Clean up all active sessions."""
        for session_id in list(self.sessions.ids()):
            await self._cleanup_session(session_id)
