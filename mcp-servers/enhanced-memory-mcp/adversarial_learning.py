#!/usr/bin/env python3
"""
Adversarial Learning Module for Enhanced Memory MCP

Implements persistent learning from adversarial attacks and defense patterns.
Part of Stage 3+ hardening - the system learns from attack attempts.

Key Features:
1. Store adversarial test results in enhanced-memory
2. Track attack patterns and successful defenses
3. Learn from new attack attempts over time
4. Enable pattern recognition across attacks
5. Provide adaptive defense recommendations

Integration: Uses enhanced-memory's episodic and semantic memory tiers.
"""

import os
import json
import sqlite3
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("adversarial-learning")

DB_PATH = os.path.expanduser("~/.claude/enhanced_memories/memory.db")


class AttackCategory(Enum):
    """Categories of adversarial attacks."""
    KEYWORD_STUFFING = "keyword_stuffing"
    FALSE_CLAIMS = "false_claims"
    CIRCULAR_CAUSATION = "circular_causation"
    PROVENANCE_GAMING = "provenance_gaming"
    LOGICAL_CONTRADICTION = "logical_contradiction"
    INJECTION_ATTEMPT = "injection_attempt"
    MEMORIZATION_ATTACK = "memorization_attack"
    DISTRIBUTION_SHIFT = "distribution_shift"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    SPECIFICATION_GAMING = "specification_gaming"


class DefenseOutcome(Enum):
    """Outcome of defense against an attack."""
    BLOCKED = "blocked"
    FLAGGED = "flagged"
    ALLOWED = "allowed"  # Attack bypassed defense
    PARTIAL = "partial"  # Partially blocked


@dataclass
class AttackPattern:
    """Represents a detected attack pattern."""
    pattern_id: str
    category: AttackCategory
    signature: str  # Hash of attack characteristics
    example_content: str
    detection_method: str
    first_seen: str
    last_seen: str
    occurrence_count: int
    block_rate: float  # How often this pattern is blocked (0.0-1.0)
    defense_strategies: List[str]


@dataclass
class DefenseEvent:
    """Records a single defense event."""
    event_id: str
    timestamp: str
    attack_category: str
    attack_signature: str
    attack_content_hash: str  # Don't store actual malicious content
    outcome: DefenseOutcome
    defense_method: str
    confidence: float
    context: Dict[str, Any]


