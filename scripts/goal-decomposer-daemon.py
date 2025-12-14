#!/usr/bin/env python3
"""
Goal Decomposer Daemon for AGI Task Queue System

Monitors active goals and decomposes them into actionable tasks using LLM.
This is the MISSING PIECE that connects goals to the task queue.

Architecture:
  Goals (agent-runtime-mcp) → [THIS DAEMON] → Tasks (agent-runtime-mcp) → task-processor-daemon

Uses Ollama on cluster nodes for goal decomposition (no local CPU inference).
"""

import asyncio
import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

# Import notification helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from notification_helper import notify, notify_goal_decomposed, notify_daemon_status
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

# Configuration
CONFIG = {
    "db_path": os.path.expanduser("~/.claude/agent_runtime.db"),
    "state_file": "/mnt/agentic-system/databases/goal_decomposer_state.json",
    "log_file": "/mnt/agentic-system/logs/goal-decomposer.log",
    "kill_switch": "/mnt/agentic-system/config/autonomous-mode-enabled",
    # Primary: Claude Code headless (most capable)
    "use_claude_headless": True,
    "claude_model": "haiku",  # Cost-effective for decomposition
    "claude_max_turns": 10,
    # Fallback 1: GPU inference node with powerful models
    "ollama_url": "http://completeu-server.local:11434/api/generate",
    "ollama_model": "qwen3:32b-fp16",
    "use_ollama_fallback": True,
    # Fallback 2: Groq for fast inference
    "groq_url": "https://api.groq.com/openai/v1/chat/completions",
    "groq_model": "llama-3.3-70b-versatile",
    "use_groq_fallback": True,
    "check_interval_seconds": 300,  # 5 minutes
    "max_tasks_per_goal": 10,
    "min_hours_between_decomposition": 24,  # Don't re-decompose recently decomposed goals
}

# Setup logging
def setup_logging() -> logging.Logger:
    logger = logging.getLogger("GoalDecomposer")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path = Path(CONFIG["log_file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()


class GoalDecomposer:
    """Decomposes high-level goals into actionable tasks."""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load decomposition state."""
        state_path = Path(CONFIG["state_file"])
        if state_path.exists():
            try:
                return json.loads(state_path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return {"last_run": None, "goals_decomposed": {}}

    def _save_state(self):
        """Save decomposition state."""
        state_path = Path(CONFIG["state_file"])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.state, indent=2))

    def check_kill_switch(self) -> bool:
        """Check if autonomous mode is enabled."""
        return Path(CONFIG["kill_switch"]).exists()

    def get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite connection."""
        return sqlite3.connect(CONFIG["db_path"])

    def get_active_goals(self) -> List[dict]:
        """Fetch active goals that need decomposition."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, name, description, metadata, created_at
                FROM goals
                WHERE status = 'active'
                ORDER BY created_at ASC
            """)

            goals = []
            for row in cursor.fetchall():
                goal = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4]
                }
                goals.append(goal)

            return goals
        finally:
            conn.close()

    def get_existing_tasks_for_goal(self, goal_id: int) -> List[dict]:
        """Get existing tasks for a goal."""
        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT id, title, status
                FROM tasks
                WHERE goal_id = ?
            """, (goal_id,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({"id": row[0], "title": row[1], "status": row[2]})
            return tasks
        finally:
            conn.close()

    async def decompose_with_claude(self, goal: dict) -> List[dict]:
        """Primary: Use Claude Code headless for goal decomposition."""
        prompt = f"""You are an AGI task decomposition system. Break down this high-level goal into specific, actionable tasks.

GOAL: {goal['name']}
DESCRIPTION: {goal['description']}
METADATA: {json.dumps(goal.get('metadata', {}))}

Generate 3-7 specific tasks that will accomplish this goal. Each task should be:
- Concrete and actionable (can be completed in one session)
- Clear enough for autonomous execution
- Ordered by dependency (earlier tasks first)

