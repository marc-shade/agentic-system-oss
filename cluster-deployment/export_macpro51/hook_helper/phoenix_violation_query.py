#!/usr/bin/env python3
"""
Phoenix Violation Query Interface
Allows Phoenix to query past violations before making decisions

Usage in Claude Code:
  from phoenix_violation_query import ViolationQuery

  query = ViolationQuery()
  similar = query.find_similar_violations(code_snippet, file_path)
  if similar:
      # Learn from past violations
      for v in similar:
          print(f"Past violation: {v['tier']} - {v['patterns']}")
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional

VIOLATIONS_LOG = Path.home() / ".claude" / "ember_violations.jsonl"
OUTCOMES_LOG = Path.home() / ".claude" / "ember_outcomes.jsonl"
LEARNED_PATTERNS = Path.home() / ".claude" / "ember_learned_patterns.json"

class ViolationQuery:
    """Query interface for Phoenix to learn from past violations"""

    def __init__(self):
        self.violations = self._load_violations()
        self.outcomes = self._load_outcomes()
        self.patterns = self._load_patterns()

    def _load_violations(self) -> List[Dict]:
        """Load all violations"""
        violations = []
        if VIOLATIONS_LOG.exists():
            with open(VIOLATIONS_LOG) as f:
                for line in f:
                    try:
                        violations.append(json.loads(line))
                    except:
                        pass
        return violations

    def _load_outcomes(self) -> List[Dict]:
        """Load all outcomes"""
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
        if LEARNED_PATTERNS.exists():
            try:
                with open(LEARNED_PATTERNS) as f:
                    return json.load(f)
            except:
                pass
        return {}

    def find_similar_violations(
        self,
        code_snippet: str,
        file_path: str = "",
        limit: int = 5
    ) -> List[Dict]:
        """
        Find similar past violations

        Returns violations that match:
        - Similar code patterns
        - Same file or file type
        - Recent violations (weighted by recency)
        """
        matches = []

        for v in self.violations:
            score = 0

            # Check code similarity
            v_snippet = v.get("code_snippet", "")
            if v_snippet and self._code_similarity(code_snippet, v_snippet) > 0.5:
                score += 3

            # Check file similarity
            v_file = v.get("file_path", "")
            if file_path and self._file_similarity(file_path, v_file) > 0.5:
                score += 2

            # Check pattern overlap
            for pattern in v.get("patterns", []):
                if re.search(pattern.get("pattern", ""), code_snippet, re.IGNORECASE):
                    score += 1

            if score > 0:
                v["similarity_score"] = score
                matches.append(v)

        # Sort by similarity
        matches.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        return matches[:limit]

    def should_i_avoid_this(self, code_snippet: str, file_path: str = "") -> Dict:
        """
        Phoenix asks: "Should I avoid writing this code?"

        Returns:
        - should_avoid: bool
        - reason: str
        - confidence: float
        - similar_violations: List[Dict]
        """
        similar = self.find_similar_violations(code_snippet, file_path, limit=3)

        if not similar:
            return {
                "should_avoid": False,
                "reason": "No similar violations found",
                "confidence": 0.0,
                "similar_violations": []
            }

        # Check outcomes
        corrected_count = 0
        intentional_count = 0

        for v in similar:
            # Find outcome for this violation
            outcomes = [
                o for o in self.outcomes
                if o.get("file_path") == v.get("file_path")
                and abs(o.get("timestamp", 0) - v.get("timestamp", 0)) < 600  # 10 min window
            ]

            for o in outcomes:
                if o.get("outcome") == "corrected":
                    corrected_count += 1
                elif o.get("outcome") == "intentional":
                    intentional_count += 1

        total = corrected_count + intentional_count

        if total == 0:
            return {
                "should_avoid": False,
                "reason": "Similar violations found but no outcome data yet",
                "confidence": 0.3,
                "similar_violations": similar
            }

        correction_rate = corrected_count / total

        if correction_rate > 0.7:
            # 70%+ corrected = avoid
            return {
                "should_avoid": True,
                "reason": f"Similar code was corrected {correction_rate:.0%} of the time",
                "confidence": correction_rate,
                "similar_violations": similar
            }
        elif correction_rate < 0.3:
            # 70%+ intentional = probably okay
            return {
                "should_avoid": False,
                "reason": f"Similar code was intentional {1-correction_rate:.0%} of the time",
                "confidence": 1 - correction_rate,
                "similar_violations": similar
            }
        else:
            # Unclear
            return {
                "should_avoid": False,
                "reason": "Mixed outcomes on similar code - use judgment",
                "confidence": 0.5,
                "similar_violations": similar
            }

    def get_high_risk_patterns(self) -> List[Dict]:
        """
        Get patterns Phoenix should avoid

        Returns patterns with high correction rates
        """
        high_risk = []

        correction_rates = self.patterns.get("correction_rates", {})

        for pattern_key, rates in correction_rates.items():
            total = rates.get("total", 0)
            corrected = rates.get("corrected", 0)

            if total >= 3:  # At least 3 samples
                rate = corrected / total
                if rate >= 0.8:  # 80%+ corrected
                    high_risk.append({
                        "pattern": pattern_key,
                        "correction_rate": rate,
                        "total_instances": total,
                        "advice": "Avoid this pattern - frequently corrected"
                    })

        return sorted(high_risk, key=lambda x: x["correction_rate"], reverse=True)

    def get_safe_patterns(self) -> List[Dict]:
        """
        Get patterns that are usually intentional

        Returns exception patterns Phoenix can use
        """
        safe = []

        for exception in self.patterns.get("exception_patterns", []):
            safe.append({
                "pattern": exception.get("pattern"),
                "type": exception.get("type"),
                "file_pattern": exception.get("file_pattern"),
                "intentional_rate": exception.get("rate", 0),
                "advice": f"Okay to use in {exception.get('file_pattern')} files"
            })

        return safe

    def get_self_improvement_insights(self) -> Dict:
        """
        Get insights for Phoenix's self-improvement

        Returns:
        - patterns_to_avoid
        - safe_patterns
        - recent_trends
        - learning_progress
        """
        return {
            "patterns_to_avoid": self.get_high_risk_patterns(),
            "safe_patterns": self.get_safe_patterns(),
            "recent_trends": self._get_recent_trends(),
            "learning_progress": self._get_learning_progress()
        }

    def _get_recent_trends(self) -> Dict:
        """Analyze recent violation trends"""
        import time

        recent_cutoff = time.time() - (7 * 86400)  # Last 7 days
        recent = [v for v in self.violations if v.get("timestamp", 0) > recent_cutoff]

        if not recent:
            return {"trend": "no_data"}

        # Group by tier
        tier_counts = {}
        for v in recent:
            tier = v.get("tier", "unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        # Detect trend
        total = len(recent)
        critical_ratio = (tier_counts.get("escalate", 0) + tier_counts.get("intervene", 0)) / total

        if critical_ratio > 0.3:
            trend = "increasing_violations"
        elif critical_ratio < 0.1:
            trend = "improving"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "total_recent": total,
            "tier_breakdown": tier_counts,
            "critical_ratio": critical_ratio
        }

    def _get_learning_progress(self) -> Dict:
        """Track learning progress metrics"""
        correction_rates = self.patterns.get("correction_rates", {})

        if not correction_rates:
            return {"status": "no_data"}

        # Calculate average correction rate
        total_corrections = 0
        total_samples = 0

        for rates in correction_rates.values():
            total_corrections += rates.get("corrected", 0)
            total_samples += rates.get("total", 0)

        avg_correction_rate = total_corrections / total_samples if total_samples > 0 else 0

        return {
            "status": "learning",
            "patterns_tracked": len(correction_rates),
            "average_correction_rate": avg_correction_rate,
            "exception_patterns": len(self.patterns.get("exception_patterns", [])),
            "risk_adjustments": len(self.patterns.get("risk_adjustments", {}))
        }

    def _code_similarity(self, code1: str, code2: str) -> float:
        """Simple code similarity score"""
        # Normalize whitespace
        c1 = " ".join(code1.split())
        c2 = " ".join(code2.split())

        # Jaccard similarity on tokens
        tokens1 = set(c1.split())
        tokens2 = set(c2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _file_similarity(self, file1: str, file2: str) -> float:
        """File path similarity"""
        # Same file = 1.0
        if file1 == file2:
            return 1.0

        # Same extension
        ext1 = Path(file1).suffix
        ext2 = Path(file2).suffix

        if ext1 == ext2 and ext1:
            return 0.7

        # Same directory
        dir1 = Path(file1).parent
        dir2 = Path(file2).parent

        if dir1 == dir2:
            return 0.5

        return 0.0

# Example usage in Claude Code
if __name__ == "__main__":
    query = ViolationQuery()

    # Example: Should Phoenix avoid this code?
    test_code = 'const API_URL = "https://api.example.com"'

    result = query.should_i_avoid_this(test_code, "src/config.js")
    print(json.dumps(result, indent=2))

    print("\n--- High Risk Patterns ---")
    for pattern in query.get_high_risk_patterns():
        print(f"{pattern['pattern']}: {pattern['correction_rate']:.0%} correction rate")

    print("\n--- Safe Patterns ---")
    for pattern in query.get_safe_patterns():
        print(f"{pattern['pattern']} in {pattern['file_pattern']}: {pattern['intentional_rate']:.0%} intentional")

    print("\n--- Self-Improvement Insights ---")
    insights = query.get_self_improvement_insights()
    print(json.dumps(insights, indent=2))
