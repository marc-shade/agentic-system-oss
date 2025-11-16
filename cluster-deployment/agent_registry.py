#!/usr/bin/env python3
"""
Agent Registry and Coordination System

Manages all agents in the agentic network:
- Claude Code sessions (via MCP)
- Background system agents (cluster-self-x-daemon, intelligent agents)
- Specialized agents (code protector, health guardian, etc.)

Each agent registers with the registry to:
- Announce capabilities and role
- Discover other agents
- Coordinate distributed operations
- Request/provide cluster resources
"""

import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path
import socket

# Agent roles in the network
AGENT_ROLES = {
    "claude-code-session": {
        "description": "Interactive Claude Code session",
        "capabilities": ["interactive", "tool_use", "file_edit", "cluster_execution"],
        "can_request_resources": True,
        "can_provide_resources": False,
        "priority": 10  # Highest priority - user-facing
    },
    "cluster-orchestrator": {
        "description": "Cluster self-X daemon orchestrator",
        "capabilities": ["self_improvement", "optimization", "discovery", "coordination"],
        "can_request_resources": True,
        "can_provide_resources": True,
        "priority": 8
    },
    "performance-optimizer": {
        "description": "Real-time performance monitoring and optimization",
        "capabilities": ["monitoring", "offload_detection", "load_balancing"],
        "can_request_resources": True,
        "can_provide_resources": True,
        "priority": 7
    },
    "self-improvement-agent": {
        "description": "Autonomous self-improvement and capability enhancement",
        "capabilities": ["discovery", "gap_analysis", "deployment", "sync"],
        "can_request_resources": True,
        "can_provide_resources": False,
        "priority": 6
    },
    "code-evolution-protector": {
        "description": "Protects code from unintended evolution",
        "capabilities": ["monitoring", "rollback", "validation"],
        "can_request_resources": False,
        "can_provide_resources": True,
        "priority": 9  # High priority - safety critical
    },
    "system-health-guardian": {
        "description": "Monitors and maintains system health",
        "capabilities": ["monitoring", "alerting", "remediation"],
        "can_request_resources": True,
        "can_provide_resources": True,
        "priority": 8
    },
    "task-interceptor": {
        "description": "Automatically detects and offloads heavy tasks",
        "capabilities": ["process_monitoring", "offload_decision", "task_routing"],
        "can_request_resources": True,
        "can_provide_resources": False,
        "priority": 5
    },
    "ollama-reasoning-agent": {
        "description": "Persistent AI reasoning using Ollama models",
        "capabilities": ["reasoning", "decision_making", "analysis"],
        "can_request_resources": True,
        "can_provide_resources": True,
        "priority": 7
    },
    "mcp-server": {
        "description": "MCP server providing tools to Claude Code",
        "capabilities": ["tool_serving", "resource_coordination"],
        "can_request_resources": True,
        "can_provide_resources": True,
        "priority": 8
    }
}


@dataclass
class AgentRegistration:
    """Agent registration entry"""
    agent_id: str
    node_id: str
    role: str
    pid: int
    hostname: str
    capabilities: List[str]
    status: str  # active, idle, busy, error
    registered_at: float
    last_heartbeat: float
    metadata: Dict  # Extra info (version, config, etc.)


