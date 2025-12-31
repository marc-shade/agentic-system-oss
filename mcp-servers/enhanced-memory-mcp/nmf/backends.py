"""
Backend initialization for Neural Memory Fabric.

Handles initialization of:
- SQLite database
- Qdrant vector database
- Neo4j graph database
- Redis cache
- Filesystem storage

Extracted from neural_memory_fabric.py for modularity.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import MemoryTier, logger


async def init_sqlite(sqlite_path: Path) -> sqlite3.Connection:
    """
    Initialize SQLite database with NMF schema.

    Args:
        sqlite_path: Path to SQLite database file

    Returns:
        SQLite connection
    """
    conn = sqlite3.connect(
        sqlite_path,
        check_same_thread=False
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    cursor = conn.cursor()

    # Enhanced entities table with NMF fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nmf_entities (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_until TEXT,
            keywords JSON NOT NULL,
            tags JSON NOT NULL,
            context_description TEXT,
            importance_score REAL DEFAULT 0.5,
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            tier TEXT DEFAULT 'working',
            agent_id TEXT,
            version INTEGER DEFAULT 1,
            checksum TEXT,
            metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Memory links table (for A-MEM style connections)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nmf_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_memory_id TEXT NOT NULL,
            to_memory_id TEXT NOT NULL,
            link_type TEXT DEFAULT 'relates_to',
            link_score REAL DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_memory_id) REFERENCES nmf_entities(id),
            FOREIGN KEY (to_memory_id) REFERENCES nmf_entities(id),
            UNIQUE(from_memory_id, to_memory_id)
        )
    ''')

    # Memory blocks table (Letta-style)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nmf_memory_blocks (
            block_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            block_name TEXT NOT NULL,
            block_value TEXT NOT NULL,
            size_limit INTEGER,
            persistence TEXT DEFAULT 'session',
            last_updated TEXT,
            version INTEGER DEFAULT 1,
            UNIQUE(agent_id, block_name)
        )
    ''')

    # Access log for analytics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nmf_access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL,
            agent_id TEXT,
            access_type TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (memory_id) REFERENCES nmf_entities(id)
        )
    ''')

    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_entities_agent ON nmf_entities(agent_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_entities_tier ON nmf_entities(tier)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_entities_timestamp ON nmf_entities(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_entities_importance ON nmf_entities(importance_score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_links_from ON nmf_links(from_memory_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_nmf_links_to ON nmf_links(to_memory_id)')

    conn.commit()
    logger.info("SQLite initialized")

    return conn


async def init_vector_db(config: Dict) -> tuple:
    """
    Initialize Qdrant vector database.

    Args:
        config: Configuration dictionary with 'storage.vector' settings

    Returns:
        Tuple of (QdrantClient or None, collection_name or None)
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        vector_config = config['storage']['vector']
        backend = vector_config.get('backend', 'qdrant')

        if backend != 'qdrant':
            logger.warning(f"Unknown vector backend: {backend}")
            return None, None

        # Connect to Qdrant
        vector_db = QdrantClient(
            host=vector_config.get('host', 'localhost'),
            port=vector_config.get('port', 6333),
            prefer_grpc=vector_config.get('prefer_grpc', False),
            https=vector_config.get('https', False)
        )

        # Get or create collection
        collection_name = vector_config.get('collection', 'enhanced_memory')
        collections = vector_db.get_collections().collections
        collection_exists = any(c.name == collection_name for c in collections)

        # Also check if it's an alias (check global aliases)
        if not collection_exists:
            try:
                all_aliases = vector_db.get_aliases().aliases
                collection_exists = any(a.alias_name == collection_name for a in all_aliases)
            except:
                pass  # API failed, proceed assuming it doesn't exist

        if not collection_exists:
            # Map distance metric
            distance_map = {
                'Cosine': Distance.COSINE,
                'Euclidean': Distance.EUCLID,
                'Dot': Distance.DOT
            }
            distance = distance_map.get(
                vector_config.get('distance_metric', 'Cosine'),
                Distance.COSINE
            )

            vector_db.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_config.get('vector_size', 768),
                    distance=distance
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

        logger.info(f"Qdrant vector DB initialized: {collection_name}")
        return vector_db, collection_name

    except ImportError:
        logger.warning("qdrant-client not installed - vector search disabled")
        return None, None
    except Exception as e:
        logger.warning(f"Qdrant initialization failed: {e} - vector search disabled")
        return None, None


