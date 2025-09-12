"""
TikTok session service
"""
import asyncio
import os
import uuid
from typing import Dict, Any, Optional, Literal, Union, List
from datetime import datetime, timedelta

from app.services.tiktok.tiktok_executor import TiktokExecutor
from app.services.tiktok.utils.login_detection import LoginDetector
from app.schemas.tiktok import TikTokSessionRequest, TikTokSessionResponse, TikTokLoginState, TikTokSessionConfig
from app.core.config import get_settings


class TiktokService:
    """TikTok session management service"""
    
    def __init__(self):
        self.settings = get_settings()
        self.active_sessions: Dict[str, TiktokExecutor] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
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
        return len(self.active_sessions) > 0
    
    async def get_active_session(self) -> Optional[TiktokExecutor]:
        """
        Get the active TikTok session executor
        
        Returns:
            TiktokExecutor: The active session executor or None if no active session
        """
        # For now, we'll return the first active session
        # In a more complex implementation, we might want to select based on criteria
        if self.active_sessions:
            # Get the first session
            session_id = next(iter(self.active_sessions))
            return self.active_sessions[session_id]
        return None
    
    async def search_tiktok(self, query: Union[str, List[str]], num_videos: int = 50, sort_type: str = "RELEVANCE", recency_days: str = "ALL") -> Dict[str, Any]:
        """
        Perform a TikTok search using the active session's user data.

        - Navigates directly to TikTok search results pages.
        - Collects HTML and parses videos using BeautifulSoup heuristics.
        - Supports multi-query aggregation with deduplication.
        """
        from urllib.parse import quote_plus
        from app.services.tiktok.parser import extract_video_data_from_html
        from app.services.common.adapters.scrapling_fetcher import ScraplingFetcherAdapter, FetchArgComposer
        from app.services.common.browser.camoufox import CamoufoxArgsBuilder

        # Enforce sort type (v1)
        if str(sort_type or "").upper() != "RELEVANCE":
            return {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Unsupported sortType; only RELEVANCE is supported",
                    "fields": {"sortType": "Must be 'RELEVANCE'"},
                }
            }

        # Normalize and validate query input
        if isinstance(query, list):
            queries = [str(x).strip() for x in query if str(x or "").strip()]
            if not queries:
                return {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Query array cannot be empty",
                        "fields": {"query": "Provide at least one non-empty string"},
                    }
                }
        else:
            q = str(query or "").strip()
            if not q:
                return {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid request parameters",
                        "fields": {"query": "Query cannot be empty"},
                    }
                }
            queries = [q]

        # Gate on active session
        if not await self.has_active_session():
            return {
                "error": {
                    "code": "NOT_LOGGED_IN",
                    "message": "TikTok session is not logged in",
                    "details": {"method": "dom_api_combo", "timeout": 8},
                }
            }
        session = await self.get_active_session()
        if not session:
            return {
                "error": {
                    "code": "NOT_LOGGED_IN",
                    "message": "TikTok session is not logged in",
                    "details": {"method": "dom_api_combo", "timeout": 8},
                }
            }

        # Prepare fetcher to reuse session cookies via user_data_dir
        settings = self.settings
        fetcher = ScraplingFetcherAdapter()
        composer = FetchArgComposer()
        camoufox_builder = CamoufoxArgsBuilder()

        # Carry Camoufox defaults (locale/window) but pin to existing user_data_dir
        try:
            _, extra_headers = camoufox_builder.build(type("Mock", (), {"force_user_data": False})(), settings, fetcher.detect_capabilities())
        except Exception:
            extra_headers = None
        # Reuse the executor's user data dir when available; otherwise skip to defaults
        user_data_dir = getattr(session, "user_data_dir", None) or getattr(settings, "camoufox_user_data_dir", None)
        additional_args = {"user_data_dir": user_data_dir} if user_data_dir else {}

        options = {
            "headless": True if getattr(settings, "default_headless", True) else False,
            "network_idle": False,
            "wait_for_selector": None,  # Keep light waits to avoid hangs
            "timeout_seconds": 30,
        }

        # Aggregate across queries with dedupe
        seen_ids = set()
        seen_urls = set()
        aggregated: List[Dict[str, Any]] = []

        base_url = str(settings.tiktok_url or "https://www.tiktok.com/").rstrip("/")

        for q in queries:
            try:
                search_url = f"{base_url}/search/video?q={quote_plus(q)}"
                caps = fetcher.detect_capabilities()
                # Optional page action: short scroll to render more items
                page_action = None
                try:
                    if getattr(caps, "supports_page_action", False):
                        from app.services.browser.actions.scroll import ScrollDownAction
                        page_action = ScrollDownAction(duration_s=10.0, step_px=600, interval_s=1.0, settle_s=1.0,
                                                       wait_selector="a[href*='/video/']")
                except Exception:
                    page_action = None

                fetch_kwargs = composer.compose(
                    options=options,
                    caps=caps,
                    selected_proxy=getattr(settings, "private_proxy_url", None) or None,
                    additional_args=additional_args,
                    extra_headers=extra_headers,
                    settings=settings,
                    page_action=page_action,
                )
                page = fetcher.fetch(search_url, fetch_kwargs)
                status_code = int(getattr(page, "status", 0) or 0)
                html = getattr(page, "html_content", "") or ""
                if status_code < 200 or status_code >= 300 or not html:
                    continue

                items = extract_video_data_from_html(html) or []
                for item in items:
                    vid = str(item.get("id", "") or "")
                    url = str(item.get("webViewUrl", "") or "")
                    if vid and vid not in seen_ids:
                        seen_ids.add(vid)
                        if url:
                            seen_urls.add(url)
                        aggregated.append(item)
                    elif (not vid) and url and (url not in seen_urls):
                        seen_urls.add(url)
                        aggregated.append(item)

                if len(aggregated) >= int(num_videos):
                    break
            except Exception:
                # Continue with next query on failures
                continue

        limit = max(0, min(int(num_videos), 50))
        final_results = aggregated[:limit]
        normalized_query = " ".join(queries)

        return {
            "results": final_results,
            "totalResults": len(final_results),
            "query": normalized_query,
        }
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close an active TikTok session
        
        Args:
            session_id: Session ID to close
            
        Returns:
            bool: True if session was closed successfully
        """
        try:
            if session_id not in self.active_sessions:
                return False
                
            executor = self.active_sessions[session_id]
            await executor.cleanup()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
                
            return True
            
        except Exception as e:
            print(f"Error closing session {session_id}: {e}")
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
        try:
            if session_id not in self.active_sessions:
                return None
                
            executor = self.active_sessions[session_id]
            metadata = self.session_metadata[session_id]
            
            session_info = await executor.get_session_info()
            
            return {
                **metadata,
                **session_info,
                "timeout_remaining": self._get_timeout_remaining(metadata)
            }
            
        except Exception as e:
            print(f"Error getting session info for {session_id}: {e}")
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
        try:
            if session_id not in self.active_sessions:
                return {"error": "Session not found"}
                
            executor = self.active_sessions[session_id]
            
            # Update last activity
            self.session_metadata[session_id]["last_activity"] = datetime.now()
            
            # Perform the action
            if hasattr(executor, action):
                method = getattr(executor, action)
                result = await method(**kwargs)
                return {"success": True, "result": result}
            else:
                return {"error": f"Unknown action: {action}"}
                
        except Exception as e:
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
        # - Default: headful (False)
        # - Unit tests only: headless (True)
        # - Overrideable via TIKTOK_SESSION_HEADLESS env var
        headless = False
        try:
            override = os.getenv("TIKTOK_SESSION_HEADLESS")
            if override is not None:
                headless = str(override).lower() in {"1", "true", "yes"}
            else:
                # Detect pytest and only enable headless for unit tests path
                current_test = os.environ.get("PYTEST_CURRENT_TEST", "")
                norm = current_test.replace("\\", "/").lower()
                if "/tests/unit/" in norm or "tests/unit/" in norm:
                    headless = True
        except Exception:
            headless = False
        
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