class AgentRegistry:
    """
    Central registry for all agents in the agentic network

    Agents register on startup, send heartbeats, and can:
    - Discover other agents by role/capability
    - Request cluster resources
    - Coordinate distributed operations
    - Share status and metrics
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use cluster database
            db_path = str(Path.home() / "agentic-system/databases/cluster/agent_registry.db")

        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize agent registry database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_registry (
                    agent_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    hostname TEXT NOT NULL,
                    capabilities TEXT NOT NULL,  -- JSON array
                    status TEXT NOT NULL,
                    registered_at REAL NOT NULL,
                    last_heartbeat REAL NOT NULL,
                    metadata TEXT  -- JSON object
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_role ON agent_registry(role)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_node_id ON agent_registry(node_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON agent_registry(status)
            """)

            # Coordination log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coordination_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    source_agent_id TEXT NOT NULL,
                    target_agent_id TEXT,
                    action TEXT NOT NULL,
                    details TEXT  -- JSON
                )
            """)

            conn.commit()

    def register_agent(self, node_id: str, role: str, pid: int = None,
                      metadata: Dict = None) -> str:
        """
        Register an agent in the network

        Returns:
            agent_id: Unique identifier for this agent
        """
        if role not in AGENT_ROLES:
            raise ValueError(f"Unknown role: {role}. Valid roles: {list(AGENT_ROLES.keys())}")

        # Generate agent ID
        hostname = socket.gethostname()
        timestamp = time.time()
        agent_id = f"{role}_{node_id}_{hostname}_{int(timestamp)}"

        if pid is None:
            import os
            pid = os.getpid()

        capabilities = AGENT_ROLES[role]["capabilities"]

        registration = AgentRegistration(
            agent_id=agent_id,
            node_id=node_id,
            role=role,
            pid=pid,
            hostname=hostname,
            capabilities=capabilities,
            status="active",
            registered_at=timestamp,
            last_heartbeat=timestamp,
            metadata=metadata or {}
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agent_registry
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                registration.agent_id,
                registration.node_id,
                registration.role,
                registration.pid,
                registration.hostname,
                json.dumps(registration.capabilities),
                registration.status,
                registration.registered_at,
                registration.last_heartbeat,
                json.dumps(registration.metadata)
            ))
            conn.commit()

        self._log_coordination(agent_id, None, "register", {
            "role": role,
            "node_id": node_id,
            "capabilities": capabilities
        })

        return agent_id

    def heartbeat(self, agent_id: str, status: str = "active",
                 metadata: Dict = None):
        """Send heartbeat to keep agent registration alive"""
        with sqlite3.connect(self.db_path) as conn:
            if metadata:
                conn.execute("""
                    UPDATE agent_registry
                    SET last_heartbeat = ?, status = ?, metadata = ?
                    WHERE agent_id = ?
                """, (time.time(), status, json.dumps(metadata), agent_id))
            else:
                conn.execute("""
                    UPDATE agent_registry
                    SET last_heartbeat = ?, status = ?
                    WHERE agent_id = ?
                """, (time.time(), status, agent_id))
            conn.commit()

    def unregister_agent(self, agent_id: str):
        """Unregister agent from network"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM agent_registry WHERE agent_id = ?", (agent_id,))
            conn.commit()

        self._log_coordination(agent_id, None, "unregister", {})

    def discover_agents(self, role: str = None, capability: str = None,
                       node_id: str = None, status: str = "active") -> List[AgentRegistration]:
        """
        Discover agents in the network

        Args:
            role: Filter by agent role
            capability: Filter by capability
            node_id: Filter by node
            status: Filter by status (default: active)
        """
        query = "SELECT * FROM agent_registry WHERE 1=1"
        params = []

        if role:
            query += " AND role = ?"
            params.append(role)

        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)

        if status:
            query += " AND status = ?"
            params.append(status)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            agents = []

            for row in cursor:
                capabilities = json.loads(row["capabilities"])

                # Filter by capability if specified
                if capability and capability not in capabilities:
                    continue

                agent = AgentRegistration(
                    agent_id=row["agent_id"],
                    node_id=row["node_id"],
                    role=row["role"],
                    pid=row["pid"],
                    hostname=row["hostname"],
                    capabilities=capabilities,
                    status=row["status"],
                    registered_at=row["registered_at"],
                    last_heartbeat=row["last_heartbeat"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                agents.append(agent)

        return agents

    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get specific agent by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM agent_registry WHERE agent_id = ?",
                (agent_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return AgentRegistration(
                agent_id=row["agent_id"],
                node_id=row["node_id"],
                role=row["role"],
                pid=row["pid"],
                hostname=row["hostname"],
                capabilities=json.loads(row["capabilities"]),
                status=row["status"],
                registered_at=row["registered_at"],
                last_heartbeat=row["last_heartbeat"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {}
            )

    def cleanup_stale_agents(self, timeout: int = 300):
        """Remove agents that haven't sent heartbeat in timeout seconds"""
        cutoff = time.time() - timeout

        with sqlite3.connect(self.db_path) as conn:
            # Get stale agents
            cursor = conn.execute(
                "SELECT agent_id FROM agent_registry WHERE last_heartbeat < ?",
                (cutoff,)
            )
            stale = [row[0] for row in cursor]

            # Remove them
            conn.execute(
                "DELETE FROM agent_registry WHERE last_heartbeat < ?",
                (cutoff,)
            )
            conn.commit()

        for agent_id in stale:
            self._log_coordination(agent_id, None, "cleanup_stale", {})

        return len(stale)

    def _log_coordination(self, source_agent_id: str, target_agent_id: Optional[str],
                         action: str, details: Dict):
        """Log coordination event"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO coordination_log (timestamp, source_agent_id, target_agent_id, action, details)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), source_agent_id, target_agent_id, action, json.dumps(details)))
            conn.commit()

    def get_network_status(self) -> Dict:
        """Get current network status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Total agents
            total = conn.execute("SELECT COUNT(*) as count FROM agent_registry").fetchone()["count"]

            # By status
            status_counts = {}
            cursor = conn.execute("SELECT status, COUNT(*) as count FROM agent_registry GROUP BY status")
            for row in cursor:
                status_counts[row["status"]] = row["count"]

            # By role
            role_counts = {}
            cursor = conn.execute("SELECT role, COUNT(*) as count FROM agent_registry GROUP BY role")
            for row in cursor:
                role_counts[row["role"]] = row["count"]

            # By node
            node_counts = {}
            cursor = conn.execute("SELECT node_id, COUNT(*) as count FROM agent_registry GROUP BY node_id")
            for row in cursor:
                node_counts[row["node_id"]] = row["count"]

        return {
            "total_agents": total,
            "by_status": status_counts,
            "by_role": role_counts,
            "by_node": node_counts,
            "timestamp": time.time()
        }


if __name__ == "__main__":
    # Test the registry
    registry = AgentRegistry()

    # Register test agent
    agent_id = registry.register_agent(
        node_id="macpro51",
        role="cluster-orchestrator",
        metadata={"version": "1.0.0"}
    )
    print(f"Registered: {agent_id}")

    # Discover agents
    agents = registry.discover_agents(role="cluster-orchestrator")
    print(f"\nFound {len(agents)} orchestrator agents:")
    for agent in agents:
        print(f"  - {agent.agent_id} on {agent.node_id} ({agent.status})")

    # Network status
    status = registry.get_network_status()
    print(f"\nNetwork status: {json.dumps(status, indent=2)}")
