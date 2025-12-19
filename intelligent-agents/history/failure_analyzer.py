"""
Failure Analyzer

Analyzes failures to learn from mistakes and avoid repeating them.
Following Kai pattern: Capture learnings from failures.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import re


@dataclass
class FailureRecord:
    """Record of a failure."""
    id: str
    timestamp: str
    action_type: str
    description: str
    error_message: str
    context: Dict[str, Any]
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    prevention_strategy: Optional[str] = None
    recurrence_count: int = 1


@dataclass
class FailureCluster:
    """Group of similar failures."""
    id: str
    pattern: str
    failure_ids: List[str]
    count: int
    first_seen: str
    last_seen: str
    resolution_rate: float
    common_context: Dict[str, Any]
    suggested_prevention: str


class FailureAnalyzer:
    """Analyzes failures to extract learnings and prevention strategies."""

    def __init__(self, history_dir: Optional[str] = None):
        """Initialize failure analyzer.

        Args:
            history_dir: Directory containing history files.
        """
        if history_dir:
            self.history_dir = Path(history_dir)
        else:
            self.history_dir = Path.home() / ".claude" / "history"

        self.failures_file = self.history_dir / "failures.json"
        self.clusters_file = self.history_dir / "failure_clusters.json"
        self.resolutions_file = self.history_dir / "resolutions.json"

        # Create directory
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _load_failures(self) -> List[FailureRecord]:
        """Load failure records."""
        if not self.failures_file.exists():
            return []
        try:
            with open(self.failures_file, 'r') as f:
                data = json.load(f)
            return [FailureRecord(**r) for r in data]
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted failures file, starting fresh: {e}")
            return []

    def _save_failures(self, failures: List[FailureRecord]) -> None:
        """Save failure records."""
        with open(self.failures_file, 'w') as f:
            json.dump([asdict(f) for f in failures], f, indent=2)

    def _load_clusters(self) -> List[FailureCluster]:
        """Load failure clusters."""
        if not self.clusters_file.exists():
            return []
        try:
            with open(self.clusters_file, 'r') as f:
                data = json.load(f)
            return [FailureCluster(**c) for c in data]
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted clusters file, starting fresh: {e}")
            return []

    def _save_clusters(self, clusters: List[FailureCluster]) -> None:
        """Save failure clusters."""
        with open(self.clusters_file, 'w') as f:
            json.dump([asdict(c) for c in clusters], f, indent=2)

    def _load_resolutions(self) -> Dict[str, List[Dict]]:
        """Load known resolutions."""
        if not self.resolutions_file.exists():
            return {}
        try:
            with open(self.resolutions_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted resolutions file, starting fresh: {e}")
            return {}

    def _save_resolutions(self, resolutions: Dict[str, List[Dict]]) -> None:
        """Save resolutions."""
        with open(self.resolutions_file, 'w') as f:
            json.dump(resolutions, f, indent=2)

    def record_failure(
        self,
        action_type: str,
        description: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a new failure.

        Args:
            action_type: Type of action that failed
            description: Description of what was attempted
            error_message: The error message
            context: Additional context

        Returns:
            Failure record ID
        """
        failures = self._load_failures()

        # Check for similar existing failure
        normalized_error = self._normalize_error(error_message)
        similar = self._find_similar_failure(failures, action_type, normalized_error)

        if similar:
            # Update existing failure
            similar.recurrence_count += 1
            similar.timestamp = datetime.now().isoformat()
            self._save_failures(failures)
            return similar.id
        else:
            # Create new failure record
            failure_id = f"fail_{len(failures):04d}"
            failure = FailureRecord(
                id=failure_id,
                timestamp=datetime.now().isoformat(),
                action_type=action_type,
                description=description,
                error_message=error_message,
                context=context or {}
            )
            failures.append(failure)
            self._save_failures(failures)
            return failure_id

    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message for comparison."""
        if not error_message:
            return "unknown_error"

        normalized = error_message.lower()
        # Remove specific values
        normalized = re.sub(r'/[\w/.-]+', '<path>', normalized)
        normalized = re.sub(r'\d+', '<num>', normalized)
        normalized = re.sub(r"'[^']*'", '<str>', normalized)
        normalized = re.sub(r'"[^"]*"', '<str>', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized[:150]  # Truncate

    def _find_similar_failure(
        self,
        failures: List[FailureRecord],
        action_type: str,
        normalized_error: str
    ) -> Optional[FailureRecord]:
        """Find a similar existing failure."""
        for failure in failures:
            if failure.action_type == action_type:
                existing_normalized = self._normalize_error(failure.error_message)
                if existing_normalized == normalized_error:
                    return failure
        return None

    def record_resolution(
        self,
        failure_id: str,
        resolution: str,
        root_cause: Optional[str] = None,
        prevention_strategy: Optional[str] = None
    ) -> bool:
        """Record how a failure was resolved.

        Args:
            failure_id: ID of the failure
            resolution: How it was resolved
            root_cause: What caused the failure
            prevention_strategy: How to prevent it in the future

        Returns:
            True if failure was found and updated
        """
        failures = self._load_failures()

        for failure in failures:
            if failure.id == failure_id:
                failure.resolution = resolution
                failure.root_cause = root_cause
                failure.prevention_strategy = prevention_strategy
                self._save_failures(failures)

                # Also save to resolutions index
                self._index_resolution(failure)

                return True

        return False

    def _index_resolution(self, failure: FailureRecord) -> None:
        """Index resolution for quick lookup."""
        resolutions = self._load_resolutions()

        key = f"{failure.action_type}:{self._normalize_error(failure.error_message)}"

        if key not in resolutions:
            resolutions[key] = []

        resolutions[key].append({
            "failure_id": failure.id,
            "resolution": failure.resolution,
            "root_cause": failure.root_cause,
            "prevention_strategy": failure.prevention_strategy,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 10 resolutions per pattern
        resolutions[key] = resolutions[key][-10:]

        self._save_resolutions(resolutions)

    def get_resolution_hint(
        self,
        action_type: str,
        error_message: str
    ) -> Optional[Dict[str, Any]]:
        """Get resolution hint for a failure.

        Args:
            action_type: Type of action that failed
            error_message: The error message

        Returns:
            Resolution hint dict or None
        """
        resolutions = self._load_resolutions()
        key = f"{action_type}:{self._normalize_error(error_message)}"

        if key in resolutions and resolutions[key]:
            # Return most recent resolution
            latest = resolutions[key][-1]
            return {
                "has_known_resolution": True,
                "resolution": latest.get("resolution"),
                "root_cause": latest.get("root_cause"),
                "prevention_strategy": latest.get("prevention_strategy"),
                "times_seen": len(resolutions[key])
            }

        # Check for partial matches
        normalized = self._normalize_error(error_message)
        for stored_key, stored_resolutions in resolutions.items():
            stored_action, stored_error = stored_key.split(":", 1)
            if stored_action == action_type:
                # Check for substring match
                if normalized in stored_error or stored_error in normalized:
                    latest = stored_resolutions[-1]
                    return {
                        "has_known_resolution": True,
                        "resolution": latest.get("resolution"),
                        "root_cause": latest.get("root_cause"),
                        "prevention_strategy": latest.get("prevention_strategy"),
                        "times_seen": len(stored_resolutions),
                        "partial_match": True
                    }

        return None

    def cluster_failures(self) -> List[FailureCluster]:
        """Cluster similar failures together.

        Returns:
            List of failure clusters
        """
        failures = self._load_failures()

        # Group by action type and normalized error
        groups = defaultdict(list)
        for failure in failures:
            key = f"{failure.action_type}:{self._normalize_error(failure.error_message)}"
            groups[key].append(failure)

        # Create clusters
        clusters = []
        for key, group_failures in groups.items():
            if len(group_failures) >= 2:  # Only cluster if 2+ occurrences
                resolved_count = sum(1 for f in group_failures if f.resolution)
                resolution_rate = resolved_count / len(group_failures)

                # Find common context
                common_context = self._find_common_context(group_failures)

                # Generate prevention suggestion
                prevention = self._suggest_prevention(group_failures)

                cluster = FailureCluster(
                    id=f"cluster_{len(clusters):04d}",
                    pattern=key,
                    failure_ids=[f.id for f in group_failures],
                    count=len(group_failures),
                    first_seen=min(f.timestamp for f in group_failures),
                    last_seen=max(f.timestamp for f in group_failures),
                    resolution_rate=resolution_rate,
                    common_context=common_context,
                    suggested_prevention=prevention
                )
                clusters.append(cluster)

        self._save_clusters(clusters)
        return clusters

    def _find_common_context(self, failures: List[FailureRecord]) -> Dict[str, Any]:
        """Find common context across failures."""
        if not failures:
            return {}

        # Count occurrences of each context key-value pair
        context_counts = defaultdict(Counter)
        for failure in failures:
            for key, value in failure.context.items():
                if isinstance(value, (str, int, float, bool)):
                    context_counts[key][str(value)] += 1

        # Find values that appear in majority
        common = {}
        threshold = len(failures) / 2
        for key, value_counts in context_counts.items():
            top_value, count = value_counts.most_common(1)[0]
            if count >= threshold:
                common[key] = top_value

        return common

    def _suggest_prevention(self, failures: List[FailureRecord]) -> str:
        """Generate prevention suggestion for a cluster."""
        # If any failure has a prevention strategy, use it
        for failure in failures:
            if failure.prevention_strategy:
                return failure.prevention_strategy

        # Otherwise, generate based on patterns
        action_type = failures[0].action_type
        error = self._normalize_error(failures[0].error_message)

        prevention_rules = {
            "file_read": {
                "no such file": "Check file existence with os.path.exists() before reading",
                "permission": "Verify file permissions or run with appropriate privileges",
                "encoding": "Specify explicit encoding (e.g., encoding='utf-8')"
            },
            "file_write": {
                "no such file": "Create parent directories with os.makedirs(path, exist_ok=True)",
                "permission": "Check directory write permissions",
                "disk full": "Check available disk space before large writes"
            },
            "command_exec": {
                "not found": "Verify command is installed and in PATH",
                "permission": "Check execute permissions or use sudo if appropriate",
                "timeout": "Increase timeout or optimize command"
            },
            "api_call": {
                "timeout": "Add retry logic with exponential backoff",
                "connection": "Verify network connectivity and service availability",
                "rate limit": "Implement rate limiting and backoff",
                "401": "Check authentication credentials",
                "403": "Verify API permissions and access rights",
                "404": "Verify endpoint URL is correct"
            }
        }

        for at, patterns in prevention_rules.items():
            if at in action_type.lower():
                for pattern, suggestion in patterns.items():
                    if pattern in error:
                        return suggestion

        return "Review error context and add appropriate error handling"

    def get_recurring_failures(self, min_count: int = 3) -> List[FailureRecord]:
        """Get failures that recur frequently.

        Args:
            min_count: Minimum recurrence count

        Returns:
            List of recurring failures
        """
        failures = self._load_failures()
        return [f for f in failures if f.recurrence_count >= min_count]

    def get_unresolved_failures(self) -> List[FailureRecord]:
        """Get failures without resolutions.

        Returns:
            List of unresolved failures
        """
        failures = self._load_failures()
        return [f for f in failures if not f.resolution]

    def get_recent_failures(self, days: int = 7) -> List[FailureRecord]:
        """Get recent failures.

        Args:
            days: Number of days to look back

        Returns:
            List of recent failures
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        failures = self._load_failures()
        return [f for f in failures if f.timestamp >= cutoff]

    def get_failure_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get failure statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics dict
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        failures = self._load_failures()
        recent = [f for f in failures if f.timestamp >= cutoff]

        # Count by action type
        by_action_type = Counter(f.action_type for f in recent)

        # Count resolved vs unresolved
        resolved = sum(1 for f in recent if f.resolution)
        unresolved = len(recent) - resolved

        # Total recurrences
        total_recurrences = sum(f.recurrence_count for f in recent)

        return {
            "total_failures": len(recent),
            "unique_failures": len(recent),
            "total_recurrences": total_recurrences,
            "resolved": resolved,
            "unresolved": unresolved,
            "resolution_rate": resolved / len(recent) if recent else 0,
            "by_action_type": dict(by_action_type.most_common(10)),
            "period_days": days
        }

    def get_prevention_checklist(self, action_type: str) -> List[str]:
        """Get a checklist of preventions for an action type.

        Args:
            action_type: Type of action to get checklist for

        Returns:
            List of prevention checks
        """
        # Load clusters for this action type
        clusters = self._load_clusters()
        relevant = [c for c in clusters if action_type in c.pattern]

        # Build checklist from cluster preventions
        checklist = []
        seen_suggestions = set()

        for cluster in relevant:
            suggestion = cluster.suggested_prevention
            if suggestion and suggestion not in seen_suggestions:
                checklist.append(suggestion)
                seen_suggestions.add(suggestion)

        # Add generic checks based on action type
        generic_checks = {
            "file_read": [
                "Verify file exists",
                "Check file permissions",
                "Handle encoding properly"
            ],
            "file_write": [
                "Ensure parent directory exists",
                "Check write permissions",
                "Consider atomic writes for safety"
            ],
            "command_exec": [
                "Validate command exists",
                "Set appropriate timeout",
                "Capture and handle stderr"
            ],
            "api_call": [
                "Validate request parameters",
                "Implement retry with backoff",
                "Handle rate limits",
                "Check authentication before call"
            ]
        }

        for at, checks in generic_checks.items():
            if at in action_type.lower():
                for check in checks:
                    if check not in seen_suggestions:
                        checklist.append(check)

        return checklist


