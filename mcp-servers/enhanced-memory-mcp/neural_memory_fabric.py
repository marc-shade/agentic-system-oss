#!/usr/bin/env python3
"""
Neural Memory Fabric - Core Module
Integrates multiple memory backends for the most advanced agentic memory system
"""

import asyncio
import logging
import hashlib
import json
import zlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Core imports
import sqlite3
import yaml

logger = logging.getLogger("neural-memory-fabric")


class MemoryTier(Enum):
    """Memory tier enumeration"""
    ULTRA_FAST = "ultra_fast"
    WORKING = "working"
    LONG_TERM = "long_term"
    ARCHIVAL = "archival"


class RetrievalMode(Enum):
    """Retrieval strategy enumeration"""
    SEMANTIC = "semantic"  # Vector search only
    GRAPH = "graph"  # Graph traversal only
    TEMPORAL = "temporal"  # Time-based
    HYBRID = "hybrid"  # All combined


@dataclass
class MemoryUnit:
    """A single memory unit with all attributes"""
    id: str
    content: str
    timestamp: str
    valid_from: str
    valid_until: Optional[str]
    keywords: List[str]
    tags: List[str]
    context_description: str
    embedding: Optional[List[float]]
    linked_memories: List[str]
    importance_score: float
    access_count: int
    last_accessed: str
    tier: str
    agent_id: str
    version: int
    checksum: str
    metadata: Dict[str, Any]


class NeuralMemoryFabric:
    """
    Neural Memory Fabric - The core orchestrator

    Manages multi-backend storage and intelligent retrieval for agentic memory.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize NMF with configuration"""
        self.config = self._load_config(config_path)
        self.sqlite_conn = None
        self.vector_db = None
        self.graph_db = None
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
            from embedding_providers import EmbeddingManager
            self.embedding_manager = EmbeddingManager(self.config['embeddings'])
            logger.info("Embedding manager initialized")

        logger.info("Neural Memory Fabric initialized")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML file"""
        if config_path is None:
            # Try multiple locations
            possible_paths = [
                Path(__file__).parent.parent.parent / "memory-fabric" / "nmf_config.yaml",
                Path("/Volumes/FILES/agentic-system/memory-fabric/nmf_config.yaml"),
                Path(__file__).parent / "nmf_config.yaml"
            ]

            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
            else:
                raise FileNotFoundError(f"Config not found in any location: {[str(p) for p in possible_paths]}")

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    async def initialize(self):
        """Initialize all backend connections"""
        await self._init_sqlite()
        await self._init_vector_db()
        await self._init_graph_db()
        await self._init_redis()
        logger.info("All backends initialized")

    async def _init_sqlite(self):
        """Initialize SQLite database"""
        self.sqlite_conn = sqlite3.connect(
            self.sqlite_path,
            check_same_thread=False
        )
        self.sqlite_conn.execute("PRAGMA journal_mode=WAL")
        self.sqlite_conn.execute("PRAGMA synchronous=NORMAL")

        # Create tables
        cursor = self.sqlite_conn.cursor()

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

        self.sqlite_conn.commit()
        logger.info("SQLite initialized")

    async def _init_vector_db(self):
        """Initialize vector database (Qdrant)"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct

            vector_config = self.config['storage']['vector']
            backend = vector_config.get('backend', 'qdrant')

            if backend == 'qdrant':
                # Connect to Qdrant
                self.vector_db = QdrantClient(
                    host=vector_config.get('host', 'localhost'),
                    port=vector_config.get('port', 6333),
                    prefer_grpc=vector_config.get('prefer_grpc', False),
                    https=vector_config.get('https', False)
                )

                # Get or create collection
                collection_name = vector_config.get('collection', 'enhanced_memory')
                collections = self.vector_db.get_collections().collections
                collection_exists = any(c.name == collection_name for c in collections)

                # Also check if it's an alias (check global aliases)
                if not collection_exists:
                    try:
                        all_aliases = self.vector_db.get_aliases().aliases
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

                    self.vector_db.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_config.get('vector_size', 768),
                            distance=distance
                        )
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")

                self.vector_collection_name = collection_name
                logger.info(f"Qdrant vector DB initialized: {collection_name}")

            else:
                logger.warning(f"Unknown vector backend: {backend}")
                self.vector_db = None

        except ImportError:
            logger.warning("qdrant-client not installed - vector search disabled")
            self.vector_db = None
        except Exception as e:
            logger.warning(f"Qdrant initialization failed: {e} - vector search disabled")
            self.vector_db = None

    async def _init_graph_db(self):
        """Initialize graph database (Neo4j)"""
        try:
            from neo4j import GraphDatabase

            graph_config = self.config['storage']['graph']
            self.graph_driver = GraphDatabase.driver(
                graph_config['uri'],
                auth=(graph_config['username'], graph_config['password'])
            )

            # Test connection
            with self.graph_driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()

            logger.info("Neo4j graph DB initialized")
        except ImportError:
            logger.warning("neo4j driver not installed - graph features disabled")
            self.graph_driver = None
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e} - graph features disabled")
            self.graph_driver = None

    async def _init_redis(self):
        """Initialize Redis cache"""
        try:
            import redis.asyncio as redis

            self.redis_client = redis.from_url(
                self.config['storage']['cache']['url'],
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()

            logger.info("Redis cache initialized")
        except ImportError:
            logger.warning("redis not installed - caching disabled")
            self.redis_client = None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} - caching disabled")
            self.redis_client = None

    def _generate_memory_id(self, content: str, timestamp: str) -> str:
        """Generate unique memory ID"""
        hash_input = f"{content}{timestamp}".encode('utf-8')
        return f"mem_{hashlib.sha256(hash_input).hexdigest()[:16]}"

    def _calculate_checksum(self, content: str) -> str:
        """Calculate content checksum"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    async def _extract_keywords_llm(self, content: str) -> List[str]:
        """
        Extract keywords using LLM (Phase 4 Intelligence)

        Args:
            content: Memory content

        Returns:
            List of extracted keywords
        """
        import os

        # Try Google Gemini
        try:
            import google.generativeai as genai

            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)

                model = genai.GenerativeModel('gemini-1.5-flash')

                prompt = f"""Extract 3-7 key keywords or phrases from this text. Return ONLY a comma-separated list, no explanation.