Output ONLY a JSON array of task objects with these fields:
- title: Brief task title (max 100 chars)
- description: Detailed description of what to do
- priority: 1-10 (10 highest)
- dependencies: [] or [task_index] for tasks that depend on earlier ones

JSON output only, no explanation:"""

        try:
            cmd = [
                "claude",
                "-p", prompt,
                "--output-format", "json",
                "--model", CONFIG["claude_model"],
                "--max-turns", str(CONFIG["claude_max_turns"]),
                "--allowedTools", "Read,Grep,Glob,WebSearch"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": os.path.expanduser("~")}
            )

            if result.returncode == 0:
                try:
                    output = json.loads(result.stdout)
                    text = output.get("result", "")
                except json.JSONDecodeError:
                    text = result.stdout.strip()

                # Extract JSON from response
                if "```" in text:
                    lines = text.split("\n")
                    json_lines = [l for l in lines if not l.startswith("```")]
                    text = "\n".join(json_lines)

                # Find JSON array in text
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    text = text[start:end]

                tasks = json.loads(text)

                normalized = []
                for i, task in enumerate(tasks[:CONFIG["max_tasks_per_goal"]]):
                    normalized.append({
                        "title": task.get("title", f"Task {i+1}")[:100],
                        "description": task.get("description", ""),
                        "priority": min(10, max(1, task.get("priority", 5))),
                        "dependencies": task.get("dependencies", [])
                    })

                logger.info(f"Claude decomposition successful: {len(normalized)} tasks")
                return normalized
            else:
                logger.error(f"Claude Code failed: {result.stderr}")
                return []

        except subprocess.TimeoutExpired:
            logger.error("Claude Code timed out")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return []
        except FileNotFoundError:
            logger.error("Claude CLI not found in PATH")
            return []
        except Exception as e:
            logger.error(f"Claude decomposition failed: {e}")
            return []

    def should_decompose_goal(self, goal: dict) -> bool:
        """Check if a goal should be decomposed."""
        goal_id = str(goal["id"])

        # Check if already has tasks
        existing_tasks = self.get_existing_tasks_for_goal(goal["id"])
        if existing_tasks:
            # Check if only placeholder tasks exist (like "Investigate stalled goal")
            placeholder_tasks = [t for t in existing_tasks if "investigate stalled" in t["title"].lower()]
            proper_tasks = [t for t in existing_tasks if "investigate stalled" not in t["title"].lower()]

            # If only placeholders exist, allow re-decomposition
            if placeholder_tasks and not proper_tasks:
                logger.info(f"Goal {goal_id} has only placeholder tasks, will decompose properly")
                # Continue to decompose
            elif proper_tasks:
                # Check if there are active proper tasks
                active_tasks = [t for t in proper_tasks if t["status"] not in ("completed", "failed", "cancelled")]
                if active_tasks:
                    logger.debug(f"Goal {goal_id} has {len(active_tasks)} active proper tasks, skipping")
                    return False

        # Check if recently decomposed
        if goal_id in self.state.get("goals_decomposed", {}):
            last_decomposed = datetime.fromisoformat(self.state["goals_decomposed"][goal_id])
            hours_since = (datetime.now() - last_decomposed).total_seconds() / 3600
            if hours_since < CONFIG["min_hours_between_decomposition"]:
                logger.debug(f"Goal {goal_id} decomposed {hours_since:.1f} hours ago, skipping")
                return False

        # Check if goal is marked as non-autonomous
        metadata = goal.get("metadata", {})
        if metadata.get("autonomous") == False:
            logger.debug(f"Goal {goal_id} is non-autonomous, requires user action")
            return False

        return True

    async def decompose_with_ollama(self, goal: dict) -> List[dict]:
        """Use Ollama to decompose goal into tasks."""
        prompt = f"""You are an AGI task decomposition system. Break down this high-level goal into specific, actionable tasks.

GOAL: {goal['name']}
DESCRIPTION: {goal['description']}
METADATA: {json.dumps(goal.get('metadata', {}))}

