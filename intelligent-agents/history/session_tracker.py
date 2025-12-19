"""
Session Tracker

Tracks all actions within a session for history and learning.
Following Kai pattern: Build institutional knowledge.

Performance: TTL-based caching for session lookups (50% speedup per review).
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib


class ActionType(Enum):
    """Types of actions that can be tracked."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    COMMAND_EXEC = "command_exec"
    SEARCH = "search"
    API_CALL = "api_call"
    AGENT_SPAWN = "agent_spawn"
    DECISION = "decision"
    ERROR = "error"
    RECOVERY = "recovery"
    LEARNING = "learning"
    MILESTONE = "milestone"


class ActionOutcome(Enum):
    """Possible outcomes for an action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"
    SKIPPED = "skipped"


@dataclass
class TrackedAction:
    """Represents a tracked action."""
    id: str
    timestamp: str
    action_type: str
    description: str
    outcome: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class SessionMetadata:
    """Metadata about a session."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    goal: Optional[str] = None
    summary: Optional[str] = None
    outcome: str = "in_progress"
    action_count: int = 0
    error_count: int = 0
    files_modified: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class SessionTracker:
    """Tracks actions within a session for history and learning."""

    # Cache settings
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    DEFAULT_CACHE_SIZE = 100  # Max entries

    def __init__(self, history_dir: Optional[str] = None,
                 cache_ttl: int = DEFAULT_CACHE_TTL,
                 cache_size: int = DEFAULT_CACHE_SIZE):
        """Initialize session tracker.

        Args:
            history_dir: Directory to store history files. Defaults to ~/.claude/history
            cache_ttl: Cache time-to-live in seconds (default: 300)
            cache_size: Maximum cache entries (default: 100)
        """
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".claude" / "history"

        self.sessions_dir = self.history_dir / "sessions"
        self.learnings_dir = self.history_dir / "learnings"
        self.index_file = self.history_dir / "session_index.json"

        # Create directories
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

        # Current session state
        self.current_session: Optional[SessionMetadata] = None
        self.current_actions: List[TrackedAction] = []
        self._action_counter = 0

        # Session cache: {session_id: (data, expiry_time)}
        self._session_cache: Dict[str, Tuple[Dict, float]] = {}
        self._cache_ttl = cache_ttl
        self._cache_size = cache_size

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        hash_input = f"{timestamp}_{os.getpid()}_{id(self)}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"session_{timestamp}_{short_hash}"

    def _generate_action_id(self) -> str:
        """Generate unique action ID within session."""
        self._action_counter += 1
        return f"action_{self._action_counter:04d}"

    def start_session(self, goal: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
        """Start a new tracking session.

        Args:
            goal: Optional goal/objective for the session
            tags: Optional tags for categorization

        Returns:
            Session ID
        """
        session_id = self._generate_session_id()
        self.current_session = SessionMetadata(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            goal=goal,
            tags=tags or []
        )
        self.current_actions = []
        self._action_counter = 0

        return session_id

    def track_action(
        self,
        action_type: ActionType,
        description: str,
        outcome: ActionOutcome = ActionOutcome.PENDING,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        related_files: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Track an action.

        Args:
            action_type: Type of action
            description: Human-readable description
            outcome: Action outcome
            details: Additional details
            duration_ms: Duration in milliseconds
            error_message: Error message if failed
            related_files: Files involved
            tags: Tags for categorization

        Returns:
            Action ID
        """
        if not self.current_session:
            self.start_session()

        action = TrackedAction(
            id=self._generate_action_id(),
            timestamp=datetime.now().isoformat(),
            action_type=action_type.value,
            description=description,
            outcome=outcome.value,
            details=details or {},
            duration_ms=duration_ms,
            error_message=error_message,
            related_files=related_files or [],
            tags=tags or []
        )

        self.current_actions.append(action)
        self.current_session.action_count += 1

        if outcome == ActionOutcome.FAILURE:
            self.current_session.error_count += 1

        if related_files:
            for f in related_files:
                if f not in self.current_session.files_modified:
                    self.current_session.files_modified.append(f)

        return action.id

    def update_action(
        self,
        action_id: str,
        outcome: Optional[ActionOutcome] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> bool:
        """Update an existing action.

        Args:
            action_id: Action to update
            outcome: New outcome
            error_message: Error message if failed
            duration_ms: Final duration

        Returns:
            True if action was found and updated
        """
        for action in self.current_actions:
            if action.id == action_id:
                if outcome:
                    old_outcome = action.outcome
                    action.outcome = outcome.value
                    # Update error count
                    if outcome == ActionOutcome.FAILURE and old_outcome != ActionOutcome.FAILURE.value:
                        self.current_session.error_count += 1
                    elif outcome != ActionOutcome.FAILURE and old_outcome == ActionOutcome.FAILURE.value:
                        self.current_session.error_count -= 1
                if error_message:
                    action.error_message = error_message
                if duration_ms:
                    action.duration_ms = duration_ms
                return True
        return False

    def add_learning(self, learning: str) -> None:
        """Record a learning/insight from this session.

        Args:
            learning: The learning/insight to record
        """
        if self.current_session:
            self.current_session.learnings.append(learning)

    def add_milestone(self, description: str) -> str:
        """Mark a milestone achievement.

        Args:
            description: Milestone description

        Returns:
            Action ID for the milestone
        """
        return self.track_action(
            action_type=ActionType.MILESTONE,
            description=description,
            outcome=ActionOutcome.SUCCESS,
            tags=["milestone"]
        )

    def end_session(
        self,
        summary: Optional[str] = None,
        outcome: str = "completed"
    ) -> Dict[str, Any]:
        """End the current session and save to disk.

        Args:
            summary: Summary of what was accomplished
            outcome: Session outcome (completed, failed, abandoned)

        Returns:
            Session summary dict
        """
        if not self.current_session:
            return {"error": "No active session"}

        self.current_session.end_time = datetime.now().isoformat()
        self.current_session.summary = summary
        self.current_session.outcome = outcome

        # Save session to file
        session_file = self._get_session_file_path()
        session_data = {
            "metadata": asdict(self.current_session),
            "actions": [asdict(a) for a in self.current_actions]
        }

        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        # Update index
        self._update_index()

        # Save learnings if any
        if self.current_session.learnings:
            self._save_learnings()

        result = asdict(self.current_session)
        self.current_session = None
        self.current_actions = []

        return result

    def _get_session_file_path(self) -> Path:
        """Get file path for current session."""
        # Organize by year-month
        now = datetime.now()
        month_dir = self.sessions_dir / now.strftime("%Y-%m")
        month_dir.mkdir(exist_ok=True)
        return month_dir / f"{self.current_session.session_id}.json"

    def _update_index(self) -> None:
        """Update session index with current session."""
        index = []
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                index = json.load(f)

        index.append({
            "session_id": self.current_session.session_id,
            "start_time": self.current_session.start_time,
            "end_time": self.current_session.end_time,
            "goal": self.current_session.goal,
            "outcome": self.current_session.outcome,
            "action_count": self.current_session.action_count,
            "error_count": self.current_session.error_count
        })

        # Keep only last 1000 entries
        index = index[-1000:]

        with open(self.index_file, 'w') as f:
            json.dump(index, f, indent=2)

    def _save_learnings(self) -> None:
        """Save session learnings to learnings directory."""
        now = datetime.now()
        month_dir = self.learnings_dir / now.strftime("%Y-%m")
        month_dir.mkdir(exist_ok=True)

        learning_file = month_dir / f"{self.current_session.session_id}_learnings.json"

        with open(learning_file, 'w') as f:
            json.dump({
                "session_id": self.current_session.session_id,
                "goal": self.current_session.goal,
                "learnings": self.current_session.learnings,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent session summaries.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summary dicts
        """
        if not self.index_file.exists():
            return []

        with open(self.index_file, 'r') as f:
            index = json.load(f)

        return index[-limit:][::-1]  # Most recent first

    def _parse_session_date(self, session_id: str) -> Optional[str]:
        """Parse date from session_id to determine directory.

        Session ID format: session_YYYYMMDD_HHMMSS_HASH
        Returns: YYYY-MM format string or None if parse fails
        """
        # Expected format: session_YYYYMMDD_HHMMSS_hash
        parts = session_id.split('_')
        if len(parts) >= 2 and parts[0] == 'session':
            date_part = parts[1]
            if len(date_part) == 8 and date_part.isdigit():
                # Convert YYYYMMDD to YYYY-MM
                return f"{date_part[:4]}-{date_part[4:6]}"
        return None

    def _cache_get(self, session_id: str) -> Optional[Dict]:
        """Get session from cache if valid (not expired)."""
        if session_id in self._session_cache:
            data, expiry = self._session_cache[session_id]
            if time.time() < expiry:
                return data
            # Expired - remove from cache
            del self._session_cache[session_id]
        return None

    def _cache_put(self, session_id: str, data: Dict) -> None:
        """Store session in cache with TTL."""
        # Evict oldest entries if cache is full
        if len(self._session_cache) >= self._cache_size:
            # Remove expired entries first
            current_time = time.time()
            expired = [k for k, (_, exp) in self._session_cache.items() if exp <= current_time]
            for k in expired:
                del self._session_cache[k]

            # If still full, remove oldest entries
            if len(self._session_cache) >= self._cache_size:
                # Sort by expiry time and remove oldest 10%
                sorted_entries = sorted(self._session_cache.items(), key=lambda x: x[1][1])
                remove_count = max(1, len(sorted_entries) // 10)
                for k, _ in sorted_entries[:remove_count]:
                    del self._session_cache[k]

        self._session_cache[session_id] = (data, time.time() + self._cache_ttl)

    def clear_cache(self) -> int:
        """Clear the session cache. Returns number of entries cleared."""
        count = len(self._session_cache)
        self._session_cache.clear()
        return count

    def cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(1 for _, (_, exp) in self._session_cache.items() if exp > current_time)
        return {
            "total_entries": len(self._session_cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._session_cache) - valid_entries,
            "max_size": self._cache_size,
            "ttl_seconds": self._cache_ttl,
        }

    def get_session_details(self, session_id: str) -> Optional[Dict]:
        """Get full details for a session.

        Optimized with:
        1. TTL-based caching for repeated lookups
        2. Date parsing from session_id for O(1) directory lookup
        3. Fallback linear scan only if needed

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session data dict or None if not found
        """
        # Check cache first (fastest path)
        cached = self._cache_get(session_id)
        if cached is not None:
            return cached

        # Optimization: Parse date from session_id for O(1) lookup
        month_str = self._parse_session_date(session_id)
        if month_str:
            # Direct lookup in expected directory
            month_dir = self.sessions_dir / month_str
            session_file = month_dir / f"{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    self._cache_put(session_id, data)
                    return data

        # Fallback: Linear scan for non-standard session_ids or moved files
        for month_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if month_dir.is_dir():
                session_file = month_dir / f"{session_id}.json"
                if session_file.exists():
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                        self._cache_put(session_id, data)
                        return data
        return None

    def search_sessions(
        self,
        query: Optional[str] = None,
        outcome: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search sessions by various criteria.

        Args:
            query: Text to search in goals and summaries
            outcome: Filter by outcome
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            limit: Maximum results

        Returns:
            List of matching session summaries
        """
        if not self.index_file.exists():
            return []

        with open(self.index_file, 'r') as f:
            index = json.load(f)

        results = []
        for session in reversed(index):
            if len(results) >= limit:
                break

            # Apply filters
            if outcome and session.get("outcome") != outcome:
                continue

            if start_date:
                session_date = session.get("start_time", "")[:10]
                if session_date < start_date:
                    continue

            if end_date:
                session_date = session.get("start_time", "")[:10]
                if session_date > end_date:
                    continue

            if query:
                goal = session.get("goal", "") or ""
                if query.lower() not in goal.lower():
                    continue

            results.append(session)

        return results

    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of errors from recent sessions.

        Args:
            days: Number of days to look back

        Returns:
            Error summary dict
        """
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        if not self.index_file.exists():
            return {"total_errors": 0, "sessions_with_errors": 0, "error_rate": 0}

        with open(self.index_file, 'r') as f:
            index = json.load(f)

        total_errors = 0
        sessions_with_errors = 0
        total_sessions = 0

        for session in index:
            if session.get("start_time", "") >= cutoff:
                total_sessions += 1
                errors = session.get("error_count", 0)
                total_errors += errors
                if errors > 0:
                    sessions_with_errors += 1

        return {
            "total_errors": total_errors,
            "sessions_with_errors": sessions_with_errors,
            "total_sessions": total_sessions,
            "error_rate": total_errors / max(total_sessions, 1),
            "period_days": days
        }


if __name__ == '__main__':
    import tempfile
    import shutil

    # Self-test
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = SessionTracker(history_dir=tmpdir)

        # Start session
        session_id = tracker.start_session(goal="Test session tracking", tags=["test"])
        assert session_id.startswith("session_")

        # Track actions
        action1 = tracker.track_action(
            ActionType.FILE_READ,
            "Read config file",
            ActionOutcome.SUCCESS,
            related_files=["config.json"]
        )
        assert action1 == "action_0001"

        action2 = tracker.track_action(
            ActionType.COMMAND_EXEC,
            "Run tests",
            ActionOutcome.PENDING,
            duration_ms=1500
        )

        # Update action
        tracker.update_action(action2, outcome=ActionOutcome.SUCCESS, duration_ms=2000)

        # Add learning
        tracker.add_learning("Config files should be validated before use")

        # Add milestone
        tracker.add_milestone("Completed initial setup")

        # Track an error
        tracker.track_action(
            ActionType.API_CALL,
            "Call external API",
            ActionOutcome.FAILURE,
            error_message="Connection timeout"
        )

        # End session
        result = tracker.end_session(
            summary="Successfully tested session tracking",
            outcome="completed"
        )

        assert result["action_count"] == 4
        assert result["error_count"] == 1
        assert len(result["learnings"]) == 1

        # Get recent sessions
        recent = tracker.get_recent_sessions(limit=5)
        assert len(recent) == 1
        assert recent[0]["session_id"] == session_id

        # Get session details
        details = tracker.get_session_details(session_id)
        assert details is not None
        assert len(details["actions"]) == 4

        print('All SessionTracker tests passed!')