Text: {content[:1000]}

Keywords:"""

                response = model.generate_content(prompt)
                keywords_text = response.text.strip()

                # Parse comma-separated keywords
                keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
                keywords = keywords[:7]  # Limit to 7

                logger.debug(f"Extracted keywords: {keywords}")
                return keywords

        except Exception as e:
            logger.debug(f"LLM keyword extraction failed: {e}")

        # Fallback: Simple extraction from content
        words = content.lower().split()
        # Get unique words longer than 4 characters
        keywords = list(set([w.strip('.,!?;:') for w in words if len(w) > 4]))[:5]
        return keywords

    async def _generate_context_description_llm(self, content: str) -> str:
        """
        Generate context description using LLM (Phase 4 Intelligence)

        Args:
            content: Memory content

        Returns:
            Brief context description
        """
        import os

        # Try Google Gemini
        try:
            import google.generativeai as genai

            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)

                model = genai.GenerativeModel('gemini-1.5-flash')

                prompt = f"""Summarize this text in ONE concise sentence (max 100 chars). Focus on the main topic and key points.

Text: {content[:1000]}

Summary:"""

                response = model.generate_content(prompt)
                description = response.text.strip()

                # Limit length
                if len(description) > 200:
                    description = description[:197] + "..."

                logger.debug(f"Generated description: {description}")
                return description

        except Exception as e:
            logger.debug(f"LLM context generation failed: {e}")

        # Fallback: First 200 characters
        return content[:200]

    async def _calculate_importance_llm(self, content: str, metadata: Optional[Dict]) -> float:
        """
        Calculate importance score using LLM (Phase 4 Intelligence)

        Args:
            content: Memory content
            metadata: Additional context

        Returns:
            Importance score (0.0 to 1.0)
        """
        import os

        # Check if user provided explicit importance
        if metadata and 'importance' in metadata:
            return float(metadata['importance'])

        # Try Google Gemini
        try:
            import google.generativeai as genai

            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)

                model = genai.GenerativeModel('gemini-1.5-flash')

                prompt = f"""Rate the importance of this memory on a scale of 0.0 to 1.0, where:
- 0.0-0.3: Trivial, temporary information
- 0.4-0.6: Moderate importance, useful reference
- 0.7-0.9: Important information, key knowledge
- 1.0: Critical, must-remember information

Text: {content[:500]}

Return ONLY a number between 0.0 and 1.0, no explanation.

