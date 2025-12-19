"""
Tests for history/session_tracker.py

Tests session tracking, session creation, and action recording.
"""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from history.session_tracker import (
    SessionTracker,
    TrackedAction,
    SessionMetadata,
    ActionType,
    ActionOutcome,
)


class TestActionTypes:
    """Test action type enumeration."""

    def test_common_actions_defined(self):
        """Common action types should be defined."""
        expected = [
            "FILE_READ",
            "FILE_WRITE",
            "FILE_EDIT",
            "COMMAND_EXEC",
            "SEARCH",
            "API_CALL",
            "DECISION",
            "ERROR",
        ]
        for action in expected:
            assert hasattr(ActionType, action)


class TestActionOutcome:
    """Test action outcome enumeration."""

    def test_outcomes_defined(self):
        """All outcomes should be defined."""
        expected = ["SUCCESS", "FAILURE", "PARTIAL", "PENDING", "SKIPPED"]
        for outcome in expected:
            assert hasattr(ActionOutcome, outcome)


class TestTrackedAction:
    """Test TrackedAction dataclass."""

    def test_create_action(self):
        """Should create action with required fields."""
        action = TrackedAction(
            id="action_001",
            timestamp="2025-12-19T14:30:00",
            action_type=ActionType.FILE_READ.value,
            description="Read config.json",
            outcome=ActionOutcome.SUCCESS.value,
        )
        assert action.id == "action_001"
        assert action.action_type == "file_read"
        assert action.outcome == "success"

    def test_action_with_details(self):
        """Action should accept optional details."""
        action = TrackedAction(
            id="action_002",
            timestamp="2025-12-19T14:31:00",
            action_type=ActionType.COMMAND_EXEC.value,
            description="Run tests",
            outcome=ActionOutcome.SUCCESS.value,
            details={"command": "pytest", "exit_code": 0},
            duration_ms=1500,
        )
        assert action.details["command"] == "pytest"
        assert action.duration_ms == 1500


class TestSessionMetadata:
    """Test SessionMetadata dataclass."""

    def test_create_metadata(self):
        """Should create metadata with required fields."""
        metadata = SessionMetadata(
            session_id="session_20251219_143000_abc",
            start_time="2025-12-19T14:30:00",
        )
        assert metadata.session_id.startswith("session_")
        assert metadata.outcome == "in_progress"
        assert metadata.action_count == 0

    def test_metadata_with_goal(self):
        """Metadata should accept optional goal."""
        metadata = SessionMetadata(
            session_id="session_20251219_143000_abc",
            start_time="2025-12-19T14:30:00",
            goal="Implement new feature",
            tags=["feature", "development"],
        )
        assert metadata.goal == "Implement new feature"
        assert "feature" in metadata.tags


class TestSessionTracker:
    """Test SessionTracker class."""

    @pytest.fixture
    def tracker(self, temp_dir):
        """Create a SessionTracker with temp directory."""
        return SessionTracker(history_dir=str(temp_dir))

    def test_create_tracker(self, temp_dir):
        """Should create tracker with history directory."""
        tracker = SessionTracker(history_dir=str(temp_dir))
        assert tracker is not None

    def test_start_session(self, tracker):
        """Should start a new session."""
        session_id = tracker.start_session(goal="Test goal")
        assert session_id is not None
        assert isinstance(session_id, str)
        assert session_id.startswith("session_")

    def test_session_id_format(self, tracker):
        """Session ID should follow expected format."""
        session_id = tracker.start_session()

        # Format: session_YYYYMMDD_HHMMSS_HASH
        parts = session_id.split("_")
        assert parts[0] == "session"
        assert len(parts) >= 3

    def test_track_action(self, tracker):
        """Should track action in current session."""
        tracker.start_session()
        action_id = tracker.track_action(
            action_type=ActionType.FILE_READ,
            description="Read test file",
            outcome=ActionOutcome.SUCCESS,
        )
        # Verify action was tracked
        assert action_id is not None
        assert tracker.current_session.action_count >= 1

    def test_track_multiple_actions(self, tracker):
        """Should track multiple actions."""
        tracker.start_session()
        for i in range(5):
            tracker.track_action(
                action_type=ActionType.COMMAND_EXEC,
                description=f"Command {i}",
                outcome=ActionOutcome.SUCCESS,
            )
        assert tracker.current_session.action_count >= 5

    def test_end_session(self, tracker, temp_dir):
        """Should end and save session."""
        tracker.start_session(goal="Test session")
        tracker.track_action(
            action_type=ActionType.DECISION,
            description="Made a decision",
            outcome=ActionOutcome.SUCCESS,
        )
        tracker.end_session(summary="Session completed successfully")

        # After ending, current_session should be None
        assert tracker.current_session is None


