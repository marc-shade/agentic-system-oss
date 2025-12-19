"""
Action Summarizer

Generates concise summaries of work done in sessions.
Following Kai pattern: Generate summaries of sessions.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict


@dataclass
class ActionSummary:
    """Summary of actions in a time period."""
    period_start: str
    period_end: str
    total_actions: int
    successful_actions: int
    failed_actions: int
    files_modified: List[str]
    action_breakdown: Dict[str, int]
    highlights: List[str]
    key_achievements: List[str]
    areas_of_concern: List[str]


@dataclass
class SessionSummary:
    """Summary of a single session."""
    session_id: str
    goal: str
    outcome: str
    duration_minutes: float
    action_count: int
    error_count: int
    key_actions: List[str]
    files_touched: List[str]
    learnings: List[str]


class ActionSummarizer:
    """Generates summaries of actions and sessions."""

    def __init__(self, history_dir: Optional[str] = None):
        """Initialize action summarizer.

        Args:
            history_dir: Directory containing history files.
        """
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".claude" / "history"

        self.sessions_dir = self.history_dir / "sessions"
        self.summaries_dir = self.history_dir / "summaries"

        # Create directories
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def _load_session(self, session_file: Path) -> Optional[Dict]:
        """Load a session from file."""
        if not session_file.exists():
            return None
        try:
            with open(session_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted session file {session_file}: {e}")
            return None

    def _load_sessions_in_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Load sessions within a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            List of session dicts
        """
        sessions = []

        if not self.sessions_dir.exists():
            return []

        for month_dir in self.sessions_dir.iterdir():
            if month_dir.is_dir():
                for session_file in month_dir.glob("*.json"):
                    session = self._load_session(session_file)
                    if session:
                        session_start = session.get("metadata", {}).get("start_time", "")

                        if start_date and session_start < start_date:
                            continue
                        if end_date and session_start > end_date:
                            continue

                        sessions.append(session)

        return sorted(sessions, key=lambda s: s.get("metadata", {}).get("start_time", ""))

    def summarize_session(self, session_id: str) -> Optional[SessionSummary]:
        """Generate summary for a specific session.

        Args:
            session_id: Session ID to summarize

        Returns:
            Session summary or None if not found
        """
        # Find session file
        session_data = None
        for month_dir in self.sessions_dir.iterdir():
            if month_dir.is_dir():
                session_file = month_dir / f"{session_id}.json"
                if session_file.exists():
                    session_data = self._load_session(session_file)
                    break

        if not session_data:
            return None

        metadata = session_data.get("metadata", {})
        actions = session_data.get("actions", [])

        # Calculate duration
        start_time = metadata.get("start_time", "")
        end_time = metadata.get("end_time", "")
        duration = 0.0
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration = (end_dt - start_dt).total_seconds() / 60
            except ValueError:
                pass

        # Extract key actions (milestones and important actions)
        key_actions = []
        for action in actions:
            if action.get("action_type") == "milestone":
                key_actions.append(f"[Milestone] {action['description']}")
            elif action.get("outcome") == "success" and "decision" in action.get("action_type", ""):
                key_actions.append(f"[Decision] {action['description']}")

        # Add first and last action for context
        if actions:
            if len(actions) > 0:
                key_actions.insert(0, f"[Start] {actions[0]['description']}")
            if len(actions) > 1:
                key_actions.append(f"[End] {actions[-1]['description']}")

        return SessionSummary(
            session_id=session_id,
            goal=metadata.get("goal", "Not specified"),
            outcome=metadata.get("outcome", "unknown"),
            duration_minutes=round(duration, 1),
            action_count=metadata.get("action_count", len(actions)),
            error_count=metadata.get("error_count", 0),
            key_actions=key_actions[:10],
            files_touched=metadata.get("files_modified", [])[:20],
            learnings=metadata.get("learnings", [])
        )

    def summarize_period(
        self,
        days: int = 1,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> ActionSummary:
        """Generate summary for a time period.

        Args:
            days: Number of days to summarize (used if dates not specified)
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Action summary for the period
        """
        if not end_date:
            end_date = datetime.now().isoformat()
        if not start_date:
            start_date = (datetime.now() - timedelta(days=days)).isoformat()

        sessions = self._load_sessions_in_range(start_date, end_date)

        # Aggregate statistics
        total_actions = 0
        successful_actions = 0
        failed_actions = 0
        all_files = set()
        action_types = Counter()
        highlights = []
        achievements = []
        concerns = []

        for session in sessions:
            metadata = session.get("metadata", {})
            actions = session.get("actions", [])

            total_actions += len(actions)

            for action in actions:
                outcome = action.get("outcome", "")
                if outcome == "success":
                    successful_actions += 1
                elif outcome == "failure":
                    failed_actions += 1

                action_types[action.get("action_type", "unknown")] += 1

                # Track milestones as highlights
                if action.get("action_type") == "milestone":
                    highlights.append(action.get("description", ""))

            # Track files
            all_files.update(metadata.get("files_modified", []))

            # Track session outcomes
            goal = metadata.get("goal", "")
            outcome = metadata.get("outcome", "")
            if outcome == "completed" and goal:
                achievements.append(f"Completed: {goal}")
            elif outcome == "failed" and goal:
                concerns.append(f"Failed: {goal}")

            # Track sessions with high error rates
            error_count = metadata.get("error_count", 0)
            action_count = metadata.get("action_count", 1)
            if error_count > 0 and error_count / action_count > 0.3:
                concerns.append(f"High error rate in session: {metadata.get('session_id', 'unknown')}")

        return ActionSummary(
            period_start=start_date,
            period_end=end_date,
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            files_modified=sorted(list(all_files))[:50],
            action_breakdown=dict(action_types.most_common(10)),
            highlights=highlights[:10],
            key_achievements=achievements[:10],
            areas_of_concern=concerns[:10]
        )

    def generate_daily_summary(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Generate a daily summary.

        Args:
            date: Date to summarize (YYYY-MM-DD), defaults to today

        Returns:
            Daily summary dict
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        start = f"{date}T00:00:00"
        end = f"{date}T23:59:59"

        summary = self.summarize_period(start_date=start, end_date=end)

        # Calculate success rate
        total = summary.successful_actions + summary.failed_actions
        success_rate = summary.successful_actions / total if total > 0 else 0

        return {
            "date": date,
            "total_actions": summary.total_actions,
            "success_rate": round(success_rate * 100, 1),
            "files_modified_count": len(summary.files_modified),
            "top_action_types": summary.action_breakdown,
            "highlights": summary.highlights,
            "achievements": summary.key_achievements,
            "concerns": summary.areas_of_concern,
            "summary_text": self._generate_text_summary(summary, "daily")
        }

    def generate_weekly_summary(self, week_start: Optional[str] = None) -> Dict[str, Any]:
        """Generate a weekly summary.

        Args:
            week_start: Start of week (YYYY-MM-DD), defaults to last Monday

        Returns:
            Weekly summary dict
        """
        if not week_start:
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            week_start = monday.strftime("%Y-%m-%d")

        start = f"{week_start}T00:00:00"
        end_date = (datetime.fromisoformat(week_start) + timedelta(days=6)).strftime("%Y-%m-%d")
        end = f"{end_date}T23:59:59"

        summary = self.summarize_period(start_date=start, end_date=end)

        # Load all sessions for detailed analysis
        sessions = self._load_sessions_in_range(start, end)

        # Calculate productivity metrics
        total_duration = 0
        for session in sessions:
            metadata = session.get("metadata", {})
            start_time = metadata.get("start_time", "")
            end_time = metadata.get("end_time", "")
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(end_time)
                    total_duration += (end_dt - start_dt).total_seconds() / 3600
                except ValueError:
                    pass

        return {
            "week_start": week_start,
            "week_end": end_date,
            "session_count": len(sessions),
            "total_hours": round(total_duration, 1),
            "total_actions": summary.total_actions,
            "files_modified_count": len(summary.files_modified),
            "top_action_types": summary.action_breakdown,
            "highlights": summary.highlights,
            "achievements": summary.key_achievements,
            "concerns": summary.areas_of_concern,
            "summary_text": self._generate_text_summary(summary, "weekly")
        }

    def _generate_text_summary(self, summary: ActionSummary, period_type: str) -> str:
        """Generate human-readable text summary.

        Args:
            summary: Action summary to convert
            period_type: Type of period (daily, weekly)

        Returns:
            Text summary
        """
        total = summary.successful_actions + summary.failed_actions
        success_rate = summary.successful_actions / total * 100 if total > 0 else 0

        lines = []

        if period_type == "daily":
            lines.append(f"Daily Summary")
        else:
            lines.append(f"Weekly Summary")

        lines.append(f"")
        lines.append(f"Actions: {summary.total_actions} total ({success_rate:.0f}% success rate)")
        lines.append(f"Files Modified: {len(summary.files_modified)}")

        if summary.action_breakdown:
            top_actions = list(summary.action_breakdown.items())[:3]
            actions_str = ", ".join(f"{k}: {v}" for k, v in top_actions)
            lines.append(f"Top Actions: {actions_str}")

        if summary.key_achievements:
            lines.append(f"")
            lines.append(f"Key Achievements:")
            for achievement in summary.key_achievements[:5]:
                lines.append(f"  - {achievement}")

        if summary.highlights:
            lines.append(f"")
            lines.append(f"Highlights:")
            for highlight in summary.highlights[:5]:
                lines.append(f"  - {highlight}")

        if summary.areas_of_concern:
            lines.append(f"")
            lines.append(f"Areas of Concern:")
            for concern in summary.areas_of_concern[:3]:
                lines.append(f"  - {concern}")

        return "\n".join(lines)

    def get_productivity_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Calculate productivity metrics.

        Args:
            days: Number of days to analyze

        Returns:
            Productivity metrics dict
        """
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        sessions = self._load_sessions_in_range(start_date, end_date)

        if not sessions:
            return {
                "sessions": 0,
                "actions_per_session": 0,
                "average_duration_minutes": 0,
                "success_rate": 0,
                "most_productive_day": None
            }

        # Calculate metrics
        total_actions = 0
        total_duration = 0
        successful = 0
        failed = 0
        by_day = defaultdict(int)

        for session in sessions:
            metadata = session.get("metadata", {})
            actions = session.get("actions", [])

            total_actions += len(actions)

            # Duration
            start_time = metadata.get("start_time", "")
            end_time = metadata.get("end_time", "")
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    end_dt = datetime.fromisoformat(end_time)
                    total_duration += (end_dt - start_dt).total_seconds() / 60

                    # Track by day
                    day = start_dt.strftime("%A")
                    by_day[day] += len(actions)
                except ValueError:
                    pass

            # Outcomes
            for action in actions:
                if action.get("outcome") == "success":
                    successful += 1
                elif action.get("outcome") == "failure":
                    failed += 1

        total_outcomes = successful + failed
        success_rate = successful / total_outcomes if total_outcomes > 0 else 0

        most_productive = max(by_day.items(), key=lambda x: x[1])[0] if by_day else None

        return {
            "sessions": len(sessions),
            "total_actions": total_actions,
            "actions_per_session": round(total_actions / len(sessions), 1),
            "average_duration_minutes": round(total_duration / len(sessions), 1),
            "success_rate": round(success_rate * 100, 1),
            "most_productive_day": most_productive,
            "actions_by_day": dict(by_day),
            "period_days": days
        }

    def compare_periods(
        self,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str
    ) -> Dict[str, Any]:
        """Compare two time periods.

        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period

        Returns:
            Comparison dict
        """
        summary1 = self.summarize_period(start_date=period1_start, end_date=period1_end)
        summary2 = self.summarize_period(start_date=period2_start, end_date=period2_end)

        def calc_change(old: int, new: int) -> float:
            if old == 0:
                return 100.0 if new > 0 else 0.0
            return ((new - old) / old) * 100

        return {
            "period1": {"start": period1_start, "end": period1_end},
            "period2": {"start": period2_start, "end": period2_end},
            "actions_change": round(calc_change(summary1.total_actions, summary2.total_actions), 1),
            "success_change": round(calc_change(summary1.successful_actions, summary2.successful_actions), 1),
            "failure_change": round(calc_change(summary1.failed_actions, summary2.failed_actions), 1),
            "period1_summary": asdict(summary1),
            "period2_summary": asdict(summary2)
        }


if __name__ == '__main__':
    import tempfile

    # Self-test
    with tempfile.TemporaryDirectory() as tmpdir:
        summarizer = ActionSummarizer(history_dir=tmpdir)

        # Test with empty history
        summary = summarizer.summarize_period(days=1)
        assert summary.total_actions == 0

        daily = summarizer.generate_daily_summary()
        assert daily["total_actions"] == 0

        weekly = summarizer.generate_weekly_summary()
        assert weekly["session_count"] == 0

        metrics = summarizer.get_productivity_metrics(days=7)
        assert metrics["sessions"] == 0

        print('All ActionSummarizer tests passed!')
