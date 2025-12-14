"""
Sharpening Engine for Self-Improvement

Implements the Sharpening Mechanism from research:
"Self-Improvement in Language Models: The Sharpening Mechanism"

Key Insight: Verification is easier than generation, so models can
improve by generating candidates, self-verifying, and training on
the high-quality subset.

Also implements Meta-Rewarding for alignment self-improvement.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("sharpening_engine")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class VerificationResult(Enum):
    """Result of self-verification."""
    VERIFIED_HIGH = "verified_high"      # High confidence correct
    VERIFIED_MEDIUM = "verified_medium"  # Medium confidence
    UNCERTAIN = "uncertain"              # Cannot verify
    REJECTED = "rejected"                # Verified incorrect


@dataclass
class SharpeningCandidate:
    """A candidate for sharpening evaluation."""
    candidate_id: int
    action_type: str
    action_description: str
    expected_result: str
    actual_result: str
    original_score: float
    verification_result: VerificationResult
    verification_confidence: float
    meta_judgment_score: float
    should_learn_from: bool


class SharpeningEngine:
    """
    Implements self-improvement via sharpening.

    The sharpening mechanism works because:
    1. Verification is computationally easier than generation
    2. Models can filter their own outputs using self-verification
    3. Training on verified-correct subset improves performance

    This engine:
    - Evaluates past actions for learning potential
    - Applies meta-judgment to filter high-quality examples
    - Prioritizes learning from verified successes and failures
    """

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure sharpening tables exist."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Sharpening candidates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sharpening_candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER,
                action_type TEXT,
                action_description TEXT,
                expected_result TEXT,
                actual_result TEXT,
                original_score REAL,
                verification_result TEXT,
                verification_confidence REAL,
                meta_judgment_score REAL DEFAULT 0.5,
                should_learn_from INTEGER DEFAULT 0,
                learning_applied INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                evaluated_at TEXT,
                FOREIGN KEY (action_id) REFERENCES action_outcomes(action_id)
            )
        ''')

        # Meta-judgments table for tracking judgment quality
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta_judgments (
                judgment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_id INTEGER,
                judgment_type TEXT,  -- 'verification', 'quality', 'alignment'
                initial_judgment REAL,
                meta_judgment REAL,
                calibration_score REAL,
                reasoning TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (candidate_id) REFERENCES sharpening_candidates(candidate_id)
            )
        ''')

        # Sharpening cycles for tracking improvement
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sharpening_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_type TEXT,  -- 'full', 'incremental', 'targeted'
                candidates_evaluated INTEGER DEFAULT 0,
                verified_high_count INTEGER DEFAULT 0,
                rejected_count INTEGER DEFAULT 0,
                learnings_extracted INTEGER DEFAULT 0,
                avg_meta_judgment REAL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def evaluate_action_for_sharpening(
        self,
        action_id: int
    ) -> Optional[SharpeningCandidate]:
        """
        Evaluate a past action for learning potential using sharpening.

        Applies the verification-generation asymmetry:
        - Verifying if an action was correct is easier than generating correct action
        - High-confidence verifications become learning candidates

        Args:
            action_id: Action to evaluate

        Returns:
            SharpeningCandidate if evaluable, None otherwise
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get action details
        cursor.execute('''
            SELECT * FROM action_outcomes WHERE action_id = ?
        ''', (action_id,))

        action = cursor.fetchone()
        if not action:
            conn.close()
            return None

        # Perform self-verification
        verification_result, confidence = self._self_verify(dict(action))

        # Apply meta-judgment (judge the judgment)
        meta_score = self._meta_judge(
            action_type=action['action_type'],
            original_score=action['success_score'],
            verification_result=verification_result,
            verification_confidence=confidence
        )

        # Determine if we should learn from this
        should_learn = self._should_learn_from(
            verification_result,
            confidence,
            meta_score,
            action['success_score']
        )

        # Store candidate
        cursor.execute('''
            INSERT INTO sharpening_candidates (
                action_id, action_type, action_description,
                expected_result, actual_result, original_score,
                verification_result, verification_confidence,
                meta_judgment_score, should_learn_from, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            action_id,
            action['action_type'],
            action['action_description'],
            action['expected_result'],
            action['actual_result'],
            action['success_score'],
            verification_result.value,
            confidence,
            meta_score,
            1 if should_learn else 0
        ))

        candidate_id = cursor.lastrowid

        # Store meta-judgment
        cursor.execute('''
            INSERT INTO meta_judgments (
                candidate_id, judgment_type, initial_judgment,
                meta_judgment, calibration_score, reasoning
            ) VALUES (?, 'verification', ?, ?, ?, ?)
        ''', (
            candidate_id,
            action['success_score'],
            meta_score,
            abs(action['success_score'] - meta_score),  # Calibration
            f"Verification: {verification_result.value}, Confidence: {confidence:.2f}"
        ))

        conn.commit()
        conn.close()

        candidate = SharpeningCandidate(
            candidate_id=candidate_id,
            action_type=action['action_type'],
            action_description=action['action_description'],
            expected_result=action['expected_result'],
            actual_result=action['actual_result'],
            original_score=action['success_score'],
            verification_result=verification_result,
            verification_confidence=confidence,
            meta_judgment_score=meta_score,
            should_learn_from=should_learn
        )

        logger.info(f"Evaluated action {action_id}: {verification_result.value}, learn={should_learn}")

        return candidate

    def _self_verify(self, action: Dict[str, Any]) -> Tuple[VerificationResult, float]:
        """
        Self-verify an action's correctness.

        Uses heuristics based on:
        - Outcome consistency (expected vs actual)
        - Success score distribution
        - Action type patterns

        Returns:
            (VerificationResult, confidence 0.0-1.0)
        """
        success_score = action.get('success_score', 0.5)
        expected = action.get('expected_result', '')
        actual = action.get('actual_result', '')
        outcome = action.get('outcome_category', '')

        # High success with matching outcome
        if success_score >= 0.9:
            return VerificationResult.VERIFIED_HIGH, 0.95

        # Very low success with error indication
        if success_score <= 0.2 or outcome == 'error':
            return VerificationResult.REJECTED, 0.90

        # Medium-high success
        if success_score >= 0.7:
            return VerificationResult.VERIFIED_MEDIUM, 0.75

        # Check if expected roughly matches actual
        if expected and actual:
            # Simple word overlap heuristic
            expected_words = set(expected.lower().split())
            actual_words = set(actual.lower().split())
            if expected_words and actual_words:
                overlap = len(expected_words & actual_words) / len(expected_words | actual_words)
                if overlap > 0.5:
                    return VerificationResult.VERIFIED_MEDIUM, 0.6 + overlap * 0.2

        # Cannot confidently verify
        return VerificationResult.UNCERTAIN, 0.4

    def _meta_judge(
        self,
        action_type: str,
        original_score: float,
        verification_result: VerificationResult,
        verification_confidence: float
    ) -> float:
        """
        Apply meta-judgment: judge the quality of our judgment.

        Meta-rewarding insight: Models can judge their own judgments
        to create self-consistent improvement signal.

        Returns:
            Meta-judgment score 0.0-1.0
        """
        # Start with verification confidence as base
        base_score = verification_confidence

        # Adjust based on verification result
        if verification_result == VerificationResult.VERIFIED_HIGH:
            base_score = min(1.0, base_score + 0.15)
        elif verification_result == VerificationResult.REJECTED:
            base_score = min(1.0, base_score + 0.10)  # Also valuable for learning
        elif verification_result == VerificationResult.UNCERTAIN:
            base_score = max(0.0, base_score - 0.20)

        # Calibration: penalize extreme mismatch between original and meta
        calibration_penalty = abs(original_score - base_score) * 0.1

        # Apply calibration
        meta_score = base_score - calibration_penalty

        # Ensure bounds
        return max(0.0, min(1.0, meta_score))

    def _should_learn_from(
        self,
        verification_result: VerificationResult,
        confidence: float,
        meta_score: float,
        original_score: float
    ) -> bool:
        """
        Determine if this candidate should be used for learning.

        Key insight: Learn from high-confidence verifications, both
        successes (positive examples) and failures (negative examples).
        """
        # Learn from high-confidence verifications
        if verification_result == VerificationResult.VERIFIED_HIGH and meta_score > 0.7:
            return True

        # Learn from clear failures (valuable negative examples)
        if verification_result == VerificationResult.REJECTED and confidence > 0.8:
            return True

        # Learn from medium verifications with high meta-score
        if verification_result == VerificationResult.VERIFIED_MEDIUM and meta_score > 0.75:
            return True

        # Don't learn from uncertain cases
        return False

    def run_sharpening_cycle(
        self,
        limit: int = 50,
        min_age_hours: int = 1
    ) -> Dict[str, Any]:
        """
        Run a full sharpening cycle on recent actions.

        Evaluates recent actions, applies verification and meta-judgment,
        extracts learning candidates.

        Args:
            limit: Maximum actions to evaluate
            min_age_hours: Minimum age before evaluation

        Returns:
            Cycle results summary
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Start cycle
        cursor.execute('''
            INSERT INTO sharpening_cycles (cycle_type)
            VALUES ('full')
        ''')
        cycle_id = cursor.lastrowid

        # Find actions not yet evaluated
        cursor.execute('''
            SELECT a.action_id FROM action_outcomes a
            LEFT JOIN sharpening_candidates s ON a.action_id = s.action_id
            WHERE s.candidate_id IS NULL
              AND a.executed_at < datetime('now', ?)
            ORDER BY a.executed_at DESC
            LIMIT ?
        ''', (f'-{min_age_hours} hours', limit))

        action_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Evaluate each action
        results = {
            'evaluated': 0,
            'verified_high': 0,
            'verified_medium': 0,
            'rejected': 0,
            'uncertain': 0,
            'learnable': 0
        }

        for action_id in action_ids:
            candidate = self.evaluate_action_for_sharpening(action_id)
            if candidate:
                results['evaluated'] += 1

                if candidate.verification_result == VerificationResult.VERIFIED_HIGH:
                    results['verified_high'] += 1
                elif candidate.verification_result == VerificationResult.VERIFIED_MEDIUM:
                    results['verified_medium'] += 1
                elif candidate.verification_result == VerificationResult.REJECTED:
                    results['rejected'] += 1
                else:
                    results['uncertain'] += 1

                if candidate.should_learn_from:
                    results['learnable'] += 1

        # Update cycle record
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sharpening_cycles
            SET candidates_evaluated = ?,
                verified_high_count = ?,
                rejected_count = ?,
                learnings_extracted = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE cycle_id = ?
        ''', (
            results['evaluated'],
            results['verified_high'],
            results['rejected'],
            results['learnable'],
            cycle_id
        ))
        conn.commit()
        conn.close()

        logger.info(f"Sharpening cycle {cycle_id} complete: {results}")

        return {
            'cycle_id': cycle_id,
            **results
        }

    def get_learning_candidates(
        self,
        limit: int = 20,
        include_applied: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get candidates that should be learned from.

        These are high-confidence verifications that can improve
        future performance.

        Args:
            limit: Maximum candidates to return
            include_applied: Include already-applied learnings

        Returns:
            List of learning candidates
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if include_applied:
            cursor.execute('''
                SELECT * FROM sharpening_candidates
                WHERE should_learn_from = 1
                ORDER BY meta_judgment_score DESC, created_at DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT * FROM sharpening_candidates
                WHERE should_learn_from = 1 AND learning_applied = 0
                ORDER BY meta_judgment_score DESC, created_at DESC
                LIMIT ?
            ''', (limit,))

        candidates = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return candidates

    def mark_learning_applied(self, candidate_id: int):
        """Mark a learning candidate as applied."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE sharpening_candidates
            SET learning_applied = 1
            WHERE candidate_id = ?
        ''', (candidate_id,))
        conn.commit()
        conn.close()

    def get_sharpening_statistics(self) -> Dict[str, Any]:
        """Get statistics about sharpening performance."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Total candidates
        cursor.execute('SELECT COUNT(*) FROM sharpening_candidates')
        total = cursor.fetchone()[0]

        # By verification result
        cursor.execute('''
            SELECT verification_result, COUNT(*) as count
            FROM sharpening_candidates
            GROUP BY verification_result
        ''')
        by_result = {row[0]: row[1] for row in cursor.fetchall()}

        # Learning stats
        cursor.execute('''
            SELECT
                SUM(CASE WHEN should_learn_from = 1 THEN 1 ELSE 0 END) as learnable,
                SUM(CASE WHEN learning_applied = 1 THEN 1 ELSE 0 END) as applied,
                AVG(meta_judgment_score) as avg_meta_score
            FROM sharpening_candidates
        ''')
        learning_stats = cursor.fetchone()

        # Cycle stats
        cursor.execute('''
            SELECT COUNT(*), AVG(candidates_evaluated), AVG(learnings_extracted)
            FROM sharpening_cycles
            WHERE completed_at IS NOT NULL
        ''')
        cycle_stats = cursor.fetchone()

        conn.close()

        return {
            'total_candidates': total,
            'by_verification_result': by_result,
            'learnable_count': learning_stats[0] or 0,
            'applied_count': learning_stats[1] or 0,
            'avg_meta_judgment_score': learning_stats[2] or 0.0,
            'total_cycles': cycle_stats[0] or 0,
            'avg_candidates_per_cycle': cycle_stats[1] or 0,
            'avg_learnings_per_cycle': cycle_stats[2] or 0
        }


# Singleton instance
_engine = None

def get_sharpening_engine() -> SharpeningEngine:
    """Get singleton sharpening engine instance."""
    global _engine
    if _engine is None:
        _engine = SharpeningEngine()
    return _engine