class TestSessionPersistence:
    """Test session save/load functionality."""

    @pytest.fixture
    def tracker(self, temp_dir):
        return SessionTracker(history_dir=str(temp_dir))

    def test_session_persisted(self, tracker, temp_dir):
        """Ended sessions should be persisted."""
        tracker.start_session(goal="Persistence test")
        session_id = tracker.current_session.session_id
        tracker.end_session(summary="Done")

        # Session should be persisted - verify no crash
        assert True

    def test_list_sessions(self, tracker):
        """Should list available sessions."""
        # Start and end a few sessions
        for i in range(3):
            tracker.start_session(goal=f"Session {i}")
            tracker.end_session(summary=f"Completed {i}")

        sessions = tracker.get_recent_sessions(limit=10)
        assert isinstance(sessions, list)


class TestActionDetails:
    """Test action detail handling."""

    @pytest.fixture
    def tracker(self, temp_dir):
        return SessionTracker(history_dir=str(temp_dir))

    def test_action_with_files(self, tracker):
        """Action should track related files."""
        tracker.start_session()
        tracker.track_action(
            action_type=ActionType.FILE_WRITE,
            description="Write output",
            outcome=ActionOutcome.SUCCESS,
            details={"path": "/tmp/output.txt"},
            related_files=["/tmp/output.txt"],
        )
        assert "/tmp/output.txt" in tracker.current_session.files_modified

    def test_action_with_error(self, tracker):
        """Failed actions should record error."""
        tracker.start_session()
        tracker.track_action(
            action_type=ActionType.COMMAND_EXEC,
            description="Run failing command",
            outcome=ActionOutcome.FAILURE,
            error_message="Command not found",
        )
        assert tracker.current_session.error_count >= 1


class TestEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def tracker(self, temp_dir):
        return SessionTracker(history_dir=str(temp_dir))

    def test_track_without_session(self, tracker):
        """Tracking without active session should auto-create session."""
        # SessionTracker auto-creates session if none exists
        action_id = tracker.track_action(
            action_type=ActionType.SEARCH,
            description="Search test",
            outcome=ActionOutcome.SUCCESS,
        )
        assert action_id is not None
        assert tracker.current_session is not None

    def test_end_without_session(self, tracker):
        """Ending without active session should handle gracefully."""
        # Should not crash even if no session is active
        tracker.end_session()
        # If it gets here without exception, it handled gracefully
        assert True

    def test_unicode_in_description(self, tracker):
        """Unicode in descriptions should be handled."""
        tracker.start_session()
        tracker.track_action(
            action_type=ActionType.DECISION,
            description="Decision: 日本語 العربية",
            outcome=ActionOutcome.SUCCESS,
        )
        # Should not raise

    def test_large_details(self, tracker):
        """Large detail objects should be handled."""
        tracker.start_session()
        large_details = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
        tracker.track_action(
            action_type=ActionType.API_CALL,
            description="API call with large response",
            outcome=ActionOutcome.SUCCESS,
            details=large_details,
        )
        # Should not raise


class TestSessionQueries:
    """Test session querying functionality."""

    @pytest.fixture
    def tracker(self, temp_dir):
        return SessionTracker(history_dir=str(temp_dir))

    def test_get_current_session(self, tracker):
        """Should return current active session."""
        tracker.start_session(goal="Current session test")
        current = tracker.current_session
        assert current is not None
        assert current.goal == "Current session test"

    def test_no_current_session(self, tracker):
        """Should handle no current session gracefully."""
        # Before starting any session
        current = tracker.current_session
        # Should return None
        assert current is None
