#!/usr/bin/env python3
"""
Cluster-Aware Memory Management

Extends enhanced-memory MCP with cluster capabilities:
- Node-specific (personal) memories
- Cluster-wide (shared) memories
- Cross-node memory queries
- Memory attribution by node
- Automatic sync to cluster

Now uses TOON format for 50% token reduction on memory serialization.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

# Add cluster-deployment to path for TOON imports
sys.path.insert(0, str(Path(__file__).parent))
from toon_serialization import encode_toon, decode_toon

logger = logging.getLogger("cluster-memory")

class ClusterMemoryManager:
    """Manages memories across the agentic cluster"""

    def __init__(self, node_config_path: Path):
        # Load node configuration
        with open(node_config_path) as f:
            self.config = json.load(f)

        self.node_id = self.config['node_id']

        # Database paths
        self.local_db = Path(self.config['memory']['local_db'])
        self.personal_db = Path(self.config['memory']['personal_db'])
        self.shared_db = Path(self.config['memory']['shared_db'])

        # Ensure directories exist
        self.personal_db.parent.mkdir(parents=True, exist_ok=True)
        self.shared_db.parent.mkdir(parents=True, exist_ok=True)

        # Initialize databases
        self.init_personal_db()
        self.init_shared_db()

        logger.info(f"Cluster memory manager initialized for node: {self.node_id}")

    def init_personal_db(self):
        """Initialize node's personal memory database"""
        if self.personal_db.exists():
            return  # Already initialized

        conn = sqlite3.connect(self.personal_db)
        cursor = conn.cursor()

        # Same schema as enhanced_memories.db but for personal use
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                node_id TEXT NOT NULL,
                FOREIGN KEY(from_entity) REFERENCES entities(name),
                FOREIGN KEY(to_entity) REFERENCES entities(name),
                UNIQUE(from_entity, to_entity, relation_type)
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Personal memory database initialized at {self.personal_db}")

    def init_shared_db(self):
        """Initialize cluster-wide shared memory database"""
        if self.shared_db.exists():
            return  # Already initialized

        conn = sqlite3.connect(self.shared_db)
        cursor = conn.cursor()

        # Shared entities with node attribution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                name TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                observations TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_node TEXT NOT NULL,
                updated_by_node TEXT NOT NULL
            )
        """)

        # Shared relations with node attribution
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_entity TEXT NOT NULL,
                to_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_node TEXT NOT NULL,
                FOREIGN KEY(from_entity) REFERENCES entities(name),
                FOREIGN KEY(to_entity) REFERENCES entities(name),
                UNIQUE(from_entity, to_entity, relation_type)
            )
        """)

        # Memory sync tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                source_node TEXT NOT NULL,
                target_node TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

        conn.commit()
        conn.close()

        logger.info(f"Shared memory database initialized at {self.shared_db}")

    def create_entity(self, name: str, entity_type: str, observations: List[str], scope: str = "personal", use_toon: bool = True) -> bool:
        """
        Create entity in appropriate scope

        Args:
            scope: "personal" (node-specific) or "shared" (cluster-wide)
            use_toon: Use TOON encoding (50% token reduction) vs JSON
        """
        db_path = self.personal_db if scope == "personal" else self.shared_db

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Use TOON encoding for 50% token reduction
            if use_toon:
                observations_serialized = encode_toon(observations)
            else:
                observations_serialized = json.dumps(observations)

            if scope == "personal":
                cursor.execute("""
                    INSERT OR REPLACE INTO entities (name, entity_type, observations, node_id, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (name, entity_type, observations_serialized, self.node_id))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO entities (name, entity_type, observations, created_by_node, updated_by_node, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (name, entity_type, observations_serialized, self.node_id, self.node_id))

            conn.commit()
            conn.close()

            logger.info(f"Created {scope} entity: {name} ({entity_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to create entity: {e}")
            return False

    def search_entities(self, query: str, scope: str = "all", node_filter: Optional[str] = None) -> List[Dict]:
        """
        Search entities across specified scope

        Args:
            scope: "personal", "shared", or "all"
            node_filter: Filter by specific node (only applies to shared scope)
        """
        results = []

        # Search personal memories
        if scope in ["personal", "all"]:
            results.extend(self._search_db(self.personal_db, query, is_shared=False))

        # Search shared memories
        if scope in ["shared", "all"]:
            shared_results = self._search_db(self.shared_db, query, is_shared=True)

            # Apply node filter if specified
            if node_filter:
                shared_results = [r for r in shared_results if r.get('created_by_node') == node_filter]

            results.extend(shared_results)

        return results

    def _search_db(self, db_path: Path, query: str, is_shared: bool) -> List[Dict]:
        """Search a specific database"""
        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if is_shared:
                cursor.execute("""
                    SELECT name, entity_type, observations, created_by_node, updated_by_node, updated_at
                    FROM entities
                    WHERE name LIKE ? OR entity_type LIKE ? OR observations LIKE ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%"))

                results = []
                for row in cursor.fetchall():
                    # Try TOON decode first, fallback to JSON
                    try:
                        observations = decode_toon(row[2])
                    except (ValueError, json.JSONDecodeError):
                        observations = json.loads(row[2])

                    results.append({
                        'name': row[0],
                        'entity_type': row[1],
                        'observations': observations,
                        'created_by_node': row[3],
                        'updated_by_node': row[4],
                        'updated_at': row[5],
                        'scope': 'shared'
                    })
            else:
                cursor.execute("""
                    SELECT name, entity_type, observations, node_id, updated_at
                    FROM entities
                    WHERE name LIKE ? OR entity_type LIKE ? OR observations LIKE ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%"))

                results = []
                for row in cursor.fetchall():
                    # Try TOON decode first, fallback to JSON
                    try:
                        observations = decode_toon(row[2])
                    except (ValueError, json.JSONDecodeError):
                        observations = json.loads(row[2])

                    results.append({
                        'name': row[0],
                        'entity_type': row[1],
                        'observations': observations,
                        'node_id': row[3],
                        'updated_at': row[4],
                        'scope': 'personal'
                    })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def sync_to_cluster(self, entity_name: str) -> bool:
        """Promote a personal memory to cluster-wide shared memory"""
        try:
            # Get entity from personal db
            conn_personal = sqlite3.connect(self.personal_db)
            cursor = conn_personal.cursor()

            cursor.execute("""
                SELECT name, entity_type, observations
                FROM entities
                WHERE name = ?
            """, (entity_name,))

            row = cursor.fetchone()
            conn_personal.close()

            if not row:
                logger.warning(f"Entity not found in personal memory: {entity_name}")
                return False

            name, entity_type, observations = row

            # Create in shared db
            conn_shared = sqlite3.connect(self.shared_db)
            cursor = conn_shared.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO entities (name, entity_type, observations, created_by_node, updated_by_node)
                VALUES (?, ?, ?, ?, ?)
            """, (name, entity_type, observations, self.node_id, self.node_id))

            # Log sync
            cursor.execute("""
                INSERT INTO sync_log (entity_name, operation, source_node, status)
                VALUES (?, 'sync', ?, 'completed')
            """, (entity_name, self.node_id))

            conn_shared.commit()
            conn_shared.close()

            logger.info(f"Synced entity to cluster: {entity_name}")
            return True

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False

    def get_node_memories(self, node_id: str) -> List[Dict]:
        """Get all shared memories created by a specific node"""
        try:
            conn = sqlite3.connect(self.shared_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name, entity_type, observations, created_by_node, updated_at
                FROM entities
                WHERE created_by_node = ?
                ORDER BY updated_at DESC
            """, (node_id,))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'name': row[0],
                    'entity_type': row[1],
                    'observations': json.loads(row[2]),
                    'created_by_node': row[3],
                    'updated_at': row[4],
                    'scope': 'shared'
                })

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Failed to get node memories: {e}")
            return []

    def get_cluster_stats(self) -> Dict:
        """Get cluster memory statistics"""
        stats = {
            'node_id': self.node_id,
            'personal': self._get_db_stats(self.personal_db),
            'shared': self._get_db_stats(self.shared_db),
            'timestamp': datetime.now().isoformat()
        }

        return stats

    def _get_db_stats(self, db_path: Path) -> Dict:
        """Get statistics for a database"""
        if not db_path.exists():
            return {'entities': 0, 'relations': 0}

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM entities")
            entity_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM relations")
            relation_count = cursor.fetchone()[0]

            conn.close()

            return {
                'entities': entity_count,
                'relations': relation_count
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'entities': 0, 'relations': 0}

# Example usage
if __name__ == "__main__":
    import sys

    node_config = Path.home() / ".claude" / "node-config.json"

    if not node_config.exists():
        print("Error: Node configuration not found")
        sys.exit(1)

    manager = ClusterMemoryManager(node_config)

    # Demo: Create personal memory
    manager.create_entity(
        name="test-research-project",
        entity_type="project",
        observations=["Research on agentic systems", "Started Nov 2025"],
        scope="personal"
    )

    # Demo: Create shared memory
    manager.create_entity(
        name="cluster-architecture",
        entity_type="knowledge",
        observations=["Distributed multi-agent system", "Node-based personas"],
        scope="shared"
    )

    # Demo: Search
    results = manager.search_entities("research", scope="all")
    print(f"\nSearch results: {len(results)} matches")
    for r in results:
        print(f"  - {r['name']} ({r['scope']})")

    # Demo: Stats
    stats = manager.get_cluster_stats()
    print(f"\nCluster stats:")
    print(f"  Personal: {stats['personal']['entities']} entities")
    print(f"  Shared: {stats['shared']['entities']} entities")
