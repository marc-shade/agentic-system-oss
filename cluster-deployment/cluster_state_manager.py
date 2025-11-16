#!/usr/bin/env python3
"""
Cluster State Manager - Single Source of Truth

Unified intelligent state management for the entire agentic cluster.

Replaces fragmented systems:
- node_registry.db → cluster_state.db (nodes table)
- agent_registry.db → cluster_state.db (agents table)
- Task queues → cluster_state.db (tasks table)
- Resource allocation → cluster_state.db (resources table)
- Shared memories → cluster_state.db (memories table)

Everything in the cluster queries THIS for truth.
No more scattered databases, no more sync issues.
"""

import json
import sqlite3
import time
import socket
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path
from enum import Enum


class NodeStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class AgentStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Node:
    """Cluster node representation"""
    node_id: str
    hostname: str
    ip_address: str
    os_type: str  # linux, darwin
    architecture: str  # x86_64, arm64
    role: str  # orchestrator, researcher, developer, builder
    status: NodeStatus
    cpu_percent: float
    memory_percent: float
    load_average_1m: float
    capabilities: List[str]  # docker, podman, gpu, etc.
    last_heartbeat: float
    metadata: Dict


@dataclass
class Agent:
    """Agent running in the cluster"""
    agent_id: str
    node_id: str
    agent_type: str  # claude-code-session, cluster-orchestrator, etc.
    pid: int
    status: AgentStatus
    role: str
    capabilities: List[str]
    priority: int
    registered_at: float
    last_heartbeat: float
    current_task_id: Optional[str]
    metadata: Dict


@dataclass
class Task:
    """Task in the cluster"""
    task_id: str
    task_type: str  # shell, python, build, test, etc.
    command: str
    priority: int
    status: TaskStatus
    created_by_agent: str
    assigned_to_node: Optional[str]
    assigned_to_agent: Optional[str]
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    result: Optional[Dict]
    metadata: Dict


@dataclass
class Resource:
    """Resource allocation"""
    resource_id: str
    resource_type: str  # cpu, memory, gpu, port, file_lock, etc.
    node_id: str
    allocated_to_agent: Optional[str]
    allocated_to_task: Optional[str]
    amount: float  # Amount allocated
    allocated_at: float
    expires_at: Optional[float]
    metadata: Dict


