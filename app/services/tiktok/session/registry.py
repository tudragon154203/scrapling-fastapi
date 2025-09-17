"""Utilities for tracking TikTok scraping sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple

from app.schemas.tiktok.session import TikTokLoginState, TikTokSessionConfig
from app.services.tiktok.tiktok_executor import TiktokExecutor


@dataclass
class SessionRecord:
    """Lightweight container holding executor state and metadata."""

    id: str
    executor: TiktokExecutor
    config: TikTokSessionConfig
    login_state: TikTokLoginState
    user_data_dir: Optional[str]
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def touch(self) -> None:
        """Refresh the last-activity timestamp for the session."""
        self.last_activity = datetime.now()

    def timeout_remaining(self) -> int:
        """Return the remaining number of seconds before the session expires."""
        window = timedelta(seconds=int(self.config.max_session_duration))
        timeout_at = max(self.created_at, self.last_activity) + window
        return max(0, int((timeout_at - datetime.now()).total_seconds()))

    def to_metadata(self) -> Dict[str, Any]:
        """Expose a dict view compatible with legacy metadata payloads."""
        return {
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "user_data_dir": self.user_data_dir,
            "config": self.config,
            "login_state": self.login_state,
        }


class SessionRegistry:
    """In-memory registry for tracking active TikTok scraping sessions."""

    def __init__(self) -> None:
        self._records: Dict[str, SessionRecord] = {}

    def register(self, record: SessionRecord) -> None:
        """Insert or replace a session record."""
        self._records[record.id] = record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        """Return the record for the given session identifier."""
        return self._records.get(session_id)

    def remove(self, session_id: str) -> Optional[SessionRecord]:
        """Remove and return the record associated with *session_id*."""
        return self._records.pop(session_id, None)

    def first(self) -> Optional[SessionRecord]:
        """Return the first registered session record, if any exist."""
        return next(iter(self._records.values()), None)

    def clear(self) -> None:
        """Remove all registered sessions."""
        self._records.clear()

    def __len__(self) -> int:  # pragma: no cover - trivial delegation
        return len(self._records)

    def __bool__(self) -> bool:  # pragma: no cover - trivial delegation
        return bool(self._records)

    def items(self) -> Iterator[Tuple[str, SessionRecord]]:
        """Iterate over `(session_id, record)` pairs."""
        return iter(self._records.items())

    def values(self) -> Iterator[SessionRecord]:
        """Iterate over the registered session records."""
        return iter(self._records.values())

    def ids(self) -> Iterable[str]:
        """Return a snapshot list of active session identifiers."""
        return list(self._records.keys())
