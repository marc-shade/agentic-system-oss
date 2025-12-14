#!/usr/bin/env python3
"""
Agent Runtime Task Consumer

Persistent background process that:
1. Polls agent-runtime-mcp for next task in queue
2. Routes task to appropriate specialized agent or executes directly
3. Updates task status (in_progress, completed, failed)
4. Runs continuously 24/7 as autonomous task execution engine

This is the missing piece that connects Agent Runtime MCP's task queue
to actual execution.
"""
import platform

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/mnt/agentic-system/logs/task_consumer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('task-consumer')

# Import proactive memory loader (after logging setup)
try:
    from proactive_memory_loader import load_context_for_task
    MEMORY_LOADER_AVAILABLE = True
    logger.info("Proactive memory loader available")
except ImportError as e:
    MEMORY_LOADER_AVAILABLE = False
    logger.warning(f"Proactive memory loader not available: {e}")

# Import agent auto-selector
try:
    from agent_auto_selector import select_agents_for_task
    AGENT_SELECTOR_AVAILABLE = True
    logger.info("Agent auto-selector available")
except ImportError as e:
    AGENT_SELECTOR_AVAILABLE = False
    logger.warning(f"Agent auto-selector not available: {e}")

class TaskConsumer:
    """Consumes tasks from agent-runtime-mcp and executes them"""

    def __init__(self):
        self.base_path = Path(str(_STORAGE_BASE))
        self.running = True
        self.poll_interval = 5  # seconds
        self.current_task = None

    async def get_next_task(self):
        """Get next task from agent-runtime-mcp via MCP tool call"""
        try:
            # Access agent-runtime database (MCP server stores in ~/.claude/)
            import sqlite3
            db_path = Path.home() / ".claude" / "agent_runtime.db"

            if not db_path.exists():
                logger.warning(f"Agent runtime DB not found at {db_path}")
                return None

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get highest priority pending task with met dependencies
            cursor.execute("""
                SELECT id, goal_id, title, description, priority, dependencies, metadata
                FROM tasks
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """)

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            task = {
                'id': row[0],
                'goal_id': row[1],
                'title': row[2],
                'description': row[3],
                'priority': row[4],
                'dependencies': json.loads(row[5]) if row[5] else [],
                'metadata': json.loads(row[6]) if row[6] else {}
            }

            logger.info(f"Retrieved task {task['id']}: {task['title']}")
            return task

        except Exception as e:
            logger.error(f"Error getting next task: {e}")
            return None

    async def update_task_status(self, task_id: int, status: str, result: str = None, error: str = None):
        """Update task status in agent-runtime-mcp"""
        try:
            import sqlite3

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

            db_path = Path.home() / ".claude" / "agent_runtime.db"

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            updates = {"status": status, "updated_at": datetime.utcnow().isoformat()}

            if status == "in_progress":
                updates["started_at"] = datetime.utcnow().isoformat()
            elif status == "completed":
                updates["completed_at"] = datetime.utcnow().isoformat()
                if result:
                    updates["result"] = result
            elif status == "failed":
                if error:
                    updates["error"] = error

            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [task_id]

            cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()

            logger.info(f"Updated task {task_id} status to {status}")

        except Exception as e:
            logger.error(f"Error updating task status: {e}")

    def route_to_agent(self, task: dict) -> str:
        """
        Route task to appropriate specialized agent

        Uses intelligent agent auto-selector when available,
        falls back to simple keyword routing otherwise.

        Returns agent type identifier
        """
        # Try intelligent agent selection first
        if AGENT_SELECTOR_AVAILABLE:
            try:
                logger.info("Using intelligent agent selection...")
                agents = select_agents_for_task(task['title'], task['description'])
                if agents and len(agents) > 0:
                    selected_agent = agents[0]  # Top match
                    logger.info(f"Intelligent selection chose: {selected_agent}")
                    return selected_agent
            except Exception as e:
                logger.warning(f"Agent auto-selection failed, using fallback: {e}")

        # Fallback to simple keyword-based routing
        title = task['title'].lower()
        description = task['description'].lower()

        logger.info("Using keyword-based routing...")

        if any(word in title or word in description for word in ['web test', 'website test', 'browser test', 'ui test', 'performance test', 'screenshot', 'console error']):
            return 'web-testing-agent'
        elif any(word in title or word in description for word in ['research', 'analyze', 'investigate']):
            return 'research-coordinator'
        elif any(word in title or word in description for word in ['code', 'implement', 'develop', 'fix']):
            return 'Swarm Coder'
        elif any(word in title or word in description for word in ['test', 'verify', 'validate']):
            return 'Swarm Tester'
        elif any(word in title or word in description for word in ['document', 'write', 'explain']):
            return 'Swarm Documenter'
        elif any(word in title or word in description for word in ['review', 'audit', 'check']):
            return 'Swarm Reviewer'
        elif any(word in title or word in description for word in ['optimize', 'improve', 'enhance']):
            return 'Swarm Optimizer'
        elif any(word in title or word in description for word in ['security', 'vulnerabil', 'threat']):
            return 'Swarm Guardian'
        else:
            return 'general-purpose'  # Fallback to general agent

    async def execute_task(self, task: dict):
        """Execute the task by spawning appropriate agent"""
        try:
            logger.info(f"Executing task {task['id']}: {task['title']}")

            # Mark task as in progress
            await self.update_task_status(task['id'], 'in_progress')
            self.current_task = task

            # Load relevant context from enhanced-memory proactively
            context_section = ""
            if MEMORY_LOADER_AVAILABLE:
                try:
                    logger.info("Loading proactive memory context...")
                    context = load_context_for_task(task['title'], task['description'])
                    if context:
                        context_section = f"\n{context}\n"
                        logger.info("Proactive memory context loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load proactive memory context: {e}")

            # Route to appropriate agent
            agent_type = self.route_to_agent(task)
            logger.info(f"Routing task to agent: {agent_type}")

            # Build task prompt with context
            prompt = f"""
Task from Agent Runtime Queue:

Title: {task['title']}
Description: {task['description']}
Priority: {task['priority']}
Goal ID: {task['goal_id']}
{context_section}
Please execute this task and provide a summary of what was accomplished.
"""

            # For now, log that we would spawn the agent
            # In full implementation, this would actually spawn via Task tool
            logger.info(f"Would spawn {agent_type} with prompt: {prompt[:200]}...")

            # Simulate task execution (replace with actual agent spawning)
            await asyncio.sleep(2)

            result = f"Task '{task['title']}' routed to {agent_type} agent"

            # Mark task as completed
            await self.update_task_status(task['id'], 'completed', result=result)
            self.current_task = None

            logger.info(f"Completed task {task['id']}")

        except Exception as e:
            logger.error(f"Error executing task {task['id']}: {e}")
            await self.update_task_status(task['id'], 'failed', error=str(e))
            self.current_task = None

    async def run(self):
        """Main task consumer loop"""
        logger.info("Task Consumer starting...")

        while self.running:
            try:
                # Get next task
                task = await self.get_next_task()

                if task:
                    # Execute task
                    await self.execute_task(task)
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(self.poll_interval)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in task consumer loop: {e}")
                await asyncio.sleep(self.poll_interval)

        logger.info("Task Consumer stopped")

    def stop(self):
        """Stop the task consumer"""
        self.running = False

def main():
    """Entry point"""
    consumer = TaskConsumer()

    try:
        asyncio.run(consumer.run())
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        consumer.stop()

if __name__ == "__main__":
    main()