class ClusterStateManager:
    """
    Single Source of Truth for Cluster State

    All cluster components query this for:
    - Node status and capabilities
    - Agent registration and discovery
    - Task assignment and status
    - Resource allocation
    - Shared state

    NO other databases for cluster coordination!
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            # THE single source of truth
            db_path = str(Path.home() / "agentic-system/databases/cluster/cluster_state.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize the single source of truth database"""
        with sqlite3.connect(self.db_path) as conn:
            # NODES - Cluster hardware
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    hostname TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    os_type TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    load_average_1m REAL NOT NULL,
                    capabilities TEXT NOT NULL,  -- JSON array
                    last_heartbeat REAL NOT NULL,
                    metadata TEXT  -- JSON object
                )
            """)

            # AGENTS - Processes running in cluster
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    role TEXT NOT NULL,
                    capabilities TEXT NOT NULL,  -- JSON array
                    priority INTEGER NOT NULL,
                    registered_at REAL NOT NULL,
                    last_heartbeat REAL NOT NULL,
                    current_task_id TEXT,
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id)
                )
            """)

            # TASKS - Work units in cluster
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    command TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_by_agent TEXT NOT NULL,
                    assigned_to_node TEXT,
                    assigned_to_agent TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    result TEXT,  -- JSON object
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (created_by_agent) REFERENCES agents(agent_id),
                    FOREIGN KEY (assigned_to_node) REFERENCES nodes(node_id),
                    FOREIGN KEY (assigned_to_agent) REFERENCES agents(agent_id)
                )
            """)

            # RESOURCES - Allocated resources
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    allocated_to_agent TEXT,
                    allocated_to_task TEXT,
                    amount REAL NOT NULL,
                    allocated_at REAL NOT NULL,
                    expires_at REAL,
                    metadata TEXT,  -- JSON object
                    FOREIGN KEY (node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY (allocated_to_agent) REFERENCES agents(agent_id),
                    FOREIGN KEY (allocated_to_task) REFERENCES tasks(task_id)
                )
            """)

            # EVENT LOG - All cluster events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    node_id TEXT,
                    agent_id TEXT,
                    task_id TEXT,
                    details TEXT  -- JSON object
                )
            """)

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node_status ON nodes(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_status ON agents(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_node ON agents(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_resource_node ON resources(node_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_timestamp ON event_log(timestamp)")

            conn.commit()

    # === NODE MANAGEMENT ===

    def register_node(self, node_id: str, hostname: str, ip_address: str,
                     os_type: str, architecture: str, role: str,
                     capabilities: List[str], metadata: Dict = None) -> None:
        """Register or update a node in the cluster"""
        node = Node(
            node_id=node_id,
            hostname=hostname,
            ip_address=ip_address,
            os_type=os_type,
            architecture=architecture,
            role=role,
            status=NodeStatus.ONLINE,
            cpu_percent=0.0,
            memory_percent=0.0,
            load_average_1m=0.0,
            capabilities=capabilities,
            last_heartbeat=time.time(),
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.node_id, node.hostname, node.ip_address, node.os_type,
                node.architecture, node.role, node.status.value,
                node.cpu_percent, node.memory_percent, node.load_average_1m,
                json.dumps(node.capabilities), node.last_heartbeat,
                json.dumps(node.metadata)
            ))
            conn.commit()

        self._log_event("node_register", node_id=node_id, details={"role": role})

    def update_node_metrics(self, node_id: str, cpu_percent: float,
                           memory_percent: float, load_average_1m: float):
        """Update node performance metrics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE nodes
                SET cpu_percent = ?, memory_percent = ?, load_average_1m = ?, last_heartbeat = ?
                WHERE node_id = ?
            """, (cpu_percent, memory_percent, load_average_1m, time.time(), node_id))
            conn.commit()

    def get_nodes(self, status: NodeStatus = None) -> List[Node]:
        """Get all nodes, optionally filtered by status"""
        query = "SELECT * FROM nodes"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status.value)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            nodes = []

            for row in cursor:
                node = Node(
                    node_id=row["node_id"],
                    hostname=row["hostname"],
                    ip_address=row["ip_address"],
                    os_type=row["os_type"],
                    architecture=row["architecture"],
                    role=row["role"],
                    status=NodeStatus(row["status"]),
                    cpu_percent=row["cpu_percent"],
                    memory_percent=row["memory_percent"],
                    load_average_1m=row["load_average_1m"],
                    capabilities=json.loads(row["capabilities"]),
                    last_heartbeat=row["last_heartbeat"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                nodes.append(node)

        return nodes

    # === AGENT MANAGEMENT ===

    def register_agent(self, node_id: str, agent_type: str, role: str,
                      capabilities: List[str], priority: int = 5,
                      metadata: Dict = None) -> str:
        """Register an agent in the cluster"""
        import os
        agent_id = f"{agent_type}_{node_id}_{int(time.time())}_{os.getpid()}"

        agent = Agent(
            agent_id=agent_id,
            node_id=node_id,
            agent_type=agent_type,
            pid=os.getpid(),
            status=AgentStatus.ACTIVE,
            role=role,
            capabilities=capabilities,
            priority=priority,
            registered_at=time.time(),
            last_heartbeat=time.time(),
            current_task_id=None,
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO agents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent.agent_id, agent.node_id, agent.agent_type, agent.pid,
                agent.status.value, agent.role, json.dumps(agent.capabilities),
                agent.priority, agent.registered_at, agent.last_heartbeat,
                agent.current_task_id, json.dumps(agent.metadata)
            ))
            conn.commit()

        self._log_event("agent_register", agent_id=agent_id,
                       details={"type": agent_type, "node": node_id})

        return agent_id

    def agent_heartbeat(self, agent_id: str, status: AgentStatus = AgentStatus.ACTIVE):
        """Agent heartbeat"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE agents SET last_heartbeat = ?, status = ? WHERE agent_id = ?
            """, (time.time(), status.value, agent_id))
            conn.commit()

    def discover_agents(self, agent_type: str = None, capability: str = None,
                       node_id: str = None, status: AgentStatus = None) -> List[Agent]:
        """Discover agents matching criteria"""
        query = "SELECT * FROM agents WHERE 1=1"
        params = []

        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)

        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            agents = []

            for row in cursor:
                capabilities = json.loads(row["capabilities"])

                # Filter by capability if specified
                if capability and capability not in capabilities:
                    continue

                agent = Agent(
                    agent_id=row["agent_id"],
                    node_id=row["node_id"],
                    agent_type=row["agent_type"],
                    pid=row["pid"],
                    status=AgentStatus(row["status"]),
                    role=row["role"],
                    capabilities=capabilities,
                    priority=row["priority"],
                    registered_at=row["registered_at"],
                    last_heartbeat=row["last_heartbeat"],
                    current_task_id=row["current_task_id"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                agents.append(agent)

        return agents

    # === TASK MANAGEMENT ===

    def create_task(self, created_by_agent: str, task_type: str, command: str,
                   priority: int = 5, metadata: Dict = None) -> str:
        """Create a new task"""
        import uuid
        task_id = f"task_{int(time.time())}_{str(uuid.uuid4())[:8]}"

        task = Task(
            task_id=task_id,
            task_type=task_type,
            command=command,
            priority=priority,
            status=TaskStatus.PENDING,
            created_by_agent=created_by_agent,
            assigned_to_node=None,
            assigned_to_agent=None,
            created_at=time.time(),
            started_at=None,
            completed_at=None,
            result=None,
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.task_type, task.command, task.priority,
                task.status.value, task.created_by_agent, task.assigned_to_node,
                task.assigned_to_agent, task.created_at, task.started_at,
                task.completed_at, json.dumps(task.result) if task.result else None,
                json.dumps(task.metadata)
            ))
            conn.commit()

        self._log_event("task_create", task_id=task_id,
                       details={"type": task_type, "priority": priority})

        return task_id

    def assign_task(self, task_id: str, node_id: str, agent_id: str):
        """Assign task to node and agent"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE tasks
                SET status = ?, assigned_to_node = ?, assigned_to_agent = ?, started_at = ?
                WHERE task_id = ?
            """, (TaskStatus.ASSIGNED.value, node_id, agent_id, time.time(), task_id))

            conn.execute("""
                UPDATE agents SET current_task_id = ? WHERE agent_id = ?
            """, (task_id, agent_id))

            conn.commit()

        self._log_event("task_assign", task_id=task_id,
                       details={"node": node_id, "agent": agent_id})

    # === UTILITY ===

    def _log_event(self, event_type: str, node_id: str = None,
                   agent_id: str = None, task_id: str = None, details: Dict = None):
        """Log cluster event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO event_log (timestamp, event_type, node_id, agent_id, task_id, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (time.time(), event_type, node_id, agent_id, task_id,
                 json.dumps(details) if details else None))
            conn.commit()

    def get_cluster_state(self) -> Dict:
        """Get complete cluster state snapshot"""
        return {
            "nodes": len(self.get_nodes()),
            "agents": len(self.discover_agents()),
            "tasks_pending": len(self.get_tasks(TaskStatus.PENDING)),
            "tasks_running": len(self.get_tasks(TaskStatus.RUNNING)),
            "timestamp": time.time()
        }

    def get_tasks(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at ASC",
                (status.value,)
            )

            tasks = []
            for row in cursor:
                task = Task(
                    task_id=row["task_id"],
                    task_type=row["task_type"],
                    command=row["command"],
                    priority=row["priority"],
                    status=TaskStatus(row["status"]),
                    created_by_agent=row["created_by_agent"],
                    assigned_to_node=row["assigned_to_node"],
                    assigned_to_agent=row["assigned_to_agent"],
                    created_at=row["created_at"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    result=json.loads(row["result"]) if row["result"] else None,
                    metadata=json.loads(row["metadata"])
                )
                tasks.append(task)

        return tasks


if __name__ == "__main__":
    # Test the single source of truth
    csm = ClusterStateManager()

    # Register node
    csm.register_node(
        node_id="macpro51",
        hostname="macpro51",
        ip_address="192.168.1.154",
        os_type="linux",
        architecture="x86_64",
        role="builder",
        capabilities=["docker", "podman", "build", "test"]
    )

    # Register agent
    agent_id = csm.register_agent(
        node_id="macpro51",
        agent_type="cluster-orchestrator",
        role="coordination",
        capabilities=["task_routing", "resource_allocation"],
        priority=8
    )

    # Create task
    task_id = csm.create_task(
        created_by_agent=agent_id,
        task_type="shell",
        command="echo 'Hello from cluster'",
        priority=5
    )

    # Check state
    state = csm.get_cluster_state()
    print(f"Cluster state: {json.dumps(state, indent=2)}")