if __name__ == '__main__':
    import tempfile

    # Self-test
    with tempfile.TemporaryDirectory() as tmpdir:
        analyzer = FailureAnalyzer(history_dir=tmpdir)

        # Record failures
        fail1 = analyzer.record_failure(
            action_type="file_read",
            description="Read config file",
            error_message="FileNotFoundError: /path/to/config.json",
            context={"file": "config.json"}
        )
        assert fail1 == "fail_0000"

        # Record same failure again (should increment recurrence)
        fail2 = analyzer.record_failure(
            action_type="file_read",
            description="Read config file",
            error_message="FileNotFoundError: /path/to/different.json",
            context={"file": "different.json"}
        )
        assert fail2 == "fail_0000"  # Same normalized error

        # Record resolution
        resolved = analyzer.record_resolution(
            failure_id="fail_0000",
            resolution="Added file existence check",
            root_cause="File not created before read",
            prevention_strategy="Check file exists before reading"
        )
        assert resolved

        # Get resolution hint
        hint = analyzer.get_resolution_hint("file_read", "FileNotFoundError: /some/file.txt")
        assert hint is not None
        assert hint["has_known_resolution"]

        # Record different failure
        fail3 = analyzer.record_failure(
            action_type="api_call",
            description="Call weather API",
            error_message="ConnectionTimeout: api.weather.com",
            context={}
        )
        assert fail3 == "fail_0001"

        # Get stats
        stats = analyzer.get_failure_stats(days=7)
        assert stats["total_failures"] == 2
        assert stats["resolved"] == 1

        # Get prevention checklist
        checklist = analyzer.get_prevention_checklist("file_read")
        assert len(checklist) > 0

        print('All FailureAnalyzer tests passed!')
