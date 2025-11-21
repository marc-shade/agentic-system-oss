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
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import uuid

<<<<<<< HEAD
# Import physics-informed learning for constrained agent selection
try:
    from physics_informed_learning import PhysicsInformedLearning
    PHYSICS_AVAILABLE = True
except ImportError:
    PHYSICS_AVAILABLE = False
    logging.warning("Physics-informed learning not available")

# Import cluster distribution for task offloading
import sys
cluster_path = Path(__file__).parent.parent / "cluster-deployment"
if str(cluster_path) not in sys.path:
    sys.path.insert(0, str(cluster_path))

try:
    from distributed_task_router import DistributedTaskRouter, CLUSTER_NODES
    CLUSTER_AVAILABLE = True
except ImportError:
    CLUSTER_AVAILABLE = False
    logging.warning("Cluster distribution not available")

=======
>>>>>>> origin/main
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
<<<<<<< HEAD
DB_PATH = Path("/Volumes/SSDRAID0/agentic-system/databases/coordination.db")
=======
DB_PATH = Path("/mnt/agentic-system/databases/coordination.db")
>>>>>>> origin/main


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

<<<<<<< HEAD
    def __init__(self, db_path: Path = DB_PATH, enable_physics_constraints: bool = True,
                 enable_cluster_offload: bool = True):
        """
        Initialize multi-agent coordinator.

        Args:
            db_path: Path to coordination database
            enable_physics_constraints: Enable physics-informed agent selection
            enable_cluster_offload: Enable task offloading to cluster nodes
        """
=======
    def __init__(self, db_path: Path = DB_PATH):
        """Initialize multi-agent coordinator"""
>>>>>>> origin/main
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Available agents registry
        self.agents: Dict[str, AgentCapability] = {}
        self._register_default_agents()

<<<<<<< HEAD
        # Cluster distribution (prioritize remote execution)
        self.enable_cluster_offload = enable_cluster_offload and CLUSTER_AVAILABLE
        if self.enable_cluster_offload:
            self.task_router = DistributedTaskRouter()
            self._register_cluster_agents()
            logger.info(f"✓ Cluster task offloading enabled ({len(CLUSTER_NODES)} nodes)")
        else:
            self.task_router = None
            if enable_cluster_offload and not CLUSTER_AVAILABLE:
                logger.warning("Cluster offload requested but not available")

        # Physics-informed learning (optional enhancement)
        self.enable_physics_constraints = enable_physics_constraints and PHYSICS_AVAILABLE
        if self.enable_physics_constraints:
            self.physics_learning = PhysicsInformedLearning()
            logger.info("✓ Physics-informed agent selection enabled")
        else:
            self.physics_learning = None
            if enable_physics_constraints and not PHYSICS_AVAILABLE:
                logger.warning("Physics constraints requested but not available")

=======
>>>>>>> origin/main
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

<<<<<<< HEAD
    def _register_cluster_agents(self):
        """
        Register cluster nodes as virtual agents.

        Cluster nodes can handle heavy computational tasks and are prioritized
        for offloading to distribute work across the network.
        """
        if not CLUSTER_AVAILABLE:
            return

        for node_id, node_info in CLUSTER_NODES.items():
            # Skip local node (already has local agents)
            if node_id == self.task_router.local_node_id:
                continue

            role = node_info['role']
            capabilities = node_info['capabilities']

            # Map node roles to task types
            task_types_map = {
                "builder": ["code_generation", "compilation", "docker_build", "testing"],
                "researcher": ["research", "analysis", "documentation", "web_scraping"],
                "production": ["deployment", "monitoring", "scaling", "production"]
            }

            task_types = task_types_map.get(role, ["general"])

            # Add general capabilities based on node
            if "docker" in capabilities:
                task_types.extend(["containerization", "deployment"])
            if "python" in capabilities:
                task_types.extend(["data_processing", "analysis"])

            # Remove duplicates
            task_types = list(set(task_types))

            # Create virtual agent for cluster node
            cluster_agent = AgentCapability(
                agent_name=f"cluster:{node_id}",
                task_types=task_types,
                max_concurrent_tasks=8,  # Higher capacity for remote nodes
                current_load=0,
                status=AgentStatus.IDLE,
                performance_score=0.95  # Prioritize cluster offloading
            )

            self.register_agent(cluster_agent)
            logger.info(f"Registered cluster agent: {node_id} ({role}) - {len(task_types)} task types")

=======
>>>>>>> origin/main
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
<<<<<<< HEAD
        4. [NEW] Respects physics constraints if enabled (load balancing, energy conservation)
        """
        # Use physics-constrained selection if enabled
        if self.enable_physics_constraints and self.physics_learning:
            return self._assign_agent_physics_constrained(subtask)

        # Standard selection (fallback)
        return self._assign_agent_standard(subtask)

    def _assign_agent_standard(self, subtask: SubTask) -> Optional[str]:
        """Standard agent assignment without physics constraints"""
=======
        """
>>>>>>> origin/main
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

