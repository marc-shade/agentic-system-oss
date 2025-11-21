"""
Action Outcome Tracking Module

Implements memory-action closed loop for AGI learning from experience.

Key Features:
- Track action outcomes (success/failure)
- Learn from past actions to improve future decisions
- Extract learnings automatically
- Query past actions for similar contexts
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("action-tracker")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class ActionTracker:
    """Tracks action outcomes for learning"""

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id

    def record_action(
        self,
        action_type: str,
        action_description: str,
        expected_result: str,
        actual_result: str,
        success_score: float,
        session_id: Optional[str] = None,
        entity_id: Optional[int] = None,
        action_context: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record an action and its outcome

        Args:
            action_type: Type of action ("code_change", "command", "research", etc.)
            action_description: What was done
            expected_result: What we expected to happen
            actual_result: What actually happened
            success_score: 0.0 (failure) to 1.0 (success)
            session_id: Session this action belongs to
            entity_id: Associated memory entity
            action_context: Why this action was taken
            duration_ms: How long it took
            metadata: Additional data

        Returns:
            action_id
        """
        # Determine outcome category from success score
        if success_score >= 0.8:
            outcome_category = "success"
        elif success_score >= 0.5:
            outcome_category = "partial"
        elif success_score >= 0.2:
            outcome_category = "failure"
        else:
            outcome_category = "error"

        # Extract learning from outcome
        learning = self._extract_learning(
            action_type,
            action_description,
            expected_result,
            actual_result,
            success_score
        )

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO action_outcomes (
                entity_id, session_id,
                action_type, action_description, action_context,
                expected_result, actual_result,
                success_score, outcome_category,
                learning_extracted, will_retry,
                executed_at, duration_ms, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                entity_id, session_id,
                action_type, action_description, action_context,
                expected_result, actual_result,
                success_score, outcome_category,
                learning, 0 if success_score >= 0.7 else 1,
                datetime.now().isoformat(), duration_ms,
                json.dumps(metadata or {})
            )
        )

        action_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded {outcome_category} action: {action_type} (score: {success_score})")

        return action_id

    def get_similar_actions(
        self,
        action_type: str,
        context: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar past actions for learning

        Returns most recent similar actions with outcomes
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if context:
            # Search with context similarity (simple LIKE for now)
            cursor.execute(
                '''
                SELECT * FROM action_outcomes
                WHERE action_type = ?
                AND (action_description LIKE ? OR action_context LIKE ?)
                ORDER BY executed_at DESC
                LIMIT ?
                ''',
                (action_type, f'%{context}%', f'%{context}%', limit)
            )
        else:
            # Just match action type
            cursor.execute(
                '''
                SELECT * FROM action_outcomes
                WHERE action_type = ?
                ORDER BY executed_at DESC
                LIMIT ?
                ''',
                (action_type, limit)
            )

        rows = cursor.fetchall()
        conn.close()

        actions = []
        for row in rows:
            action = dict(row)

            # Parse metadata
            if action.get('metadata'):
                try:
                    action['metadata'] = json.loads(action['metadata'])
                except:
                    pass

            actions.append(action)

        return actions

    def get_success_rate(
        self,
        action_type: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate success rate for an action type

        Returns:
            {
                "action_type": str,
                "total_actions": int,
                "success_count": int,
                "success_rate": float,
                "avg_score": float,
                "time_window_hours": int
            }
        """
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success_score >= 0.7 THEN 1 ELSE 0 END) as successes,
                AVG(success_score) as avg_score
            FROM action_outcomes
            WHERE action_type = ?
            AND executed_at >= ?
            ''',
            (action_type, cutoff_time.isoformat())
        )

        row = cursor.fetchone()
        conn.close()

        total, successes, avg_score = row

        return {
            "action_type": action_type,
            "total_actions": total or 0,
            "success_count": successes or 0,
            "success_rate": (successes / total) if total > 0 else 0.0,
            "avg_score": avg_score or 0.0,
            "time_window_hours": time_window_hours
        }

    def get_learnings_for_action(
        self,
        action_type: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get key learnings from past actions of this type

        Returns list of learning strings
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT learning_extracted, success_score
            FROM action_outcomes
            WHERE action_type = ?
            AND learning_extracted IS NOT NULL
            AND learning_extracted != ''
            ORDER BY executed_at DESC
            LIMIT ?
            ''',
            (action_type, limit * 2)  # Get more to filter
        )

        rows = cursor.fetchall()
        conn.close()

        # Prioritize learnings from failures (more valuable)
        learnings = []
        for learning, score in rows:
            if score < 0.5:  # Failures first
                learnings.append(learning)

        # Add successes if we need more
        for learning, score in rows:
            if score >= 0.5 and learning not in learnings:
                learnings.append(learning)

        return learnings[:limit]

    def should_retry_action(
        self,
        original_action_id: int,
        proposed_changes: str
    ) -> Dict[str, Any]:
        """
        Decide if an action should be retried with changes

        Returns:
            {
                "should_retry": bool,
                "confidence": float,
                "reasoning": str,
                "suggested_changes": List[str]
            }
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get original action
        cursor.execute(
            'SELECT * FROM action_outcomes WHERE action_id = ?',
            (original_action_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "should_retry": False,
                "confidence": 0.0,
                "reasoning": "Original action not found"
            }

        action = dict(row)

        # Simple heuristic for now:
        # - If score < 0.3 and changes proposed: definitely retry
        # - If score 0.3-0.7 and changes proposed: maybe retry
        # - If score > 0.7: probably don't retry (already good)

        score = action['success_score']

        if score < 0.3:
            return {
                "should_retry": True,
                "confidence": 0.9,
                "reasoning": "Action failed significantly, retry with changes likely to improve",
                "suggested_changes": [proposed_changes]
            }
        elif score < 0.7:
            return {
                "should_retry": True,
                "confidence": 0.6,
                "reasoning": "Partial success, changes might improve outcome",
                "suggested_changes": [proposed_changes]
            }
        else:
            return {
                "should_retry": False,
                "confidence": 0.8,
                "reasoning": "Action already succeeded, retry unnecessary",
                "suggested_changes": []
            }

    def get_action_statistics(self) -> Dict[str, Any]:
        """Get overall action statistics"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total actions
        cursor.execute('SELECT COUNT(*) FROM action_outcomes')
        total = cursor.fetchone()[0]

        # By outcome category
        cursor.execute(
            '''
            SELECT outcome_category, COUNT(*) as count
            FROM action_outcomes
            GROUP BY outcome_category
            '''
        )
        by_category = {row[0]: row[1] for row in cursor.fetchall()}

        # Average success score
        cursor.execute('SELECT AVG(success_score) FROM action_outcomes')
        avg_score = cursor.fetchone()[0] or 0.0

        # Recent trend (last 24h vs previous 24h)
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        previous_cutoff = now - timedelta(hours=48)

        cursor.execute(
            '''
            SELECT AVG(success_score)
            FROM action_outcomes
            WHERE executed_at >= ?
            ''',
            (recent_cutoff.isoformat(),)
        )
        recent_avg = cursor.fetchone()[0] or 0.0

        cursor.execute(
            '''
            SELECT AVG(success_score)
            FROM action_outcomes
            WHERE executed_at >= ? AND executed_at < ?
            ''',
            (previous_cutoff.isoformat(), recent_cutoff.isoformat())
        )
        previous_avg = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "total_actions": total,
            "by_category": by_category,
            "avg_success_score": avg_score,
            "recent_24h_avg": recent_avg,
            "previous_24h_avg": previous_avg,
            "trend": "improving" if recent_avg > previous_avg else "declining" if recent_avg < previous_avg else "stable"
        }

    def _extract_learning(
        self,
        action_type: str,
        description: str,
        expected: str,
        actual: str,
        score: float
    ) -> str:
        """
        Extract learning from action outcome

        Simple rule-based extraction for now
        """
        if score >= 0.8:
            return f"Successful {action_type}: '{description}' worked as expected"
        elif score >= 0.5:
            return f"Partial {action_type}: '{description}' - expected '{expected}' but got '{actual}'"
        else:
            return f"Failed {action_type}: '{description}' - '{actual}' indicates need for different approach"
