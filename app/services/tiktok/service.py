"""
TikTok session service
"""
import asyncio
import os
import logging
import uuid
from typing import Dict, Any, Optional, Literal, Union, List
from datetime import datetime, timedelta
from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.tiktok.utils.login_detection import LoginDetector
from app.schemas.tiktok import TikTokSessionRequest, TikTokSessionResponse, TikTokLoginState, TikTokSessionConfig
from app.core.config import get_settings
from app.services.tiktok.search_service import TikTokSearchService

class TiktokService:
    """TikTok session management service"""
    def __init__(self):
        self.settings = get_settings()
        self.active_sessions: Dict[str, TiktokExecutor] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    async def create_session(self, request: TikTokSessionRequest, user_data_dir: Optional[str] = None, immediate_cleanup: bool = False) -> TikTokSessionResponse:
        """
        Create a new TikTok session with login detection
        Args:
            request: TikTok session request (empty body)
            user_data_dir: Optional user data directory path
        Returns:
            TikTokSessionResponse: Session creation result
        """
        session_id = str(uuid.uuid4())
        try:
            # Load TikTok configuration
            config = await self._load_tiktok_config(user_data_dir)
            # Create executor instance
            executor = TiktokExecutor(config)
            # Start browser session
            await executor.start_session()
            # Detect login state
            login_state = await self._detect_login_state(executor, config.login_detection_timeout)
            if login_state == TikTokLoginState.LOGGED_OUT:
                # User not logged in - close session and return 409
                await executor.cleanup()
                return TikTokSessionResponse(
                    status="error",
                    message="Not logged in to TikTok",
                    error_details={
                        "code": "NOT_LOGGED_IN",
                        "details": "User is not logged in to TikTok",
                        "method": "dom_api_combo",
                        "timeout": config.login_detection_timeout
                    }
                )
            # Session created successfully
            if not immediate_cleanup:
                self.active_sessions[session_id] = executor
                self.session_metadata[session_id] = {
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "user_data_dir": executor.user_data_dir,
                    "config": config,
                    "login_state": login_state
                }
            response = TikTokSessionResponse(
                status="success",
                message="TikTok session established successfully"
            )
            # If immediate cleanup is requested, clean up now
            if immediate_cleanup:
                await executor.cleanup()
            return response
        except Exception as e:
            await self._cleanup_session(session_id)
            return TikTokSessionResponse(
                status="error",
                message="Failed to create TikTok session",
                error_details={
                    "code": "SESSION_CREATION_FAILED",
                    "details": str(e),
                    "method": "internal_error"
                }
            )
    async def has_active_session(self) -> bool:
        """
        Check if there is an active TikTok session
        Returns:
            bool: True if there is an active session, False otherwise
        """
        # For now, we'll check if there are any active sessions
        # In a more complex implementation, we might want to check session validity
        has_session = len(self.active_sessions) > 0
        self.logger.debug(f"[TiktokService] has_active_session called - current sessions: {len(self.active_sessions)}, result: {has_session}")
        return has_session
    async def get_active_session(self) -> Optional[TiktokExecutor]:
        """
        Get the active TikTok session executor
        Returns:
            TiktokExecutor: The active session executor or None if no active session
        """
        # For now, we'll return the first active session
        # In a more complex implementation, we might want to select based on criteria
        session_count = len(self.active_sessions)
        self.logger.debug(f"[TiktokService] get_active_session called - available sessions: {session_count}")
        if self.active_sessions:
            # Get the first session
            session_id = next(iter(self.active_sessions))
            self.logger.debug(f"[TiktokService] Returning active session: {session_id}")
            return self.active_sessions[session_id]
        self.logger.debug(f"[TiktokService] No active session available")
        return None
    async def search_tiktok(self, query: Union[str, List[str]], num_videos: int = 50, sort_type: str = "RELEVANCE", recency_days: str = "ALL") -> Dict[str, Any]:
        """Delegate to TikTokSearchService to execute the search."""
        self.logger.debug(f"[TiktokService] search_tiktok called - query: {query}, num_videos: {num_videos}, sort_type: {sort_type}, recency_days: {recency_days}")
        
        # Check if there's an active session
        if not await self.has_active_session():
            self.logger.debug(f"[TiktokService] No active session found, returning error")
            return {
                "error": {
                    "code": "NOT_LOGGED_IN",
                    "message": "TikTok session is not logged in"
                }
            }
        
        try:
            # Execute search (search operates independently of sessions)
            self.logger.debug(f"[TiktokService] Creating TikTokSearchService and executing independent search")
            search_service = TikTokSearchService(self)
            result = await search_service.search(query, num_videos=num_videos, sort_type=sort_type, recency_days=recency_days)
            self.logger.debug(f"[TiktokService] Search completed successfully - total results: {len(result.get('results', []))}")
            return result
        except Exception as e:
            self.logger.error(f"[TiktokService] Exception in search_tiktok: {e}", exc_info=True)
            return {"error": f"Search failed: {str(e)}"}
    # Search helpers moved to app.services.tiktok.search_service
    async def close_session(self, session_id: str) -> bool:
        """
        Close an active TikTok session
        Args:
            session_id: Session ID to close
        Returns:
            bool: True if session was closed successfully
        """
        self.logger.debug(f"[TiktokService] Attempting to close session: {session_id}")
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"[TiktokService] Session {session_id} not found in active sessions")
                return False
            executor = self.active_sessions[session_id]
            await executor.cleanup()
            # Remove from active sessions
            del self.active_sessions[session_id]
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            self.logger.debug(f"[TiktokService] Successfully closed session: {session_id}")
            return True
        except Exception as e:
            self.logger.error(f"[TiktokService] Error closing session {session_id}: {e}", exc_info=True)
            return False
    async def keep_alive(self, session_id: str) -> bool:
        """
        Keep session alive by updating activity timestamp
        Args:
            session_id: Session ID to keep alive
        Returns:
            bool: True if session was found and kept alive
        """
        try:
            if session_id not in self.active_sessions:
                return False
            # Check if session is still active
            executor = self.active_sessions[session_id]
            if not await executor.is_still_active():
                await self.close_session(session_id)
                return False
            # Update last activity time
            self.session_metadata[session_id]["last_activity"] = datetime.now()
            return True
        except Exception:
            return False
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an active session
        Args:
            session_id: Session ID to query
        Returns:
            Dict with session information or None if not found
        """
        self.logger.debug(f"[TiktokService] Getting session info for: {session_id}")
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"[TiktokService] Session {session_id} not found")
                return None
            executor = self.active_sessions[session_id]
            metadata = self.session_metadata[session_id]
            self.logger.debug(f"[TiktokService] Session {session_id} metadata: {metadata}")
            session_info = await executor.get_session_info()
            result = {
                **metadata,
                **session_info,
                "timeout_remaining": self._get_timeout_remaining(metadata)
            }
            self.logger.debug(f"[TiktokService] Session {session_id} info retrieved successfully")
            return result
        except Exception as e:
            self.logger.error(f"[TiktokService] Error getting session info for {session_id}: {e}", exc_info=True)
            return None
    async def perform_action(self, session_id: str, action: str, **kwargs) -> Dict[str, Any]:
        """
        Perform an action using an active TikTok session
        Args:
            session_id: Session ID to use
            action: Action to perform
            **kwargs: Action-specific parameters
        Returns:
            Dict with action result
        """
        self.logger.debug(f"[TiktokService] Performing action '{action}' on session '{session_id}' with args: {kwargs}")
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"[TiktokService] Session {session_id} not found for action '{action}'")
                return {"error": "Session not found"}
            executor = self.active_sessions[session_id]
            # Update last activity
            self.session_metadata[session_id]["last_activity"] = datetime.now()
            self.logger.debug(f"[TiktokService] Updated last activity for session {session_id}")
            # Perform the action
            if hasattr(executor, action):
                method = getattr(executor, action)
                self.logger.debug(f"[TiktokService] Found method '{action}' on executor")
                result = await method(**kwargs)
                self.logger.debug(f"[TiktokService] Action '{action}' completed successfully")
                return {"success": True, "result": result}
            else:
                self.logger.warning(f"[TiktokService] Unknown action '{action}' requested")
                return {"error": f"Unknown action: {action}"}
        except Exception as e:
            self.logger.error(f"[TiktokService] Exception performing action '{action}' on session {session_id}: {e}", exc_info=True)
            return {"error": str(e)}
    async def check_session_timeout(self, session_id: str) -> bool:
        """
        Check if a session has timed out
        Args:
            session_id: Session ID to check
        Returns:
            bool: True if session has timed out
        """
        try:
            if session_id not in self.session_metadata:
                return True
            metadata = self.session_metadata[session_id]
            timeout_remaining = self._get_timeout_remaining(metadata)
            return timeout_remaining <= 0
        except Exception:
            return True
    async def _load_tiktok_config(self, user_data_dir: Optional[str] = None) -> TikTokSessionConfig:
        """Load TikTok configuration from settings"""
        # Use CAMOUFOX_USER_DATA_DIR for both master and clones directories
        base_user_data_dir = self.settings.camoufox_user_data_dir or "./user_data"
        # Headless policy:
        # - Default aligns with global HEADLESS setting (settings.default_headless)
        # - Unit tests (some) force headless
        headless = bool(getattr(self.settings, "default_headless", True))
        try:
            # Detect pytest and only enable headless for unit tests path
            current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
            norm = current_test.replace("\\", "/").lower()
            if "/tests/unit/" in norm or "tests/unit/" in norm:
                headless = True
        except Exception:
            headless = bool(getattr(self.settings, "default_headless", True))
        return TikTokSessionConfig(
            user_data_master_dir=base_user_data_dir,
            user_data_clones_dir=base_user_data_dir,
            write_mode_enabled=self.settings.tiktok_write_mode_enabled,
            acquire_lock_timeout=30,
            login_detection_timeout=self.settings.tiktok_login_detection_timeout,
            max_session_duration=self.settings.tiktok_max_session_duration,
            tiktok_url=self.settings.tiktok_url,
            headless=headless
        )
    async def _detect_login_state(self, executor: TiktokExecutor, timeout: int) -> TikTokLoginState:
        """Detect login state using the executor"""
        if not executor.browser:
            return TikTokLoginState.UNCERTAIN
        detector = LoginDetector(executor.browser, await self._load_tiktok_config())
        return await detector.detect_login_state(timeout)
    def _get_timeout_remaining(self, metadata: Dict[str, Any]) -> int:
        """Calculate timeout remaining for a session"""
        created_at = metadata["created_at"]
        last_activity = metadata["last_activity"]
        max_duration = metadata["config"].max_session_duration
        # Use the later of creation time or last activity
        time_reference = max(created_at, last_activity)
        timeout_at = time_reference + timedelta(seconds=max_duration)
        now = datetime.now()
        return max(0, int((timeout_at - now).total_seconds()))
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources"""
        try:
            if session_id in self.active_sessions:
                await self.close_session(session_id)
        except Exception as e:
            print(f"Error cleaning up session {session_id}: {e}")
    async def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions"""
        sessions_info = {}
        for session_id in list(self.active_sessions.keys()):
            session_info = await self.get_session_info(session_id)
            if session_info:
                sessions_info[session_id] = session_info
            else:
                # Session no longer active, clean it up
                await self._cleanup_session(session_id)
        return sessions_info
    async def cleanup_all_sessions(self) -> None:
        """Clean up all active sessions"""
        for session_id in list(self.active_sessions.keys()):
            await self._cleanup_session(session_id)

