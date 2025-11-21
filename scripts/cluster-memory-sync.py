#!/usr/bin/env python3
"""
Cluster Memory Synchronization
Syncs memories between nodes in the agentic cluster

Features:
- Push high-value memories to cluster shared database
- Pull shared memories from other nodes
- Intelligent sync scoring based on access patterns and SAFLA metrics
- SAFLA-aware synchronization
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.claude' / 'cluster-memory-sync.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cluster-memory-sync')


class ClusterMemorySync:
    """Synchronize memories between nodes in the agentic cluster"""

    def __init__(self):
        """Initialize sync with node configuration"""
        self.node_config = self._load_node_config()
        self.node_id = self.node_config.get('node_id', 'unknown')
        self.local_db_path = self._get_local_db_path()
        self.cluster_db_path = self._get_cluster_db_path()

        logger.info(f"🔄 Cluster Memory Sync initialized for node: {self.node_id}")
        logger.info(f"📂 Local DB: {self.local_db_path}")
        logger.info(f"🌐 Cluster DB: {self.cluster_db_path}")

        self._ensure_cluster_schema()

    def _load_node_config(self) -> Dict[str, Any]:
        """Load node configuration"""
        config_path = Path.home() / '.claude' / 'node-config.json'
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def _get_local_db_path(self) -> Path:
        """Get path to local enhanced-memory database"""
        # Use the actual enhanced-memory MCP database location
        # This is where Claude's active memories are stored
        mcp_db_path = Path.home() / '.claude' / 'enhanced_memories' / 'memory.db'
        if mcp_db_path.exists():
            return mcp_db_path

        # Try node config as fallback
        if 'memory' in self.node_config and 'local_db' in self.node_config['memory']:
            db_path = Path(self.node_config['memory']['local_db'])
            if db_path.exists():
                return db_path

        # Final fallback detection
        if Path('/Volumes/SSDRAID0/agentic-system').exists():
            return Path('/Volumes/SSDRAID0/agentic-system/databases/mcp/enhanced_memories.db')
        else:
            return Path.home() / 'agentic-system' / 'databases' / 'cluster' / 'nodes' / self.node_id / 'enhanced_memories.db'

    def _get_cluster_db_path(self) -> Path:
        """Get path to cluster shared database"""
        # Try node config first
        if 'memory' in self.node_config and 'cluster_db' in self.node_config['memory']:
            return Path(self.node_config['memory']['cluster_db'])

        # Fallback to orchestrator location
        if Path('/Volumes/SSDRAID0/agentic-system').exists():
            return Path('/Volumes/SSDRAID0/agentic-system/databases/cluster/shared_memories.db')
        else:
            # Mobile node - can't access cluster DB directly
            logger.warning("⚠️ Cluster database not accessible from mobile node")
            return Path('/tmp/cluster_memories.db')  # Placeholder

    def _ensure_cluster_schema(self):
        """Ensure cluster database has proper schema"""
        if not self.cluster_db_path.parent.exists():
            self.cluster_db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.cluster_db_path))
        cursor = conn.cursor()

        # Shared entities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                tier TEXT DEFAULT 'working',
                compressed_data BLOB,
                original_size INTEGER,
                compressed_size INTEGER,
                compression_ratio REAL,
                checksum TEXT,
                source_node TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                sync_score REAL DEFAULT 0.0,
                UNIQUE(name, source_node)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                source_node TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES shared_entities(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id TEXT NOT NULL,
                last_push TEXT,
                last_pull TEXT,
                entities_pushed INTEGER DEFAULT 0,
                entities_pulled INTEGER DEFAULT 0,
                last_sync_score REAL DEFAULT 0.0
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_entities_score ON shared_entities(sync_score DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_entities_node ON shared_entities(source_node)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shared_observations_entity ON shared_observations(entity_id)')

        conn.commit()
        conn.close()

        logger.info("✅ Cluster database schema verified")

    def calculate_sync_score(self, entity: Dict[str, Any]) -> float:
        """Calculate sync score for an entity (0-100)"""
        score = 0.0

        # Access count (40 points)
        access_count = entity.get('access_count', 0)
        if access_count > 0:
            score += min(40, access_count * 2)

        # Tier (30 points)
        tier_scores = {
            'procedural': 30,
            'semantic': 20,
            'episodic': 10,
            'working': 0
        }
        tier = entity.get('tier', 'working')
        score += tier_scores.get(tier, 0)

        # Entity type (20 points)
        entity_type = entity.get('entity_type', 'unknown')
        if 'tool_usage' in entity_type:
            score += 20
        elif 'pattern' in entity_type:
            score += 15
        elif 'insight' in entity_type:
            score += 10
        else:
            score += 5

        # Recency (10 points)
        last_accessed = entity.get('last_accessed')
        if last_accessed:
            try:
                last_access_time = datetime.fromisoformat(last_accessed)
                days_ago = (datetime.now() - last_access_time).days
                if days_ago == 0:
                    score += 10
                elif days_ago <= 7:
                    score += 7
                elif days_ago <= 30:
                    score += 5
                elif days_ago <= 90:
                    score += 2
            except:
                pass

        return min(100.0, score)

    def push_to_cluster(self, min_score: float = 50.0, limit: int = 100) -> Dict[str, Any]:
        """Push high-value memories to cluster"""
        logger.info(f"🚀 Pushing memories to cluster (min_score={min_score}, limit={limit})")

        local_conn = sqlite3.connect(str(self.local_db_path))
        local_cursor = local_conn.cursor()

        cluster_conn = sqlite3.connect(str(self.cluster_db_path))
        cluster_cursor = cluster_conn.cursor()

        stats = {'pushed': 0, 'skipped': 0, 'updated': 0, 'errors': 0}

        local_cursor.execute('''
            SELECT id, name, entity_type, tier, compressed_data,
                   original_size, compressed_size, compression_ratio,
                   checksum, access_count, last_accessed
            FROM entities
            ORDER BY access_count DESC, last_accessed DESC
            LIMIT ?
        ''', (limit * 2,))

        for row in local_cursor.fetchall():
            entity_id, name, entity_type, tier, compressed_data, \
                original_size, compressed_size, compression_ratio, \
                checksum, access_count, last_accessed = row

            entity = {
                'name': name,
                'entity_type': entity_type,
                'tier': tier,
                'access_count': access_count,
                'last_accessed': last_accessed
            }

            sync_score = self.calculate_sync_score(entity)

            if sync_score < min_score:
                stats['skipped'] += 1
                continue

            try:
                cluster_cursor.execute('''
                    SELECT id, access_count FROM shared_entities
                    WHERE name = ? AND source_node = ?
                ''', (name, self.node_id))

                existing = cluster_cursor.fetchone()

                if existing:
                    existing_id, existing_count = existing
                    cluster_cursor.execute('''
                        UPDATE shared_entities
                        SET compressed_data = ?, original_size = ?, compressed_size = ?,
                            compression_ratio = ?, checksum = ?, access_count = ?,
                            sync_score = ?, last_modified = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (compressed_data, original_size, compressed_size, compression_ratio,
                          checksum, access_count, sync_score, existing_id))
                    stats['updated'] += 1
                else:
                    cluster_cursor.execute('''
                        INSERT INTO shared_entities
                        (name, entity_type, tier, compressed_data, original_size,
                         compressed_size, compression_ratio, checksum, source_node,
                         access_count, sync_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, entity_type, tier, compressed_data, original_size,
                          compressed_size, compression_ratio, checksum, self.node_id,
                          access_count, sync_score))
                    stats['pushed'] += 1

                if stats['pushed'] + stats['updated'] >= limit:
                    break

            except Exception as e:
                logger.error(f"❌ Error pushing entity {name}: {e}")
                stats['errors'] += 1

        cluster_cursor.execute('''
            INSERT OR REPLACE INTO sync_metadata
            (node_id, last_push, entities_pushed, last_sync_score)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
        ''', (self.node_id, stats['pushed'] + stats['updated'], min_score))

        cluster_conn.commit()
        cluster_conn.close()
        local_conn.close()

        logger.info(f"✅ Push complete: {stats}")
        return stats

    def pull_from_cluster(self, min_score: float = 60.0, limit: int = 50) -> Dict[str, Any]:
        """Pull shared memories from cluster"""
        logger.info(f"⬇️ Pulling memories from cluster (min_score={min_score}, limit={limit})")

        local_conn = sqlite3.connect(str(self.local_db_path))
        local_cursor = local_conn.cursor()

        cluster_conn = sqlite3.connect(str(self.cluster_db_path))
        cluster_cursor = cluster_conn.cursor()

        stats = {'pulled': 0, 'skipped': 0, 'errors': 0}

        cluster_cursor.execute('''
            SELECT name, entity_type, tier, compressed_data, original_size,
                   compressed_size, compression_ratio, checksum, source_node,
                   access_count, sync_score
            FROM shared_entities
            WHERE source_node != ? AND sync_score >= ?
            ORDER BY sync_score DESC
            LIMIT ?
        ''', (self.node_id, min_score, limit))

        for row in cluster_cursor.fetchall():
            name, entity_type, tier, compressed_data, original_size, \
                compressed_size, compression_ratio, checksum, source_node, \
                access_count, sync_score = row

            try:
                local_cursor.execute('SELECT id FROM entities WHERE name = ?', (name,))
                if local_cursor.fetchone():
                    stats['skipped'] += 1
                    continue

                local_cursor.execute('''
                    INSERT INTO entities
                    (name, entity_type, tier, compressed_data, original_size,
                     compressed_size, compression_ratio, checksum, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (name, entity_type, tier, compressed_data, original_size,
                      compressed_size, compression_ratio, checksum))

                local_entity_id = local_cursor.lastrowid

                observation = json.dumps({
                    'source': 'cluster_sync',
                    'original_node': source_node,
                    'sync_score': sync_score,
                    'pulled_at': datetime.now().isoformat()
                })

                local_cursor.execute('''
                    INSERT INTO observations (entity_id, content)
                    VALUES (?, ?)
                ''', (local_entity_id, observation))

                stats['pulled'] += 1

            except Exception as e:
                logger.error(f"❌ Error pulling entity {name}: {e}")
                stats['errors'] += 1

        local_conn.commit()
        local_conn.close()
        cluster_conn.close()

        logger.info(f"✅ Pull complete: {stats}")
        return stats

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        cluster_conn = sqlite3.connect(str(self.cluster_db_path))
        cluster_cursor = cluster_conn.cursor()

        cluster_cursor.execute('''
            SELECT last_push, last_pull, entities_pushed, entities_pulled, last_sync_score
            FROM sync_metadata WHERE node_id = ?
        ''', (self.node_id,))

        row = cluster_cursor.fetchone()

        if row:
            last_push, last_pull, entities_pushed, entities_pulled, last_sync_score = row
        else:
            last_push = last_pull = None
            entities_pushed = entities_pulled = last_sync_score = 0

        cluster_cursor.execute('SELECT COUNT(*) FROM shared_entities')
        total_cluster_entities = cluster_cursor.fetchone()[0]

        cluster_cursor.execute('SELECT COUNT(*) FROM shared_entities WHERE source_node = ?', (self.node_id,))
        my_contributions = cluster_cursor.fetchone()[0]

        cluster_conn.close()

        return {
            'node_id': self.node_id,
            'last_push': last_push,
            'last_pull': last_pull,
            'entities_pushed': entities_pushed,
            'entities_pulled': entities_pulled,
            'last_sync_score': last_sync_score,
            'total_cluster_entities': total_cluster_entities,
            'my_contributions': my_contributions
        }


def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Cluster Memory Synchronization')
    parser.add_argument('action', choices=['push', 'pull', 'status', 'sync'],
                      help='Action to perform')
    parser.add_argument('--min-score', type=float, default=50.0,
                      help='Minimum sync score (default: 50)')
    parser.add_argument('--limit', type=int, default=100,
                      help='Maximum entities (default: 100)')

    args = parser.parse_args()

    sync = ClusterMemorySync()

    if args.action == 'push':
        stats = sync.push_to_cluster(min_score=args.min_score, limit=args.limit)
        print(json.dumps(stats, indent=2))

    elif args.action == 'pull':
        stats = sync.pull_from_cluster(min_score=args.min_score, limit=args.limit)
        print(json.dumps(stats, indent=2))

    elif args.action == 'status':
        status = sync.get_sync_status()
        print(json.dumps(status, indent=2))

    elif args.action == 'sync':
        print("🔄 Starting bidirectional sync...")
        push_stats = sync.push_to_cluster(min_score=args.min_score, limit=args.limit)
        print(f"📤 Push: {push_stats}")

        pull_stats = sync.pull_from_cluster(min_score=args.min_score + 10, limit=args.limit // 2)
        print(f"📥 Pull: {pull_stats}")

        status = sync.get_sync_status()
        print(f"📊 Status: {status}")


if __name__ == '__main__':
    main()