Generate 3-7 specific tasks that will accomplish this goal. Each task should be:
- Concrete and actionable (can be completed in one session)
- Clear enough for autonomous execution
- Ordered by dependency (earlier tasks first)

Output ONLY a JSON array of task objects with these fields:
- title: Brief task title (max 100 chars)
- description: Detailed description of what to do
- priority: 1-10 (10 highest)
- dependencies: [] or [task_index] for tasks that depend on earlier ones

Example output:
[
  {{"title": "Research existing implementations", "description": "Search codebase for existing patterns and gather information", "priority": 7, "dependencies": []}},
  {{"title": "Design solution architecture", "description": "Based on research, design the implementation approach", "priority": 8, "dependencies": [0]}}
]

JSON output only, no explanation:"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    CONFIG["ollama_url"],
                    json={
                        "model": CONFIG["ollama_model"],
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 2000
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result.get("response", "")

                    # Extract JSON from response
                    text = text.strip()
                    if text.startswith("```"):
                        # Remove markdown code blocks
                        lines = text.split("\n")
                        json_lines = [l for l in lines if not l.startswith("```")]
                        text = "\n".join(json_lines)

                    tasks = json.loads(text)

                    # Validate and normalize
                    normalized = []
                    for i, task in enumerate(tasks[:CONFIG["max_tasks_per_goal"]]):
                        normalized.append({
                            "title": task.get("title", f"Task {i+1}")[:100],
                            "description": task.get("description", ""),
                            "priority": min(10, max(1, task.get("priority", 5))),
                            "dependencies": task.get("dependencies", [])
                        })

                    return normalized
                else:
                    logger.error(f"Ollama error: {response.status_code} - {response.text}")
                    return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            # Try Groq fallback
            if CONFIG["use_groq_fallback"]:
                return await self.decompose_with_groq(goal)
            return []
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            # Try Groq fallback
            if CONFIG["use_groq_fallback"]:
                return await self.decompose_with_groq(goal)
            return []

    async def decompose_with_groq(self, goal: dict) -> List[dict]:
        """Fallback: Use Groq for fast goal decomposition."""
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            logger.warning("GROQ_API_KEY not set, cannot use Groq fallback")
            return []

        prompt = f"""You are an AGI task decomposition system. Break down this high-level goal into specific, actionable tasks.

GOAL: {goal['name']}
DESCRIPTION: {goal['description']}

Generate 3-7 specific tasks. Each task should be concrete and actionable.

Output ONLY a JSON array of task objects:
- title: Brief task title (max 100 chars)
- description: What to do
- priority: 1-10 (10 highest)
- dependencies: [] or [task_index]

JSON output only:"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    CONFIG["groq_url"],
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": CONFIG["groq_model"],
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 2000
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    text = result["choices"][0]["message"]["content"].strip()

                    # Extract JSON
                    if text.startswith("```"):
                        lines = text.split("\n")
                        json_lines = [l for l in lines if not l.startswith("```")]
                        text = "\n".join(json_lines)

                    tasks = json.loads(text)

                    normalized = []
                    for i, task in enumerate(tasks[:CONFIG["max_tasks_per_goal"]]):
                        normalized.append({
                            "title": task.get("title", f"Task {i+1}")[:100],
                            "description": task.get("description", ""),
                            "priority": min(10, max(1, task.get("priority", 5))),
                            "dependencies": task.get("dependencies", [])
                        })

                    logger.info(f"Groq decomposition successful: {len(normalized)} tasks")
                    return normalized
                else:
                    logger.error(f"Groq error: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Groq request failed: {e}")
            return []

    def create_tasks(self, goal_id: int, tasks: List[dict]) -> List[int]:
        """Create tasks in the database."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        created_ids = []

        try:
            for i, task in enumerate(tasks):
                # Map dependency indices to actual task IDs
                deps = []
                for dep_idx in task.get("dependencies", []):
                    if dep_idx < len(created_ids):
                        deps.append(created_ids[dep_idx])

                cursor.execute("""
                    INSERT INTO tasks (goal_id, title, description, status, priority, dependencies, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    goal_id,
                    task["title"],
                    task.get("description", ""),
                    task.get("priority", 5),
                    json.dumps(deps) if deps else None
                ))

                created_ids.append(cursor.lastrowid)

            conn.commit()
            logger.info(f"Created {len(created_ids)} tasks for goal {goal_id}")
            return created_ids

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create tasks: {e}")
            return []
        finally:
            conn.close()

    async def process_goals(self):
        """Main processing loop."""
        logger.info("=" * 60)
        logger.info("Starting goal decomposition run")

        if not self.check_kill_switch():
            logger.info("Autonomous mode disabled, skipping")
            return

        goals = self.get_active_goals()
        logger.info(f"Found {len(goals)} active goals")

        decomposed_count = 0
        tasks_created = 0

        for goal in goals:
            if not self.should_decompose_goal(goal):
                continue

            logger.info(f"Decomposing goal {goal['id']}: {goal['name']}")

            # Try decomposition methods in order: Claude -> Ollama -> Groq
            tasks = []
            if CONFIG["use_claude_headless"]:
                tasks = await self.decompose_with_claude(goal)

            if not tasks and CONFIG["use_ollama_fallback"]:
                logger.info("Claude failed, trying Ollama fallback")
                tasks = await self.decompose_with_ollama(goal)

            if not tasks and CONFIG["use_groq_fallback"]:
                logger.info("Ollama failed, trying Groq fallback")
                tasks = await self.decompose_with_groq(goal)

            if tasks:
                created_ids = self.create_tasks(goal["id"], tasks)
                if created_ids:
                    decomposed_count += 1
                    tasks_created += len(created_ids)

                    # Record decomposition time
                    self.state.setdefault("goals_decomposed", {})[str(goal["id"])] = datetime.now().isoformat()

                    # Send notification
                    if NOTIFICATIONS_AVAILABLE:
                        await notify_goal_decomposed(goal["name"], goal["id"], len(created_ids))

        self.state["last_run"] = datetime.now().isoformat()
        self._save_state()

        logger.info(f"Decomposition complete: {decomposed_count} goals, {tasks_created} tasks created")
        logger.info("=" * 60)

    async def run_daemon(self):
        """Run as continuous daemon."""
        logger.info("Goal Decomposer Daemon starting...")
        logger.info(f"Check interval: {CONFIG['check_interval_seconds']} seconds")
        logger.info(f"Ollama endpoint: {CONFIG['ollama_url']}")

        # Send startup notification
        if NOTIFICATIONS_AVAILABLE:
            await notify_daemon_status("goal-decomposer", "starting", f"interval: {CONFIG['check_interval_seconds']}s")

        while True:
            try:
                await self.process_goals()
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")

            await asyncio.sleep(CONFIG["check_interval_seconds"])


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Goal Decomposer Daemon")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--goal", type=int, help="Decompose specific goal")
    args = parser.parse_args()

    decomposer = GoalDecomposer()

    if args.status:
        print(json.dumps(decomposer.state, indent=2))
        print(f"\nKill switch: {'ENABLED' if decomposer.check_kill_switch() else 'DISABLED'}")
        print(f"Active goals: {len(decomposer.get_active_goals())}")
        return

    if args.goal:
        goals = [g for g in decomposer.get_active_goals() if g["id"] == args.goal]
        if goals:
            tasks = await decomposer.decompose_with_ollama(goals[0])
            print(f"Generated {len(tasks)} tasks:")
            for t in tasks:
                print(f"  - [{t['priority']}] {t['title']}")

            confirm = input("Create these tasks? [y/N] ")
            if confirm.lower() == 'y':
                decomposer.create_tasks(args.goal, tasks)
        else:
            print(f"Goal {args.goal} not found")
        return

    if args.once:
        await decomposer.process_goals()
    else:
        await decomposer.run_daemon()


if __name__ == "__main__":
    asyncio.run(main())
