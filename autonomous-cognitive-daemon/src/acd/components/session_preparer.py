"""Session Preparer - Prepares context and briefings for upcoming sessions."""

import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..utils.config import get_path, get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class SessionPreparer:
    """
    Prepares context and briefings for upcoming Claude sessions.

    Responsibilities:
    - Generate session briefings with relevant context
    - Identify high-priority tasks and goals
    - Surface important unfinished work
    - Preload relevant memories
    - Create actionable session agendas
    """

    def __init__(self, config: dict):
        """Initialize Session Preparer.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.memory_db_path = get_path("memory_db", config)
        self.agent_runtime_db_path = get_path("agent_runtime_db", config)

        # Output path for briefings
        self.briefing_dir = Path(
            get_config_value(
                "components.session_preparer.briefing_dir",
                "/mnt/agentic-system/session-briefings",
                config,
            )
        )
        self.briefing_dir.mkdir(parents=True, exist_ok=True)

        # Configuration
        self.max_context_items = get_config_value(
            "components.session_preparer.max_context_items", 10, config
        )
        self.lookback_hours = get_config_value(
            "components.session_preparer.lookback_hours", 48, config
        )

        logger.info(
            "session_preparer_initialized",
            briefing_dir=str(self.briefing_dir),
            max_context_items=self.max_context_items,
        )

    async def prepare_briefing(self) -> Dict[str, Any]:
        """Prepare a session briefing.

        Returns:
            Briefing content and metadata
        """
        logger.info("preparing_session_briefing")

        briefing = {
            "generated_at": datetime.now().isoformat(),
            "sections": {},
        }

        try:
            # Section 1: Active Goals Summary
            goals = await self._get_active_goals()
            briefing["sections"]["active_goals"] = goals

            # Section 2: Pending Tasks
            tasks = await self._get_pending_tasks()
            briefing["sections"]["pending_tasks"] = tasks

            # Section 3: Knowledge Gaps
            gaps = await self._get_open_knowledge_gaps()
            briefing["sections"]["knowledge_gaps"] = gaps

            # Section 4: Recent Learnings
            learnings = await self._get_recent_learnings()
            briefing["sections"]["recent_learnings"] = learnings

            # Section 5: Recent Session Context
            context = await self._get_recent_session_context()
            briefing["sections"]["session_context"] = context

            # Section 6: Stalled Work
            stalled = await self._get_stalled_work()
            briefing["sections"]["stalled_work"] = stalled

            # Generate actionable agenda
            agenda = self._generate_agenda(briefing)
            briefing["agenda"] = agenda

            # Save briefing to file
            briefing_path = await self._save_briefing(briefing)
            briefing["briefing_path"] = str(briefing_path)

            logger.info(
                "session_briefing_prepared",
                sections=len(briefing["sections"]),
                agenda_items=len(agenda),
            )

        except Exception as e:
            logger.error("session_briefing_failed", error=str(e))
            briefing["error"] = str(e)

        return briefing

    async def _get_active_goals(self) -> Dict[str, Any]:
        """Get active goals summary.

        Returns:
            Active goals data
        """
        try:
            async with aiosqlite.connect(self.agent_runtime_db_path) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT g.id, g.name, g.description, g.status, g.created_at,
                           COUNT(CASE WHEN t.status = 'pending' THEN 1 END) as pending_tasks,
                           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks
                    FROM goals g
                    LEFT JOIN tasks t ON g.id = t.goal_id
                    WHERE g.status = 'active'
                    GROUP BY g.id
                    ORDER BY g.created_at DESC
                    """
                )

                goals = [dict(row) for row in await cursor.fetchall()]

                return {
                    "count": len(goals),
                    "goals": goals[:self.max_context_items],
                }

        except Exception as e:
            logger.warning("get_active_goals_failed", error=str(e))
            return {"count": 0, "goals": [], "error": str(e)}

    async def _get_pending_tasks(self) -> Dict[str, Any]:
        """Get high-priority pending tasks.

        Returns:
            Pending tasks data
        """
        try:
            async with aiosqlite.connect(self.agent_runtime_db_path) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT t.id, t.title, t.description, t.priority, t.goal_id,
                           g.name as goal_name
                    FROM tasks t
                    LEFT JOIN goals g ON t.goal_id = g.id
                    WHERE t.status = 'pending'
                    ORDER BY t.priority DESC, t.created_at ASC
                    LIMIT ?
                    """,
                    (self.max_context_items,),
                )

                tasks = [dict(row) for row in await cursor.fetchall()]

                return {
                    "count": len(tasks),
                    "tasks": tasks,
                }

        except Exception as e:
            logger.warning("get_pending_tasks_failed", error=str(e))
            return {"count": 0, "tasks": [], "error": str(e)}

    async def _get_open_knowledge_gaps(self) -> Dict[str, Any]:
        """Get open knowledge gaps.

        Returns:
            Knowledge gaps data
        """
        try:
            async with aiosqlite.connect(self.memory_db_path) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT gap_id, domain, gap_description, gap_type, severity,
                           learning_progress
                    FROM knowledge_gaps
                    WHERE status = 'open'
                    ORDER BY severity DESC
                    LIMIT ?
                    """,
                    (self.max_context_items,),
                )

                gaps = [dict(row) for row in await cursor.fetchall()]

                return {
                    "count": len(gaps),
                    "gaps": gaps,
                }

        except Exception as e:
            logger.warning("get_knowledge_gaps_failed", error=str(e))
            return {"count": 0, "gaps": [], "error": str(e)}

    async def _get_recent_learnings(self) -> Dict[str, Any]:
        """Get recent learnings from episodic memory.

        Returns:
            Recent learnings data
        """
        try:
            async with aiosqlite.connect(self.memory_db_path) as db:
                db.row_factory = aiosqlite.Row

                lookback = datetime.now() - timedelta(hours=self.lookback_hours)

                # Note: episodic_memory uses 'id' not 'episode_id'
                cursor = await db.execute(
                    """
                    SELECT id, event_type, episode_data, significance_score
                    FROM episodic_memory
                    WHERE created_at > ?
                      AND event_type = 'learning'
                    ORDER BY significance_score DESC
                    LIMIT ?
                    """,
                    (lookback.isoformat(), self.max_context_items),
                )

                learnings = []
                for row in await cursor.fetchall():
                    learning = dict(row)
                    # Parse episode_data if it's JSON
                    if learning.get("episode_data"):
                        try:
                            learning["episode_data"] = json.loads(learning["episode_data"])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    learnings.append(learning)

                return {
                    "count": len(learnings),
                    "learnings": learnings,
                }

        except Exception as e:
            logger.warning("get_recent_learnings_failed", error=str(e))
            return {"count": 0, "learnings": [], "error": str(e)}

    async def _get_recent_session_context(self) -> Dict[str, Any]:
        """Get context from recent sessions.

        Returns:
            Session context data
        """
        try:
            async with aiosqlite.connect(self.memory_db_path) as db:
                db.row_factory = aiosqlite.Row

                # Get recent sessions
                # Note: Table is session_continuity, not sessions
                cursor = await db.execute(
                    """
                    SELECT session_id, context_summary, key_learnings, unfinished_work,
                           started_at, ended_at
                    FROM session_continuity
                    WHERE started_at > datetime('now', '-7 days')
                    ORDER BY started_at DESC
                    LIMIT 5
                    """
                )

                sessions = []
                for row in await cursor.fetchall():
                    session = dict(row)
                    # Parse JSON fields
                    for field in ["key_learnings", "unfinished_work"]:
                        if session.get(field):
                            try:
                                session[field] = json.loads(session[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    sessions.append(session)

                return {
                    "recent_sessions": len(sessions),
                    "sessions": sessions,
                }

        except Exception as e:
            logger.warning("get_session_context_failed", error=str(e))
            return {"recent_sessions": 0, "sessions": [], "error": str(e)}

    async def _get_stalled_work(self) -> Dict[str, Any]:
        """Get work that has been stalled.

        Returns:
            Stalled work data
        """
        try:
            async with aiosqlite.connect(self.agent_runtime_db_path) as db:
                db.row_factory = aiosqlite.Row

                stall_threshold = datetime.now() - timedelta(hours=24)

                cursor = await db.execute(
                    """
                    SELECT t.id, t.title, t.status, t.updated_at, g.name as goal_name
                    FROM tasks t
                    LEFT JOIN goals g ON t.goal_id = g.id
                    WHERE t.status = 'in_progress'
                      AND t.updated_at < ?
                    ORDER BY t.updated_at ASC
                    """,
                    (stall_threshold.isoformat(),),
                )

                stalled = [dict(row) for row in await cursor.fetchall()]

                return {
                    "count": len(stalled),
                    "stalled_tasks": stalled,
                }

        except Exception as e:
            logger.warning("get_stalled_work_failed", error=str(e))
            return {"count": 0, "stalled_tasks": [], "error": str(e)}

    def _generate_agenda(self, briefing: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate an actionable agenda from briefing data.

        Args:
            briefing: Full briefing data

        Returns:
            List of agenda items
        """
        agenda = []

        # Priority 1: Stalled work
        stalled = briefing["sections"].get("stalled_work", {})
        for task in stalled.get("stalled_tasks", [])[:3]:
            agenda.append({
                "priority": 1,
                "type": "stalled_task",
                "title": f"Resume stalled: {task['title']}",
                "task_id": task["id"],
            })

        # Priority 2: High-priority pending tasks
        pending = briefing["sections"].get("pending_tasks", {})
        for task in pending.get("tasks", [])[:3]:
            if task.get("priority", 0) >= 7:
                agenda.append({
                    "priority": 2,
                    "type": "high_priority_task",
                    "title": task["title"],
                    "task_id": task["id"],
                })

        # Priority 3: Knowledge gaps with high severity
        gaps = briefing["sections"].get("knowledge_gaps", {})
        for gap in gaps.get("gaps", [])[:2]:
            if gap.get("severity", 0) >= 0.7:
                agenda.append({
                    "priority": 3,
                    "type": "knowledge_gap",
                    "title": f"Research: {gap['domain']} - {gap['gap_description'][:50]}",
                    "gap_id": gap["gap_id"],
                })

        # Priority 4: Active goals needing attention
        goals = briefing["sections"].get("active_goals", {})
        for goal in goals.get("goals", [])[:2]:
            if goal.get("pending_tasks", 0) > 0:
                agenda.append({
                    "priority": 4,
                    "type": "goal_progress",
                    "title": f"Advance goal: {goal['name']}",
                    "goal_id": goal["id"],
                    "pending_tasks": goal["pending_tasks"],
                })

        # Sort by priority
        agenda.sort(key=lambda x: x["priority"])

        return agenda

    async def _save_briefing(self, briefing: Dict[str, Any]) -> Path:
        """Save briefing to file.

        Args:
            briefing: Briefing data

        Returns:
            Path to saved briefing
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"briefing_{timestamp}.json"
        filepath = self.briefing_dir / filename

        # Also save as "latest"
        latest_path = self.briefing_dir / "latest.json"

        # Save briefing files using thread pool for I/O
        def write_json(path, data):
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        await asyncio.to_thread(write_json, filepath, briefing)
        await asyncio.to_thread(write_json, latest_path, briefing)

        # Generate human-readable version
        readable_path = self.briefing_dir / "latest_readable.md"
        await self._save_readable_briefing(briefing, readable_path)

        logger.debug("briefing_saved", path=str(filepath))
        return filepath

    async def _save_readable_briefing(
        self, briefing: Dict[str, Any], path: Path
    ) -> None:
        """Save a human-readable version of the briefing.

        Args:
            briefing: Briefing data
            path: Output path
        """
        lines = [
            "# Session Briefing",
            f"Generated: {briefing['generated_at']}",
            "",
            "## Agenda",
            "",
        ]

        for item in briefing.get("agenda", []):
            lines.append(f"- [{item['priority']}] {item['title']}")

        lines.extend(["", "## Active Goals", ""])
        goals = briefing["sections"].get("active_goals", {})
        for goal in goals.get("goals", []):
            pending = goal.get("pending_tasks", 0)
            completed = goal.get("completed_tasks", 0)
            lines.append(f"- **{goal['name']}** ({completed} done, {pending} pending)")

        lines.extend(["", "## Pending Tasks", ""])
        tasks = briefing["sections"].get("pending_tasks", {})
        for task in tasks.get("tasks", [])[:5]:
            lines.append(f"- [P{task.get('priority', 0)}] {task['title']}")

        lines.extend(["", "## Knowledge Gaps", ""])
        gaps = briefing["sections"].get("knowledge_gaps", {})
        for gap in gaps.get("gaps", [])[:3]:
            lines.append(f"- [{gap.get('severity', 0):.1f}] {gap['domain']}: {gap['gap_description'][:60]}")

        lines.extend(["", "---", "*Generated by Autonomous Cognitive Daemon*"])

        content = "\n".join(lines)

        def write_markdown(filepath, text):
            with open(filepath, "w") as f:
                f.write(text)

        await asyncio.to_thread(write_markdown, path, content)

    async def get_latest_briefing(self) -> Optional[Dict[str, Any]]:
        """Get the latest briefing.

        Returns:
            Latest briefing or None
        """
        latest_path = self.briefing_dir / "latest.json"

        if not latest_path.exists():
            return None

        try:
            with open(latest_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("load_latest_briefing_failed", error=str(e))
            return None