Importance:"""

                response = model.generate_content(prompt)
                score_text = response.text.strip()

                # Parse score
                try:
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                    logger.debug(f"LLM importance score: {score}")
                    return score
                except ValueError:
                    logger.debug(f"Could not parse importance: {score_text}")

        except Exception as e:
            logger.debug(f"LLM importance scoring failed: {e}")

        # Fallback: Heuristic based on length and metadata
        base_score = 0.5

        # Longer content is often more important
        if len(content) > 500:
            base_score += 0.1
        if len(content) > 1000:
            base_score += 0.1

        # Has tags = more important
        if metadata and metadata.get('tags'):
            base_score += 0.1

        return min(1.0, base_score)

    async def _generate_embedding(self, text: str, provider: Optional[str] = None) -> Optional[List[float]]:
        """
        Generate embedding for text using configured embedding providers

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
        Store a new memory with automatic linking and distribution

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
        keywords = await self._extract_keywords_llm(content)
        tags = metadata.get('tags', []) if metadata else []

        # Generate context description using LLM (Phase 4)
        context_description = await self._generate_context_description_llm(content)

        # Calculate importance score using LLM (Phase 4)
        importance_score = await self._calculate_importance_llm(content, metadata)

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
                import uuid

                # Convert memory_id to UUID (Qdrant requires UUID or integer)
                # Use hash of memory_id to generate consistent UUID
                uuid_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, memory_id))

                self.vector_db.upsert(
                    collection_name=self.vector_collection_name,
                    points=[
                        PointStruct(
                            id=uuid_id,
                            vector=embedding,
                            payload={
                                'memory_id': memory_id,  # Store original ID in payload
                                'agent_id': agent_id,
                                'timestamp': timestamp,
                                'tier': MemoryTier.ULTRA_FAST.value,
                                'tags': tags,
                                'content': content[:1000]  # Store snippet
                            }
                        )
                    ]
                )
                logger.info(f"Stored embedding in Qdrant for {memory_id} (UUID: {uuid_id})")
            except Exception as e:
                logger.error(f"Failed to store in Qdrant: {e}")

        # Create graph node in Neo4j (Phase 3)
        if self.graph_driver:
            await self._create_graph_node(
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
                links_created = await self.create_dynamic_links(
                    memory_id,
                    similarity_threshold=0.6,
                    max_links=5
                )
                logger.info(f"Created {links_created} automatic links for {memory_id}")
            except Exception as e:
                logger.warning(f"Dynamic linking failed: {e}")

        # TODO: Store in file system (Phase 4)

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
        Retrieve memories using hybrid search

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
            cache_key = f"nmf:query:{hashlib.md5(query.encode()).hexdigest()}"
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
                            'memory_id': result.payload.get('memory_id', result.id),  # Use original memory_id from payload
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
            # Combine results, deduplicate, and rank
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
                        'rank_score': vr['similarity_score'] * 0.7  # Vector weight
                    })

            # Add SQL results (weighted by importance)
            for sr in sql_results:
                if sr['memory_id'] not in seen_ids:
                    seen_ids.add(sr['memory_id'])
                    combined.append({
                        **sr,
                        'rank_score': sr['importance_score'] * 0.3  # SQL weight
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
            cache_key = f"nmf:query:{hashlib.md5(query.encode()).hexdigest()}"
            await self.redis_client.setex(
                cache_key,
                self.config['storage']['cache']['ttl'],
                json.dumps(results)
            )

        logger.info(f"Recalled {len(results)} memories for query: {query[:50]}... (mode: {mode})")

        # TODO: Integrate graph traversal
        # TODO: LLM re-ranking

        return results

    async def open_block(self, agent_id: str, block_name: str) -> Dict[str, Any]:
        """Load a memory block into context (Letta-style)"""
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
        """Edit a memory block"""
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

    async def get_status(self) -> Dict[str, Any]:
        """Get system status and statistics"""
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

    # === PHASE 3: Graph & Dynamic Linking Features ===

    async def _create_graph_node(
        self,
        memory_id: str,
        content: str,
        timestamp: str,
        agent_id: str,
        tags: List[str],
        importance_score: float
    ) -> bool:
        """
        Create temporal entity node in Neo4j graph database

        Implements bi-temporal tracking (Zep/Graphiti pattern):
        - event_time: When the memory was created
        - valid_from: When this version became valid
        - valid_until: When this version was superseded (None if current)
        """
        if not self.graph_driver:
            return False

        try:
            with self.graph_driver.session() as session:
                # Create memory node with bi-temporal properties
                session.run("""
                    CREATE (m:Memory {
                        id: $id,
                        content: $content,
                        agent_id: $agent_id,
                        event_time: datetime($timestamp),
                        valid_from: datetime($valid_from),
                        valid_until: null,
                        importance_score: $importance,
                        access_count: 0,
                        tags: $tags
                    })
                """, {
                    'id': memory_id,
                    'content': content[:500],  # Store excerpt
                    'agent_id': agent_id,
                    'timestamp': timestamp,
                    'valid_from': timestamp,
                    'importance': importance_score,
                    'tags': tags
                })

                logger.info(f"Created graph node for {memory_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to create graph node: {e}")
            return False

    async def _create_temporal_edge(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str = "RELATES_TO",
        link_score: float = 0.5,
        valid_from: Optional[str] = None
    ) -> bool:
        """
        Create bi-temporal edge between memory nodes

        Args:
            from_id: Source memory ID
            to_id: Target memory ID
            relationship_type: Type of relationship (RELATES_TO, REFERENCES, CONTRADICTS, etc.)
            link_score: Strength of relationship (0.0 to 1.0)
            valid_from: When this relationship became valid (default: now)
        """
        if not self.graph_driver:
            return False

        if valid_from is None:
            valid_from = datetime.utcnow().isoformat()

        try:
            with self.graph_driver.session() as session:
                session.run(f"""
                    MATCH (from:Memory {{id: $from_id}})
                    MATCH (to:Memory {{id: $to_id}})
                    CREATE (from)-[r:{relationship_type} {{
                        link_score: $score,
                        valid_from: datetime($valid_from),
                        valid_until: null,
                        created_at: datetime()
                    }}]->(to)
                """, {
                    'from_id': from_id,
                    'to_id': to_id,
                    'score': link_score,
                    'valid_from': valid_from
                })

                logger.info(f"Created {relationship_type} edge: {from_id} -> {to_id} (score: {link_score})")
                return True

        except Exception as e:
            logger.error(f"Failed to create temporal edge: {e}")
            return False

    async def find_related_memories(
        self,
        memory_id: str,
        similarity_threshold: float = 0.6,
        max_links: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find related memories using semantic similarity (A-MEM pattern)

        Returns list of (memory_id, similarity_score) tuples
        """
        if not self.vector_db:
            return []

        try:
            # Get embedding for the source memory
            cursor = self.sqlite_conn.cursor()
            cursor.execute('SELECT content FROM nmf_entities WHERE id = ?', (memory_id,))
            row = cursor.fetchone()

            if not row:
                return []

            content = row[0]
            query_embedding = await self._generate_embedding(content)

            if not query_embedding:
                return []

            # Search for similar memories
            search_results = self.vector_db.search(
                collection_name=self.vector_collection_name,
                query_vector=query_embedding,
                limit=max_links + 1  # +1 because it includes itself
            )

            related = []
            if search_results:
                for result in search_results:
                    result_memory_id = result.payload.get('memory_id', result.id)
                    if result_memory_id == memory_id:
                        continue  # Skip self

                    similarity = result.score

                    if similarity >= similarity_threshold:
                        related.append((result_memory_id, similarity))

            return related[:max_links]

        except Exception as e:
            logger.error(f"Failed to find related memories: {e}")
            return []

    async def create_dynamic_links(
        self,
        memory_id: str,
        similarity_threshold: float = 0.6,
        max_links: int = 5
    ) -> int:
        """
        Automatically create links to related memories (A-MEM pattern)

        Returns number of links created
        """
        related = await self.find_related_memories(memory_id, similarity_threshold, max_links)

        if not related:
            logger.info(f"No related memories found for {memory_id}")
            return 0

        links_created = 0
        cursor = self.sqlite_conn.cursor()

        for related_id, similarity in related:
            try:
                # Store in SQLite
                cursor.execute('''
                    INSERT OR IGNORE INTO nmf_links (from_memory_id, to_memory_id, link_type, link_score)
                    VALUES (?, ?, ?, ?)
                ''', (memory_id, related_id, 'relates_to', similarity))

                # Create graph edge if Neo4j available
                await self._create_temporal_edge(
                    memory_id,
                    related_id,
                    "RELATES_TO",
                    similarity
                )

                links_created += 1
                logger.info(f"Linked {memory_id} -> {related_id} (similarity: {similarity:.3f})")

            except Exception as e:
                logger.error(f"Failed to create link: {e}")

        self.sqlite_conn.commit()
        logger.info(f"Created {links_created} dynamic links for {memory_id}")

        return links_created

    async def traverse_graph(
        self,
        start_memory_id: str,
        max_depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Traverse memory graph from starting node

        Args:
            start_memory_id: Starting memory ID
            max_depth: Maximum traversal depth
            relationship_types: Filter by relationship types (default: all)

        Returns:
            List of connected memories with relationship info
        """
        if not self.graph_driver:
            logger.warning("Graph traversal requires Neo4j")
            return []

        if relationship_types is None:
            relationship_types = ["RELATES_TO", "REFERENCES", "CONTRADICTS"]

        try:
            with self.graph_driver.session() as session:
                # Cypher query for graph traversal
                rel_pattern = "|".join(relationship_types)

                result = session.run(f"""
                    MATCH path = (start:Memory {{id: $start_id}})-[r:{rel_pattern}*1..{max_depth}]-(connected:Memory)
                    WHERE all(rel in relationships(path) WHERE rel.valid_until IS NULL)
                    RETURN
                        connected.id AS id,
                        connected.content AS content,
                        connected.importance_score AS importance,
                        length(path) AS distance,
                        [rel in relationships(path) | type(rel)] AS relationship_chain,
                        [rel in relationships(path) | rel.link_score] AS score_chain
                    ORDER BY distance ASC, importance DESC
                    LIMIT 20
                """, {'start_id': start_memory_id})

                connected_memories = []
                for record in result:
                    connected_memories.append({
                        'memory_id': record['id'],
                        'content': record['content'],
                        'importance': record['importance'],
                        'graph_distance': record['distance'],
                        'relationship_path': record['relationship_chain'],
                        'link_scores': record['score_chain']
                    })

                logger.info(f"Graph traversal from {start_memory_id} found {len(connected_memories)} connected memories")
                return connected_memories

        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            return []

    async def temporal_query(
        self,
        agent_id: str,
        as_of_time: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query memories as they existed at a specific point in time (Zep pattern)

        Args:
            agent_id: Filter by agent
            as_of_time: ISO timestamp to query
            query: Optional search query

        Returns:
            Memories that were valid at the specified time
        """
        cursor = self.sqlite_conn.cursor()

        # SQL query with temporal validity check
        if query:
            cursor.execute('''
                SELECT id, content, timestamp, valid_from, valid_until, importance_score
                FROM nmf_entities
                WHERE agent_id = ?
                AND valid_from <= ?
                AND (valid_until IS NULL OR valid_until > ?)
                AND content LIKE ?
                ORDER BY importance_score DESC, timestamp DESC
                LIMIT 20
            ''', (agent_id, as_of_time, as_of_time, f'%{query}%'))
        else:
            cursor.execute('''
                SELECT id, content, timestamp, valid_from, valid_until, importance_score
                FROM nmf_entities
                WHERE agent_id = ?
                AND valid_from <= ?
                AND (valid_until IS NULL OR valid_until > ?)
                ORDER BY importance_score DESC, timestamp DESC
                LIMIT 20
            ''', (agent_id, as_of_time, as_of_time))

        results = []
        for row in cursor.fetchall():
            results.append({
                'memory_id': row[0],
                'content': row[1],
                'timestamp': row[2],
                'valid_from': row[3],
                'valid_until': row[4],
                'importance_score': row[5],
                'was_valid_at': as_of_time
            })

        logger.info(f"Temporal query found {len(results)} memories valid at {as_of_time}")
        return results

    # === End Phase 3 Features ===

    # === PHASE 4: LLM Intelligence & Consolidation ===

    async def consolidate_memories(
        self,
        agent_id: str,
        min_access_count: int = 3,
        similarity_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Consolidate related memories (sleep-time processing)

        This implements memory consolidation inspired by human memory:
        1. Find frequently accessed memories
        2. Identify highly similar memory clusters
        3. Create abstract summaries
        4. Strengthen important connections
        5. Prune weak links

        Args:
            agent_id: Agent to consolidate memories for
            min_access_count: Minimum access count to consider
            similarity_threshold: Threshold for grouping similar memories

        Returns:
            Consolidation statistics
        """
        logger.info(f"Starting memory consolidation for {agent_id}")

        # Find frequently accessed memories
        cursor = self.sqlite_conn.cursor()
        cursor.execute('''
            SELECT id, content, access_count, importance_score
            FROM nmf_entities
            WHERE agent_id = ? AND access_count >= ?
            ORDER BY access_count DESC, importance_score DESC
            LIMIT 50
        ''', (agent_id, min_access_count))

        frequent_memories = cursor.fetchall()

        if not frequent_memories or not self.vector_db:
            return {
                'memories_processed': 0,
                'clusters_created': 0,
                'summaries_created': 0,
                'links_strengthened': 0,
                'links_pruned': 0
            }

        # Group similar memories into clusters
        clusters = []
        processed = set()

        for mem_id, content, access_count, importance in frequent_memories:
            if mem_id in processed:
                continue

            # Find similar memories
            related = await self.find_related_memories(
                mem_id,
                similarity_threshold=similarity_threshold,
                max_links=10
            )

            if related:
                cluster = {
                    'anchor': mem_id,
                    'members': [r[0] for r in related],
                    'similarities': [r[1] for r in related],
                    'avg_similarity': sum(r[1] for r in related) / len(related)
                }
                clusters.append(cluster)
                processed.add(mem_id)
                processed.update(cluster['members'])

        # Create abstract summaries for each cluster
        summaries_created = 0
        for cluster in clusters:
            try:
                # Get all content from cluster
                member_ids = [cluster['anchor']] + cluster['members']
                cursor.execute(f'''
                    SELECT content FROM nmf_entities
                    WHERE id IN ({','.join('?' * len(member_ids))})
                ''', member_ids)

                contents = [row[0] for row in cursor.fetchall()]
                combined_content = ' '.join(contents)

                # Generate summary using LLM
                summary = await self._generate_cluster_summary(combined_content)

                if summary:
                    # Store summary as new memory
                    await self.remember(
                        content=summary,
                        metadata={
                            'tags': ['consolidated', 'summary'],
                            'cluster_members': member_ids,
                            'importance': 0.8  # High importance for summaries
                        },
                        agent_id=agent_id
                    )
                    summaries_created += 1

            except Exception as e:
                logger.error(f"Failed to consolidate cluster: {e}")

        # Strengthen important links (increase score)
        cursor.execute('''
            UPDATE nmf_links
            SET link_score = MIN(1.0, link_score * 1.2)
            WHERE from_memory_id IN (
                SELECT id FROM nmf_entities
                WHERE agent_id = ? AND importance_score > 0.7
            )
        ''', (agent_id,))

        links_strengthened = cursor.rowcount

        # Prune weak links (below 0.3 similarity)
        cursor.execute('''
            DELETE FROM nmf_links
            WHERE link_score < 0.3
            AND from_memory_id IN (
                SELECT id FROM nmf_entities WHERE agent_id = ?
            )
        ''', (agent_id,))

        links_pruned = cursor.rowcount
        self.sqlite_conn.commit()

        logger.info(f"Consolidation complete: {len(clusters)} clusters, {summaries_created} summaries")

        return {
            'memories_processed': len(frequent_memories),
            'clusters_created': len(clusters),
            'summaries_created': summaries_created,
            'links_strengthened': links_strengthened,
            'links_pruned': links_pruned
        }

    async def _generate_cluster_summary(self, combined_content: str) -> Optional[str]:
        """
        Generate abstract summary for memory cluster using LLM

        Args:
            combined_content: Combined content from cluster members

        Returns:
            Abstract summary or None
        """
        import os

        try:
            import google.generativeai as genai

            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                return None

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')

            prompt = f"""Create a concise abstract summary that captures the key themes and insights from these related memories. Focus on patterns, connections, and higher-order understanding.

Memories:
{combined_content[:2000]}

Abstract Summary (2-3 sentences):"""

            response = model.generate_content(prompt)
            summary = response.text.strip()

            logger.info(f"Generated cluster summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Cluster summary generation failed: {e}")
            return None

    # === End Phase 4 Features ===

    async def close(self):
        """Close all connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
        if self.graph_driver:
            self.graph_driver.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Neural Memory Fabric closed")


# Singleton instance
_nmf_instance: Optional[NeuralMemoryFabric] = None


async def get_nmf() -> NeuralMemoryFabric:
    """Get or create NMF singleton instance"""
    global _nmf_instance
    if _nmf_instance is None:
        _nmf_instance = NeuralMemoryFabric()
        await _nmf_instance.initialize()
    return _nmf_instance
