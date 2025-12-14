"""
Epistemic Flexibility Scheduler
Automated counterfactual challenge scheduling for maintaining agent flexibility

Implements:
- Periodic flexibility audits
- Automated challenge scheduling for low-score agents
- Progressive difficulty adjustment
- Cross-agent coordination
"""

import sqlite3
import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("epistemic-scheduler")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Scheduling thresholds
CRITICAL_THRESHOLD = 0.2  # Below this = urgent intervention
WARNING_THRESHOLD = 0.4   # Below this = scheduled challenges
HEALTHY_THRESHOLD = 0.6   # Above this = maintenance mode
AUDIT_INTERVAL_HOURS = 24
CHALLENGE_INTERVAL_HOURS = 6


@dataclass
class ScheduledChallenge:
    """A scheduled epistemic challenge for an agent"""
    challenge_id: str
    agent_id: str
    challenge_type: str  # 'prt', 'counterfactual', 'meta_prt'
    priority: str  # 'critical', 'high', 'medium', 'low'
    scheduled_at: str
    due_at: str
    status: str  # 'pending', 'in_progress', 'completed', 'skipped'
    trigger_reason: str
    current_score: float
    parameters: Dict[str, Any] = field(default_factory=dict)


class EpistemicScheduler:
    """
    Manages automated epistemic flexibility challenges.

    Monitors agent flexibility scores and schedules appropriate
    challenges to maintain cognitive health across the system.
    """

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure scheduler tables exist"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS epistemic_schedule (
                challenge_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                challenge_type TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                scheduled_at TEXT NOT NULL,
                due_at TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                trigger_reason TEXT,
                current_score REAL,
                parameters_json TEXT,
                started_at TEXT,
                completed_at TEXT,
                result_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS epistemic_audit_log (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_type TEXT NOT NULL,
                agents_checked INTEGER,
                challenges_scheduled INTEGER,
                findings_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_schedule_agent
            ON epistemic_schedule(agent_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_schedule_status
            ON epistemic_schedule(status, due_at)
        ''')

        conn.commit()
        conn.close()

    def run_audit(self) -> Dict[str, Any]:
        """
        Run system-wide epistemic flexibility audit.

        Checks all agents and schedules challenges as needed.
        """
        try:
            from .counterfactual_testing import run_flexibility_audit
        except ImportError:
            from counterfactual_testing import run_flexibility_audit

        # Run the audit
        audit_results = run_flexibility_audit()

        findings = {
            "critical_agents": [],
            "warning_agents": [],
            "healthy_agents": []
        }

        challenges_scheduled = 0

        for agent_id, result in audit_results.get('per_agent_results', {}).items():
            score = result.get('composite_flexibility_score', 0)

            if score < CRITICAL_THRESHOLD:
                findings["critical_agents"].append({
                    "agent_id": agent_id,
                    "score": score
                })
                # Schedule urgent PRT
                self._schedule_challenge(
                    agent_id=agent_id,
                    challenge_type="prt",
                    priority="critical",
                    current_score=score,
                    trigger_reason=f"Critical flexibility score: {score:.2f}",
                    hours_until_due=1
                )
                challenges_scheduled += 1

            elif score < WARNING_THRESHOLD:
                findings["warning_agents"].append({
                    "agent_id": agent_id,
                    "score": score
                })
                # Schedule standard challenges
                self._schedule_challenge(
                    agent_id=agent_id,
                    challenge_type="counterfactual",
                    priority="high",
                    current_score=score,
                    trigger_reason=f"Low flexibility score: {score:.2f}",
                    hours_until_due=CHALLENGE_INTERVAL_HOURS
                )
                challenges_scheduled += 1

            else:
                findings["healthy_agents"].append({
                    "agent_id": agent_id,
                    "score": score
                })
                # Schedule maintenance check
                if not self._has_recent_challenge(agent_id, hours=48):
                    self._schedule_challenge(
                        agent_id=agent_id,
                        challenge_type="calibration",
                        priority="low",
                        current_score=score,
                        trigger_reason="Maintenance check",
                        hours_until_due=AUDIT_INTERVAL_HOURS
                    )
                    challenges_scheduled += 1

        # Log the audit
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO epistemic_audit_log (
                audit_type, agents_checked, challenges_scheduled, findings_json
            ) VALUES (?, ?, ?, ?)
        ''', (
            "system_audit",
            len(audit_results.get('per_agent_results', {})),
            challenges_scheduled,
            json.dumps(findings)
        ))
        conn.commit()
        conn.close()

        logger.info(
            f"Audit complete: {len(findings['critical_agents'])} critical, "
            f"{len(findings['warning_agents'])} warning, "
            f"{challenges_scheduled} challenges scheduled"
        )

        return {
            "audit_timestamp": datetime.now().isoformat(),
            "agents_checked": len(audit_results.get('per_agent_results', {})),
            "challenges_scheduled": challenges_scheduled,
            "findings": findings,
            "cluster_health": audit_results.get('cluster_health', 'Unknown')
        }

    def _schedule_challenge(
        self,
        agent_id: str,
        challenge_type: str,
        priority: str,
        current_score: float,
        trigger_reason: str,
        hours_until_due: int,
        parameters: Optional[Dict] = None
    ) -> str:
        """Schedule a challenge for an agent"""
        challenge_id = f"challenge_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Check if similar challenge already pending
        if self._has_pending_challenge(agent_id, challenge_type):
            logger.debug(f"Skipping duplicate {challenge_type} for {agent_id}")
            return ""

        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        now = datetime.now()
        due = now + timedelta(hours=hours_until_due)

        cursor.execute('''
            INSERT INTO epistemic_schedule (
                challenge_id, agent_id, challenge_type, priority,
                scheduled_at, due_at, status, trigger_reason,
                current_score, parameters_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            challenge_id, agent_id, challenge_type, priority,
            now.isoformat(), due.isoformat(), 'pending',
            trigger_reason, current_score,
            json.dumps(parameters or {})
        ))

        conn.commit()
        conn.close()

        logger.info(f"Scheduled {priority} {challenge_type} for {agent_id}")
        return challenge_id

    def _has_pending_challenge(self, agent_id: str, challenge_type: str) -> bool:
        """Check if agent has a pending challenge of this type"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM epistemic_schedule
            WHERE agent_id = ? AND challenge_type = ? AND status = 'pending'
        ''', (agent_id, challenge_type))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def _has_recent_challenge(self, agent_id: str, hours: int) -> bool:
        """Check if agent had a challenge recently"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        cursor.execute('''
            SELECT COUNT(*) FROM epistemic_schedule
            WHERE agent_id = ? AND scheduled_at >= ?
        ''', (agent_id, cutoff))

        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def get_pending_challenges(
        self,
        agent_id: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending challenges, optionally filtered"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM epistemic_schedule WHERE status = 'pending'"
        params = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY CASE priority "
        query += "WHEN 'critical' THEN 1 "
        query += "WHEN 'high' THEN 2 "
        query += "WHEN 'medium' THEN 3 "
        query += "WHEN 'low' THEN 4 END, due_at"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_due_challenges(self) -> List[Dict[str, Any]]:
        """Get challenges that are due for execution"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            SELECT * FROM epistemic_schedule
            WHERE status = 'pending' AND due_at <= ?
            ORDER BY CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END
        ''', (now,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def start_challenge(self, challenge_id: str) -> Dict[str, Any]:
        """Mark a challenge as started"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE epistemic_schedule
            SET status = 'in_progress', started_at = ?
            WHERE challenge_id = ?
        ''', (datetime.now().isoformat(), challenge_id))

        conn.commit()
        conn.close()

        return {"challenge_id": challenge_id, "status": "in_progress"}

    def complete_challenge(
        self,
        challenge_id: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mark a challenge as completed with results"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE epistemic_schedule
            SET status = 'completed',
                completed_at = ?,
                result_json = ?
            WHERE challenge_id = ?
        ''', (datetime.now().isoformat(), json.dumps(result), challenge_id))

        conn.commit()
        conn.close()

        logger.info(f"Challenge {challenge_id} completed")
        return {"challenge_id": challenge_id, "status": "completed", "result": result}

    def get_agent_schedule(
        self,
        agent_id: str,
        include_completed: bool = False
    ) -> List[Dict[str, Any]]:
        """Get schedule for a specific agent"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if include_completed:
            cursor.execute('''
                SELECT * FROM epistemic_schedule
                WHERE agent_id = ?
                ORDER BY scheduled_at DESC
                LIMIT 50
            ''', (agent_id,))
        else:
            cursor.execute('''
                SELECT * FROM epistemic_schedule
                WHERE agent_id = ? AND status IN ('pending', 'in_progress')
                ORDER BY due_at
            ''', (agent_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_schedule_summary(self) -> Dict[str, Any]:
        """Get summary of current schedule"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Count by status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM epistemic_schedule
            GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())

        # Count by priority (pending only)
        cursor.execute('''
            SELECT priority, COUNT(*) as count
            FROM epistemic_schedule
            WHERE status = 'pending'
            GROUP BY priority
        ''')
        priority_counts = dict(cursor.fetchall())

        # Get due now
        now = datetime.now().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM epistemic_schedule
            WHERE status = 'pending' AND due_at <= ?
        ''', (now,))
        due_now = cursor.fetchone()[0]

        # Recent completions
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM epistemic_schedule
            WHERE status = 'completed' AND completed_at >= ?
        ''', (yesterday,))
        completed_24h = cursor.fetchone()[0]

        conn.close()

        return {
            "status_counts": status_counts,
            "pending_by_priority": priority_counts,
            "due_now": due_now,
            "completed_24h": completed_24h,
            "timestamp": datetime.now().isoformat()
        }


async def run_scheduler_cycle():
    """
    Run one cycle of the epistemic scheduler.

    This can be called by a daemon or Temporal workflow.
    """
    scheduler = EpistemicScheduler()

    # Check due challenges
    due = scheduler.get_due_challenges()

    results = {
        "cycle_time": datetime.now().isoformat(),
        "due_challenges": len(due),
        "executed": [],
        "errors": []
    }

    for challenge in due:
        try:
            # Start the challenge
            scheduler.start_challenge(challenge['challenge_id'])

            # Execute based on type
            if challenge['challenge_type'] == 'prt':
                try:
                    from .probability_reversal_task import ProbabilityReversalTask
                except ImportError:
                    from probability_reversal_task import ProbabilityReversalTask
                prt = ProbabilityReversalTask(challenge['agent_id'])
                session = prt.create_session(task_type='calibration')
                result = {
                    "type": "prt",
                    "session_id": session.session_id,
                    "status": "session_created"
                }

            elif challenge['challenge_type'] == 'counterfactual':
                try:
                    from .counterfactual_testing import CounterfactualTester
                except ImportError:
                    from counterfactual_testing import CounterfactualTester
                tester = CounterfactualTester(challenge['agent_id'])
                scenarios = tester.get_scenarios(tested_only=False, limit=1)
                result = {
                    "type": "counterfactual",
                    "pending_scenarios": len(scenarios),
                    "status": "ready_for_execution"
                }

            else:
                result = {
                    "type": challenge['challenge_type'],
                    "status": "type_not_implemented"
                }

            scheduler.complete_challenge(challenge['challenge_id'], result)
            results['executed'].append(challenge['challenge_id'])

        except Exception as e:
            logger.error(f"Error executing {challenge['challenge_id']}: {e}")
            results['errors'].append({
                "challenge_id": challenge['challenge_id'],
                "error": str(e)
            })

    return results


def schedule_immediate_challenge(
    agent_id: str,
    challenge_type: str = "prt"
) -> Dict[str, Any]:
    """
    Schedule an immediate challenge for an agent.

    Useful for manual intervention when agent shows low flexibility.
    """
    scheduler = EpistemicScheduler()

    challenge_id = scheduler._schedule_challenge(
        agent_id=agent_id,
        challenge_type=challenge_type,
        priority="high",
        current_score=0.0,  # Will be updated on execution
        trigger_reason="Manual intervention",
        hours_until_due=0  # Immediate
    )

    return {
        "challenge_id": challenge_id,
        "agent_id": agent_id,
        "type": challenge_type,
        "status": "scheduled_immediate"
    }


def get_system_epistemic_health() -> Dict[str, Any]:
    """
    Get overall epistemic health of the system.

    Combines audit results with schedule status.
    """
    scheduler = EpistemicScheduler()
    schedule_summary = scheduler.get_schedule_summary()

    # Run quick audit
    try:
        from .counterfactual_testing import run_flexibility_audit
    except ImportError:
        from counterfactual_testing import run_flexibility_audit
    audit = run_flexibility_audit()

    # Determine overall health
    critical_count = len([
        a for a, r in audit.get('per_agent_results', {}).items()
        if r.get('composite_flexibility_score', 1.0) < CRITICAL_THRESHOLD
    ])

    warning_count = len([
        a for a, r in audit.get('per_agent_results', {}).items()
        if CRITICAL_THRESHOLD <= r.get('composite_flexibility_score', 1.0) < WARNING_THRESHOLD
    ])

    if critical_count > 0:
        health_status = "CRITICAL"
    elif warning_count > 0:
        health_status = "WARNING"
    else:
        health_status = "HEALTHY"

    return {
        "health_status": health_status,
        "cluster_average": audit.get('cluster_average_flexibility', 0),
        "agents_critical": critical_count,
        "agents_warning": warning_count,
        "agents_healthy": len(audit.get('per_agent_results', {})) - critical_count - warning_count,
        "schedule": schedule_summary,
        "timestamp": datetime.now().isoformat()
    }
