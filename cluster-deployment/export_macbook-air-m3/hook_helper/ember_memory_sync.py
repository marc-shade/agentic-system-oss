#!/usr/bin/env python3
"""
Ember Memory Sync
Syncs Ember violation logs into enhanced-memory for Phoenix's self-improvement

This creates a closed feedback loop:
1. Ember detects violations → Logs to .jsonl
2. This script imports into enhanced-memory
3. Phoenix queries memory for context
4. Phoenix learns from patterns
5. Phoenix improves decision-making
"""

import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Paths
VIOLATIONS_LOG = Path.home() / ".claude" / "ember_violations.jsonl"
OUTCOMES_LOG = Path.home() / ".claude" / "ember_outcomes.jsonl"
LEARNED_PATTERNS = Path.home() / ".claude" / "ember_learned_patterns.json"
SYNC_STATE = Path.home() / ".claude" / "ember_memory_sync_state.json"

class EmberMemorySync:
    """Sync Ember logs into enhanced-memory"""

    def __init__(self):
        self.sync_state = self._load_sync_state()
        self.entities_created = 0
        self.entities_updated = 0

    def _load_sync_state(self) -> Dict:
        """Load last sync state"""
        if SYNC_STATE.exists():
            try:
                with open(SYNC_STATE) as f:
                    return json.load(f)
            except:
                pass

        return {
            "last_sync": 0,
            "violations_synced": 0,
            "outcomes_synced": 0,
            "patterns_synced": 0
        }

    def _save_sync_state(self) -> None:
        """Save sync state"""
        with open(SYNC_STATE, "w") as f:
            json.dump(self.sync_state, f, indent=2)

    def sync_violations(self) -> List[Dict]:
        """
        Sync violations to enhanced-memory

        Creates entities with:
        - name: ember-violation-{type}-{timestamp}
        - entityType: production_violation
        - observations: detailed violation info
        """
        if not VIOLATIONS_LOG.exists():
            return []

        violations = []
        last_sync = self.sync_state.get("last_sync", 0)

        with open(VIOLATIONS_LOG) as f:
            for line in f:
                try:
                    v = json.loads(line)
                    timestamp = v.get("timestamp", 0)

                    # Only sync new violations
                    if timestamp > last_sync:
                        violations.append(v)
                except:
                    pass

        # Create enhanced-memory entities
        entities = []
        for v in violations:
            entity = self._violation_to_entity(v)
            entities.append(entity)

        self.sync_state["violations_synced"] += len(entities)
        return entities

    def sync_outcomes(self) -> List[Dict]:
        """
        Sync outcomes to enhanced-memory

        Creates entities with:
        - name: ember-outcome-{corrected|intentional}-{timestamp}
        - entityType: violation_outcome
        - observations: outcome details
        """
        if not OUTCOMES_LOG.exists():
            return []

        outcomes = []
        last_sync = self.sync_state.get("last_sync", 0)

        with open(OUTCOMES_LOG) as f:
            for line in f:
                try:
                    o = json.loads(line)
                    timestamp = o.get("timestamp", 0)

                    if timestamp > last_sync:
                        outcomes.append(o)
                except:
                    pass

        entities = []
        for o in outcomes:
            entity = self._outcome_to_entity(o)
            entities.append(entity)

        self.sync_state["outcomes_synced"] += len(entities)
        return entities

    def sync_learned_patterns(self) -> List[Dict]:
        """
        Sync learned patterns to enhanced-memory

        Creates entities with:
        - name: ember-pattern-{pattern_type}-{hash}
        - entityType: learned_pattern
        - observations: pattern details, correction rates
        """
        if not LEARNED_PATTERNS.exists():
            return []

        with open(LEARNED_PATTERNS) as f:
            patterns_db = json.load(f)

        entities = []

        # Sync risk adjustments
        for pattern_key, adjustment in patterns_db.get("risk_adjustments", {}).items():
            entity = {
                "name": f"ember-risk-adjustment-{self._hash(pattern_key)}",
                "entityType": "risk_adjustment",
                "observations": [
                    f"pattern_key: {pattern_key}",
                    f"risk_delta: {adjustment}",
                    f"reason: learned_from_corrections",
                    f"last_updated: {int(time.time())}"
                ]
            }
            entities.append(entity)

        # Sync exception patterns
        for i, exception in enumerate(patterns_db.get("exception_patterns", [])):
            entity = {
                "name": f"ember-exception-{self._hash(exception.get('pattern', str(i)))}",
                "entityType": "exception_pattern",
                "observations": [
                    f"pattern: {exception.get('pattern')}",
                    f"type: {exception.get('type')}",
                    f"file_pattern: {exception.get('file_pattern')}",
                    f"reason: {exception.get('reason')}",
                    f"intentional_rate: {exception.get('rate', 0)}"
                ]
            }
            entities.append(entity)

        # Sync correction rates
        for pattern_key, rates in patterns_db.get("correction_rates", {}).items():
            entity = {
                "name": f"ember-correction-rate-{self._hash(pattern_key)}",
                "entityType": "correction_rate",
                "observations": [
                    f"pattern_key: {pattern_key}",
                    f"total: {rates.get('total', 0)}",
                    f"corrected: {rates.get('corrected', 0)}",
                    f"intentional: {rates.get('intentional', 0)}",
                    f"correction_rate: {rates.get('corrected', 0) / max(rates.get('total', 1), 1):.2f}"
                ]
            }
            entities.append(entity)

        self.sync_state["patterns_synced"] += len(entities)
        return entities

    def _violation_to_entity(self, violation: Dict) -> Dict:
        """Convert violation to enhanced-memory entity"""
        timestamp = violation.get("timestamp", time.time())
        tier = violation.get("tier", "unknown")
        file_path = violation.get("file_path", "unknown")
        risk = violation.get("risk_score", 0)
        patterns = violation.get("patterns", [])

        observations = [
            f"tier: {tier}",
            f"risk_score: {risk}",
            f"file_path: {file_path}",
            f"timestamp: {timestamp}",
            f"datetime: {datetime.fromtimestamp(timestamp).isoformat()}",
            f"pattern_count: {len(patterns)}"
        ]

        # Add pattern details
        for p in patterns:
            pattern_type = p.get("type", "unknown")
            observations.append(f"violation_type: {pattern_type}")
            observations.append(f"pattern_matched: {p.get('pattern', 'N/A')}")

        # Add code snippet
        snippet = violation.get("code_snippet", "")
        if snippet:
            observations.append(f"code_preview: {snippet[:100]}")

        return {
            "name": f"ember-violation-{tier}-{int(timestamp)}",
            "entityType": "production_violation",
            "observations": observations
        }

    def _outcome_to_entity(self, outcome: Dict) -> Dict:
        """Convert outcome to enhanced-memory entity"""
        timestamp = outcome.get("timestamp", time.time())
        outcome_type = outcome.get("outcome", "pending")
        tracking_id = outcome.get("tracking_id", "unknown")

        observations = [
            f"outcome: {outcome_type}",
            f"tracking_id: {tracking_id}",
            f"timestamp: {timestamp}",
            f"datetime: {datetime.fromtimestamp(timestamp).isoformat()}",
            f"file_path: {outcome.get('file_path', 'unknown')}",
            f"tier: {outcome.get('tier', 'unknown')}",
            f"risk_score: {outcome.get('risk_score', 0)}"
        ]

        # Add outcome-specific details
        if outcome_type == "corrected":
            observations.append("phoenix_action: fixed_violation")
            observations.append("learning: pattern_risk_increased")
        elif outcome_type == "intentional":
            observations.append("phoenix_action: committed_anyway")
            observations.append("learning: potential_exception_pattern")

        return {
            "name": f"ember-outcome-{outcome_type}-{int(timestamp)}",
            "entityType": "violation_outcome",
            "observations": observations
        }

    def _hash(self, text: str) -> str:
        """Simple hash for entity names"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()[:8]

    def generate_sync_payload(self) -> Dict:
        """
        Generate complete sync payload for enhanced-memory

        Returns dict ready for enhanced-memory MCP
        """
        violations = self.sync_violations()
        outcomes = self.sync_outcomes()
        patterns = self.sync_learned_patterns()

        all_entities = violations + outcomes + patterns

        self.sync_state["last_sync"] = int(time.time())
        self._save_sync_state()

        return {
            "entities": all_entities,
            "stats": {
                "violations": len(violations),
                "outcomes": len(outcomes),
                "patterns": len(patterns),
                "total": len(all_entities)
            },
            "sync_timestamp": self.sync_state["last_sync"]
        }

    def generate_context_summary(self) -> str:
        """
        Generate human-readable context summary for Phoenix

        Used in environmental awareness startup
        """
        # Load recent data
        recent_violations = self._get_recent_violations(hours=24)
        learned_patterns_db = self._load_learned_patterns()

        summary = []
        summary.append("# Ember Watchdog Context")
        summary.append("")

        # Recent violations
        summary.append(f"## Last 24 Hours")
        summary.append(f"- Total violations: {len(recent_violations)}")

        tier_counts = {}
        for v in recent_violations:
            tier = v.get("tier", "unknown")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        for tier, count in sorted(tier_counts.items()):
            summary.append(f"  - {tier}: {count}")

        # Learning stats
        summary.append("")
        summary.append("## Learning Status")

        correction_rates = learned_patterns_db.get("correction_rates", {})
        exception_patterns = learned_patterns_db.get("exception_patterns", [])
        risk_adjustments = learned_patterns_db.get("risk_adjustments", {})

        summary.append(f"- Patterns tracked: {len(correction_rates)}")
        summary.append(f"- Exception patterns: {len(exception_patterns)}")
        summary.append(f"- Risk adjustments: {len(risk_adjustments)}")

        # Common violations
        summary.append("")
        summary.append("## Common Recent Patterns")

        pattern_types = {}
        for v in recent_violations[-20:]:  # Last 20
            for p in v.get("patterns", []):
                ptype = p.get("type", "unknown")
                pattern_types[ptype] = pattern_types.get(ptype, 0) + 1

        for ptype, count in sorted(pattern_types.items(), key=lambda x: -x[1])[:5]:
            summary.append(f"- {ptype}: {count} times")

        # Self-improvement insights
        summary.append("")
        summary.append("## Self-Improvement Insights")

        # Find high-correction-rate patterns
        high_correction = []
        for pattern_key, rates in correction_rates.items():
            total = rates.get("total", 0)
            corrected = rates.get("corrected", 0)
            if total > 0:
                rate = corrected / total
                if rate > 0.8:
                    high_correction.append((pattern_key, rate))

        if high_correction:
            summary.append("- Patterns I should avoid (80%+ correction rate):")
            for pattern, rate in sorted(high_correction, key=lambda x: -x[1])[:3]:
                summary.append(f"  - {pattern}: {rate:.1%} corrected")
        else:
            summary.append("- No high-correction patterns yet (learning)")

        # Find exception patterns
        if exception_patterns:
            summary.append("- Patterns that are intentional:")
            for exc in exception_patterns[:3]:
                pattern = exc.get("pattern", "unknown")
                file_pat = exc.get("file_pattern", "unknown")
                summary.append(f"  - {pattern} in {file_pat} files")

        return "\n".join(summary)

    def _get_recent_violations(self, hours: int = 24) -> List[Dict]:
        """Get recent violations"""
        if not VIOLATIONS_LOG.exists():
            return []

        cutoff = time.time() - (hours * 3600)
        violations = []

        with open(VIOLATIONS_LOG) as f:
            for line in f:
                try:
                    v = json.loads(line)
                    if v.get("timestamp", 0) > cutoff:
                        violations.append(v)
                except:
                    pass

        return violations

    def _load_learned_patterns(self) -> Dict:
        """Load learned patterns DB"""
        if LEARNED_PATTERNS.exists():
            try:
                with open(LEARNED_PATTERNS) as f:
                    return json.load(f)
            except:
                pass

        return {
            "risk_adjustments": {},
            "exception_patterns": [],
            "correction_rates": {}
        }

def main():
    """
    Main entry point

    Modes:
    - sync: Sync to enhanced-memory (outputs JSON for MCP)
    - summary: Generate context summary for startup
    - stats: Show sync statistics
    """
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "sync"

    syncer = EmberMemorySync()

    if mode == "sync":
        # Generate sync payload
        payload = syncer.generate_sync_payload()
        print(json.dumps(payload, indent=2))

    elif mode == "summary":
        # Generate context summary
        summary = syncer.generate_context_summary()
        print(summary)

    elif mode == "stats":
        # Show statistics
        stats = {
            "sync_state": syncer.sync_state,
            "violations_available": len(syncer._get_recent_violations(hours=168)),  # 1 week
            "learned_patterns": syncer._load_learned_patterns()
        }
        print(json.dumps(stats, indent=2))

    else:
        print(f"Unknown mode: {mode}")
        print("Usage: ember_memory_sync.py [sync|summary|stats]")
        sys.exit(1)

if __name__ == "__main__":
    main()
