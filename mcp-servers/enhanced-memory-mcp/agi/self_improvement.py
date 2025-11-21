"""
Self-Improvement Module

Implements self-improvement capabilities for AGI memory.

Key Features:
- Improvement cycle management
- Performance assessment
- Strategy application
- Validation and verification
- Learning from outcomes
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("self_improvement")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class SelfImprovement:
    """Manages self-improvement cycles and optimization"""

    def __init__(self):
        pass

    def start_improvement_cycle(
        self,
        agent_id: str,
        cycle_type: str,
        improvement_goals: Dict[str, Any]
    ) -> int:
        """
        Start a new self-improvement cycle

        Args:
            agent_id: Agent identifier
            cycle_type: Type of improvement (performance, knowledge, reasoning, meta)
            improvement_goals: Specific goals for this cycle

        Returns:
            cycle_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get next cycle number
        cursor.execute(
            'SELECT COALESCE(MAX(cycle_number), 0) + 1 FROM self_improvement_cycles WHERE agent_id = ?',
            (agent_id,)
        )
        cycle_number = cursor.fetchone()[0]

        cursor.execute(
            '''
            INSERT INTO self_improvement_cycles (
                agent_id, cycle_number, cycle_type,
                improvement_goals
            ) VALUES (?, ?, ?, ?)
            ''',
            (
                agent_id, cycle_number, cycle_type,
                json.dumps(improvement_goals)
            )
        )

        cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Started improvement cycle {cycle_number} for {agent_id}: {cycle_type}")

        return cycle_id

    def assess_baseline_performance(
        self,
        cycle_id: int,
        baseline_metrics: Dict[str, float],
        identified_weaknesses: List[str]
    ):
        """
        Assess baseline performance before improvement

        Args:
            cycle_id: Cycle identifier
            baseline_metrics: Performance metrics before improvement
            identified_weaknesses: List of weaknesses to address
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Calculate overall baseline
        baseline_performance = sum(baseline_metrics.values()) / len(baseline_metrics)

        cursor.execute(
            '''
            UPDATE self_improvement_cycles
            SET
                baseline_performance = ?,
                identified_weaknesses = ?
            WHERE cycle_id = ?
            ''',
            (
                baseline_performance,
                json.dumps(identified_weaknesses),
                cycle_id
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Assessed baseline for cycle {cycle_id}: {baseline_performance:.3f}")

    def apply_improvement_strategies(
        self,
        cycle_id: int,
        strategies: List[Dict[str, Any]],
        changes: List[str]
    ):
        """
        Apply improvement strategies

        Args:
            cycle_id: Cycle identifier
            strategies: List of strategies being applied
            changes: Description of changes made
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE self_improvement_cycles
            SET
                strategies_applied = ?,
                changes_made = ?,
                experiments_run = ?
            WHERE cycle_id = ?
            ''',
            (
                json.dumps(strategies),
                json.dumps(changes),
                len(strategies),
                cycle_id
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Applied {len(strategies)} improvement strategies to cycle {cycle_id}")

    def validate_improvements(
        self,
        cycle_id: int,
        new_metrics: Dict[str, float],
        success_criteria: Dict[str, Any]
    ) -> bool:
        """
        Validate that improvements met success criteria

        Args:
            cycle_id: Cycle identifier
            new_metrics: Performance metrics after improvement
            success_criteria: Criteria for success

        Returns:
            True if improvements were successful
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Calculate new performance
        new_performance = sum(new_metrics.values()) / len(new_metrics)

        # Get baseline
        cursor.execute(
            'SELECT baseline_performance FROM self_improvement_cycles WHERE cycle_id = ?',
            (cycle_id,)
        )
        row = cursor.fetchone()
        baseline_performance = row[0] if row else 0.0

        # Calculate improvement
        improvement_delta = new_performance - baseline_performance

        # Check success criteria
        success = improvement_delta > success_criteria.get('min_improvement', 0.0)

        cursor.execute(
            '''
            UPDATE self_improvement_cycles
            SET
                new_performance = ?,
                improvement_delta = ?,
                success_criteria_met = ?
            WHERE cycle_id = ?
            ''',
            (
                new_performance,
                improvement_delta,
                success,
                cycle_id
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Validated cycle {cycle_id}: improvement={improvement_delta:.3f}, success={success}")

        return success

    def complete_cycle(
        self,
        cycle_id: int,
        lessons_learned: List[str],
        next_recommendations: List[str]
    ):
        """
        Complete an improvement cycle and record learnings

        Args:
            cycle_id: Cycle identifier
            lessons_learned: Insights from this cycle
            next_recommendations: Recommendations for next cycle
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get start time
        cursor.execute(
            'SELECT started_at FROM self_improvement_cycles WHERE cycle_id = ?',
            (cycle_id,)
        )
        row = cursor.fetchone()
        started_at = datetime.fromisoformat(row[0]) if row else datetime.now()

        # Calculate duration
        completed_at = datetime.now()
        duration_seconds = int((completed_at - started_at).total_seconds())

        cursor.execute(
            '''
            UPDATE self_improvement_cycles
            SET
                lessons_learned = ?,
                next_cycle_recommendations = ?,
                completed_at = CURRENT_TIMESTAMP,
                duration_seconds = ?
            WHERE cycle_id = ?
            ''',
            (
                json.dumps(lessons_learned),
                json.dumps(next_recommendations),
                duration_seconds,
                cycle_id
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Completed improvement cycle {cycle_id} ({duration_seconds}s)")

    def get_improvement_history(
        self,
        agent_id: str,
        cycle_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get improvement cycle history

        Args:
            agent_id: Agent identifier
            cycle_type: Optional filter by cycle type
            limit: Maximum results

        Returns:
            List of improvement cycles
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if cycle_type:
            cursor.execute(
                '''
                SELECT * FROM improvement_progress
                WHERE agent_id = ? AND cycle_type = ?
                ORDER BY cycle_number DESC
                LIMIT ?
                ''',
                (agent_id, cycle_type, limit)
            )
        else:
            cursor.execute(
                '''
                SELECT * FROM improvement_progress
                WHERE agent_id = ?
                ORDER BY cycle_number DESC
                LIMIT ?
                ''',
                (agent_id, limit)
            )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_best_performing_strategies(
        self,
        agent_id: str,
        min_success_rate: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Get strategies that have worked well in the past

        Args:
            agent_id: Agent identifier
            min_success_rate: Minimum success rate

        Returns:
            List of effective strategies
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Analyze past cycles to find successful strategies
        cursor.execute(
            '''
            SELECT
                strategies_applied,
                COUNT(*) as usage_count,
                AVG(improvement_delta) as avg_improvement,
                AVG(CASE WHEN success_criteria_met THEN 1.0 ELSE 0.0 END) as success_rate
            FROM self_improvement_cycles
            WHERE agent_id = ?
              AND completed_at IS NOT NULL
            GROUP BY strategies_applied
            HAVING success_rate >= ?
            ORDER BY success_rate DESC, avg_improvement DESC
            ''',
            (agent_id, min_success_rate)
        )

        results = []
        for row in cursor.fetchall():
            try:
                strategies = json.loads(row['strategies_applied'])
                results.append({
                    'strategies': strategies,
                    'usage_count': row['usage_count'],
                    'avg_improvement': row['avg_improvement'],
                    'success_rate': row['success_rate']
                })
            except:
                continue

        conn.close()

        return results


class CoordinationManager:
    """Manages multi-agent coordination and communication"""

    def __init__(self):
        pass

    def send_message(
        self,
        sender_agent_id: str,
        recipient_agent_id: Optional[str],
        message_type: str,
        subject: str,
        message_content: Dict[str, Any],
        priority: float = 0.5,
        requires_response: bool = False
    ) -> int:
        """
        Send a coordination message to another agent

        Args:
            sender_agent_id: Sending agent
            recipient_agent_id: Receiving agent (None for broadcast)
            message_type: request, response, notification, coordination
            subject: Message subject
            message_content: Message payload
            priority: 0.0 (low) to 1.0 (urgent)
            requires_response: Whether response is needed

        Returns:
            message_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO coordination_messages (
                sender_agent_id, recipient_agent_id,
                message_type, subject, message_content,
                priority, requires_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                sender_agent_id, recipient_agent_id,
                message_type, subject, json.dumps(message_content),
                priority, requires_response
            )
        )

        message_id = cursor.lastrowid
        conn.commit()
        conn.close()

        recipient = recipient_agent_id or "ALL"
        logger.info(f"Message {message_id} sent from {sender_agent_id} to {recipient}: {subject}")

        return message_id

    def receive_messages(
        self,
        agent_id: str,
        status: str = "pending"
    ) -> List[Dict[str, Any]]:
        """
        Receive messages for an agent

        Args:
            agent_id: Agent identifier
            status: Filter by status (pending, delivered, etc.)

        Returns:
            List of messages
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM coordination_messages
            WHERE (recipient_agent_id = ? OR recipient_agent_id IS NULL)
              AND status = ?
            ORDER BY priority DESC, sent_at ASC
            ''',
            (agent_id, status)
        )

        results = [dict(row) for row in cursor.fetchall()]

        # Mark as delivered
        if results:
            message_ids = [r['message_id'] for r in results]
            cursor.execute(
                f'''
                UPDATE coordination_messages
                SET status = 'delivered'
                WHERE message_id IN ({','.join('?' * len(message_ids))})
                ''',
                message_ids
            )
            conn.commit()

        conn.close()

        return results

    def acknowledge_message(
        self,
        message_id: int,
        response_content: Optional[Dict[str, Any]] = None
    ):
        """
        Acknowledge receipt of a message

        Args:
            message_id: Message to acknowledge
            response_content: Optional response payload
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE coordination_messages
            SET
                status = 'acknowledged',
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE message_id = ?
            ''',
            (message_id,)
        )

        # If response provided, send it
        if response_content:
            cursor.execute(
                'SELECT sender_agent_id, recipient_agent_id, subject FROM coordination_messages WHERE message_id = ?',
                (message_id,)
            )
            row = cursor.fetchone()
            if row:
                original_sender, original_recipient, original_subject = row

                cursor.execute(
                    '''
                    INSERT INTO coordination_messages (
                        sender_agent_id, recipient_agent_id,
                        message_type, subject, message_content,
                        response_message_id, status
                    ) VALUES (?, ?, 'response', ?, ?, ?, 'delivered')
                    ''',
                    (
                        original_recipient,  # Now the sender
                        original_sender,     # Now the recipient
                        f"Re: {original_subject}",
                        json.dumps(response_content),
                        message_id
                    )
                )

        conn.commit()
        conn.close()

        logger.info(f"Acknowledged message {message_id}")

    def get_pending_coordination(
        self,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending coordination tasks

        Args:
            agent_id: Optional filter by agent

        Returns:
            List of pending messages
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if agent_id:
            cursor.execute(
                '''
                SELECT * FROM pending_coordination
                WHERE recipient_agent_id = ? OR recipient_agent_id IS NULL
                ORDER BY priority DESC, sent_at ASC
                ''',
                (agent_id,)
            )
        else:
            cursor.execute('SELECT * FROM pending_coordination')

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results
