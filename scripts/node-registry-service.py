#!/usr/bin/env python3
"""
Agentic Cluster Node Registry Service

Tracks all active nodes in the cluster, handles discovery, and maintains
cluster-wide state. This service runs on the primary node (Mac Studio).

Features:
- Node discovery via Bonjour/mDNS
- Heartbeat monitoring
- Health checking
- Node capability tracking
- Persona management
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import socket
import logging

# Configuration
CLUSTER_DB_PATH = Path("/mnt/agentic-system/databases/cluster")
NODE_REGISTRY_DB = CLUSTER_DB_PATH / "node_registry.db"
NODES_DIR = CLUSTER_DB_PATH / "nodes"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("node-registry")

class NodeRegistry:
    """Manages cluster node registration and health"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize node registry database"""
        CLUSTER_DB_PATH.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                ip_address TEXT,
                persona_name TEXT NOT NULL,
                persona_id TEXT NOT NULL,
                specialty TEXT,
                status TEXT DEFAULT 'active',
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                capabilities TEXT,
                persona_config TEXT,
                UNIQUE(hostname)
            )
        """)

        # Node health table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_health (
                node_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                health_status TEXT,
                memory_usage INTEGER,
                cpu_usage INTEGER,
                active_tasks INTEGER,
                FOREIGN KEY(node_id) REFERENCES nodes(node_id)
            )
        """)

        # Node capabilities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_capabilities (
                node_id TEXT,
                capability TEXT,
                version TEXT,
                status TEXT DEFAULT 'enabled',
                FOREIGN KEY(node_id) REFERENCES nodes(node_id),
                PRIMARY KEY(node_id, capability)
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Node registry database initialized at {self.db_path}")

    def register_node(self, node_info: Dict) -> bool:
        """Register or update a node in the cluster"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Load persona config if provided
            persona_name = node_info.get('persona', {}).get('name', 'Unknown')
            persona_id = node_info.get('persona', {}).get('persona_id', 'unknown')
            specialty = node_info.get('persona', {}).get('specialty', '')

            # Upsert node
            cursor.execute("""
                INSERT INTO nodes (
                    node_id, hostname, ip_address, persona_name,
                    persona_id, specialty, capabilities, persona_config
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    hostname=excluded.hostname,
                    ip_address=excluded.ip_address,
                    persona_name=excluded.persona_name,
                    persona_id=excluded.persona_id,
                    specialty=excluded.specialty,
                    last_heartbeat=CURRENT_TIMESTAMP,
                    status='active',
                    capabilities=excluded.capabilities,
                    persona_config=excluded.persona_config
            """, (
                node_info['node_id'],
                node_info.get('hostname', ''),
                node_info.get('ip_address', ''),
                persona_name,
                persona_id,
                specialty,
                json.dumps(node_info.get('capabilities', [])),
                json.dumps(node_info.get('persona', {}))
            ))

            # Update capabilities
            if 'capabilities' in node_info:
                for cap in node_info['capabilities']:
                    cursor.execute("""
                        INSERT OR REPLACE INTO node_capabilities
                        (node_id, capability, version, status)
                        VALUES (?, ?, ?, 'enabled')
                    """, (node_info['node_id'], cap, 'latest'))

            conn.commit()
            conn.close()

            logger.info(f"Node registered: {node_info['node_id']} ({persona_name})")
            return True

        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            return False

    def heartbeat(self, node_id: str) -> bool:
        """Update node heartbeat timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE nodes
                SET last_heartbeat = CURRENT_TIMESTAMP,
                    status = 'active'
                WHERE node_id = ?
            """, (node_id,))

            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(f"Heartbeat failed for {node_id}: {e}")
            return False

    def get_active_nodes(self, max_age_seconds: int = 60) -> List[Dict]:
        """Get all active nodes (heartbeat within max_age_seconds)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            threshold = datetime.now() - timedelta(seconds=max_age_seconds)

            cursor.execute("""
                SELECT
                    node_id, hostname, ip_address, persona_name,
                    persona_id, specialty, status, last_heartbeat,
                    capabilities, persona_config
                FROM nodes
                WHERE datetime(last_heartbeat) >= ?
                ORDER BY persona_id, node_id
            """, (threshold.isoformat(),))

            nodes = []
            for row in cursor.fetchall():
                nodes.append({
                    'node_id': row[0],
                    'hostname': row[1],
                    'ip_address': row[2],
                    'persona_name': row[3],
                    'persona_id': row[4],
                    'specialty': row[5],
                    'status': row[6],
                    'last_heartbeat': row[7],
                    'capabilities': json.loads(row[8] or '[]'),
                    'persona': json.loads(row[9] or '{}')
                })

            conn.close()
            return nodes

        except Exception as e:
            logger.error(f"Failed to get active nodes: {e}")
            return []

    def mark_inactive_nodes(self, max_age_seconds: int = 120):
        """Mark nodes as inactive if no heartbeat received"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            threshold = datetime.now() - timedelta(seconds=max_age_seconds)

            cursor.execute("""
                UPDATE nodes
                SET status = 'inactive'
                WHERE datetime(last_heartbeat) < ?
                AND status = 'active'
            """, (threshold.isoformat(),))

            affected = cursor.rowcount
            conn.commit()
            conn.close()

            if affected > 0:
                logger.warning(f"Marked {affected} nodes as inactive")

        except Exception as e:
            logger.error(f"Failed to mark inactive nodes: {e}")

    def get_node_by_persona(self, persona_id: str) -> Optional[Dict]:
        """Find a node by its persona ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    node_id, hostname, ip_address, persona_name,
                    persona_id, specialty, status, last_heartbeat,
                    capabilities, persona_config
                FROM nodes
                WHERE persona_id = ?
                AND status = 'active'
                ORDER BY last_heartbeat DESC
                LIMIT 1
            """, (persona_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'node_id': row[0],
                    'hostname': row[1],
                    'ip_address': row[2],
                    'persona_name': row[3],
                    'persona_id': row[4],
                    'specialty': row[5],
                    'status': row[6],
                    'last_heartbeat': row[7],
                    'capabilities': json.loads(row[8] or '[]'),
                    'persona': json.loads(row[9] or '{}')
                }
            return None

        except Exception as e:
            logger.error(f"Failed to find node by persona: {e}")
            return None

    def get_cluster_status(self) -> Dict:
        """Get overall cluster status"""
        active_nodes = self.get_active_nodes()

        personas = {}
        for node in active_nodes:
            persona_id = node['persona_id']
            if persona_id not in personas:
                personas[persona_id] = []
            personas[persona_id].append(node['node_id'])

        return {
            'total_nodes': len(active_nodes),
            'active_nodes': active_nodes,
            'personas': personas,
            'timestamp': datetime.now().isoformat()
        }

def auto_register_self():
    """Automatically register this node using its configuration"""
    try:
        # Load node configuration
        node_config_path = Path.home() / ".claude" / "node-config.json"
        if not node_config_path.exists():
            logger.warning("Node configuration not found, skipping auto-registration")
            return False

        with open(node_config_path) as f:
            node_config = json.load(f)

        # Load persona state
        persona_config_path = Path(node_config['persona_config'])
        with open(persona_config_path) as f:
            persona_state = json.load(f)

        # Get IP address
        hostname = socket.gethostname()
        try:
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = "127.0.0.1"

        # Create node info
        node_info = {
            'node_id': persona_state['node_id'],
            'hostname': hostname,
            'ip_address': ip_address,
            'persona': persona_state['persona'],
            'capabilities': persona_state['capabilities']
        }

        # Register
        registry = NodeRegistry(NODE_REGISTRY_DB)
        success = registry.register_node(node_info)

        if success:
            logger.info(f"Auto-registered node: {node_info['node_id']}")

        return success

    except Exception as e:
        logger.error(f"Auto-registration failed: {e}")
        return False

# CLI Interface
if __name__ == "__main__":
    import sys

    registry = NodeRegistry(NODE_REGISTRY_DB)

    if len(sys.argv) < 2:
        print("Usage: node-registry-service.py [command]")
        print("Commands:")
        print("  register      - Auto-register this node")
        print("  list          - List all active nodes")
        print("  status        - Show cluster status")
        print("  heartbeat     - Send heartbeat for this node")
        print("  cleanup       - Mark inactive nodes")
        sys.exit(1)

    command = sys.argv[1]

    if command == "register":
        success = auto_register_self()
        sys.exit(0 if success else 1)

    elif command == "list":
        nodes = registry.get_active_nodes()
        print(f"\nActive Nodes: {len(nodes)}")
        print("-" * 80)
        for node in nodes:
            print(f"{node['node_id']:15} | {node['persona_name']:15} | {node['status']:10} | {node['last_heartbeat']}")

    elif command == "status":
        status = registry.get_cluster_status()
        print(json.dumps(status, indent=2))

    elif command == "heartbeat":
        # Load node config to get node_id
        node_config_path = Path.home() / ".claude" / "node-config.json"
        with open(node_config_path) as f:
            node_config = json.load(f)

        success = registry.heartbeat(node_config['node_id'])
        sys.exit(0 if success else 1)

    elif command == "cleanup":
        registry.mark_inactive_nodes()
        print("Cleanup complete")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