class AdversarialLearningSystem:
    """
    Persistent learning system for adversarial patterns.

    Stores attack patterns and defense outcomes in enhanced-memory
    to enable learning and adaptation over time.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()
        self._load_known_patterns()

    def _init_tables(self):
        """Initialize adversarial learning tables."""
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found at {self.db_path}")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table for attack patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attack_patterns (
                pattern_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                signature TEXT NOT NULL,
                example_content TEXT,
                detection_method TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                block_rate REAL DEFAULT 1.0,
                defense_strategies TEXT,
                UNIQUE(category, signature)
            )
        """)

        # Table for defense events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defense_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                attack_category TEXT NOT NULL,
                attack_signature TEXT NOT NULL,
                attack_content_hash TEXT NOT NULL,
                outcome TEXT NOT NULL,
                defense_method TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                context TEXT,
                pattern_id TEXT,
                FOREIGN KEY (pattern_id) REFERENCES attack_patterns(pattern_id)
            )
        """)

        # Table for defense effectiveness
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defense_effectiveness (
                defense_method TEXT PRIMARY KEY,
                total_attempts INTEGER DEFAULT 0,
                successful_blocks INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                false_negatives INTEGER DEFAULT 0,
                effectiveness_score REAL DEFAULT 0.0,
                last_updated TEXT
            )
        """)

        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_defense_events_category
            ON defense_events(attack_category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_defense_events_timestamp
            ON defense_events(timestamp)
        """)

        conn.commit()
        conn.close()
        logger.info("Adversarial learning tables initialized")

    def _load_known_patterns(self):
        """Load known attack patterns from database."""
        self.known_patterns: Dict[str, AttackPattern] = {}

        if not os.path.exists(self.db_path):
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM attack_patterns")
            rows = cursor.fetchall()

            for row in rows:
                pattern = AttackPattern(
                    pattern_id=row[0],
                    category=AttackCategory(row[1]),
                    signature=row[2],
                    example_content=row[3],
                    detection_method=row[4],
                    first_seen=row[5],
                    last_seen=row[6],
                    occurrence_count=row[7],
                    block_rate=row[8],
                    defense_strategies=json.loads(row[9]) if row[9] else []
                )
                self.known_patterns[pattern.pattern_id] = pattern

            logger.info(f"Loaded {len(self.known_patterns)} known attack patterns")
        except sqlite3.OperationalError:
            pass  # Tables don't exist yet
        finally:
            conn.close()

    def _compute_signature(self, content: str, category: AttackCategory) -> str:
        """Compute a signature for an attack pattern."""
        # Extract key features for signature
        features = {
            "category": category.value,
            "length_bucket": len(content) // 100,  # Bucket by 100 chars
            "word_count_bucket": len(content.split()) // 10,
            "has_numbers": any(c.isdigit() for c in content),
            "has_special": any(not c.isalnum() and not c.isspace() for c in content),
        }

        # Category-specific features
        if category == AttackCategory.KEYWORD_STUFFING:
            words = content.lower().split()
            word_freq = defaultdict(int)
            for w in words:
                word_freq[w] += 1
            max_freq = max(word_freq.values()) if word_freq else 0
            features["max_word_freq"] = max_freq
            features["unique_ratio"] = len(set(words)) / len(words) if words else 0

        elif category == AttackCategory.FALSE_CLAIMS:
            features["has_equals"] = "=" in content or "equals" in content.lower()
            features["has_math_op"] = any(op in content for op in ["+", "-", "*", "/", "×", "÷"])

        # Generate hash from features
        feature_str = json.dumps(features, sort_keys=True)
        return hashlib.sha256(feature_str.encode()).hexdigest()[:16]

    def record_defense_event(
        self,
        content: str,
        category: AttackCategory,
        outcome: DefenseOutcome,
        defense_method: str,
        confidence: float = 0.9,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a defense event and update attack patterns.

        Args:
            content: The content that was evaluated
            category: Category of the attack
            outcome: Whether the attack was blocked/flagged/allowed
            defense_method: Which defense mechanism was used
            confidence: Confidence in the defense decision
            context: Additional context about the event

        Returns:
            event_id of the recorded event
        """
        timestamp = datetime.utcnow().isoformat()
        signature = self._compute_signature(content, category)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        # Generate unique event_id with timestamp and content hash
        event_id = f"def_{timestamp.replace(':', '').replace('-', '').replace('.', '')[:17]}_{content_hash[:8]}"

        # Check if this matches a known pattern
        pattern_id = self._find_or_create_pattern(
            category=category,
            signature=signature,
            example_content=content[:200],  # Truncate for storage
            detection_method=defense_method,
            defense_strategies=[defense_method]
        )

        # Record the event
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO defense_events
                (event_id, timestamp, attack_category, attack_signature,
                 attack_content_hash, outcome, defense_method, confidence,
                 context, pattern_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, timestamp, category.value, signature,
                content_hash, outcome.value, defense_method, confidence,
                json.dumps(context or {}), pattern_id
            ))

            # Update pattern statistics
            self._update_pattern_stats(cursor, pattern_id, outcome)

            # Update defense effectiveness
            self._update_defense_effectiveness(cursor, defense_method, outcome)

            conn.commit()
            logger.info(f"Recorded defense event: {event_id} ({category.value} → {outcome.value})")

        finally:
            conn.close()

        return event_id

    def _find_or_create_pattern(
        self,
        category: AttackCategory,
        signature: str,
        example_content: str,
        detection_method: str,
        defense_strategies: List[str]
    ) -> str:
        """Find existing pattern or create new one."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Check for existing pattern
            cursor.execute("""
                SELECT pattern_id FROM attack_patterns
                WHERE category = ? AND signature = ?
            """, (category.value, signature))

            row = cursor.fetchone()
            if row:
                pattern_id = row[0]
                # Update last_seen and occurrence_count
                cursor.execute("""
                    UPDATE attack_patterns
                    SET last_seen = ?, occurrence_count = occurrence_count + 1
                    WHERE pattern_id = ?
                """, (datetime.utcnow().isoformat(), pattern_id))
                conn.commit()
                return pattern_id

            # Create new pattern
            pattern_id = f"pat_{hashlib.sha256(f'{category.value}_{signature}'.encode()).hexdigest()[:12]}"
            timestamp = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO attack_patterns
                (pattern_id, category, signature, example_content, detection_method,
                 first_seen, last_seen, occurrence_count, block_rate, defense_strategies)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1.0, ?)
            """, (
                pattern_id, category.value, signature, example_content,
                detection_method, timestamp, timestamp, json.dumps(defense_strategies)
            ))

            conn.commit()
            logger.info(f"Created new attack pattern: {pattern_id} ({category.value})")
            return pattern_id

        finally:
            conn.close()

    def _update_pattern_stats(
        self,
        cursor: sqlite3.Cursor,
        pattern_id: str,
        outcome: DefenseOutcome
    ):
        """Update pattern statistics based on defense outcome."""
        # Get current stats
        cursor.execute("""
            SELECT occurrence_count, block_rate FROM attack_patterns
            WHERE pattern_id = ?
        """, (pattern_id,))

        row = cursor.fetchone()
        if not row:
            return

        count, current_rate = row

        # Calculate new block rate
        blocked = 1.0 if outcome in [DefenseOutcome.BLOCKED, DefenseOutcome.FLAGGED] else 0.0
        new_rate = ((current_rate * (count - 1)) + blocked) / count

        cursor.execute("""
            UPDATE attack_patterns
            SET block_rate = ?
            WHERE pattern_id = ?
        """, (new_rate, pattern_id))

    def _update_defense_effectiveness(
        self,
        cursor: sqlite3.Cursor,
        defense_method: str,
        outcome: DefenseOutcome
    ):
        """Update defense method effectiveness statistics."""
        cursor.execute("""
            INSERT INTO defense_effectiveness (defense_method, total_attempts, last_updated)
            VALUES (?, 1, ?)
            ON CONFLICT(defense_method) DO UPDATE SET
                total_attempts = total_attempts + 1,
                last_updated = excluded.last_updated
        """, (defense_method, datetime.utcnow().isoformat()))

        if outcome == DefenseOutcome.BLOCKED:
            cursor.execute("""
                UPDATE defense_effectiveness
                SET successful_blocks = successful_blocks + 1
                WHERE defense_method = ?
            """, (defense_method,))
        elif outcome == DefenseOutcome.ALLOWED:
            cursor.execute("""
                UPDATE defense_effectiveness
                SET false_negatives = false_negatives + 1
                WHERE defense_method = ?
            """, (defense_method,))

        # Recalculate effectiveness score
        cursor.execute("""
            UPDATE defense_effectiveness
            SET effectiveness_score =
                CAST(successful_blocks AS REAL) / NULLIF(total_attempts, 0)
            WHERE defense_method = ?
        """, (defense_method,))

    def get_attack_pattern_summary(self) -> Dict[str, Any]:
        """Get summary of known attack patterns."""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get pattern counts by category
            cursor.execute("""
                SELECT category, COUNT(*), AVG(block_rate), SUM(occurrence_count)
                FROM attack_patterns
                GROUP BY category
            """)

            categories = {}
            for row in cursor.fetchall():
                categories[row[0]] = {
                    "pattern_count": row[1],
                    "avg_block_rate": round(row[2], 3) if row[2] else 0,
                    "total_occurrences": row[3]
                }

            # Get total events
            cursor.execute("SELECT COUNT(*) FROM defense_events")
            total_events = cursor.fetchone()[0]

            # Get recent events
            cursor.execute("""
                SELECT attack_category, outcome, COUNT(*)
                FROM defense_events
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY attack_category, outcome
            """)

            recent_by_category = defaultdict(lambda: defaultdict(int))
            for row in cursor.fetchall():
                recent_by_category[row[0]][row[1]] = row[2]

            return {
                "total_patterns": len(categories),
                "total_defense_events": total_events,
                "categories": categories,
                "recent_7_days": dict(recent_by_category),
                "last_updated": datetime.utcnow().isoformat()
            }

        finally:
            conn.close()

    def get_defense_effectiveness_report(self) -> Dict[str, Any]:
        """Get effectiveness report for all defense methods."""
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT defense_method, total_attempts, successful_blocks,
                       false_positives, false_negatives, effectiveness_score
                FROM defense_effectiveness
                ORDER BY effectiveness_score DESC
            """)

            methods = []
            for row in cursor.fetchall():
                methods.append({
                    "method": row[0],
                    "total_attempts": row[1],
                    "successful_blocks": row[2],
                    "false_positives": row[3],
                    "false_negatives": row[4],
                    "effectiveness_score": round(row[5], 3) if row[5] else 0
                })

            return {
                "defense_methods": methods,
                "total_methods": len(methods),
                "avg_effectiveness": sum(m["effectiveness_score"] for m in methods) / len(methods) if methods else 0,
                "last_updated": datetime.utcnow().isoformat()
            }

        finally:
            conn.close()

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving defenses based on learned patterns."""
        recommendations = []

        if not os.path.exists(self.db_path):
            return recommendations

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Find patterns with low block rates
            cursor.execute("""
                SELECT category, signature, block_rate, occurrence_count
                FROM attack_patterns
                WHERE block_rate < 0.9 AND occurrence_count > 2
                ORDER BY block_rate ASC
                LIMIT 5
            """)

            for row in cursor.fetchall():
                recommendations.append({
                    "type": "low_block_rate",
                    "priority": "high" if row[2] < 0.5 else "medium",
                    "category": row[0],
                    "block_rate": round(row[2], 3),
                    "occurrences": row[3],
                    "recommendation": f"Improve defense for {row[0]} attacks (current block rate: {row[2]:.1%})"
                })

            # Find defense methods with low effectiveness
            cursor.execute("""
                SELECT defense_method, effectiveness_score, total_attempts
                FROM defense_effectiveness
                WHERE effectiveness_score < 0.9 AND total_attempts > 5
                ORDER BY effectiveness_score ASC
                LIMIT 3
            """)

            for row in cursor.fetchall():
                recommendations.append({
                    "type": "weak_defense",
                    "priority": "high" if row[1] < 0.7 else "medium",
                    "method": row[0],
                    "effectiveness": round(row[1], 3),
                    "attempts": row[2],
                    "recommendation": f"Review and strengthen {row[0]} (effectiveness: {row[1]:.1%})"
                })

            # Check for new attack categories
            cursor.execute("""
                SELECT category, COUNT(*)
                FROM attack_patterns
                WHERE first_seen > datetime('now', '-7 days')
                GROUP BY category
            """)

            for row in cursor.fetchall():
                recommendations.append({
                    "type": "new_category",
                    "priority": "medium",
                    "category": row[0],
                    "new_patterns": row[1],
                    "recommendation": f"New attack patterns detected in {row[0]} - review defenses"
                })

            return recommendations

        finally:
            conn.close()

    def store_learning_to_memory(self) -> Dict[str, Any]:
        """
        Store learned patterns as semantic memory entities.

        This creates persistent memory entities from attack patterns,
        enabling the system to retain learning across sessions.
        """
        if not os.path.exists(self.db_path):
            return {"error": "Database not found"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stored_count = 0

        try:
            # Get patterns that should be stored as memories
            cursor.execute("""
                SELECT pattern_id, category, detection_method, block_rate, occurrence_count
                FROM attack_patterns
                WHERE occurrence_count >= 3
            """)

            patterns = cursor.fetchall()

            for pattern in patterns:
                pattern_id, category, detection_method, block_rate, count = pattern

                # Create semantic memory entity
                entity_name = f"adversarial_pattern_{pattern_id}"

                # Check if already stored
                cursor.execute("""
                    SELECT id FROM entities WHERE name = ?
                """, (entity_name,))

                if cursor.fetchone():
                    continue  # Already stored

                # Insert as semantic memory
                cursor.execute("""
                    INSERT INTO entities (name, entity_type, tier, created_at)
                    VALUES (?, 'adversarial_learning', 'semantic', ?)
                """, (entity_name, datetime.utcnow().isoformat()))

                entity_id = cursor.lastrowid

                # Add observations
                observations = [
                    f"Attack category: {category}",
                    f"Detection method: {detection_method}",
                    f"Block rate: {block_rate:.1%}",
                    f"Occurrences: {count}",
                    f"Learned defense pattern for {category} attacks"
                ]

                for obs in observations:
                    cursor.execute("""
                        INSERT INTO observations (entity_id, content, created_at)
                        VALUES (?, ?, ?)
                    """, (entity_id, obs, datetime.utcnow().isoformat()))

                stored_count += 1

            conn.commit()

            return {
                "status": "success",
                "patterns_stored": stored_count,
                "total_patterns": len(patterns),
                "timestamp": datetime.utcnow().isoformat()
            }

        finally:
            conn.close()


# Singleton instance
_learning_system = None


def get_adversarial_learning_system() -> AdversarialLearningSystem:
    """Get singleton adversarial learning system instance."""
    global _learning_system
    if _learning_system is None:
        _learning_system = AdversarialLearningSystem()
    return _learning_system


def record_blocked_attack(
    content: str,
    category: str,
    defense_method: str,
    confidence: float = 0.9
) -> str:
    """Convenience function to record a blocked attack."""
    system = get_adversarial_learning_system()
    return system.record_defense_event(
        content=content,
        category=AttackCategory(category),
        outcome=DefenseOutcome.BLOCKED,
        defense_method=defense_method,
        confidence=confidence
    )


def record_flagged_content(
    content: str,
    category: str,
    defense_method: str,
    confidence: float = 0.7
) -> str:
    """Convenience function to record flagged content."""
    system = get_adversarial_learning_system()
    return system.record_defense_event(
        content=content,
        category=AttackCategory(category),
        outcome=DefenseOutcome.FLAGGED,
        defense_method=defense_method,
        confidence=confidence
    )


if __name__ == "__main__":
    # Test the adversarial learning system
    print("Testing Adversarial Learning System...")

    system = AdversarialLearningSystem()

    # Record some test events
    event1 = system.record_defense_event(
        content="algorithm optimization code performance benchmark test framework",
        category=AttackCategory.KEYWORD_STUFFING,
        outcome=DefenseOutcome.BLOCKED,
        defense_method="semantic_coherence_check",
        confidence=0.95
    )
    print(f"Recorded event 1: {event1}")

    event2 = system.record_defense_event(
        content="2+2=5 is true in alternative mathematics",
        category=AttackCategory.FALSE_CLAIMS,
        outcome=DefenseOutcome.BLOCKED,
        defense_method="fact_validation",
        confidence=0.98
    )
    print(f"Recorded event 2: {event2}")

    event3 = system.record_defense_event(
        content="Entity A causes Entity A through self-reference",
        category=AttackCategory.CIRCULAR_CAUSATION,
        outcome=DefenseOutcome.BLOCKED,
        defense_method="causal_link_validator",
        confidence=0.99
    )
    print(f"Recorded event 3: {event3}")

    # Get summary
    print("\n--- Attack Pattern Summary ---")
    summary = system.get_attack_pattern_summary()
    print(json.dumps(summary, indent=2))

    # Get effectiveness report
    print("\n--- Defense Effectiveness Report ---")
    report = system.get_defense_effectiveness_report()
    print(json.dumps(report, indent=2))

    # Get recommendations
    print("\n--- Recommendations ---")
    recommendations = system.get_recommendations()
    for rec in recommendations:
        print(f"  [{rec['priority']}] {rec['recommendation']}")

    # Store to memory
    print("\n--- Storing Patterns to Memory ---")
    result = system.store_learning_to_memory()
    print(json.dumps(result, indent=2))

    print("\n✅ Adversarial Learning System test complete")
