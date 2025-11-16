"""
Meta-Cognitive Awareness Module

Implements meta-cognitive capabilities for AGI memory.

Key Features:
- Self-awareness and monitoring
- Knowledge gap detection
- Reasoning strategy management
- Performance tracking
- Confidence calibration
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("metacognition")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class MetaCognition:
    """Manages meta-cognitive awareness and self-monitoring"""

    def __init__(self):
        pass

    def record_metacognitive_state(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        self_awareness: float = 0.5,
        knowledge_awareness: float = 0.5,
        process_awareness: float = 0.5,
        limitation_awareness: float = 0.5,
        cognitive_load: float = 0.5,
        confidence_level: float = 0.5,
        task_context: Optional[Dict[str, Any]] = None,
        reasoning_trace: Optional[List[str]] = None
    ) -> int:
        """
        Record current meta-cognitive state

        Args:
            agent_id: Agent identifier
            session_id: Current session
            self_awareness: Awareness of own existence (0.0-1.0)
            knowledge_awareness: Awareness of what it knows (0.0-1.0)
            process_awareness: Awareness of how it thinks (0.0-1.0)
            limitation_awareness: Awareness of limitations (0.0-1.0)
            cognitive_load: Mental effort level (0.0-1.0)
            confidence_level: Confidence in reasoning (0.0-1.0)
            task_context: What task is being performed
            reasoning_trace: Trace of reasoning steps

        Returns:
            state_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Calculate uncertainty from confidence
        uncertainty_level = 1.0 - confidence_level

        cursor.execute(
            '''
            INSERT INTO metacognitive_states (
                agent_id, session_id,
                self_awareness, knowledge_awareness,
                process_awareness, limitation_awareness,
                cognitive_load, confidence_level,
                uncertainty_level,
                task_context, reasoning_trace
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                agent_id, session_id,
                self_awareness, knowledge_awareness,
                process_awareness, limitation_awareness,
                cognitive_load, confidence_level,
                uncertainty_level,
                json.dumps(task_context or {}),
                json.dumps(reasoning_trace or [])
            )
        )

        state_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded meta-cognitive state for {agent_id}: "
                   f"confidence={confidence_level:.2f}, load={cognitive_load:.2f}")

        return state_id

    def get_current_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get current meta-cognitive state for agent"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM current_metacognitive_state
            WHERE agent_id = ?
            ''',
            (agent_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def identify_knowledge_gap(
        self,
        agent_id: str,
        domain: str,
        gap_description: str,
        gap_type: str = "factual",
        severity: float = 0.5,
        discovered_by: str = "self-reflection",
        discovery_context: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Identify and record a knowledge gap

        Args:
            agent_id: Agent identifier
            domain: What domain/topic
            gap_description: Description of the gap
            gap_type: factual, procedural, conceptual, meta
            severity: How critical (0.0-1.0)
            discovered_by: How was it discovered
            discovery_context: Circumstances of discovery

        Returns:
            gap_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO knowledge_gaps (
                agent_id, domain, gap_description,
                gap_type, severity,
                discovered_by, discovery_context,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                agent_id, domain, gap_description,
                gap_type, severity,
                discovered_by, json.dumps(discovery_context or {}),
                'open'
            )
        )

        gap_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Identified knowledge gap in {domain}: {gap_description} "
                   f"(severity: {severity:.2f})")

        return gap_id

    def get_knowledge_gaps(
        self,
        agent_id: str,
        status: Optional[str] = None,
        min_severity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Get knowledge gaps for agent"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = ["agent_id = ?", "severity >= ?"]
        params = [agent_id, min_severity]

        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions)

        cursor.execute(
            f'''
            SELECT * FROM knowledge_gaps
            WHERE {where_clause}
            ORDER BY severity DESC, discovered_at DESC
            ''',
            params
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def update_gap_progress(
        self,
        gap_id: int,
        learning_progress: float,
        learning_plan: Optional[Dict[str, Any]] = None
    ):
        """Update knowledge gap learning progress"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        update_fields = ["learning_progress = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [learning_progress]

        if learning_plan:
            update_fields.append("learning_plan = ?")
            params.append(json.dumps(learning_plan))

        if learning_progress >= 1.0:
            update_fields.append("status = 'resolved'")
            update_fields.append("resolved_at = CURRENT_TIMESTAMP")

        params.append(gap_id)

        cursor.execute(
            f'''
            UPDATE knowledge_gaps
            SET {", ".join(update_fields)}
            WHERE gap_id = ?
            ''',
            params
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated gap {gap_id} progress: {learning_progress:.2f}")

    def track_reasoning_strategy(
        self,
        agent_id: str,
        strategy_name: str,
        strategy_type: str,
        success: bool,
        confidence: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """Track usage and effectiveness of reasoning strategy"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if strategy exists
        cursor.execute(
            'SELECT strategy_id, times_used, success_count, failure_count, average_confidence FROM reasoning_strategies WHERE agent_id = ? AND strategy_name = ?',
            (agent_id, strategy_name)
        )

        row = cursor.fetchone()

        if row:
            # Update existing
            strategy_id, times_used, success_count, failure_count, avg_conf = row

            new_success = success_count + (1 if success else 0)
            new_failure = failure_count + (0 if success else 1)
            new_times = times_used + 1
            new_avg_conf = ((avg_conf * times_used) + confidence) / new_times

            cursor.execute(
                '''
                UPDATE reasoning_strategies
                SET
                    times_used = ?,
                    success_count = ?,
                    failure_count = ?,
                    average_confidence = ?,
                    last_used = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE strategy_id = ?
                ''',
                (new_times, new_success, new_failure, new_avg_conf, strategy_id)
            )

            if success:
                cursor.execute(
                    'UPDATE reasoning_strategies SET last_success = CURRENT_TIMESTAMP WHERE strategy_id = ?',
                    (strategy_id,)
                )
        else:
            # Create new strategy
            cursor.execute(
                '''
                INSERT INTO reasoning_strategies (
                    agent_id, strategy_name, strategy_type,
                    times_used, success_count, failure_count,
                    average_confidence, last_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    agent_id, strategy_name, strategy_type,
                    1, (1 if success else 0), (0 if success else 1),
                    confidence
                )
            )

        conn.commit()
        conn.close()

        logger.info(f"Tracked reasoning strategy '{strategy_name}': "
                   f"success={success}, confidence={confidence:.2f}")

    def get_effective_strategies(
        self,
        agent_id: str,
        min_success_rate: float = 0.6,
        min_usage: int = 3
    ) -> List[Dict[str, Any]]:
        """Get most effective reasoning strategies"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM effective_strategies
            WHERE times_used >= ?
              AND success_rate >= ?
            ''',
            (min_usage, min_success_rate)
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results


class PerformanceTracker:
    """Track performance metrics for self-improvement"""

    def __init__(self):
        pass

    def update_metric(
        self,
        agent_id: str,
        metric_name: str,
        metric_category: str,
        current_value: float,
        target_value: Optional[float] = None
    ):
        """Update a performance metric"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if metric exists
        cursor.execute(
            'SELECT metric_id, baseline_value, historical_values FROM performance_metrics WHERE agent_id = ? AND metric_name = ?',
            (agent_id, metric_name)
        )

        row = cursor.fetchone()

        if row:
            metric_id, baseline_value, historical_json = row

            # Parse historical values
            try:
                historical = json.loads(historical_json) if historical_json else []
            except:
                historical = []

            # Add current value to history
            historical.append({
                "timestamp": datetime.now().isoformat(),
                "value": current_value
            })

            # Keep last 100 values
            if len(historical) > 100:
                historical = historical[-100:]

            cursor.execute(
                '''
                UPDATE performance_metrics
                SET
                    current_value = ?,
                    target_value = COALESCE(?, target_value),
                    historical_values = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE metric_id = ?
                ''',
                (current_value, target_value, json.dumps(historical), metric_id)
            )
        else:
            # Create new metric
            historical = [{
                "timestamp": datetime.now().isoformat(),
                "value": current_value
            }]

            cursor.execute(
                '''
                INSERT INTO performance_metrics (
                    agent_id, metric_name, metric_category,
                    current_value, baseline_value, target_value,
                    historical_values
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    agent_id, metric_name, metric_category,
                    current_value, current_value, target_value,
                    json.dumps(historical)
                )
            )

        conn.commit()
        conn.close()

        logger.info(f"Updated metric '{metric_name}': {current_value:.3f}")

    def get_performance_trends(
        self,
        agent_id: str,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get performance trends"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if category:
            cursor.execute(
                '''
                SELECT * FROM performance_trends
                WHERE agent_id = ? AND metric_category = ?
                ''',
                (agent_id, category)
            )
        else:
            cursor.execute(
                'SELECT * FROM performance_trends WHERE agent_id = ?',
                (agent_id,)
            )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results