<<<<<<< HEAD
    def _assign_agent_physics_constrained(self, subtask: SubTask) -> Optional[str]:
        """
        Physics-constrained agent assignment.

        Respects:
        - Computational energy conservation (total load)
        - Load balancing symmetry (similar agents get similar loads)
        - Causal ordering (dependencies)
        """
        # Get available agents for this task type
        available = []
        for agent_name, agent in self.agents.items():
            if subtask.task_type in agent.task_types or "general" in agent.task_types:
                if agent.current_load < agent.max_concurrent_tasks:
                    if agent.status == AgentStatus.IDLE:
                        available.append(agent_name)

        if not available:
            logger.warning(f"No available agents for task type: {subtask.task_type}")
            return None

        # Build state for physics validation
        agent_capabilities = {name: self.agents[name].performance_score for name in available}
        current_loads = {name: self.agents[name].current_load / self.agents[name].max_concurrent_tasks
                        for name in self.agents}

        # Use physics-informed selection
        selected_agent, validation = self.physics_learning.constrained_agent_selection(
            task_type=subtask.task_type,
            available_agents=available,
            agent_capabilities=agent_capabilities,
            current_loads=current_loads
        )

        if selected_agent and not validation['physics_valid']:
            logger.warning(f"Physics constraint violations detected: {validation['violations']}")
            logger.warning(f"Total penalty: {validation['total_penalty']}")

        if selected_agent:
            # Update agent load
            self.agents[selected_agent].current_load += 1
            if self.agents[selected_agent].current_load >= self.agents[selected_agent].max_concurrent_tasks:
                self.agents[selected_agent].status = AgentStatus.BUSY

            logger.info(f"Assigned task {subtask.task_id} to agent: {selected_agent} "
                       f"(physics-constrained, valid={validation['physics_valid']})")

        return selected_agent

    def select_best_agent(self, task_type: str, required_capabilities: List[str]) -> Optional[AgentCapability]:
        """
        Select best agent for a task type.

        This is a convenience method for direct agent selection without creating a SubTask.
        Used by benchmarking and other direct selection scenarios.

        Args:
            task_type: Type of task
            required_capabilities: List of required capabilities (optional)

        Returns:
            Best matching AgentCapability or None
        """
        candidates = []

        for agent_name, agent in self.agents.items():
            # Check if agent supports this task type
            if task_type in agent.task_types or "general" in agent.task_types:
                # Check if agent has capacity
                if agent.current_load < agent.max_concurrent_tasks:
                    if agent.status == AgentStatus.IDLE or agent.status == AgentStatus.BUSY:
                        # Calculate score based on performance and current load
                        availability = 1.0 - (agent.current_load / agent.max_concurrent_tasks)
                        score = agent.performance_score * availability
                        candidates.append((agent, score))

        if not candidates:
            logger.warning(f"No available agents for task type: {task_type}")
            return None

        # Select best performer considering load
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def execute_subtask(self, subtask: SubTask) -> Dict:
        """
        Execute a subtask - offloads to cluster nodes when possible.

        Args:
            subtask: The subtask to execute

        Returns:
            Execution result dict with status, output, execution_time_ms
        """
        logger.info(f"Executing subtask {subtask.task_id} with agent {subtask.assigned_agent}")

        # Check if this is a cluster agent (remote execution)
        if subtask.assigned_agent and subtask.assigned_agent.startswith("cluster:"):
            return await self._execute_on_cluster(subtask)

        # Local execution (would call actual local agent in production)
        await asyncio.sleep(0.5)  # Simulate local work

        result = {
            "task_id": subtask.task_id,
            "status": "completed",
            "output": f"Local execution: {subtask.description}",
            "execution_time_ms": 500,
            "execution_location": "local"
=======
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
>>>>>>> origin/main
        }

        return result

<<<<<<< HEAD
    async def _execute_on_cluster(self, subtask: SubTask) -> Dict:
        """
        Execute subtask on a remote cluster node.

        Args:
            subtask: The subtask to execute remotely

        Returns:
            Execution result from remote node
        """
        if not self.enable_cluster_offload or not self.task_router:
            logger.error("Cluster offload requested but not available")
            return {
                "task_id": subtask.task_id,
                "status": "failed",
                "error": "Cluster offload not available",
                "execution_time_ms": 0
            }

        # Extract node_id from agent name (format: "cluster:node_id")
        node_id = subtask.assigned_agent.split(":", 1)[1]

        logger.info(f"🌐 Offloading task {subtask.task_id} to cluster node: {node_id}")

        # Submit task to cluster
        task_def = {
            "type": "shell",
            "command": f"echo 'Executing: {subtask.description}'",  # Placeholder - would be actual command
            "task_type": subtask.task_type,
            "description": subtask.description,
            "force_node": node_id
        }

        try:
            # Submit and wait for result
            task_id = self.task_router.submit_task(task_def)
            result = self.task_router.wait_for_result(task_id, timeout=300)

            if result.get("status") == "completed":
                logger.info(f"✓ Task {subtask.task_id} completed on {node_id}")
                return {
                    "task_id": subtask.task_id,
                    "status": "completed",
                    "output": result.get("result", {}).get("stdout", ""),
                    "execution_time_ms": 1000,  # Would be tracked from actual execution
                    "execution_location": f"cluster:{node_id}"
                }
            else:
                logger.error(f"✗ Task {subtask.task_id} failed on {node_id}: {result.get('error')}")
                return {
                    "task_id": subtask.task_id,
                    "status": "failed",
                    "error": result.get("error", "Unknown cluster execution error"),
                    "execution_time_ms": 0,
                    "execution_location": f"cluster:{node_id}"
                }

        except Exception as e:
            logger.error(f"Cluster execution error for task {subtask.task_id}: {e}")
            return {
                "task_id": subtask.task_id,
                "status": "failed",
                "error": str(e),
                "execution_time_ms": 0,
                "execution_location": f"cluster:{node_id}"
            }

=======
>>>>>>> origin/main
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
