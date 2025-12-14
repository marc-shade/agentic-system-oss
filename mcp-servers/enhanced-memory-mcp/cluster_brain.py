#!/usr/bin/env python3
"""
Cluster Brain - Unified Intelligence Layer

Provides a single "brain" that all cluster nodes can access while maintaining
their specialized roles. Think of it as:

- Shared Cortex: Knowledge all nodes can access (semantic memory)
- Shared Goals: What the cluster is working toward
- Shared Learnings: Insights from any node, available to all
- Node Specialty: Each node's unique capabilities and current work

Architecture:
- cluster_brain.db: Shared across all nodes (via SMB/NFS or sync)
- Node-specific working memory: Local to each node
- Sync daemon: Pushes important learnings to cluster brain
"""
import platform

import sqlite3
import json
import os
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

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


logger = logging.getLogger(__name__)

# Cluster brain database - shared location accessible by all nodes
CLUSTER_DB_PATH = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "databases/cluster/cluster_brain.db"))

# Node roles and their specialties - loaded from config
def _load_node_roles() -> dict:
    """
    Load node roles from environment or config file.

    Configuration sources (in priority order):
    1. NODE_ROLES_JSON environment variable (JSON string)
    2. cluster-nodes.json file in ~/.claude/
    3. Default generic roles

    Example cluster-nodes.json:
    {
        "builder-node": {"role": "builder", "name": "Builder", "specialty": ["build", "test"]},
        "orchestrator-node": {"role": "orchestrator", "name": "Orchestrator", "specialty": ["coordination"]}
    }
    """
    # Try environment variable
    env_config = os.environ.get("NODE_ROLES_JSON")
    if env_config:
        try:
            return json.loads(env_config)
        except json.JSONDecodeError:
            pass

    # Try config file
    config_path = Path.home() / ".claude" / "cluster-nodes.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Return generic default roles
    return {
        "builder": {
            "role": "builder",
            "name": "Builder",
            "specialty": ["compilation", "testing", "containers", "benchmarks"],
            "can_execute": ["build", "test", "containerize", "benchmark", "deploy"]
        },
        "orchestrator": {
            "role": "orchestrator",
            "name": "Orchestrator",
            "specialty": ["coordination", "planning", "monitoring", "routing"],
            "can_execute": ["coordinate", "plan", "monitor", "route", "decide"]
        },
        "researcher": {
            "role": "researcher",
            "name": "Researcher",
            "specialty": ["analysis", "documentation", "research", "learning"],
            "can_execute": ["research", "analyze", "document", "synthesize"]
        },
        "inference": {
            "role": "inference",
            "name": "AI Inference",
            "specialty": ["inference", "patterns", "classification", "AI"],
            "can_execute": ["infer", "classify", "predict", "recognize"]
        }
    }

NODE_ROLES = _load_node_roles()


