#!/usr/bin/env python3
"""
Orchestrator Hive Mind Integration
Provides simple Python API for Claude to participate in cluster communication

Usage in Claude Code:
    from cluster_deployment.orchestrator_hive_mind import HiveMind

    hive = HiveMind()

    # Send message to a node
    hive.send_message("macpro51", "Test message from orchestrator")

    # Execute command on remote node
    result = hive.execute_remote("macpro51", "hostname")

    # Get cluster status
    status = hive.get_cluster_status()

    # Query shared memories
    memories = hive.query_shared_memory("optimization")

    # Store shared memory
    hive.store_shared_memory("optimization_pattern", "Use TOON format for 50% savings")
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from distributed_task_router import DistributedTaskRouter
from orchestrator_remote_exec import send_command
from toon_serialization import encode_result, decode_toon


class HiveMind:
    """Simple API for orchestrator to participate in hive mind"""

    def __init__(self):
        self.node_id = "mac-studio"
        self.router = DistributedTaskRouter()

        # Database paths
        self.db_base = Path("/Volumes/SSDRAID0/agentic-system/databases/cluster")
        self.messages_db = self.db_base / "node_messages.db"
        self.shared_memory_db = self.db_base / "shared_memories.db"
        self.registry_db = self.db_base / "node_registry.db"

        # Ensure databases exist
        self._init_databases()

    def _init_databases(self):
        """Initialize cluster databases if needed"""
        # Messages DB
        if not self.messages_db.exists():
            conn = sqlite3.connect(self.messages_db)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    subject TEXT NOT NULL,
                    body TEXT,
                    metadata TEXT,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    requires_action BOOLEAN DEFAULT 0,
                    action_taken BOOLEAN DEFAULT 0,
                    action_result TEXT,
                    processed_at TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

        # Shared Memory DB - always create table even if file exists
        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                observations TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                node_id TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def send_message(
        self,
        to_node: str,
        message: str,
        subject: str = "Message from orchestrator",
        priority: int = 5,
        message_type: str = "notification",
        metadata: Optional[Dict] = None
    ) -> str:
        """Send a message to another node via the message queue"""

        message_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages
            (message_id, from_node, to_node, message_type, priority, subject, body, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            self.node_id,
            to_node,
            message_type,
            priority,
            subject,
            message,
            json.dumps(metadata or {})
        ))

        conn.commit()
        conn.close()

        print(f"[HIVE] Message sent to {to_node}: {subject}")
        return message_id

    def execute_remote(
        self,
        node_id: str,
        command: str,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """Execute a command on a remote node"""

        # Get node info
        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"error": f"Node {node_id} not found in registry"}

        metadata = json.loads(row[0])
        node_ip = metadata.get("ip")

        if not node_ip:
            return {"error": f"No IP address for node {node_id}"}

        # Send command
        print(f"[HIVE] Executing on {node_id} ({node_ip}): {command}")
        response = send_command(node_ip, f"exec {command}", timeout=timeout)

        # Try to parse response
        try:
            if response.startswith("TOON|"):
                result = decode_toon(response)
            else:
                result = json.loads(response)
        except:
            result = {"raw_response": response}

        return result

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get status of all nodes in the cluster"""

        conn = sqlite3.connect(self.registry_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT node_id, node_name, role, hardware, capabilities, status, metadata
            FROM nodes
        """)

        nodes = []
        for row in cursor.fetchall():
            capabilities = row[4]
            metadata = row[6]
            nodes.append({
                "node_id": row[0],
                "node_name": row[1],
                "role": row[2],
                "hardware": row[3],
                "capabilities": json.loads(capabilities) if capabilities else [],
                "status": row[5],
                "metadata": json.loads(metadata) if metadata else {}
            })

        conn.close()

        return {
            "total_nodes": len(nodes),
            "orchestrator": self.node_id,
            "nodes": nodes,
            "timestamp": datetime.now().isoformat()
        }

    def query_shared_memory(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Query shared cluster memory"""

        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
        if not cursor.fetchone():
            conn.close()
            return []

        # Simple text search in observations
        cursor.execute("""
            SELECT name, entity_type, observations, node_id, created_at
            FROM entities
            WHERE observations LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (f"%{query}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "name": row[0],
                "type": row[1],
                "observations": json.loads(row[2]),
                "source_node": row[3],
                "created_at": row[4]
            })

        conn.close()

        return results

    def store_shared_memory(
        self,
        name: str,
        observations: Any,
        entity_type: str = "knowledge"
    ):
        """Store memory in shared cluster database"""

        conn = sqlite3.connect(self.shared_memory_db)
        cursor = conn.cursor()

        # Convert observations to JSON if needed
        if not isinstance(observations, str):
            obs_json = json.dumps(observations if isinstance(observations, list) else [observations])
        else:
            obs_json = json.dumps([observations])

        cursor.execute("""
            INSERT OR REPLACE INTO entities
            (name, entity_type, observations, node_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (name, entity_type, obs_json, self.node_id))

        conn.commit()
        conn.close()

        print(f"[HIVE] Stored shared memory: {name}")

    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages received by this node"""

        conn = sqlite3.connect(self.messages_db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, from_node, subject, body, message_type,
                   priority, received_at, action_taken
            FROM messages
            WHERE to_node = ?
            ORDER BY received_at DESC
            LIMIT ?
        """, (self.node_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                "message_id": row[0],
                "from": row[1],
                "subject": row[2],
                "body": row[3],
                "type": row[4],
                "priority": row[5],
                "received_at": row[6],
                "action_taken": bool(row[7])
            })

        conn.close()

        return messages

    def broadcast_message(
        self,
        message: str,
        subject: str = "Broadcast from orchestrator",
        priority: int = 7
    ) -> List[str]:
        """Send a message to all nodes in the cluster"""

        status = self.get_cluster_status()
        message_ids = []

        for node in status["nodes"]:
            if node["node_id"] != self.node_id:  # Don't send to self
                msg_id = self.send_message(
                    node["node_id"],
                    message,
                    subject=subject,
                    priority=priority,
                    message_type="broadcast"
                )
                message_ids.append(msg_id)

        return message_ids

    def __repr__(self):
        return f"<HiveMind orchestrator={self.node_id}>"


# Convenience instance for easy import
hive = HiveMind()


if __name__ == "__main__":
    # Demo usage
    print("Hive Mind Orchestrator Integration")
    print("=" * 60)

    hive = HiveMind()

    print("\nCluster Status:")
    status = hive.get_cluster_status()
    print(json.dumps(status, indent=2))

    print("\nRecent Messages:")
    messages = hive.get_recent_messages(5)
    for msg in messages:
        print(f"  [{msg['from']}] {msg['subject']}")

    print("\nShared Memories:")
    memories = hive.query_shared_memory("", limit=5)
    for mem in memories:
        print(f"  {mem['name']} ({mem['source_node']})")
