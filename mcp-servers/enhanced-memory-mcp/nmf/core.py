"""
Core NeuralMemoryFabric class for Neural Memory Fabric.

The main orchestrator that manages multi-backend storage and
intelligent retrieval for agentic memory.

Extracted from neural_memory_fabric.py for modularity.
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import MemoryTier, RetrievalMode, load_config, logger
from .backends import (
    init_sqlite,
    init_vector_db,
    init_graph_db,
    init_redis,
    store_to_filesystem,
)
from .intelligence import (
    extract_keywords_llm,
    generate_context_description_llm,
    calculate_importance_llm,
    llm_rerank_results,
)
from .graph_ops import (
    create_graph_node,
    create_temporal_edge,
    find_related_memories,
    create_dynamic_links,
    traverse_graph,
    enrich_with_graph_traversal,
    temporal_query,
)
from .consolidation import consolidate_memories


class NeuralMemoryFabric:
    """
    Neural Memory Fabric - The core orchestrator.

    Manages multi-backend storage and intelligent retrieval for agentic memory.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize NMF with configuration."""
        self.config = load_config(config_path)
        self.sqlite_conn = None
        self.vector_db = None
        self.vector_collection_name = None
        self.graph_driver = None
        self.redis_client = None
        self.embedding_manager = None

        # Initialize paths
        self.sqlite_path = Path(self.config['storage']['sqlite']['path']).expanduser()
        self.file_root = Path(self.config['storage']['files']['root'])

        # Ensure directories exist
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_root.mkdir(parents=True, exist_ok=True)

        # Initialize embedding manager
        if 'embeddings' in self.config:
            try:
                from embedding_providers import EmbeddingManager
                self.embedding_manager = EmbeddingManager(self.config['embeddings'])
                logger.info("Embedding manager initialized")
            except ImportError:
                logger.warning("embedding_providers not available")

        logger.info("Neural Memory Fabric initialized")

    async def initialize(self):
        """Initialize all backend connections."""
        self.sqlite_conn = await init_sqlite(self.sqlite_path)
        self.vector_db, self.vector_collection_name = await init_vector_db(self.config)
        self.graph_driver = await init_graph_db(self.config)
        self.redis_client = await init_redis(self.config)
        logger.info("All backends initialized")

    def _generate_memory_id(self, content: str, timestamp: str) -> str:
        """Generate unique memory ID."""
        hash_input = f"{content}{timestamp}".encode('utf-8')
        return f"mem_{hashlib.sha256(hash_input).hexdigest()[:16]}"

    def _calculate_checksum(self, content: str) -> str:
        """Calculate content checksum."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    async def _generate_embedding(self, text: str, provider: Optional[str] = None) -> Optional[List[float]]:
        """
        Generate embedding for text using configured embedding providers.

        Args:
            text: Text to embed
            provider: Specific provider to use (or None for automatic)

        Returns:
            List of floats representing the embedding, or None if failed
        """
        if not self.embedding_manager:
            logger.warning("Embedding manager not initialized")
            return None

        result = await self.embedding_manager.generate_embedding(text, provider)

        if result:
            logger.debug(f"Generated {result.provider} embedding: {result.dimensions} dims in {result.latency_ms:.2f}ms")
            return result.embedding
        else:
            logger.warning("All embedding providers failed")
            return None

    async def remember(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Store a new memory with automatic linking and distribution.

        Args:
            content: The memory content
            metadata: Additional metadata
            agent_id: The agent storing this memory

        Returns:
            Result dictionary with memory_id and statistics
        """
        timestamp = datetime.utcnow().isoformat()
        memory_id = self._generate_memory_id(content, timestamp)

        # Extract keywords using LLM (Phase 4)
        keywords = await extract_keywords_llm(content)
        tags = metadata.get('tags', []) if metadata else []

        # Generate context description using LLM (Phase 4)
        context_description = await generate_context_description_llm(content)

        # Calculate importance score using LLM (Phase 4)
        importance_score = await calculate_importance_llm(content, metadata)

        # Generate embedding
        embedding = None
        if self.vector_db:
            embedding = await self._generate_embedding(content)
            logger.info(f"Embedding generated: {embedding is not None}")

        # Store in SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO nmf_entities
            (id, content, timestamp, valid_from, valid_until, keywords, tags,
             context_description, importance_score, access_count, last_accessed,
             tier, agent_id, version, checksum, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory_id, content, timestamp, timestamp, None,
            json.dumps(keywords), json.dumps(tags), context_description,
            importance_score, 0, timestamp, MemoryTier.ULTRA_FAST.value,
            agent_id, 1, self._calculate_checksum(content),
            json.dumps(metadata or {})
        ))
        self.sqlite_conn.commit()

        # Store in Redis cache if available
        if self.redis_client:
            cache_key = f"nmf:memory:{memory_id}"
            cache_data = json.dumps({
                'content': content,
                'timestamp': timestamp,
                'agent_id': agent_id
            })
            ttl = self.config['storage']['cache']['ttl']
            await self.redis_client.setex(cache_key, ttl, cache_data)

        # Store embedding in vector DB
        if self.vector_db and embedding:
            try:
                from qdrant_client.models import PointStruct

                # Convert memory_id to UUID (Qdrant requires UUID or integer)
                uuid_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, memory_id))

                self.vector_db.upsert(
                    collection_name=self.vector_collection_name,
                    points=[
                        PointStruct(
                            id=uuid_id,
                            vector=embedding,
                            payload={
                                'memory_id': memory_id,
                                'agent_id': agent_id,
                                'timestamp': timestamp,
                                'tier': MemoryTier.ULTRA_FAST.value,
                                'tags': tags,
                                'content': content[:1000]
                            }
                        )
                    ]
                )
                logger.info(f"Stored embedding in Qdrant for {memory_id} (UUID: {uuid_id})")
            except Exception as e:
                logger.error(f"Failed to store in Qdrant: {e}")

        # Create graph node in Neo4j (Phase 3)
        if self.graph_driver:
            await create_graph_node(
                self.graph_driver,
                memory_id,
                content,
                timestamp,
                agent_id,
                tags,
                0.5  # Default importance score
            )

        # Find and create dynamic links to related memories (Phase 3 - A-MEM pattern)
        if self.vector_db and embedding:
            try:
                links_created = await create_dynamic_links(
                    self.vector_db,
                    self.vector_collection_name,
                    self.sqlite_conn,
                    self.graph_driver,
                    self._generate_embedding,
                    memory_id,
                    similarity_threshold=0.6,
                    max_links=5
                )
                logger.info(f"Created {links_created} automatic links for {memory_id}")
            except Exception as e:
                logger.warning(f"Dynamic linking failed: {e}")

        # Phase 4: Store in file system for backup/persistence
        await store_to_filesystem(memory_id, content, timestamp, agent_id, tags, embedding)

        logger.info(f"Stored memory {memory_id} for agent {agent_id}")

        return {
            'success': True,
            'memory_id': memory_id,
            'timestamp': timestamp,
            'tier': MemoryTier.ULTRA_FAST.value
        }

    async def recall(
        self,
        query: str,
        mode: str = "hybrid",
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories using hybrid search.

        Args:
            query: Search query
            mode: Retrieval mode (semantic, graph, temporal, hybrid)
            agent_id: Filter by agent
            limit: Maximum results

        Returns:
            List of memory dictionaries
        """
        results = []
        vector_results = []
        sql_results = []

        # Step 1: Check Redis cache for recent queries
        if self.redis_client:
            cache_key = f"nmf:query:{hashlib.md5(query.encode(), usedforsecurity=False).hexdigest()}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return json.loads(cached)

        # Step 2: Vector semantic search (if available and mode allows)
        if self.vector_db and mode in ["semantic", "hybrid"]:
            try:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                query_embedding = await self._generate_embedding(query)
                if query_embedding:
                    # Build filter
                    query_filter = None
                    if agent_id:
                        query_filter = Filter(
                            must=[
                                FieldCondition(
                                    key="agent_id",
                                    match=MatchValue(value=agent_id)
                                )
                            ]
                        )

                    # Use named vector format for collections with named vectors
                    search_results = self.vector_db.search(
                        collection_name=self.vector_collection_name,
                        query_vector=("text-dense", query_embedding),
                        query_filter=query_filter,
                        limit=limit
                    )

                    # Process vector results
                    for result in search_results:
                        vector_results.append({
                            'memory_id': result.payload.get('memory_id', result.id),
                            'content': result.payload.get('content', ''),
                            'metadata': result.payload,
                            'similarity_score': result.score,
                            'source': 'vector'
                        })
                    logger.info(f"Vector search found {len(vector_results)} results")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")

        # Step 3: SQLite full-text search
        if mode in ["graph", "temporal", "hybrid"] or not vector_results:
            cursor = self.sqlite_conn.cursor()
            sql = '''
                SELECT id, content, timestamp, keywords, tags, importance_score,
                       access_count, tier, agent_id
                FROM nmf_entities
                WHERE content LIKE ?
            '''
            params = [f'%{query}%']

            if agent_id:
                sql += ' AND agent_id = ?'
                params.append(agent_id)

            sql += ' ORDER BY importance_score DESC, timestamp DESC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)

            for row in cursor.fetchall():
                sql_results.append({
                    'memory_id': row[0],
                    'content': row[1],
                    'timestamp': row[2],
                    'keywords': json.loads(row[3]),
                    'tags': json.loads(row[4]),
                    'importance_score': row[5],
                    'access_count': row[6],
                    'tier': row[7],
                    'agent_id': row[8],
                    'source': 'sql'
                })
            logger.info(f"SQL search found {len(sql_results)} results")

        # Step 4: Merge and rank results (hybrid mode)
        if mode == "hybrid" and vector_results and sql_results:
            seen_ids = set()
            combined = []

            # Add vector results first (weighted by similarity)
            for vr in vector_results:
                if vr['memory_id'] not in seen_ids:
                    seen_ids.add(vr['memory_id'])
                    combined.append({
                        'memory_id': vr['memory_id'],
                        'content': vr['content'],
                        'similarity_score': vr['similarity_score'],
                        'source': 'vector+sql',
                        'rank_score': vr['similarity_score'] * 0.7
                    })

            # Add SQL results (weighted by importance)
            for sr in sql_results:
                if sr['memory_id'] not in seen_ids:
                    seen_ids.add(sr['memory_id'])
                    combined.append({
                        **sr,
                        'rank_score': sr['importance_score'] * 0.3
                    })
                else:
                    # Boost if found in both
                    for item in combined:
                        if item['memory_id'] == sr['memory_id']:
                            item['rank_score'] = item.get('rank_score', 0) + (sr['importance_score'] * 0.3)
                            item['source'] = 'hybrid'

            # Sort by rank score
            combined.sort(key=lambda x: x.get('rank_score', 0), reverse=True)
            results = combined[:limit]

        elif mode == "semantic" or vector_results:
            results = vector_results[:limit]
        else:
            results = sql_results[:limit]

        # Step 5: Enrich results from SQLite if needed
        for result in results:
            if 'timestamp' not in result:
                cursor = self.sqlite_conn.cursor()
                cursor.execute('''
                    SELECT timestamp, keywords, tags, importance_score, access_count, tier, agent_id
                    FROM nmf_entities
                    WHERE id = ?
                ''', (result['memory_id'],))
                row = cursor.fetchone()
                if row:
                    result.update({
                        'timestamp': row[0],
                        'keywords': json.loads(row[1]),
                        'tags': json.loads(row[2]),
                        'importance_score': row[3],
                        'access_count': row[4],
                        'tier': row[5],
                        'agent_id': row[6]
                    })

        # Update access counts
        cursor = self.sqlite_conn.cursor()
        for result in results:
            cursor.execute('''
                UPDATE nmf_entities
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), result['memory_id']))
        self.sqlite_conn.commit()

        # Cache results
        if self.redis_client and results:
            cache_key = f"nmf:query:{hashlib.md5(query.encode(), usedforsecurity=False).hexdigest()}"
            await self.redis_client.setex(
                cache_key,
                self.config['storage']['cache']['ttl'],
                json.dumps(results)
            )

        logger.info(f"Recalled {len(results)} memories for query: {query[:50]}... (mode: {mode})")

        # Graph traversal enhancement
        if self.graph_driver and results and mode in ["graph", "hybrid"]:
            results = await enrich_with_graph_traversal(
                self.graph_driver,
                lambda **kwargs: traverse_graph(self.graph_driver, **kwargs),
                results,
                limit
            )

        # LLM re-ranking
        if results and len(results) > 1:
            results = await llm_rerank_results(query, results, limit)

        return results

    async def open_block(self, agent_id: str, block_name: str) -> Dict[str, Any]:
        """Load a memory block into context (Letta-style)."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT block_id, block_value, version, last_updated
            FROM nmf_memory_blocks
            WHERE agent_id = ? AND block_name = ?
        ''', (agent_id, block_name))

        row = cursor.fetchone()
        if row:
            return {
                'success': True,
                'block_id': row[0],
                'block_name': block_name,
                'value': row[1],
                'version': row[2],
                'last_updated': row[3]
            }
        else:
            return {
                'success': False,
                'error': f'Block {block_name} not found for agent {agent_id}'
            }

    async def edit_block(
        self,
        agent_id: str,
        block_name: str,
        new_value: str
    ) -> Dict[str, Any]:
        """Edit a memory block."""
        timestamp = datetime.utcnow().isoformat()
        block_id = f"{agent_id}_{block_name}"

        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO nmf_memory_blocks
            (block_id, agent_id, block_name, block_value, last_updated, version)
            VALUES (?, ?, ?, ?, ?, COALESCE(
                (SELECT version + 1 FROM nmf_memory_blocks WHERE block_id = ?), 1
            ))
        ''', (block_id, agent_id, block_name, new_value, timestamp, block_id))
        self.sqlite_conn.commit()

        return {
            'success': True,
            'block_id': block_id,
            'block_name': block_name,
            'updated_at': timestamp
        }

    async def close_block(self, agent_id: str, block_name: str) -> Dict[str, Any]:
        """Close a memory block (remove from active context)."""
        # In this implementation, closing is a no-op since we don't track active blocks
        # Could be extended to track active blocks in Redis
        return {
            'success': True,
            'block_name': block_name,
            'agent_id': agent_id,
            'action': 'closed'
        }

    async def list_blocks(self, agent_id: str) -> List[Dict[str, Any]]:
        """List all memory blocks for an agent."""
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT block_id, block_name, version, last_updated
            FROM nmf_memory_blocks
            WHERE agent_id = ?
            ORDER BY last_updated DESC
        ''', (agent_id,))

        blocks = []
        for row in cursor.fetchall():
            blocks.append({
                'block_id': row[0],
                'block_name': row[1],
                'version': row[2],
                'last_updated': row[3]
            })

        return blocks

    async def get_status(self) -> Dict[str, Any]:
        """Get system status and statistics."""
        cursor = self.sqlite_conn.cursor()

        # Count memories by tier
        cursor.execute('SELECT tier, COUNT(*) FROM nmf_entities GROUP BY tier')
        tier_counts = dict(cursor.fetchall())

        # Total memories
        cursor.execute('SELECT COUNT(*) FROM nmf_entities')
        total_memories = cursor.fetchone()[0]

        # Total links
        cursor.execute('SELECT COUNT(*) FROM nmf_links')
        total_links = cursor.fetchone()[0]

        return {
            'total_memories': total_memories,
            'total_links': total_links,
            'tier_distribution': tier_counts,
            'backends': {
                'sqlite': True,
                'vector': self.vector_db is not None,
                'graph': self.graph_driver is not None,
                'redis': self.redis_client is not None
            }
        }

    async def find_related_memories(
        self,
        memory_id: str,
        similarity_threshold: float = 0.6,
        max_links: int = 5
    ) -> List[tuple]:
        """Find related memories using semantic similarity."""
        return await find_related_memories(
            self.vector_db,
            self.vector_collection_name,
            self.sqlite_conn,
            self._generate_embedding,
            memory_id,
            similarity_threshold,
            max_links
        )

    async def create_dynamic_links(
        self,
        memory_id: str,
        similarity_threshold: float = 0.6,
        max_links: int = 5
    ) -> int:
        """Automatically create links to related memories."""
        return await create_dynamic_links(
            self.vector_db,
            self.vector_collection_name,
            self.sqlite_conn,
            self.graph_driver,
            self._generate_embedding,
            memory_id,
            similarity_threshold,
            max_links
        )

    async def traverse_graph(
        self,
        start_memory_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Traverse memory graph from starting node."""
        return await traverse_graph(
            self.graph_driver,
            start_memory_id,
            max_depth,
            relationship_types
        )

    async def temporal_query(
        self,
        agent_id: str,
        as_of_time: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query memories as they existed at a specific point in time."""
        return await temporal_query(
            self.sqlite_conn,
            agent_id,
            as_of_time,
            query
        )

    async def consolidate_memories(
        self,
        agent_id: str,
        min_access_count: int = 3,
        similarity_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Consolidate related memories (sleep-time processing)."""
        return await consolidate_memories(
            self.sqlite_conn,
            self.vector_db,
            self.find_related_memories,
            self.remember,
            agent_id,
            min_access_count,
            similarity_threshold
        )

    async def close(self):
        """Close all connections."""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.graph_driver:
            self.graph_driver.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Neural Memory Fabric closed")


__all__ = [
    'NeuralMemoryFabric',
]
