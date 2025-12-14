#!/usr/bin/env python3
"""
Multi-Agent Coordinator for AGI System
======================================

Orchestrates swarms of specialized agents for complex tasks requiring parallel
execution, task decomposition, and result aggregation.

Key Capabilities:
- Dynamic task decomposition into subtasks
- Intelligent agent assignment based on specialization
- Parallel execution with dependency management
- Result aggregation and conflict resolution
- Load balancing across available agents
- Failure handling and retry logic

Integration:
- Agent Runtime MCP for task persistence
- Enhanced Memory for shared context
- Meta-Learning Engine for agent selection
"""

import asyncio
import json
import logging
import os
import platform
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        macos_primary = Path("/Volumes/SSDRAID0/agentic-system")
        macos_fallback = Path("/Volumes/FILES/agentic-system")
        if macos_primary.exists():
            return macos_primary
        elif macos_fallback.exists():
            return macos_fallback
    elif system == "Linux":
        linux_primary = Path("/home/marc/agentic-system")
        linux_fallback = Path("/mnt/agentic-system")
        if linux_primary.exists():
            return linux_primary
        elif linux_fallback.exists():
            return linux_fallback
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Database path
DB_PATH = _STORAGE_BASE / "databases/coordination.db"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentStatus(Enum):
    """Agent availability status"""
    IDLE = "idle"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"


@dataclass
class SubTask:
    """Decomposed subtask"""
    task_id: str
    parent_task_id: Optional[str]
    description: str
    task_type: str
    priority: int
    dependencies: List[str]
    assigned_agent: Optional[str]
    status: TaskStatus
    result: Optional[Dict]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class AgentCapability:
    """Agent capability definition"""
    agent_name: str
    task_types: List[str]
    max_concurrent_tasks: int
    current_load: int
    status: AgentStatus
    performance_score: float  # 0.0-1.0


