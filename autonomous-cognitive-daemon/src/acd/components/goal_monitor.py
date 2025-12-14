"""Goal Monitor - Tracks and advances active goals."""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..utils.config import get_path, get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class GoalMonitor:
    """
    Monitors active goals from agent-runtime and detects stalled progress.

    Responsibilities:
    - Poll goals every N minutes
    - Detect stalled goals (no progress in 24h)
    - Create research tasks for blocked goals
    - Update goal progress based on completed work
    """

    def __init__(self, config: dict):
        """Initialize Goal Monitor.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.db_path = get_path("agent_runtime_db", config)

        # Configuration
        self.stall_threshold_hours = get_config_value(
            "thresholds.goal_stall_hours", 24, config
        )

        logger.info(
            "goal_monitor_initialized",
            db_path=str(self.db_path),
            stall_threshold_hours=self.stall_threshold_hours,
        )

    async def check_goals(self) -> Dict[str, Any]:
        """Check all active goals for progress.

        Returns:
            Status report of goal checking
        """
        logger.info("checking_goals")

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get active goals
                cursor = await db.execute(
                    "SELECT * FROM goals WHERE status = 'active'"
                )
                goals = await cursor.fetchall()

                report = {
                    "checked_at": datetime.now().isoformat(),
                    "total_goals": len(goals),
                    "stalled_goals": [],
                    "progressing_goals": [],
                    "actions_taken": [],
                }

                for goal in goals:
                    goal_dict = dict(goal)
                    goal_id = goal_dict["id"]
                    goal_name = goal_dict["name"]

                    # Check for recent task completions
                    stalled = await self._is_goal_stalled(db, goal_id)

                    if stalled:
                        report["stalled_goals"].append({
                            "id": goal_id,
                            "name": goal_name,
                            "stall_hours": stalled,
                        })

                        # Create a research task to investigate
                        action = await self._handle_stalled_goal(db, goal_dict)
                        if action:
                            report["actions_taken"].append(action)
                    else:
                        report["progressing_goals"].append({
                            "id": goal_id,
                            "name": goal_name,
                        })

                logger.info(
                    "goals_checked",
                    total=report["total_goals"],
                    stalled=len(report["stalled_goals"]),
                    progressing=len(report["progressing_goals"]),
                )

                return report

        except Exception as e:
            logger.error("goal_check_failed", error=str(e))
            return {"error": str(e), "checked_at": datetime.now().isoformat()}

    async def _is_goal_stalled(self, db: aiosqlite.Connection, goal_id: int) -> Optional[float]:
        """Check if a goal is stalled.

        Args:
            db: Database connection
            goal_id: Goal ID to check

        Returns:
            Hours stalled, or None if not stalled
        """
        threshold = datetime.now() - timedelta(hours=self.stall_threshold_hours)

        # Check for recent completed tasks
        cursor = await db.execute(
            """
            SELECT MAX(updated_at) as last_activity
            FROM tasks
            WHERE goal_id = ? AND status = 'completed'
            """,
            (goal_id,),
        )
        row = await cursor.fetchone()

        if row and row["last_activity"]:
            last_activity = datetime.fromisoformat(row["last_activity"])
            if last_activity < threshold:
                stall_hours = (datetime.now() - last_activity).total_seconds() / 3600
                return stall_hours
        else:
            # No completed tasks - check goal creation date
            cursor = await db.execute(
                "SELECT created_at FROM goals WHERE id = ?",
                (goal_id,),
            )
            goal_row = await cursor.fetchone()
            if goal_row:
                created = datetime.fromisoformat(goal_row["created_at"])
                if created < threshold:
                    stall_hours = (datetime.now() - created).total_seconds() / 3600
                    return stall_hours

        return None

    async def _handle_stalled_goal(
        self, db: aiosqlite.Connection, goal: dict
    ) -> Optional[Dict[str, Any]]:
        """Handle a stalled goal by creating investigation task.

        Args:
            db: Database connection
            goal: Goal dictionary

        Returns:
            Action taken, or None
        """
        goal_id = goal["id"]
        goal_name = goal["name"]
        goal_desc = goal.get("description", "")

        # Check if we already have an investigation task
        cursor = await db.execute(
            """
            SELECT id FROM tasks
            WHERE goal_id = ? AND title LIKE '%investigate%stall%'
            AND status != 'completed'
            """,
            (goal_id,),
        )
        existing = await cursor.fetchone()

        if existing:
            logger.debug(
                "stalled_goal_already_tracked",
                goal_id=goal_id,
                existing_task=existing["id"],
            )
            return None

        # Create investigation task
        task_title = f"Investigate stalled goal: {goal_name}"
        task_desc = f"""
Goal '{goal_name}' has been stalled for over {self.stall_threshold_hours} hours.

Goal description: {goal_desc}

Investigation steps:
1. Review pending tasks for this goal
2. Identify blockers or dependencies
3. Research solutions for blockers
4. Create actionable next steps

This task was auto-created by the Autonomous Cognitive Daemon.
"""

        await db.execute(
            """
            INSERT INTO tasks (title, description, goal_id, status, priority, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', 8, datetime('now'), datetime('now'))
            """,
            (task_title, task_desc, goal_id),
        )
        await db.commit()

        logger.info(
            "created_investigation_task",
            goal_id=goal_id,
            goal_name=goal_name,
        )

        return {
            "action": "created_investigation_task",
            "goal_id": goal_id,
            "goal_name": goal_name,
            "task_title": task_title,
        }

    async def get_goal_summary(self) -> Dict[str, Any]:
        """Get a summary of all goals.

        Returns:
            Goal summary
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                # Count by status
                cursor = await db.execute(
                    """
                    SELECT status, COUNT(*) as count
                    FROM goals
                    GROUP BY status
                    """
                )
                status_counts = {row["status"]: row["count"] for row in await cursor.fetchall()}

                # Get active goals with task counts
                cursor = await db.execute(
                    """
                    SELECT g.id, g.name, g.status,
                           COUNT(CASE WHEN t.status = 'pending' THEN 1 END) as pending_tasks,
                           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks
                    FROM goals g
                    LEFT JOIN tasks t ON g.id = t.goal_id
                    WHERE g.status = 'active'
                    GROUP BY g.id
                    """
                )
                active_goals = [dict(row) for row in await cursor.fetchall()]

                return {
                    "status_counts": status_counts,
                    "active_goals": active_goals,
                    "generated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error("goal_summary_failed", error=str(e))
            return {"error": str(e)}
