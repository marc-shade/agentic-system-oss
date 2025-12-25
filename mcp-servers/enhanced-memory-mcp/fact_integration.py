"""
FACT Integration Layer for Enhanced Memory MCP

Implements cache-first retrieval pattern from ruvnet's FACT system.
Routes queries through high-performance cache before falling back to Qdrant semantic search.

Performance targets:
- Cache hit: <48ms (vs ~200-500ms for Qdrant)
- Cache miss: <140ms (cache check + Qdrant)
- Target hit rate: 87%+
- Cost reduction: 93% vs direct LLM calls

Architecture:
    Query → FACT Cache Check → [Hit: Return cached] | [Miss: Qdrant Search → Cache → Return]
"""

import asyncio
import hashlib
import json
import time
import zlib
import base64
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import logging
import threading

logger = logging.getLogger("fact-integration")


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"              # Least Recently Used
    LFU = "lfu"              # Least Frequently Used
    ADAPTIVE = "adaptive"     # Adaptive based on metrics
    TOKEN_OPTIMIZED = "token_optimized"  # Optimized for token efficiency


@dataclass
class CacheEntry:
    """A cached query result."""
    query_hash: str
    query: str
    result: str
    token_count: int
    created_at: float
    access_count: int = 0
    last_accessed: Optional[float] = None
    ttl_seconds: int = 3600  # 1 hour default
    compressed: bool = False

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (~4 chars per token)."""
        return max(1, len(text) // 4)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > (self.created_at + self.ttl_seconds)

    def touch(self) -> None:
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheMetrics:
    """Performance metrics for the cache."""
    hits: int = 0
    misses: int = 0
    total_queries: int = 0
    total_hit_latency_ms: float = 0
    total_miss_latency_ms: float = 0
    evictions: int = 0
    compressions: int = 0
    bytes_saved: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.hits / self.total_queries

    @property
    def avg_hit_latency_ms(self) -> float:
        if self.hits == 0:
            return 0.0
        return self.total_hit_latency_ms / self.hits

    @property
    def avg_miss_latency_ms(self) -> float:
        if self.misses == 0:
            return 0.0
        return self.total_miss_latency_ms / self.misses


class CircuitBreaker:
    """Circuit breaker for cache resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_seconds: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds

        self._failures = 0
        self._successes = 0
        self._state = "closed"  # closed, open, half_open
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._state == "open":
                # Check if timeout has passed
                if self._last_failure_time and \
                   time.time() - self._last_failure_time > self.timeout_seconds:
                    self._state = "half_open"
                    return False
                return True
            return False

    def record_success(self) -> None:
        with self._lock:
            self._successes += 1
            if self._state == "half_open" and self._successes >= self.success_threshold:
                self._state = "closed"
                self._failures = 0
                self._successes = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = "open"
                logger.warning(f"Circuit breaker opened after {self._failures} failures")


