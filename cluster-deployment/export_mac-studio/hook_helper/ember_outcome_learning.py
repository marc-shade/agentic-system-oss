#!/usr/bin/env python3
"""
Ember Outcome Learning System
Learn from what Phoenix does after notifications

Did Phoenix:
- Fix the violation? (notification was correct)
- Ignore it? (maybe false positive)
- Explain why it's intentional? (learn exception pattern)
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

VIOLATIONS_LOG = Path.home() / ".claude" / "ember_violations.jsonl"
OUTCOMES_LOG = Path.home() / ".claude" / "ember_outcomes.jsonl"
PATTERNS_DB = Path.home() / ".claude" / "ember_learned_patterns.json"

class OutcomeLearner:
    """Learn from violation outcomes to improve accuracy"""

    def __init__(self):
        self.outcomes = self._load_outcomes()
        self.learned_patterns = self._load_patterns()

    def _load_outcomes(self) -> List[Dict]:
        """Load historical outcomes"""
        outcomes = []
        if OUTCOMES_LOG.exists():
            with open(OUTCOMES_LOG) as f:
                for line in f:
                    try:
                        outcomes.append(json.loads(line))
                    except:
                        pass
        return outcomes

    def _load_patterns(self) -> Dict:
        """Load learned patterns"""
        if PATTERNS_DB.exists():
            try:
                with open(PATTERNS_DB) as f:
                    return json.load(f)
            except:
                pass

        return {
            "risk_adjustments": {},      # Pattern -> risk delta
            "exception_patterns": [],     # Patterns that are intentional
            "correction_rates": {},       # Pattern -> correction rate
            "false_positive_patterns": [] # Patterns that are false positives
        }

    def _save_patterns(self) -> None:
        """Save learned patterns"""
        with open(PATTERNS_DB, "w") as f:
            json.dump(self.learned_patterns, f, indent=2)

    def track_violation(
        self,
        violation: Dict,
        tier: str
    ) -> str:
        """
        Start tracking a violation to learn from outcome

        Returns tracking_id for later outcome recording
        """
        tracking_id = self._generate_tracking_id(violation)

        tracking_entry = {
            "tracking_id": tracking_id,
            "timestamp": time.time(),
            "file_path": violation.get("file_path", ""),
            "code_hash": self._hash_code(violation.get("code_content", "")),
            "tier": tier,
            "risk_score": violation.get("risk_score", 0),
            "patterns": violation.get("matched_patterns", []),
            "outcome": "pending"
        }

        with open(OUTCOMES_LOG, "a") as f:
            f.write(json.dumps(tracking_entry) + "\n")

        return tracking_id

    def record_outcome(
        self,
        tracking_id: str,
        outcome: str,
        details: Optional[Dict] = None
    ) -> None:
        """
        Record outcome of a tracked violation

        Outcomes:
        - corrected: Phoenix fixed the violation
        - intentional: Phoenix committed it anyway (intentional)
        - ignored: Phoenix didn't commit or fix (still pending)
        """
        # Find tracking entry
        tracking = None
        all_entries = []

        if OUTCOMES_LOG.exists():
            with open(OUTCOMES_LOG) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("tracking_id") == tracking_id:
                            tracking = entry
                            tracking["outcome"] = outcome
                            tracking["outcome_timestamp"] = time.time()
                            if details:
                                tracking["outcome_details"] = details
                        all_entries.append(entry)
                    except:
                        pass

        if tracking:
            # Rewrite file with updated entry
            with open(OUTCOMES_LOG, "w") as f:
                for entry in all_entries:
                    f.write(json.dumps(entry) + "\n")

            # Learn from outcome
            self._learn_from_outcome(tracking)

    def _learn_from_outcome(self, tracking: Dict) -> None:
        """
        Learn from violation outcome

        Adjust risk scores and pattern exceptions
        """
        outcome = tracking.get("outcome")
        patterns = tracking.get("patterns", [])
        tier = tracking.get("tier")

        for pattern in patterns:
            pattern_key = f"{pattern.get('type')}:{pattern.get('pattern')}"

            # Initialize if not exists
            if pattern_key not in self.learned_patterns["correction_rates"]:
                self.learned_patterns["correction_rates"][pattern_key] = {
                    "corrected": 0,
                    "intentional": 0,
                    "total": 0
                }

            # Update counts
            self.learned_patterns["correction_rates"][pattern_key]["total"] += 1

            if outcome == "corrected":
                self.learned_patterns["correction_rates"][pattern_key]["corrected"] += 1

                # High correction rate = increase risk
                correction_rate = (
                    self.learned_patterns["correction_rates"][pattern_key]["corrected"] /
                    self.learned_patterns["correction_rates"][pattern_key]["total"]
                )

                if correction_rate > 0.8:  # 80%+ corrected
                    # Increase risk for this pattern
                    if pattern_key not in self.learned_patterns["risk_adjustments"]:
                        self.learned_patterns["risk_adjustments"][pattern_key] = 0.0
                    self.learned_patterns["risk_adjustments"][pattern_key] += 0.05

            elif outcome == "intentional":
                self.learned_patterns["correction_rates"][pattern_key]["intentional"] += 1

                # High intentional rate = add exception
                intentional_rate = (
                    self.learned_patterns["correction_rates"][pattern_key]["intentional"] /
                    self.learned_patterns["correction_rates"][pattern_key]["total"]
                )

                if intentional_rate > 0.7:  # 70%+ intentional
                    # Add as exception pattern
                    exception = {
                        "pattern": pattern.get("pattern"),
                        "type": pattern.get("type"),
                        "file_pattern": self._extract_file_pattern(tracking.get("file_path", "")),
                        "reason": "high_intentional_rate",
                        "rate": intentional_rate
                    }

                    if exception not in self.learned_patterns["exception_patterns"]:
                        self.learned_patterns["exception_patterns"].append(exception)

        # Save updated patterns
        self._save_patterns()

    def _extract_file_pattern(self, file_path: str) -> str:
        """Extract file pattern (e.g., test files, config files)"""
        import re

        if re.search(r"test", file_path, re.I):
            return "test_files"
        elif re.search(r"config", file_path, re.I):
            return "config_files"
        elif re.search(r"example|demo|sample", file_path, re.I):
            return "example_files"
        else:
            return "general"

    def should_adjust_risk(
        self,
        pattern_key: str,
        base_risk: float
    ) -> float:
        """
        Adjust risk based on learned patterns

        Returns adjusted risk score
        """
        adjustment = self.learned_patterns["risk_adjustments"].get(pattern_key, 0.0)
        adjusted = base_risk + adjustment

        # Clamp to [0, 1]
        return max(0.0, min(1.0, adjusted))

    def is_exception(
        self,
        pattern: Dict,
        file_path: str
    ) -> bool:
        """
        Check if pattern matches learned exception

        Returns True if this should be ignored
        """
        file_pattern = self._extract_file_pattern(file_path)

        for exception in self.learned_patterns["exception_patterns"]:
            if (exception.get("pattern") == pattern.get("pattern") and
                exception.get("file_pattern") == file_pattern):
                return True

        return False

    def get_statistics(self) -> Dict:
        """Get learning statistics"""
        total_outcomes = len(self.outcomes)
        corrected = sum(1 for o in self.outcomes if o.get("outcome") == "corrected")
        intentional = sum(1 for o in self.outcomes if o.get("outcome") == "intentional")
        pending = sum(1 for o in self.outcomes if o.get("outcome") == "pending")

        return {
            "total_tracked": total_outcomes,
            "corrected": corrected,
            "intentional": intentional,
            "pending": pending,
            "correction_rate": corrected / total_outcomes if total_outcomes > 0 else 0,
            "exception_patterns": len(self.learned_patterns["exception_patterns"]),
            "risk_adjustments": len(self.learned_patterns["risk_adjustments"])
        }

    def _generate_tracking_id(self, violation: Dict) -> str:
        """Generate unique tracking ID"""
        import hashlib

        data = f"{violation.get('file_path')}{violation.get('code_content')}{time.time()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def _hash_code(self, code: str) -> str:
        """Hash code content for tracking"""
        return hashlib.md5(code.encode()).hexdigest()

# Git monitoring for outcome detection
class GitOutcomeMonitor:
    """Monitor git commits to detect violation outcomes"""

    def __init__(self):
        self.learner = OutcomeLearner()

    def check_pending_outcomes(self) -> None:
        """
        Check pending violations against git commits

        Run this periodically to detect outcomes
        """
        import subprocess

        # Get pending outcomes
        pending = [
            o for o in self.learner.outcomes
            if o.get("outcome") == "pending"
            and time.time() - o.get("timestamp", 0) < 3600  # Last hour
        ]

        if not pending:
            return

        # Check if files were committed
        try:
            result = subprocess.run(
                ["git", "log", "--name-only", "--format=", "-1"],
                capture_output=True,
                text=True,
                check=True
            )

            committed_files = [
                f.strip() for f in result.stdout.split("\n")
                if f.strip()
            ]

        except:
            return

        # Check each pending outcome
        for outcome in pending:
            file_path = outcome.get("file_path", "")

            # Was this file committed?
            committed = any(file_path.endswith(f) for f in committed_files)

            if committed:
                # File was committed - mark as intentional
                self.learner.record_outcome(
                    outcome.get("tracking_id"),
                    "intentional",
                    {"method": "git_commit_detected"}
                )

if __name__ == "__main__":
    # Test harness
    learner = OutcomeLearner()

    # Example: Track violation
    violation = {
        "file_path": "src/test.js",
        "code_content": 'const API = "example.com"',
        "risk_score": 0.6,
        "matched_patterns": [
            {"type": "fake_ui", "pattern": "example.com"}
        ]
    }

    tracking_id = learner.track_violation(violation, "notify")
    print(f"Tracking: {tracking_id}")

    # Later: Record outcome
    learner.record_outcome(tracking_id, "corrected")

    # Get statistics
    stats = learner.get_statistics()
    print(json.dumps(stats, indent=2))
