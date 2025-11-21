#!/usr/bin/env python3
"""
Meta-Learning Engine for AGI System
====================================

Learns from task outcomes to continuously improve agent selection, task routing,
and system performance. Implements meta-cognitive feedback loops for autonomous
improvement.

Key Capabilities:
- Task outcome tracking and analysis
- Agent performance evaluation
- Dynamic agent selection optimization
- Pattern recognition in task success/failure
- Continuous learning from experience

Integration:
- Enhanced Memory MCP for persistent learning storage
- Agent Runtime MCP for task history
- SAFLA for pattern detection
"""

import asyncio
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path("/Volumes/SSDRAID0/agentic-system/databases/meta_learning.db")


@dataclass
class TaskOutcome:
    """Task execution outcome for learning"""
    task_id: str
    task_type: str
    agent_used: str
    success: bool
    execution_time_ms: int
    error_message: Optional[str]
    quality_score: float  # 0.0-1.0
    timestamp: datetime
    context: Dict  # Task context and metadata


@dataclass
class AgentPerformance:
    """Agent performance metrics"""
    agent_name: str
    task_type: str
    success_rate: float
    avg_execution_time_ms: float
    avg_quality_score: float
    total_tasks: int
    last_updated: datetime


class MetaLearningEngine:
    """
    Meta-learning system that learns from task execution patterns
    to optimize agent selection and system performance.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize meta-learning engine"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for meta-learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Task outcomes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                agent_used TEXT NOT NULL,
                success INTEGER NOT NULL,
                execution_time_ms INTEGER NOT NULL,
                error_message TEXT,
                quality_score REAL NOT NULL,
                timestamp TEXT NOT NULL,
                context TEXT NOT NULL
            )
        """)

        # Agent performance cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success_rate REAL NOT NULL,
                avg_execution_time_ms REAL NOT NULL,
                avg_quality_score REAL NOT NULL,
                total_tasks INTEGER NOT NULL,
                last_updated TEXT NOT NULL,
                UNIQUE(agent_name, task_type)
            )
        """)

        # Pattern recognition table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence REAL NOT NULL,
                discovered_at TEXT NOT NULL,
                last_validated TEXT NOT NULL
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_type ON task_outcomes(task_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_used ON task_outcomes(agent_used)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON task_outcomes(timestamp)")

        conn.commit()
        conn.close()

    def record_outcome(self, outcome: TaskOutcome) -> None:
        """Record a task outcome for learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_outcomes
            (task_id, task_type, agent_used, success, execution_time_ms,
             error_message, quality_score, timestamp, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            outcome.task_id,
            outcome.task_type,
            outcome.agent_used,
            1 if outcome.success else 0,
            outcome.execution_time_ms,
            outcome.error_message,
            outcome.quality_score,
            outcome.timestamp.isoformat(),
            json.dumps(outcome.context)
        ))

        conn.commit()
        conn.close()

        # Update performance metrics
        self._update_agent_performance(outcome)

        logger.info(f"Recorded outcome for task {outcome.task_id} "
                   f"(agent={outcome.agent_used}, success={outcome.success})")

    def _update_agent_performance(self, outcome: TaskOutcome) -> None:
        """Update cached agent performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent outcomes for this agent and task type
        cursor.execute("""
            SELECT success, execution_time_ms, quality_score
            FROM task_outcomes
            WHERE agent_used = ? AND task_type = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (outcome.agent_used, outcome.task_type))

        outcomes = cursor.fetchall()

        if outcomes:
            successes = sum(1 for o in outcomes if o[0] == 1)
            success_rate = successes / len(outcomes)
            avg_execution_time = statistics.mean(o[1] for o in outcomes)
            avg_quality = statistics.mean(o[2] for o in outcomes)

            # Upsert performance metrics
            cursor.execute("""
                INSERT INTO agent_performance
                (agent_name, task_type, success_rate, avg_execution_time_ms,
                 avg_quality_score, total_tasks, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_name, task_type) DO UPDATE SET
                    success_rate = excluded.success_rate,
                    avg_execution_time_ms = excluded.avg_execution_time_ms,
                    avg_quality_score = excluded.avg_quality_score,
                    total_tasks = excluded.total_tasks,
                    last_updated = excluded.last_updated
            """, (
                outcome.agent_used,
                outcome.task_type,
                success_rate,
                avg_execution_time,
                avg_quality,
                len(outcomes),
                datetime.now().isoformat()
            ))

            conn.commit()

        conn.close()

    def recommend_agent(self, task_type: str, context: Optional[Dict] = None,
                       use_pysr: bool = True) -> Tuple[str, float]:
        """
        Recommend best agent for a task type based on learned performance.

        Args:
            task_type: Type of task
            context: Optional context dictionary
            use_pysr: Use PySR-discovered equation for scoring (default: True)

        Returns:
            Tuple of (agent_name, confidence)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get agent performance for this task type
        cursor.execute("""
            SELECT agent_name, success_rate, avg_quality_score, total_tasks, avg_execution_time_ms
            FROM agent_performance
            WHERE task_type = ?
        """, (task_type,))

        results = cursor.fetchall()
        conn.close()

        if not results:
            # No learning data yet - return default
            return ("general-purpose", 0.0)

        # Score each agent
        scored_agents = []
        for agent_name, success_rate, quality_score, total_tasks, exec_time_ms in results:
            if use_pysr:
                try:
                    # Use PySR-discovered equation
                    from equation_integration import get_integrator
                    import numpy as np

                    integrator = get_integrator()
                    log_exec_time = np.log1p(exec_time_ms or 1000)  # Default 1000ms if None

                    performance_score = integrator.meta_learning_agent_score(
                        success_rate=success_rate,
                        avg_quality_score=quality_score,
                        log_exec_time=log_exec_time,
                        total_tasks=total_tasks,
                        task_type_encoded=0  # Could be enhanced with actual encoding
                    )

                    logger.info(f"PySR agent score for '{agent_name}': {performance_score:.4f}")

                except Exception as e:
                    logger.warning(f"PySR equation failed, using fallback: {e}")
                    # Fallback to original 50/50 heuristic
                    performance_score = (success_rate * 0.5 + quality_score * 0.5)
            else:
                # Original heuristic (fallback)
                performance_score = (success_rate * 0.5 + quality_score * 0.5)

            scored_agents.append((agent_name, performance_score, success_rate, quality_score, total_tasks))

        # Sort by performance score
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Top performer
        agent_name, performance_score, success_rate, quality_score, total_tasks = scored_agents[0]

        # Calculate confidence based on amount of data
        confidence = min(1.0, total_tasks / 20.0)  # Full confidence after 20 tasks

        # Adjust confidence by performance
        confidence *= performance_score

        logger.info(f"Recommended agent '{agent_name}' for task type '{task_type}' "
                   f"(confidence={confidence:.2f}, score={performance_score:.4f})")

        return (agent_name, confidence)

    def get_agent_performance(self, agent_name: Optional[str] = None,
                            task_type: Optional[str] = None) -> List[AgentPerformance]:
        """Get performance metrics for agents"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM agent_performance WHERE 1=1"
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY success_rate DESC, avg_quality_score DESC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        performances = []
        for row in results:
            performances.append(AgentPerformance(
                agent_name=row[1],
                task_type=row[2],
                success_rate=row[3],
                avg_execution_time_ms=row[4],
                avg_quality_score=row[5],
                total_tasks=row[6],
                last_updated=datetime.fromisoformat(row[7])
            ))

        return performances

    def detect_patterns(self, lookback_days: int = 7) -> List[Dict]:
        """
        Detect patterns in task execution for meta-learning.

        Patterns detected:
        - Time-based performance variations
        - Context-based success factors
        - Error clustering
        - Performance trends
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(days=lookback_days)).isoformat()

        # Get recent outcomes
        cursor.execute("""
            SELECT task_type, agent_used, success, execution_time_ms,
                   quality_score, timestamp, context
            FROM task_outcomes
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff,))

        outcomes = cursor.fetchall()
        conn.close()

        patterns = []

        # Pattern 1: Time-based performance
        time_performance = defaultdict(lambda: {"success": 0, "total": 0})
        for outcome in outcomes:
            timestamp = datetime.fromisoformat(outcome[5])
            hour = timestamp.hour
            success = outcome[2]

            time_performance[hour]["total"] = time_performance[hour]["total"] + 1
            if success:
                time_performance[hour]["success"] = time_performance[hour]["success"] + 1

        # Find best and worst hours
        hour_success_rates = {}
        for hour, data in time_performance.items():
            if data["total"] >= 5:  # Minimum sample size
                hour_success_rates[hour] = data["success"] / data["total"]

        if hour_success_rates:
            best_hour = max(hour_success_rates.items(), key=lambda x: x[1])
            worst_hour = min(hour_success_rates.items(), key=lambda x: x[1])

            if best_hour[1] - worst_hour[1] > 0.2:  # Significant difference
                patterns.append({
                    "type": "time_based_performance",
                    "best_hour": best_hour[0],
                    "best_success_rate": best_hour[1],
                    "worst_hour": worst_hour[0],
                    "worst_success_rate": worst_hour[1],
                    "confidence": min(1.0, len(hour_success_rates) / 10.0)
                })

        # Pattern 2: Agent specialization
        agent_specialization = defaultdict(lambda: defaultdict(int))
        for outcome in outcomes:
            task_type = outcome[0]
            agent = outcome[1]
            success = outcome[2]

            agent_specialization[agent][task_type] = agent_specialization[agent][task_type] + 1

        for agent, tasks in agent_specialization.items():
            if len(tasks) >= 3:  # Agent handles multiple task types
                total = sum(tasks.values())
                dominant_task = max(tasks.items(), key=lambda x: x[1])
                dominance = dominant_task[1] / total

                if dominance > 0.6:  # Agent is specialized
                    patterns.append({
                        "type": "agent_specialization",
                        "agent": agent,
                        "dominant_task_type": dominant_task[0],
                        "dominance": dominance,
                        "confidence": min(1.0, total / 20.0)
                    })

        logger.info(f"Detected {len(patterns)} patterns in recent task execution")

        return patterns

    def get_learning_summary(self) -> Dict:
        """Get summary of meta-learning status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total outcomes
        cursor.execute("SELECT COUNT(*) FROM task_outcomes")
        total_outcomes = cursor.fetchone()[0]

        # Success rate
        cursor.execute("SELECT AVG(success) FROM task_outcomes")
        overall_success_rate = cursor.fetchone()[0] or 0.0

        # Unique agents
        cursor.execute("SELECT COUNT(DISTINCT agent_used) FROM task_outcomes")
        unique_agents = cursor.fetchone()[0]

        # Unique task types
        cursor.execute("SELECT COUNT(DISTINCT task_type) FROM task_outcomes")
        unique_task_types = cursor.fetchone()[0]

        # Recent performance (last 24 hours)
        cutoff = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute("""
            SELECT AVG(success), AVG(quality_score)
            FROM task_outcomes
            WHERE timestamp > ?
        """, (cutoff,))
        recent = cursor.fetchone()
        recent_success_rate = recent[0] or 0.0
        recent_quality = recent[1] or 0.0

        conn.close()

        return {
            "total_outcomes": total_outcomes,
            "overall_success_rate": overall_success_rate,
            "recent_success_rate": recent_success_rate,
            "recent_quality_score": recent_quality,
            "unique_agents": unique_agents,
            "unique_task_types": unique_task_types,
            "learning_maturity": min(1.0, total_outcomes / 100.0)
        }


async def main():
    """Demo of meta-learning engine"""
    engine = MetaLearningEngine()

    # Example: Record some outcomes
    outcomes = [
        TaskOutcome(
            task_id="task_001",
            task_type="code_generation",
            agent_used="coder",
            success=True,
            execution_time_ms=1500,
            error_message=None,
            quality_score=0.9,
            timestamp=datetime.now(),
            context={"language": "python", "complexity": "medium"}
        ),
        TaskOutcome(
            task_id="task_002",
            task_type="code_generation",
            agent_used="general-purpose",
            success=True,
            execution_time_ms=2500,
            error_message=None,
            quality_score=0.7,
            timestamp=datetime.now(),
            context={"language": "python", "complexity": "medium"}
        ),
    ]

    for outcome in outcomes:
        engine.record_outcome(outcome)

    # Get recommendation
    agent, confidence = engine.recommend_agent("code_generation")
    print(f"\nRecommended agent: {agent} (confidence: {confidence:.2f})")

    # Get performance metrics
    performances = engine.get_agent_performance()
    print(f"\nAgent Performance Metrics:")
    for perf in performances:
        print(f"  {perf.agent_name} - {perf.task_type}: "
              f"success_rate={perf.success_rate:.2f}, "
              f"quality={perf.avg_quality_score:.2f}")

    # Detect patterns
    patterns = engine.detect_patterns()
    print(f"\nDetected Patterns: {len(patterns)}")
    for pattern in patterns:
        print(f"  {pattern['type']}: {json.dumps(pattern, indent=2)}")

    # Learning summary
    summary = engine.get_learning_summary()
    print(f"\nLearning Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