class FACTCacheManager:
    """
    FACT-style cache manager for enhanced-memory queries.

    Implements cache-first retrieval with adaptive strategies.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        max_entries: int = 10000,
        max_size_mb: int = 100,
        min_tokens: int = 50,  # Minimum tokens to cache
        ttl_seconds: int = 3600,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        hit_target_ms: float = 48.0,
        miss_target_ms: float = 140.0
    ):
        self.db_path = db_path or Path.home() / ".claude" / "fact_cache" / "cache.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.max_entries = max_entries
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.min_tokens = min_tokens
        self.ttl_seconds = ttl_seconds
        self.strategy = strategy
        self.hit_target_ms = hit_target_ms
        self.miss_target_ms = miss_target_ms

        self.metrics = CacheMetrics()
        self.circuit_breaker = CircuitBreaker()

        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._initialized = False

    def _init_db(self) -> None:
        """Initialize SQLite database for persistent cache."""
        if self._initialized:
            return

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fact_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    result TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    ttl_seconds INTEGER DEFAULT 3600,
                    compressed INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fact_cache_created
                ON fact_cache(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fact_cache_accessed
                ON fact_cache(last_accessed)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fact_metrics (
                    id INTEGER PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    hits INTEGER DEFAULT 0,
                    misses INTEGER DEFAULT 0,
                    hit_rate REAL DEFAULT 0,
                    avg_hit_latency_ms REAL DEFAULT 0,
                    avg_miss_latency_ms REAL DEFAULT 0
                )
            """)
            conn.commit()
            self._initialized = True
            logger.info(f"FACT cache initialized at {self.db_path}")
        finally:
            conn.close()

    def _generate_hash(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate unique hash for query + context."""
        key = query
        if context:
            key += json.dumps(context, sort_keys=True)
        return hashlib.sha256(key.encode()).hexdigest()[:32]

    def _compress(self, data: str) -> Tuple[str, bool]:
        """Compress data if beneficial."""
        original_size = len(data.encode())
        if original_size < 1024:  # Don't compress small data
            return data, False

        compressed = zlib.compress(data.encode(), level=6)
        compressed_b64 = base64.b64encode(compressed).decode()

        if len(compressed_b64) < original_size * 0.8:  # 20%+ savings
            self.metrics.bytes_saved += original_size - len(compressed_b64)
            self.metrics.compressions += 1
            return compressed_b64, True

        return data, False

    def _decompress(self, data: str, compressed: bool) -> str:
        """Decompress data if needed."""
        if not compressed:
            return data
        compressed_bytes = base64.b64decode(data.encode())
        return zlib.decompress(compressed_bytes).decode()

    def _should_cache(self, query: str, result: str) -> bool:
        """Determine if result should be cached based on strategy."""
        token_count = CacheEntry.estimate_tokens(result)

        # Minimum token threshold
        if token_count < self.min_tokens:
            return False

        # Don't cache error responses
        if "error" in result.lower()[:100] or "failed" in result.lower()[:100]:
            return False

        return True

    def _evict_if_needed(self) -> int:
        """Evict entries based on strategy. Returns count evicted."""
        with self._lock:
            if len(self._cache) <= self.max_entries:
                return 0

            # Calculate how many to evict (20% of excess)
            to_evict = max(1, (len(self._cache) - self.max_entries) + len(self._cache) // 10)

            if self.strategy == CacheStrategy.LRU:
                # Sort by last accessed (oldest first)
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].last_accessed or 0
                )
            elif self.strategy == CacheStrategy.LFU:
                # Sort by access count (lowest first)
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].access_count
                )
            else:  # ADAPTIVE or TOKEN_OPTIMIZED
                # Combined score: recency + frequency + token efficiency
                def adaptive_score(entry: CacheEntry) -> float:
                    age = time.time() - (entry.last_accessed or entry.created_at)
                    recency = 1.0 / (age + 1)
                    frequency = min(entry.access_count / 10.0, 1.0)
                    efficiency = entry.token_count / 1000.0
                    return recency * 0.4 + frequency * 0.4 + efficiency * 0.2

                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: adaptive_score(x[1])
                )

            evicted = 0
            for key, _ in sorted_entries[:to_evict]:
                del self._cache[key]
                evicted += 1

            self.metrics.evictions += evicted
            return evicted

    async def get(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get cached result for query.

        Returns None on cache miss.
        """
        if self.circuit_breaker.is_open:
            return None

        start = time.perf_counter()

        try:
            self._init_db()
            query_hash = self._generate_hash(query, context)

            with self._lock:
                # Check in-memory cache first
                if query_hash in self._cache:
                    entry = self._cache[query_hash]
                    if not entry.is_expired():
                        entry.touch()
                        result = self._decompress(entry.result, entry.compressed)

                        latency = (time.perf_counter() - start) * 1000
                        self.metrics.hits += 1
                        self.metrics.total_queries += 1
                        self.metrics.total_hit_latency_ms += latency

                        self.circuit_breaker.record_success()
                        logger.debug(f"FACT cache hit: {latency:.2f}ms")
                        return result
                    else:
                        # Expired - remove
                        del self._cache[query_hash]

            # Check persistent storage
            conn = sqlite3.connect(str(self.db_path))
            try:
                cursor = conn.execute(
                    """
                    SELECT result, token_count, created_at, access_count,
                           last_accessed, ttl_seconds, compressed
                    FROM fact_cache WHERE query_hash = ?
                    """,
                    (query_hash,)
                )
                row = cursor.fetchone()

                if row:
                    result, token_count, created_at, access_count, \
                    last_accessed, ttl_seconds, compressed = row

                    # Check expiration
                    if time.time() > created_at + ttl_seconds:
                        conn.execute("DELETE FROM fact_cache WHERE query_hash = ?",
                                    (query_hash,))
                        conn.commit()
                    else:
                        # Update access stats
                        conn.execute(
                            """
                            UPDATE fact_cache
                            SET access_count = access_count + 1, last_accessed = ?
                            WHERE query_hash = ?
                            """,
                            (time.time(), query_hash)
                        )
                        conn.commit()

                        # Load into memory cache
                        entry = CacheEntry(
                            query_hash=query_hash,
                            query=query,
                            result=result,
                            token_count=token_count,
                            created_at=created_at,
                            access_count=access_count + 1,
                            last_accessed=time.time(),
                            ttl_seconds=ttl_seconds,
                            compressed=bool(compressed)
                        )
                        with self._lock:
                            self._cache[query_hash] = entry

                        result = self._decompress(result, bool(compressed))

                        latency = (time.perf_counter() - start) * 1000
                        self.metrics.hits += 1
                        self.metrics.total_queries += 1
                        self.metrics.total_hit_latency_ms += latency

                        self.circuit_breaker.record_success()
                        logger.debug(f"FACT cache hit (disk): {latency:.2f}ms")
                        return result
            finally:
                conn.close()

            # Cache miss
            latency = (time.perf_counter() - start) * 1000
            self.metrics.misses += 1
            self.metrics.total_queries += 1
            self.circuit_breaker.record_success()
            return None

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(f"FACT cache get failed: {e}")
            return None

    async def store(
        self,
        query: str,
        result: str,
        context: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Store result in cache.

        Returns True if stored successfully.
        """
        if self.circuit_breaker.is_open:
            return False

        if not self._should_cache(query, result):
            return False

        try:
            self._init_db()
            query_hash = self._generate_hash(query, context)

            # Compress if beneficial
            stored_result, compressed = self._compress(result)

            entry = CacheEntry(
                query_hash=query_hash,
                query=query,
                result=stored_result,
                token_count=CacheEntry.estimate_tokens(result),
                created_at=time.time(),
                ttl_seconds=ttl_seconds or self.ttl_seconds,
                compressed=compressed
            )

            # Store in memory
            with self._lock:
                self._cache[query_hash] = entry

            # Persist to disk
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fact_cache
                    (query_hash, query, result, token_count, created_at,
                     access_count, last_accessed, ttl_seconds, compressed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        query_hash, query, stored_result, entry.token_count,
                        entry.created_at, 0, None, entry.ttl_seconds,
                        1 if compressed else 0
                    )
                )
                conn.commit()
            finally:
                conn.close()

            # Evict if needed
            self._evict_if_needed()

            self.circuit_breaker.record_success()
            logger.debug(f"FACT cache stored: {query_hash[:8]}...")
            return True

        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(f"FACT cache store failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics."""
        return {
            "hit_rate": self.metrics.hit_rate,
            "hits": self.metrics.hits,
            "misses": self.metrics.misses,
            "total_queries": self.metrics.total_queries,
            "avg_hit_latency_ms": self.metrics.avg_hit_latency_ms,
            "avg_miss_latency_ms": self.metrics.avg_miss_latency_ms,
            "cache_entries": len(self._cache),
            "evictions": self.metrics.evictions,
            "bytes_saved_by_compression": self.metrics.bytes_saved,
            "compressions": self.metrics.compressions,
            "circuit_breaker_state": self.circuit_breaker._state,
            "targets": {
                "hit_latency_ms": self.hit_target_ms,
                "miss_latency_ms": self.miss_target_ms
            }
        }

    async def clear_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        removed = 0

        # Clear in-memory
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1

        # Clear from disk
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "DELETE FROM fact_cache WHERE created_at + ttl_seconds < ?",
                (time.time(),)
            )
            removed += cursor.rowcount
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to clear expired entries from disk: {e}")

        return removed


class FACTEnhancedMemoryWrapper:
    """
    Wrapper that adds FACT caching to enhanced-memory-mcp operations.

    Usage:
        wrapper = FACTEnhancedMemoryWrapper(memory_client)
        result = await wrapper.search_nodes("query")  # Cache-first!
    """

    def __init__(
        self,
        memory_client,
        cache_manager: Optional[FACTCacheManager] = None
    ):
        self.memory_client = memory_client
        self.cache = cache_manager or FACTCacheManager()
        self._fallback_fn: Optional[Callable] = None

    def set_fallback(self, fn: Callable) -> None:
        """Set fallback search function (e.g., Qdrant search)."""
        self._fallback_fn = fn

    async def search_nodes(
        self,
        query: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Cache-first search for memory nodes.

        Flow:
        1. Check FACT cache for query
        2. On hit: return cached result
        3. On miss: execute search, cache result, return
        """
        start = time.perf_counter()

        # Build context for cache key
        context = {"limit": limit, **kwargs}

        # Try cache first
        cached = await self.cache.get(query, context)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass  # Cache corruption, fall through to fresh search

        # Cache miss - execute actual search
        try:
            if hasattr(self.memory_client, 'search_nodes'):
                result = await self.memory_client.search_nodes(query, limit=limit)
            elif self._fallback_fn:
                result = await self._fallback_fn(query, limit=limit, **kwargs)
            else:
                # Direct SQL fallback
                result = await self._direct_search(query, limit)

            # Cache the result
            result_json = json.dumps(result, default=str)
            await self.cache.store(query, result_json, context)

            miss_latency = (time.perf_counter() - start) * 1000
            self.cache.metrics.total_miss_latency_ms += miss_latency

            return result

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def _direct_search(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Direct SQLite search fallback."""
        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        if not db_path.exists():
            return []

        conn = sqlite3.connect(str(db_path))
        try:
            # Check observations table schema
            cursor = conn.execute("PRAGMA table_info(observations)")
            obs_columns = [row[1] for row in cursor.fetchall()]

            # Determine the correct column name for observation content
            obs_col = None
            if 'content' in obs_columns:
                obs_col = 'content'
            elif 'observation' in obs_columns:
                obs_col = 'observation'

            if obs_col:
                # Search with observations join
                cursor = conn.execute(
                    f"""
                    SELECT DISTINCT e.name, e.entity_type, o.{obs_col}, e.created_at
                    FROM entities e
                    LEFT JOIN observations o ON e.id = o.entity_id
                    WHERE e.name LIKE ? OR o.{obs_col} LIKE ?
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", limit)
                )

                results = []
                for row in cursor.fetchall():
                    results.append({
                        "name": row[0],
                        "entity_type": row[1],
                        "observation": row[2],
                        "created_at": row[3]
                    })
            else:
                # Fallback to entities-only search
                cursor = conn.execute(
                    """
                    SELECT name, entity_type, created_at
                    FROM entities
                    WHERE name LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit)
                )

                results = []
                for row in cursor.fetchall():
                    results.append({
                        "name": row[0],
                        "entity_type": row[1],
                        "observation": None,
                        "created_at": row[2]
                    })
            return results
        except Exception as e:
            logger.warning(f"Direct search failed: {e}")
            return []
        finally:
            conn.close()

    async def nmf_recall(
        self,
        query: str,
        mode: str = "hybrid",
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Cache-first Neural Memory Fabric recall."""
        context = {"mode": mode, "limit": limit, **kwargs}

        cached = await self.cache.get(f"nmf:{query}", context)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                pass

        # Execute actual NMF recall
        if hasattr(self.memory_client, 'nmf_recall'):
            result = await self.memory_client.nmf_recall(query, mode=mode, limit=limit)
        else:
            result = await self.search_nodes(query, limit=limit)

        result_json = json.dumps(result, default=str)
        await self.cache.store(f"nmf:{query}", result_json, context)

        return result

    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get FACT cache performance metrics."""
        return self.cache.get_metrics()


# Global instance for easy access
_fact_cache: Optional[FACTCacheManager] = None
_fact_wrapper: Optional[FACTEnhancedMemoryWrapper] = None


def get_fact_cache() -> FACTCacheManager:
    """Get or create global FACT cache manager."""
    global _fact_cache
    if _fact_cache is None:
        _fact_cache = FACTCacheManager()
    return _fact_cache


def get_fact_wrapper(memory_client=None) -> FACTEnhancedMemoryWrapper:
    """Get or create global FACT wrapper."""
    global _fact_wrapper
    if _fact_wrapper is None:
        _fact_wrapper = FACTEnhancedMemoryWrapper(
            memory_client=memory_client,
            cache_manager=get_fact_cache()
        )
    return _fact_wrapper


async def fact_cached_search(
    query: str,
    limit: int = 10,
    **kwargs
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function for FACT-cached search.

    Returns:
        Tuple of (results, metrics)
    """
    wrapper = get_fact_wrapper()
    results = await wrapper.search_nodes(query, limit=limit, **kwargs)
    metrics = wrapper.get_cache_metrics()
    return results, metrics


# MCP Tool Registration
def register_fact_tools(app, memory_client=None):
    """Register FACT caching tools with FastMCP app."""

    wrapper = get_fact_wrapper(memory_client)

    @app.tool()
    async def fact_search(
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        FACT-accelerated memory search with cache-first retrieval.

        Performance: <48ms on cache hit, <140ms on miss.

        Args:
            query: Search query
            limit: Maximum results (default: 10)

        Returns:
            Search results with performance metrics
        """
        start = time.perf_counter()
        results = await wrapper.search_nodes(query, limit=limit)
        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "results": results,
            "result_count": len(results),
            "latency_ms": round(latency_ms, 2),
            "cache_metrics": wrapper.get_cache_metrics()
        }

    @app.tool()
    async def fact_cache_status() -> Dict[str, Any]:
        """
        Get FACT cache performance metrics.

        Returns hit rate, latency stats, and cache health.
        """
        return wrapper.get_cache_metrics()

    @app.tool()
    async def fact_cache_clear_expired() -> Dict[str, Any]:
        """
        Clear expired entries from FACT cache.

        Returns count of entries removed.
        """
        removed = await wrapper.cache.clear_expired()
        return {
            "entries_removed": removed,
            "cache_metrics": wrapper.get_cache_metrics()
        }

    @app.tool()
    async def fact_warm_cache(
        queries: List[str],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Warm the FACT cache with common queries.

        Pre-populates cache for faster subsequent access.

        Args:
            queries: List of queries to warm
            limit: Results per query (default: 10)

        Returns:
            Warming results and timing
        """
        start = time.perf_counter()
        warmed = 0

        for query in queries:
            try:
                await wrapper.search_nodes(query, limit=limit)
                warmed += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for '{query}': {e}")

        latency_ms = (time.perf_counter() - start) * 1000

        return {
            "queries_warmed": warmed,
            "total_queries": len(queries),
            "total_latency_ms": round(latency_ms, 2),
            "cache_metrics": wrapper.get_cache_metrics()
        }

    logger.info("FACT caching tools registered successfully")
    return wrapper


if __name__ == "__main__":
    # Test the integration
    import asyncio

    async def test():
        cache = FACTCacheManager()

        # Test store and retrieve
        test_query = "test query for FACT cache"
        test_result = json.dumps({"results": [{"name": "test", "score": 0.95}]})

        stored = await cache.store(test_query, test_result)
        print(f"Stored: {stored}")

        retrieved = await cache.get(test_query)
        print(f"Retrieved: {retrieved}")

        print(f"Metrics: {cache.get_metrics()}")

    asyncio.run(test())