class ClusterBrain:
    """
    Unified cluster brain - shared intelligence across all nodes.

    Each node can:
    - Read any shared knowledge
    - Contribute learnings to the shared brain
    - Query for task routing (who should handle what)
    - Access cluster-wide goals and context
    """

    def __init__(self, node_id: str = None):
        """
        Initialize cluster brain connection.

        Args:
            node_id: This node's identifier (auto-detected if not provided)
        """
        self.node_id = node_id or self._detect_node_id()
        self.node_role = NODE_ROLES.get(self.node_id, {})
        self.db_path = CLUSTER_DB_PATH

        # Ensure database exists with proper schema
        self._ensure_database()

        logger.info(f"ClusterBrain initialized for {self.node_id} ({self.node_role.get('name', 'Unknown')})")

    def _detect_node_id(self) -> str:
        """Auto-detect node ID from hostname or config"""
        hostname = socket.gethostname().lower()

        # Load hostname mappings from config (or use empty dict)
        hostname_map = {}
        env_map = os.environ.get("HOSTNAME_NODE_MAP_JSON")
        if env_map:
            try:
                hostname_map = json.loads(env_map)
            except json.JSONDecodeError:
                pass

        if not hostname_map:
            config_path = Path.home() / ".claude" / "hostname-map.json"
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        hostname_map = json.load(f)
                except (json.JSONDecodeError, IOError):
                    pass

        for key, node_id in hostname_map.items():
            if key in hostname:
                return node_id

        # Try loading from config
        config_path = Path.home() / ".claude" / "node-config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                return config.get("node_id", hostname)

        return hostname

    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Shared semantic knowledge - concepts all nodes can access
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                contributed_by TEXT NOT NULL,
                confidence REAL DEFAULT 0.8,
                access_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Cluster goals - what we're working toward
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',
                priority INTEGER DEFAULT 5,
                assigned_nodes TEXT,
                progress REAL DEFAULT 0.0,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Shared learnings - insights from any node
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learning TEXT NOT NULL,
                category TEXT,
                source_task TEXT,
                learned_by TEXT NOT NULL,
                applies_to TEXT,
                success_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Node status - what each node is doing right now
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_status (
                node_id TEXT PRIMARY KEY,
                role TEXT,
                status TEXT DEFAULT 'online',
                current_task TEXT,
                cpu_percent REAL,
                memory_percent REAL,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Task routing history - who handled what successfully
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_routing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                task_description TEXT,
                routed_to TEXT NOT NULL,
                success INTEGER,
                execution_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indices for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_category ON shared_knowledge(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON cluster_goals(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_learnings_category ON shared_learnings(category)")

        conn.commit()
        conn.close()

    # ==================== KNOWLEDGE OPERATIONS ====================

    def add_knowledge(self, concept: str, category: str, content: str,
                      confidence: float = 0.8) -> Dict:
        """
        Add knowledge to the shared cluster brain.

        Args:
            concept: Name/title of the knowledge
            category: Category (e.g., 'architecture', 'patterns', 'tools')
            content: The actual knowledge content
            confidence: How confident we are (0.0-1.0)

        Returns:
            Result with knowledge_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO shared_knowledge (concept, category, content, contributed_by, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (concept, category, content, self.node_id, confidence))

        knowledge_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Added knowledge: {concept} (category: {category})")

        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "contributed_by": self.node_id
        }

    def query_knowledge(self, query: str = None, category: str = None,
                        limit: int = 10) -> List[Dict]:
        """
        Query the shared knowledge base.

        Args:
            query: Search term (searches concept and content)
            category: Filter by category
            limit: Max results

        Returns:
            List of matching knowledge entries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT * FROM shared_knowledge WHERE 1=1"
        params = []

        if query:
            sql += " AND (concept LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY access_count DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]

        # Update access count for retrieved items
        for result in results:
            cursor.execute(
                "UPDATE shared_knowledge SET access_count = access_count + 1 WHERE id = ?",
                (result["id"],)
            )

        conn.commit()
        conn.close()

        return results

    # ==================== GOALS OPERATIONS ====================

    def add_goal(self, goal: str, description: str = None,
                 priority: int = 5, assigned_nodes: List[str] = None) -> Dict:
        """
        Add a cluster-wide goal.

        Args:
            goal: Short goal statement
            description: Detailed description
            priority: 1-10 (10 is highest)
            assigned_nodes: Which nodes should work on this

        Returns:
            Result with goal_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        nodes_json = json.dumps(assigned_nodes) if assigned_nodes else None

        cursor.execute("""
            INSERT INTO cluster_goals (goal, description, priority, assigned_nodes, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (goal, description, priority, nodes_json, self.node_id))

        goal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Added cluster goal: {goal}")

        return {
            "success": True,
            "goal_id": goal_id,
            "created_by": self.node_id
        }

    def get_active_goals(self, assigned_to: str = None) -> List[Dict]:
        """
        Get active cluster goals.

        Args:
            assigned_to: Filter by assigned node (optional)

        Returns:
            List of active goals
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM cluster_goals
            WHERE status = 'active'
            ORDER BY priority DESC, created_at DESC
        """)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Filter by assigned node if specified
        if assigned_to:
            filtered = []
            for goal in results:
                assigned = json.loads(goal.get("assigned_nodes") or "[]")
                if not assigned or assigned_to in assigned:
                    filtered.append(goal)
            return filtered

        return results

    def update_goal_progress(self, goal_id: int, progress: float,
                            status: str = None) -> Dict:
        """
        Update progress on a goal.

        Args:
            goal_id: Goal to update
            progress: Progress 0.0-1.0
            status: New status (optional)

        Returns:
            Update result
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                UPDATE cluster_goals
                SET progress = ?, status = ?,
                    completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                WHERE id = ?
            """, (progress, status, status, goal_id))
        else:
            cursor.execute("""
                UPDATE cluster_goals SET progress = ? WHERE id = ?
            """, (progress, goal_id))

        conn.commit()
        conn.close()

        return {"success": True, "goal_id": goal_id, "progress": progress}

    # ==================== LEARNINGS OPERATIONS ====================

    def add_learning(self, learning: str, category: str = None,
                     source_task: str = None, success_score: float = None,
                     applies_to: List[str] = None) -> Dict:
        """
        Share a learning with the cluster brain.

        Args:
            learning: What was learned
            category: Learning category
            source_task: What task led to this learning
            success_score: How successful was the outcome (0.0-1.0)
            applies_to: Which node roles might benefit

        Returns:
            Result with learning_id
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        applies_json = json.dumps(applies_to) if applies_to else None

        cursor.execute("""
            INSERT INTO shared_learnings
            (learning, category, source_task, learned_by, applies_to, success_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (learning, category, source_task, self.node_id, applies_json, success_score))

        learning_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Shared learning: {learning[:50]}...")

        return {
            "success": True,
            "learning_id": learning_id,
            "learned_by": self.node_id
        }

    def get_learnings(self, category: str = None, applies_to: str = None,
                      limit: int = 20) -> List[Dict]:
        """
        Get learnings from the cluster brain.

        Args:
            category: Filter by category
            applies_to: Filter by applicable role
            limit: Max results

        Returns:
            List of learnings
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT * FROM shared_learnings WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Filter by applies_to if specified
        if applies_to:
            filtered = []
            for learning in results:
                applies = json.loads(learning.get("applies_to") or "[]")
                if not applies or applies_to in applies:
                    filtered.append(learning)
            return filtered

        return results

    # ==================== NODE STATUS OPERATIONS ====================

    def update_status(self, current_task: str = None,
                      cpu_percent: float = None, memory_percent: float = None) -> Dict:
        """
        Update this node's status in the cluster brain.

        Args:
            current_task: What we're working on
            cpu_percent: Current CPU usage
            memory_percent: Current memory usage

        Returns:
            Update result
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO node_status
            (node_id, role, status, current_task, cpu_percent, memory_percent, last_heartbeat)
            VALUES (?, ?, 'online', ?, ?, ?, CURRENT_TIMESTAMP)
        """, (self.node_id, self.node_role.get("role"), current_task,
              cpu_percent, memory_percent))

        conn.commit()
        conn.close()

        return {"success": True, "node_id": self.node_id}

    def get_cluster_status(self) -> Dict:
        """
        Get status of all nodes in the cluster.

        Returns:
            Dict with all node statuses
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM node_status ORDER BY node_id")
        nodes = {row["node_id"]: dict(row) for row in cursor.fetchall()}
        conn.close()

        # Add role info for any missing nodes
        for node_id, role_info in NODE_ROLES.items():
            if node_id not in nodes:
                nodes[node_id] = {
                    "node_id": node_id,
                    "role": role_info["role"],
                    "status": "unknown",
                    "current_task": None
                }

        return nodes

    # ==================== TASK ROUTING ====================

    def route_task(self, task_type: str, task_description: str = None) -> Dict:
        """
        Determine which node should handle a task.

        Args:
            task_type: Type of task (build, test, research, infer, etc.)
            task_description: Optional description for better routing

        Returns:
            Routing recommendation with node_id and reasoning
        """
        # Check historical success
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT routed_to,
                   COUNT(*) as total,
                   SUM(success) as successes,
                   AVG(execution_time_ms) as avg_time
            FROM task_routing
            WHERE task_type = ?
            GROUP BY routed_to
            ORDER BY successes DESC, avg_time ASC
        """, (task_type,))

        history = cursor.fetchall()
        conn.close()

        # Find best node based on capabilities
        best_node = None
        best_score = 0
        reasoning = []

        for node_id, role_info in NODE_ROLES.items():
            score = 0

            # Check if task type matches capabilities
            if task_type.lower() in [c.lower() for c in role_info.get("can_execute", [])]:
                score += 50
                reasoning.append(f"{node_id} can execute '{task_type}'")

            # Check specialty match
            for specialty in role_info.get("specialty", []):
                if specialty.lower() in task_type.lower():
                    score += 30
                    reasoning.append(f"{node_id} specializes in '{specialty}'")

            # Add historical success bonus
            for row in history:
                if row["routed_to"] == node_id and row["successes"]:
                    success_rate = row["successes"] / row["total"]
                    score += int(success_rate * 20)
                    reasoning.append(f"{node_id} has {success_rate:.0%} success rate")

            if score > best_score:
                best_score = score
                best_node = node_id

        # Default to orchestrator if no clear match
        if not best_node:
            best_node = "orchestrator"
            reasoning.append("Defaulting to orchestrator for unknown task type")

        return {
            "recommended_node": best_node,
            "role": NODE_ROLES.get(best_node, {}).get("name", "Unknown"),
            "confidence": min(best_score / 100, 1.0),
            "reasoning": reasoning
        }

    def record_task_result(self, task_type: str, routed_to: str,
                           success: bool, execution_time_ms: int = None,
                           task_description: str = None) -> Dict:
        """
        Record the result of a routed task for learning.

        Args:
            task_type: Type of task
            routed_to: Which node handled it
            success: Whether it succeeded
            execution_time_ms: How long it took
            task_description: Description of the task

        Returns:
            Recording result
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO task_routing (task_type, task_description, routed_to, success, execution_time_ms)
            VALUES (?, ?, ?, ?, ?)
        """, (task_type, task_description, routed_to, 1 if success else 0, execution_time_ms))

        conn.commit()
        conn.close()

        return {"success": True, "recorded": True}

    # ==================== CLUSTER SUMMARY ====================

    def get_brain_summary(self) -> Dict:
        """
        Get a summary of the cluster brain state.

        Returns:
            Summary with counts and recent activity
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count everything
        cursor.execute("SELECT COUNT(*) FROM shared_knowledge")
        knowledge_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cluster_goals WHERE status = 'active'")
        active_goals = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM shared_learnings")
        learnings_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM node_status WHERE status = 'online'")
        online_nodes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM task_routing")
        routed_tasks = cursor.fetchone()[0]

        conn.close()

        return {
            "shared_knowledge": knowledge_count,
            "active_goals": active_goals,
            "shared_learnings": learnings_count,
            "online_nodes": online_nodes,
            "routed_tasks": routed_tasks,
            "this_node": {
                "id": self.node_id,
                "role": self.node_role.get("name", "Unknown"),
                "specialties": self.node_role.get("specialty", [])
            }
        }


# Singleton instance
_brain_instance = None

def get_cluster_brain(node_id: str = None) -> ClusterBrain:
    """Get or create the cluster brain instance"""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = ClusterBrain(node_id)
    return _brain_instance


# Quick test
if __name__ == "__main__":
    brain = ClusterBrain()

    print(f"\n{'='*60}")
    print("CLUSTER BRAIN STATUS")
    print(f"{'='*60}")

    summary = brain.get_brain_summary()
    print(f"\nThis Node: {summary['this_node']['id']} ({summary['this_node']['role']})")
    print(f"Specialties: {', '.join(summary['this_node']['specialties'])}")
    print(f"\nCluster Brain Contents:")
    print(f"  - Shared Knowledge: {summary['shared_knowledge']}")
    print(f"  - Active Goals: {summary['active_goals']}")
    print(f"  - Shared Learnings: {summary['shared_learnings']}")
    print(f"  - Online Nodes: {summary['online_nodes']}")
    print(f"  - Routed Tasks: {summary['routed_tasks']}")

    print(f"\n{'='*60}")
    print("CLUSTER STATUS")
    print(f"{'='*60}")

    status = brain.get_cluster_status()
    for node_id, info in status.items():
        print(f"\n{node_id}:")
        print(f"  Role: {info.get('role', 'unknown')}")
        print(f"  Status: {info.get('status', 'unknown')}")
        if info.get('current_task'):
            print(f"  Working on: {info['current_task']}")