async def init_graph_db(config: Dict):
    """
    Initialize Neo4j graph database.

    Args:
        config: Configuration dictionary with 'storage.graph' settings

    Returns:
        Neo4j driver or None
    """
    try:
        from neo4j import GraphDatabase

        graph_config = config['storage']['graph']
        graph_driver = GraphDatabase.driver(
            graph_config['uri'],
            auth=(graph_config['username'], graph_config['password'])
        )

        # Test connection
        with graph_driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()

        logger.info("Neo4j graph DB initialized")
        return graph_driver

    except ImportError:
        logger.warning("neo4j driver not installed - graph features disabled")
        return None
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e} - graph features disabled")
        return None


async def init_redis(config: Dict):
    """
    Initialize Redis cache.

    Args:
        config: Configuration dictionary with 'storage.cache' settings

    Returns:
        Redis client or None
    """
    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(
            config['storage']['cache']['url'],
            decode_responses=True
        )

        # Test connection
        await redis_client.ping()

        logger.info("Redis cache initialized")
        return redis_client

    except ImportError:
        logger.warning("redis not installed - caching disabled")
        return None
    except Exception as e:
        logger.warning(f"Redis connection failed: {e} - caching disabled")
        return None


async def store_to_filesystem(
    memory_id: str,
    content: str,
    timestamp: str,
    agent_id: str,
    tags: List[str],
    embedding: Optional[List[float]] = None
) -> bool:
    """
    Store memory to filesystem for backup/persistence (Phase 4).

    Uses JSON-Lines format for append-only storage.
    Enables disaster recovery and cross-system memory sharing.

    Args:
        memory_id: Unique memory identifier
        content: Memory content
        timestamp: ISO timestamp
        agent_id: Agent that created the memory
        tags: Memory tags
        embedding: Optional embedding vector (stored separately)

    Returns:
        True if stored successfully, False otherwise
    """
    try:
        # Define storage paths
        base_dir = Path.home() / ".claude" / "nmf_storage"
        memories_dir = base_dir / "memories"
        embeddings_dir = base_dir / "embeddings"

        # Ensure directories exist
        memories_dir.mkdir(parents=True, exist_ok=True)
        embeddings_dir.mkdir(parents=True, exist_ok=True)

        # Store memory as JSON-Lines (append-only)
        memory_file = memories_dir / f"{agent_id}_memories.jsonl"
        memory_record = {
            'id': memory_id,
            'content': content,
            'timestamp': timestamp,
            'agent_id': agent_id,
            'tags': tags,
            'stored_at': datetime.utcnow().isoformat()
        }

        with open(memory_file, 'a') as f:
            f.write(json.dumps(memory_record) + '\n')

        # Store embedding separately (if available) to enable vector reconstruction
        if embedding:
            embedding_file = embeddings_dir / f"{memory_id}.json"
            with open(embedding_file, 'w') as f:
                json.dump({
                    'memory_id': memory_id,
                    'embedding': embedding,
                    'dimensions': len(embedding)
                }, f)

        logger.debug(f"Stored memory {memory_id} to filesystem")
        return True

    except Exception as e:
        logger.warning(f"Filesystem storage failed for {memory_id}: {e}")
        return False


__all__ = [
    'init_sqlite',
    'init_vector_db',
    'init_graph_db',
    'init_redis',
    'store_to_filesystem',
]