class MultiAgentCoordinator:
    """
    Coordinates multiple agents to execute complex tasks in parallel
    with intelligent task decomposition and result aggregation.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize multi-agent coordinator"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Available agents registry
        self.agents: Dict[str, AgentCapability] = {}
        self._register_default_agents()

    def _init_database(self):
        """Initialize coordination database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Subtasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subtasks (
                task_id TEXT PRIMARY KEY,
                parent_task_id TEXT,
                description TEXT NOT NULL,
                task_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                dependencies TEXT NOT NULL,
                assigned_agent TEXT,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
        """)

        # Agent registry table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_registry (
                agent_name TEXT PRIMARY KEY,
                task_types TEXT NOT NULL,
                max_concurrent_tasks INTEGER NOT NULL,
                current_load INTEGER NOT NULL,
                status TEXT NOT NULL,
                performance_score REAL NOT NULL,
                last_heartbeat TEXT NOT NULL
            )
        """)

        # Execution sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_sessions (
                session_id TEXT PRIMARY KEY,
                root_task_id TEXT NOT NULL,
                total_subtasks INTEGER NOT NULL,
                completed_subtasks INTEGER NOT NULL,
                failed_subtasks INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_task ON subtasks(parent_task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON subtasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assigned_agent ON subtasks(assigned_agent)")

        conn.commit()
        conn.close()

    def _register_default_agents(self):
        """Register default agent capabilities"""
        default_agents = [
            AgentCapability(
                agent_name="coder",
                task_types=["code_generation", "code_review", "refactoring"],
                max_concurrent_tasks=3,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.9
            ),
            AgentCapability(
                agent_name="researcher",
                task_types=["research", "analysis", "documentation"],
                max_concurrent_tasks=5,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.85
            ),
            AgentCapability(
                agent_name="tester",
                task_types=["testing", "validation", "quality_assurance"],
                max_concurrent_tasks=4,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.88
            ),
            AgentCapability(
                agent_name="architect",
                task_types=["architecture", "design", "planning"],
                max_concurrent_tasks=2,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.92
            ),
            AgentCapability(
                agent_name="general-purpose",
                task_types=["general"],
                max_concurrent_tasks=10,
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.75
            ),
        ]

        for agent in default_agents:
            self.register_agent(agent)

    def register_agent(self, agent: AgentCapability) -> None:
        """Register an agent with the coordinator"""
        self.agents[agent.agent_name] = agent

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO agent_registry
            (agent_name, task_types, max_concurrent_tasks, current_load,
             status, performance_score, last_heartbeat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.agent_name,
            json.dumps(agent.task_types),
            agent.max_concurrent_tasks,
            agent.current_load,
            agent.status.value,
            agent.performance_score,
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Registered agent: {agent.agent_name} "
                   f"(types={agent.task_types}, capacity={agent.max_concurrent_tasks})")

    async def decompose_task(self, task_description: str,
                            task_type: str = "general") -> List[SubTask]:
        """
        Decompose a complex task into subtasks.

        This is a simplified decomposition - in production, this would use
        an LLM or more sophisticated task analysis.
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        root_task_id = str(uuid.uuid4())

        # Simple decomposition logic (would be enhanced with LLM)
        subtasks = []

        # Example decomposition patterns
        if "implement" in task_description.lower() or "build" in task_description.lower():
            # Implementation pattern: design -> implement -> test
            subtasks = [
                SubTask(
                    task_id=str(uuid.uuid4()),
                    parent_task_id=root_task_id,
                    description=f"Design architecture for: {task_description}",
                    task_type="architecture",
                    priority=1,
                    dependencies=[],
                    assigned_agent=None,
                    status=TaskStatus.PENDING,
                    result=None,
                    error=None,
                    created_at=datetime.now(),
                    started_at=None,
                    completed_at=None
                ),
                SubTask(
                    task_id=str(uuid.uuid4()),
                    parent_task_id=root_task_id,
                    description=f"Implement: {task_description}",
                    task_type="code_generation",
                    priority=2,
                    dependencies=[subtasks[0].task_id] if subtasks else [],
                    assigned_agent=None,
                    status=TaskStatus.PENDING,
                    result=None,
                    error=None,
                    created_at=datetime.now(),
                    started_at=None,
                    completed_at=None
                ),
                SubTask(
                    task_id=str(uuid.uuid4()),
                    parent_task_id=root_task_id,
                    description=f"Test implementation: {task_description}",
                    task_type="testing",
                    priority=3,
                    dependencies=[subtasks[1].task_id] if len(subtasks) > 1 else [],
                    assigned_agent=None,
                    status=TaskStatus.PENDING,
                    result=None,
                    error=None,
                    created_at=datetime.now(),
                    started_at=None,
                    completed_at=None
                ),
            ]
        else:
            # Default: single subtask
            subtasks = [
                SubTask(
                    task_id=str(uuid.uuid4()),
                    parent_task_id=root_task_id,
                    description=task_description,
                    task_type=task_type,
                    priority=1,
                    dependencies=[],
                    assigned_agent=None,
                    status=TaskStatus.PENDING,
                    result=None,
                    error=None,
                    created_at=datetime.now(),
                    started_at=None,
                    completed_at=None
                ),
            ]

        # Save subtasks
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for subtask in subtasks:
            cursor.execute("""
                INSERT INTO subtasks
                (task_id, parent_task_id, description, task_type, priority,
                 dependencies, assigned_agent, status, result, error,
                 created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subtask.task_id,
                subtask.parent_task_id,
                subtask.description,
                subtask.task_type,
                subtask.priority,
                json.dumps(subtask.dependencies),
                subtask.assigned_agent,
                subtask.status.value,
                None,
                None,
                subtask.created_at.isoformat(),
                None,
                None
            ))

        # Create execution session
        cursor.execute("""
            INSERT INTO execution_sessions
            (session_id, root_task_id, total_subtasks, completed_subtasks,
             failed_subtasks, status, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            root_task_id,
            len(subtasks),
            0,
            0,
            "in_progress",
            datetime.now().isoformat(),
            None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Decomposed task into {len(subtasks)} subtasks (session={session_id})")

        return subtasks

    def assign_agent(self, subtask: SubTask) -> Optional[str]:
        """
        Assign best available agent to a subtask.

        Selection criteria:
        1. Agent supports task type
        2. Agent is available (not at capacity)
        3. Agent has best performance score
        """
        candidates = []

        for agent_name, agent in self.agents.items():
            # Check if agent supports this task type
            if subtask.task_type in agent.task_types or "general" in agent.task_types:
                # Check if agent has capacity
                if agent.current_load < agent.max_concurrent_tasks:
                    if agent.status == AgentStatus.IDLE:
                        candidates.append((agent_name, agent.performance_score))

        if not candidates:
            logger.warning(f"No available agents for task type: {subtask.task_type}")
            return None

        # Select best performer
        candidates.sort(key=lambda x: x[1], reverse=True)
        selected_agent = candidates[0][0]

        # Update agent load
        self.agents[selected_agent].current_load = self.agents[selected_agent].current_load + 1
        if self.agents[selected_agent].current_load >= self.agents[selected_agent].max_concurrent_tasks:
            self.agents[selected_agent].status = AgentStatus.BUSY

        logger.info(f"Assigned task {subtask.task_id} to agent: {selected_agent}")

        return selected_agent

    async def execute_subtask(self, subtask: SubTask) -> Dict:
        """
        Execute a subtask (simulation - would call actual agent).
        """
        logger.info(f"Executing subtask {subtask.task_id} with agent {subtask.assigned_agent}")

        # Simulate execution
        await asyncio.sleep(0.5)  # Simulate work

        # In production, this would call the actual agent
        result = {
            "task_id": subtask.task_id,
            "status": "completed",
            "output": f"Completed: {subtask.description}",
            "execution_time_ms": 500
        }

        return result

    async def execute_parallel(self, subtasks: List[SubTask]) -> List[Dict]:
        """Execute subtasks in parallel respecting dependencies"""
        completed = set()
        results = []

        # Group by priority/dependency level
        task_map = {task.task_id: task for task in subtasks}
        pending = set(task.task_id for task in subtasks)

        while pending:
            # Find tasks that can execute (dependencies met)
            ready = []
            for task_id in list(pending):
                task = task_map[task_id]
                deps_met = all(dep in completed for dep in task.dependencies)

                if deps_met:
                    # Assign agent
                    agent = self.assign_agent(task)
                    if agent:
                        task.assigned_agent = agent
                        task.status = TaskStatus.IN_PROGRESS
                        task.started_at = datetime.now()
                        ready.append(task)
                        pending.remove(task_id)

            if not ready:
                # No tasks ready - might be blocked
                logger.warning(f"No tasks ready to execute, {len(pending)} pending")
                await asyncio.sleep(1)
                continue

            # Execute ready tasks in parallel
            tasks_to_execute = [self.execute_subtask(task) for task in ready]
            task_results = await asyncio.gather(*tasks_to_execute, return_exceptions=True)

            # Process results
            for task, result in zip(ready, task_results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    logger.error(f"Task {task.task_id} failed: {result}")
                    # Enrich error result with task metadata
                    enriched_result = {
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "assigned_agent": task.assigned_agent,
                        "success": False,
                        "error": str(result),
                        "execution_time_ms": 0
                    }
                    results.append(enriched_result)
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.completed_at = datetime.now()
                    completed.add(task.task_id)
                    # Enrich result with task metadata for meta-learning
                    enriched_result = {
                        **result,
                        "task_type": task.task_type,
                        "assigned_agent": task.assigned_agent,
                        "success": True
                    }
                    results.append(enriched_result)
                    logger.info(f"Task {task.task_id} completed successfully")

                # Release agent
                if task.assigned_agent and task.assigned_agent in self.agents:
                    agent = self.agents[task.assigned_agent]
                    agent.current_load = max(0, agent.current_load - 1)
                    if agent.current_load < agent.max_concurrent_tasks:
                        agent.status = AgentStatus.IDLE

        return results

    def aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results from multiple subtasks"""
        return {
            "total_tasks": len(results),
            "successful_tasks": sum(1 for r in results if r.get("status") == "completed"),
            "results": results,
            "aggregated_at": datetime.now().isoformat()
        }

    async def execute_task(self, task_description: str,
                          task_type: str = "general") -> Dict:
        """
        Execute a complex task using multi-agent coordination.

        Steps:
        1. Decompose task into subtasks
        2. Assign agents to subtasks
        3. Execute subtasks in parallel (respecting dependencies)
        4. Aggregate results
        """
        logger.info(f"Starting coordinated execution: {task_description}")

        # Decompose
        subtasks = await self.decompose_task(task_description, task_type)

        # Execute in parallel
        results = await self.execute_parallel(subtasks)

        # Aggregate
        final_result = self.aggregate_results(results)

        logger.info(f"Coordination complete: {final_result['successful_tasks']}/{final_result['total_tasks']} tasks successful")

        return final_result

    def get_system_status(self) -> Dict:
        """Get current coordination system status"""
        agent_status = {}
        for name, agent in self.agents.items():
            agent_status[name] = {
                "status": agent.status.value,
                "current_load": agent.current_load,
                "capacity": agent.max_concurrent_tasks,
                "utilization": agent.current_load / agent.max_concurrent_tasks if agent.max_concurrent_tasks > 0 else 0
            }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Active sessions
        cursor.execute("""
            SELECT COUNT(*) FROM execution_sessions
            WHERE status = 'in_progress'
        """)
        active_sessions = cursor.fetchone()[0]

        # Pending subtasks
        cursor.execute("""
            SELECT COUNT(*) FROM subtasks
            WHERE status IN ('pending', 'assigned', 'in_progress')
        """)
        pending_tasks = cursor.fetchone()[0]

        conn.close()

        return {
            "agents": agent_status,
            "active_sessions": active_sessions,
            "pending_tasks": pending_tasks,
            "total_agents": len(self.agents)
        }


async def main():
    """Demo of multi-agent coordination"""
    coordinator = MultiAgentCoordinator()

    # Execute a coordinated task
    result = await coordinator.execute_task(
        "Implement user authentication system with JWT tokens",
        task_type="code_generation"
    )

    print("\nExecution Result:")
    print(json.dumps(result, indent=2))

    # System status
    status = coordinator.get_system_status()
    print("\nSystem Status:")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
