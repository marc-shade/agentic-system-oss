"""
Learning Synthesizer

Extracts patterns and insights from session history.
Following Kai pattern: Build institutional knowledge.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import re

logger = logging.getLogger(__name__)

from .constants import (
    DEFAULT_PATTERN_DAYS,
    TOP_SEQUENCES_LIMIT,
    MIN_PATTERN_OCCURRENCES,
    DEFAULT_SUCCESS_RATE,
    DEFAULT_ERROR_PATTERN_DAYS,
    MIN_ERROR_OCCURRENCES,
    DEFAULT_LEARNING_DAYS,
    TOP_KEYWORDS_FOR_GROUPING,
    MIN_SIMILAR_LEARNINGS,
    MIN_KEYWORD_LENGTH,
    TOP_KEYWORDS_LIMIT,
    CONFIDENCE_BASE,
    CONFIDENCE_INCREMENT_PER_OCCURRENCE,
    CONFIDENCE_MAX,
    SUCCESS_PATTERN_THRESHOLD,
    FAILURE_PATTERN_THRESHOLD,
    MAX_RECOMMENDATIONS,
    DEFAULT_SUMMARY_DAYS_LEARNING,
    MAX_TOP_ERROR_TYPES,
    MAX_SAMPLE_CONTEXTS,
)


@dataclass
class Pattern:
    """Represents a discovered pattern."""
    id: str
    name: str
    description: str
    frequency: int
    success_rate: float
    context: str
    examples: List[str]
    first_seen: str
    last_seen: str
    tags: List[str]


@dataclass
class Insight:
    """Represents a synthesized insight."""
    id: str
    content: str
    confidence: float  # 0.0 to 1.0
    source_sessions: List[str]
    category: str
    timestamp: str
    validated: bool = False


class LearningSynthesizer:
    """Synthesizes learnings and patterns from session history."""

    def __init__(self, history_dir: Optional[str] = None):
        """Initialize learning synthesizer.

        Args:
            history_dir: Directory containing history files.
        """
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".claude" / "history"

        self.learnings_dir = self.history_dir / "learnings"
        self.patterns_file = self.history_dir / "patterns.json"
        self.insights_file = self.history_dir / "insights.json"

        # Create directories
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

    def _load_patterns(self) -> List[Pattern]:
        """Load existing patterns."""
        if not self.patterns_file.exists():
            return []
        try:
            with open(self.patterns_file, 'r') as f:
                data = json.load(f)
            return [Pattern(**p) for p in data]
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted patterns file, starting fresh: {e}")
            return []

    def _save_patterns(self, patterns: List[Pattern]) -> None:
        """Save patterns to file."""
        with open(self.patterns_file, 'w') as f:
            json.dump([asdict(p) for p in patterns], f, indent=2)

    def _load_insights(self) -> List[Insight]:
        """Load existing insights."""
        if not self.insights_file.exists():
            return []
        try:
            with open(self.insights_file, 'r') as f:
                data = json.load(f)
            return [Insight(**i) for i in data]
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted insights file, starting fresh: {e}")
            return []

    def _save_insights(self, insights: List[Insight]) -> None:
        """Save insights to file."""
        with open(self.insights_file, 'w') as f:
            json.dump([asdict(i) for i in insights], f, indent=2)

    def _load_all_learnings(self, days: Optional[int] = None) -> List[Dict]:
        """Load all learnings from files.

        Args:
            days: Optional limit to recent days

        Returns:
            List of learning dicts
        """
        learnings = []
        cutoff = None
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        for month_dir in self.learnings_dir.iterdir():
            if month_dir.is_dir():
                for learning_file in month_dir.glob("*_learnings.json"):
                    try:
                        with open(learning_file, 'r') as f:
                            data = json.load(f)
                            if cutoff and data.get("timestamp", "") < cutoff:
                                continue
                            learnings.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Corrupted learning file {learning_file}: {e}")
                        continue

        return learnings

    def _load_sessions(self, days: Optional[int] = None) -> List[Dict]:
        """Load session data.

        Args:
            days: Optional limit to recent days

        Returns:
            List of session dicts
        """
        sessions = []
        sessions_dir = self.history_dir / "sessions"

        if not sessions_dir.exists():
            return []

        cutoff = None
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        for month_dir in sessions_dir.iterdir():
            if month_dir.is_dir():
                for session_file in month_dir.glob("*.json"):
                    try:
                        with open(session_file, 'r') as f:
                            data = json.load(f)
                            if cutoff:
                                start_time = data.get("metadata", {}).get("start_time", "")
                                if start_time < cutoff:
                                    continue
                            sessions.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Corrupted session file {session_file}: {e}")
                        continue

        return sessions

    def extract_action_patterns(self, days: int = DEFAULT_PATTERN_DAYS) -> List[Pattern]:
        """Extract common action patterns from session history.

        Args:
            days: Number of days to analyze

        Returns:
            List of discovered patterns
        """
        sessions = self._load_sessions(days=days)

        # Count action type sequences
        sequences = Counter()
        action_outcomes = defaultdict(lambda: {"success": 0, "failure": 0})

        for session in sessions:
            actions = session.get("actions", [])
            # Get 2-action and 3-action sequences
            for i in range(len(actions) - 1):
                seq_2 = f"{actions[i]['action_type']} -> {actions[i+1]['action_type']}"
                sequences[seq_2] += 1

                # Track outcomes
                if actions[i+1]["outcome"] == "success":
                    action_outcomes[seq_2]["success"] += 1
                elif actions[i+1]["outcome"] == "failure":
                    action_outcomes[seq_2]["failure"] += 1

            for i in range(len(actions) - 2):
                seq_3 = f"{actions[i]['action_type']} -> {actions[i+1]['action_type']} -> {actions[i+2]['action_type']}"
                sequences[seq_3] += 1

        # Create patterns for common sequences
        patterns = []
        existing = self._load_patterns()
        existing_names = {p.name for p in existing}

        for seq, count in sequences.most_common(TOP_SEQUENCES_LIMIT):
            if count >= MIN_PATTERN_OCCURRENCES:
                outcomes = action_outcomes[seq]
                total = outcomes["success"] + outcomes["failure"]
                success_rate = outcomes["success"] / total if total > 0 else DEFAULT_SUCCESS_RATE

                pattern_name = f"pattern_{seq.replace(' -> ', '_').replace(' ', '_')}"

                if pattern_name not in existing_names:
                    pattern = Pattern(
                        id=f"pat_{len(patterns) + len(existing):04d}",
                        name=pattern_name,
                        description=f"Common sequence: {seq}",
                        frequency=count,
                        success_rate=success_rate,
                        context="action_sequence",
                        examples=[seq],
                        first_seen=datetime.now().isoformat(),
                        last_seen=datetime.now().isoformat(),
                        tags=["auto_discovered", "action_sequence"]
                    )
                    patterns.append(pattern)

        # Merge with existing patterns
        all_patterns = existing + patterns
        self._save_patterns(all_patterns)

        return patterns

    def extract_error_patterns(self, days: int = DEFAULT_ERROR_PATTERN_DAYS) -> List[Dict]:
        """Extract common error patterns from session history.

        Args:
            days: Number of days to analyze

        Returns:
            List of error pattern dicts
        """
        sessions = self._load_sessions(days=days)

        error_types = Counter()
        error_contexts = defaultdict(list)

        for session in sessions:
            actions = session.get("actions", [])
            for i, action in enumerate(actions):
                if action.get("outcome") == "failure":
                    error_msg = action.get("error_message", "Unknown error")
                    action_type = action.get("action_type", "unknown")

                    # Normalize error message
                    error_key = self._normalize_error(error_msg)
                    error_types[(action_type, error_key)] += 1

                    # Get context (previous action)
                    prev_action = actions[i-1] if i > 0 else None
                    error_contexts[(action_type, error_key)].append({
                        "error": error_msg,
                        "previous_action": prev_action.get("description") if prev_action else None,
                        "session_id": session.get("metadata", {}).get("session_id")
                    })

        # Build error pattern list
        error_patterns = []
        for (action_type, error_key), count in error_types.most_common(TOP_SEQUENCES_LIMIT):
            if count >= MIN_ERROR_OCCURRENCES:
                contexts = error_contexts[(action_type, error_key)]
                error_patterns.append({
                    "error_type": error_key,
                    "action_type": action_type,
                    "frequency": count,
                    "sample_contexts": contexts[:MAX_SAMPLE_CONTEXTS],
                    "prevention_hint": self._generate_prevention_hint(action_type, error_key)
                })

        return error_patterns

    def _normalize_error(self, error_msg: str) -> str:
        """Normalize error message to find common patterns."""
        if not error_msg:
            return "unknown_error"

        # Remove specific paths, numbers, etc.
        normalized = error_msg.lower()
        normalized = re.sub(r'/[\w/.-]+', '<path>', normalized)
        normalized = re.sub(r'\d+', '<num>', normalized)
        normalized = re.sub(r"'[^']*'", '<string>', normalized)
        normalized = re.sub(r'"[^"]*"', '<string>', normalized)

        # Truncate to first 100 chars
        if len(normalized) > 100:
            normalized = normalized[:100]

        return normalized

    def _generate_prevention_hint(self, action_type: str, error_key: str) -> str:
        """Generate a hint for preventing this error."""
        hints = {
            ("file_read", "no such file"): "Verify file exists before reading",
            ("file_write", "permission denied"): "Check file permissions and directory access",
            ("command_exec", "command not found"): "Ensure command is installed and in PATH",
            ("api_call", "timeout"): "Consider adding retry logic with exponential backoff",
            ("api_call", "connection refused"): "Verify service is running and accessible",
        }

        for (at, ek), hint in hints.items():
            if at in action_type.lower() and ek in error_key.lower():
                return hint

        return "Review error context for prevention strategy"

    def synthesize_learnings(self, days: int = DEFAULT_LEARNING_DAYS) -> List[Insight]:
        """Synthesize insights from accumulated learnings.

        Args:
            days: Number of days to analyze

        Returns:
            List of synthesized insights
        """
        learnings_data = self._load_all_learnings(days=days)

        # Group learnings by similarity
        learning_groups = defaultdict(list)

        for learning_entry in learnings_data:
            session_id = learning_entry.get("session_id", "")
            for learning in learning_entry.get("learnings", []):
                # Extract keywords for grouping
                keywords = self._extract_keywords(learning)
                key = tuple(sorted(keywords[:TOP_KEYWORDS_FOR_GROUPING]))
                learning_groups[key].append({
                    "content": learning,
                    "session_id": session_id
                })

        # Create insights from groups with multiple learnings
        insights = []
        existing = self._load_insights()
        existing_contents = {i.content for i in existing}

        for key, group in learning_groups.items():
            if len(group) >= MIN_SIMILAR_LEARNINGS:
                # Take the most detailed learning as representative
                representative = max(group, key=lambda x: len(x["content"]))
                session_ids = [g["session_id"] for g in group]

                if representative["content"] not in existing_contents:
                    insight = Insight(
                        id=f"ins_{len(insights) + len(existing):04d}",
                        content=representative["content"],
                        confidence=min(CONFIDENCE_BASE + len(group) * CONFIDENCE_INCREMENT_PER_OCCURRENCE, CONFIDENCE_MAX),
                        source_sessions=session_ids,
                        category="recurring_learning",
                        timestamp=datetime.now().isoformat(),
                        validated=False
                    )
                    insights.append(insight)

        # Merge with existing insights
        all_insights = existing + insights
        self._save_insights(all_insights)

        return insights

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'it', 'its', 'this', 'that', 'these',
            'those', 'and', 'or', 'but', 'if', 'then', 'so', 'use',
            'before', 'after', 'when', 'while', 'not'
        }

        keywords = [w for w in words if w not in stop_words and len(w) > MIN_KEYWORD_LENGTH]

        # Count and sort by frequency
        keyword_counts = Counter(keywords)
        return [k for k, _ in keyword_counts.most_common(TOP_KEYWORDS_LIMIT)]

    def get_recommendations(self, context: str) -> List[str]:
        """Get recommendations based on current context.

        Args:
            context: Description of current task/situation

        Returns:
            List of relevant recommendations
        """
        insights = self._load_insights()
        patterns = self._load_patterns()

        context_keywords = set(self._extract_keywords(context))
        recommendations = []

        # Find relevant insights
        for insight in insights:
            insight_keywords = set(self._extract_keywords(insight.content))
            if context_keywords & insight_keywords:  # Any overlap
                recommendations.append(f"[Insight] {insight.content}")

        # Find relevant patterns
        for pattern in patterns:
            pattern_keywords = set(self._extract_keywords(pattern.description))
            if context_keywords & pattern_keywords:
                if pattern.success_rate >= SUCCESS_PATTERN_THRESHOLD:
                    recommendations.append(
                        f"[Pattern] {pattern.description} (success rate: {pattern.success_rate:.0%})"
                    )
                elif pattern.success_rate <= FAILURE_PATTERN_THRESHOLD:
                    recommendations.append(
                        f"[Warning] {pattern.description} often fails (success rate: {pattern.success_rate:.0%})"
                    )

        return recommendations[:MAX_RECOMMENDATIONS]

    def get_success_patterns(self, min_success_rate: float = SUCCESS_PATTERN_THRESHOLD) -> List[Pattern]:
        """Get patterns with high success rates.

        Args:
            min_success_rate: Minimum success rate to include

        Returns:
            List of high-success patterns
        """
        patterns = self._load_patterns()
        return [p for p in patterns if p.success_rate >= min_success_rate]

    def get_failure_patterns(self, max_success_rate: float = FAILURE_PATTERN_THRESHOLD) -> List[Pattern]:
        """Get patterns that often fail.

        Args:
            max_success_rate: Maximum success rate to include

        Returns:
            List of failure-prone patterns
        """
        patterns = self._load_patterns()
        return [p for p in patterns if p.success_rate <= max_success_rate]

    def validate_insight(self, insight_id: str) -> bool:
        """Mark an insight as validated.

        Args:
            insight_id: ID of insight to validate

        Returns:
            True if insight was found and validated
        """
        insights = self._load_insights()
        for insight in insights:
            if insight.id == insight_id:
                insight.validated = True
                self._save_insights(insights)
                return True
        return False

    def get_summary(self, days: int = DEFAULT_SUMMARY_DAYS_LEARNING) -> Dict[str, Any]:
        """Get summary of synthesized knowledge.

        Args:
            days: Number of days to summarize

        Returns:
            Summary dict
        """
        patterns = self._load_patterns()
        insights = self._load_insights()
        error_patterns = self.extract_error_patterns(days=days)

        return {
            "total_patterns": len(patterns),
            "total_insights": len(insights),
            "validated_insights": sum(1 for i in insights if i.validated),
            "high_success_patterns": len([p for p in patterns if p.success_rate >= SUCCESS_PATTERN_THRESHOLD]),
            "failure_prone_patterns": len([p for p in patterns if p.success_rate <= FAILURE_PATTERN_THRESHOLD]),
            "common_errors": len(error_patterns),
            "top_error_types": [e["error_type"] for e in error_patterns[:MAX_TOP_ERROR_TYPES]],
            "analysis_period_days": days
        }


if __name__ == '__main__':
    import tempfile

    # Self-test
    with tempfile.TemporaryDirectory() as tmpdir:
        synthesizer = LearningSynthesizer(history_dir=tmpdir)

        # Test keyword extraction
        keywords = synthesizer._extract_keywords("Config files should be validated before use")
        assert "config" in keywords
        assert "files" in keywords
        assert "validated" in keywords

        # Test error normalization
        normalized = synthesizer._normalize_error("FileNotFoundError: /path/to/file.txt")
        assert "<path>" in normalized
        assert "/path/to/file.txt" not in normalized

        # Test prevention hints
        hint = synthesizer._generate_prevention_hint("file_read", "no such file or directory")
        assert "Verify" in hint

        # Test summary (empty history)
        summary = synthesizer.get_summary(days=7)
        assert summary["total_patterns"] == 0
        assert summary["total_insights"] == 0

        print('All LearningSynthesizer tests passed!')
