"""TikTok session service"""

import logging
from typing import Dict, Any, Optional, Union, List

from app.core.config import get_settings
from app.schemas.tiktok import TikTokSessionRequest, TikTokSessionResponse
from app.services.tiktok.actions import dispatch_action
from app.services.tiktok.search_service import TikTokSearchService
from app.services.tiktok.session_manager import TikTokSessionManager, TikTokSessionMetadata
from app.services.tiktok.tiktok_executor import TiktokExecutor


class TiktokService:
    """TikTok session management service"""

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        self.session_manager = TikTokSessionManager(self.settings, logger=self.logger)

    @property
    def active_sessions(self) -> Dict[str, TiktokExecutor]:
        """Expose active sessions dictionary for compatibility"""
        return self.session_manager.active_sessions

    @active_sessions.setter
    def active_sessions(self, value: Dict[str, TiktokExecutor]) -> None:
        self.session_manager.active_sessions = value

    @property
    def session_metadata(self) -> Dict[str, TikTokSessionMetadata]:
        """Expose session metadata dictionary for compatibility"""
        return self.session_manager.session_metadata

    @session_metadata.setter
    def session_metadata(self, value: Dict[str, TikTokSessionMetadata]) -> None:
        self.session_manager.session_metadata = value

    async def create_session(
        self, request: TikTokSessionRequest, user_data_dir: Optional[str] = None, immediate_cleanup: bool = False
    ) -> TikTokSessionResponse:
        """
        Create a new TikTok session with login detection
        Args:
            request: TikTok session request (empty body)
            user_data_dir: Optional user data directory path
        Returns:
            TikTokSessionResponse: Session creation result
        """
        return await self.session_manager.create_session(
            request, user_data_dir=user_data_dir, immediate_cleanup=immediate_cleanup
        )

    async def has_active_session(self) -> bool:
        """
        Check if there is an active TikTok session
        Returns:
            bool: True if there is an active session, False otherwise
        """
        has_session = len(self.active_sessions) > 0
        self.logger.debug(
            f"[TiktokService] has_active_session called - current sessions: {len(self.active_sessions)}, "
            f"result: {has_session}"
        )
        return has_session

    async def get_active_session(self) -> Optional[TiktokExecutor]:
        """
        Get the active TikTok session executor
        Returns:
            TiktokExecutor: The active session executor or None if no active session
        """
        session_count = len(self.active_sessions)
        self.logger.debug(f"[TiktokService] get_active_session called - available sessions: {session_count}")
        if self.active_sessions:
            session_id = next(iter(self.active_sessions))
            self.logger.debug(f"[TiktokService] Returning active session: {session_id}")
            return self.active_sessions[session_id]
        self.logger.debug("[TiktokService] No active session available")
        return None

    async def search_tiktok(
        self, query: Union[str, List[str]], num_videos: int = 50, sort_type: str = "RELEVANCE", recency_days: str = "ALL"
    ) -> Dict[str, Any]:
        """Delegate to TikTokSearchService to execute the search."""
        self.logger.debug(
            f"[TiktokService] search_tiktok called - query: {query}, num_videos: {num_videos}, "
            f"sort_type: {sort_type}, recency_days: {recency_days}"
        )

        if not await self.has_active_session():
            self.logger.debug("[TiktokService] No active session found, returning error")
            return {
                "error": {
                    "code": "NOT_LOGGED_IN",
                    "message": "TikTok session is not logged in"
                }
            }

        try:
            self.logger.debug("[TiktokService] Creating TikTokSearchService and executing independent search")
            search_service = TikTokSearchService(self)
            result = await search_service.search(
                query, num_videos=num_videos, sort_type=sort_type, recency_days=recency_days
            )
            self.logger.debug(
                f"[TiktokService] Search completed successfully - total results: "
                f"{len(result.get('results', []))}"
            )
            return result
        except Exception as e:
            self.logger.error(f"[TiktokService] Exception in search_tiktok: {e}", exc_info=True)
            return {"error": f"Search failed: {str(e)}"}

    async def close_session(self, session_id: str) -> bool:
        """
        Close an active TikTok session
        Args:
            session_id: Session ID to close
        Returns:
            bool: True if session was closed successfully
        """
        self.logger.debug(f"[TiktokService] Attempting to close session: {session_id}")
        return await self.session_manager.close_session(session_id)

    async def keep_alive(self, session_id: str) -> bool:
        """
        Keep session alive by updating activity timestamp
        Args:
            session_id: Session ID to keep alive
        Returns:
            bool: True if session was found and kept alive
        """
        return await self.session_manager.keep_alive(session_id)

    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an active session
        Args:
            session_id: Session ID to query
        Returns:
            Dict with session information or None if not found
        """
        self.logger.debug(f"[TiktokService] Getting session info for: {session_id}")
        info = await self.session_manager.get_session_info(session_id)
        if info is None:
            self.logger.warning(f"[TiktokService] Session {session_id} not found")
        else:
            self.logger.debug(f"[TiktokService] Session {session_id} info retrieved successfully")
        return info

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
        self.logger.debug(
            f"[TiktokService] Performing action '{action}' on session '{session_id}' with args: {kwargs}"
        )
        try:
            if session_id not in self.active_sessions:
                self.logger.warning(f"[TiktokService] Session {session_id} not found for action '{action}'")
                return {"error": "Session not found"}
            executor = self.active_sessions[session_id]

            metadata = self.session_metadata.get(session_id)
            if metadata:
                metadata.touch()
                self.logger.debug(f"[TiktokService] Updated last activity for session {session_id}")

            result = await dispatch_action(executor, action, **kwargs)
            self.logger.debug(f"[TiktokService] Action '{action}' completed successfully")
            return {"success": True, "result": result}
        except AttributeError:
            self.logger.warning(f"[TiktokService] Unknown action '{action}' requested")
            return {"error": f"Unknown action: {action}"}
        except Exception as e:
            self.logger.error(
                f"[TiktokService] Exception performing action '{action}' on session {session_id}: {e}",
                exc_info=True
            )
            return {"error": str(e)}

    async def check_session_timeout(self, session_id: str) -> bool:
        """
        Check if a session has timed out
        Args:
            session_id: Session ID to check
        Returns:
            bool: True if session has timed out
        """
        return await self.session_manager.check_session_timeout(session_id)

    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up session resources"""
        await self.session_manager.cleanup_session(session_id)

    async def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions"""
        return await self.session_manager.get_active_sessions()

    async def cleanup_all_sessions(self) -> None:
        """Clean up all active sessions"""
        await self.session_manager.cleanup_all_sessions()
