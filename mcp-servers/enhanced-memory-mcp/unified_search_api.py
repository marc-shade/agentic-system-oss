"""
Unified Search API - Intelligent Routing between FACT Cache and Qdrant

Provides a single search interface that:
1. Checks FACT cache first (sub-ms latency)
2. Falls back to Qdrant semantic search on cache miss
3. Caches Qdrant results for future queries
4. Tracks performance metrics for optimization

Performance targets:
- Cache hit: <1ms
- Cache miss (with Qdrant): <200ms
- Overall hit rate: 70%+
"""

import asyncio
import json
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("unified-search")


class SearchBackend(Enum):
    """Search backend options."""
    FACT_CACHE = "fact_cache"
    QDRANT = "qdrant"
    HYBRID = "hybrid"  # BM25 + Vector
    SEMANTIC = "semantic"


@dataclass
class SearchMetrics:
    """Track search performance across backends."""
    fact_hits: int = 0
    fact_misses: int = 0
    qdrant_calls: int = 0
    hybrid_calls: int = 0
    total_queries: int = 0
    total_latency_ms: float = 0
    fact_latency_ms: float = 0
    qdrant_latency_ms: float = 0

    @property
    def fact_hit_rate(self) -> float:
        total = self.fact_hits + self.fact_misses
        return self.fact_hits / total if total > 0 else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_queries if self.total_queries > 0 else 0.0


@dataclass
class SearchResult:
    """Unified search result."""
    results: List[Dict[str, Any]]
    backend: SearchBackend
    latency_ms: float
    from_cache: bool
    query: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedSearchAPI:
    """
    Unified search API with intelligent routing.

    Combines FACT cache for speed with Qdrant for semantic search.
    Enhanced with MIRAS-style ART category boosting for pattern-aware retrieval.
    """

    # ART integration parameters
    ART_BOOST_FACTOR = 1.25  # Boost for matching known patterns
    ART_MIN_MATCH_SCORE = 0.6  # Minimum ART match to apply boost

    def __init__(
        self,
        fact_wrapper=None,
        qdrant_client=None,
        nmf_instance=None,
        cache_semantic_results: bool = True,
        cache_ttl_seconds: int = 3600,
        enable_art_boost: bool = True
    ):
        """
        Initialize unified search.

        Args:
            fact_wrapper: FACTEnhancedMemoryWrapper instance
            qdrant_client: Qdrant client for vector search
            nmf_instance: Neural Memory Fabric instance for hybrid search
            cache_semantic_results: Whether to cache Qdrant results
            cache_ttl_seconds: TTL for cached results
            enable_art_boost: Enable ART category boosting for results
        """
        self.fact_wrapper = fact_wrapper
        self.qdrant_client = qdrant_client
        self.nmf_instance = nmf_instance
        self.cache_semantic_results = cache_semantic_results
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_art_boost = enable_art_boost

        self.metrics = SearchMetrics()

        # ART integration
        self._art_instance = None

        # Lazy initialization
        self._initialized = False

    def _get_art_instance(self):
        """Lazy load ART instance for category boosting."""
        if self._art_instance is None and self.enable_art_boost:
            try:
                from art_tools import get_art_instance
                self._art_instance = get_art_instance()
                logger.info("ART instance loaded for category boosting")
            except Exception as e:
                logger.warning(f"Could not load ART instance: {e}")
                self.enable_art_boost = False
        return self._art_instance

    def _apply_art_boost(
        self,
        results: List[Dict[str, Any]],
        query_embedding: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply ART category boosting to search results.

        MIRAS Integration: Results matching learned patterns get boosted.
        This helps surface content that matches known valuable patterns.

        Args:
            results: Search results to boost
            query_embedding: Optional query embedding for ART matching

        Returns:
            Results with ART-boosted scores
        """
        if not self.enable_art_boost or not results:
            return results

        art = self._get_art_instance()
        if not art or not art.categories:
            return results

        import numpy as np

        boosted_results = []
        for result in results:
            # Get result embedding if available
            embedding = result.get('embedding') or result.get('vector')

            if embedding:
                try:
                    # Check if result matches any ART category
                    input_array = np.array(embedding, dtype=np.float32)
                    coded = art._complement_code(input_array)

                    best_match_score = 0.0
                    matched_category = None

                    for category in art.categories:
                        match_score = art._match_function(coded, category.prototype)
                        if match_score > best_match_score:
                            best_match_score = match_score
                            matched_category = category

                    # Apply boost if strong match
                    if best_match_score >= self.ART_MIN_MATCH_SCORE:
                        original_score = result.get('score', 0.5)
                        boosted_score = min(1.0, original_score * self.ART_BOOST_FACTOR)

                        result = result.copy()
                        result['score'] = boosted_score
                        result['art_boost'] = {
                            'original_score': original_score,
                            'match_score': float(best_match_score),
                            'category_id': matched_category.id if matched_category else None,
                            'boost_applied': True
                        }
                        logger.debug(f"ART boost applied: {original_score:.3f} -> {boosted_score:.3f}")

                except Exception as e:
                    logger.debug(f"ART boost failed for result: {e}")

            boosted_results.append(result)

        # Re-sort by boosted scores
        boosted_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return boosted_results

    def _ensure_initialized(self):
        """Ensure FACT wrapper is initialized."""
        if self._initialized:
            return

        if self.fact_wrapper is None:
            from fact_integration import get_fact_wrapper
            self.fact_wrapper = get_fact_wrapper()

        self._initialized = True

    async def search(
        self,
        query: str,
        limit: int = 10,
        backend: SearchBackend = SearchBackend.FACT_CACHE,
        bypass_cache: bool = False,
        **kwargs
    ) -> SearchResult:
        """
        Execute unified search with intelligent routing.

        Flow:
        1. If FACT_CACHE or auto: Check cache first
        2. On cache hit: Return immediately
        3. On cache miss: Execute backend search
        4. Cache result if enabled
        5. Return with metrics

        Args:
            query: Search query
            limit: Maximum results
            backend: Preferred backend (will still check cache first)
            bypass_cache: Skip cache lookup (for testing)
            **kwargs: Additional backend-specific parameters

        Returns:
            SearchResult with results, backend info, and latency
        """
        self._ensure_initialized()
        start = time.perf_counter()
        self.metrics.total_queries += 1

        # Step 1: Try FACT cache first (unless bypassed)
        if not bypass_cache and self.fact_wrapper:
            cache_start = time.perf_counter()
            cached = await self.fact_wrapper.cache.get(query, {"limit": limit, **kwargs})
            cache_latency = (time.perf_counter() - cache_start) * 1000

            if cached:
                self.metrics.fact_hits += 1
                self.metrics.fact_latency_ms += cache_latency

                try:
                    results = json.loads(cached)
                    total_latency = (time.perf_counter() - start) * 1000
                    self.metrics.total_latency_ms += total_latency

                    return SearchResult(
                        results=results if isinstance(results, list) else results.get("results", []),
                        backend=SearchBackend.FACT_CACHE,
                        latency_ms=total_latency,
                        from_cache=True,
                        query=query,
                        metadata={"cache_latency_ms": cache_latency}
                    )
                except json.JSONDecodeError:
                    pass  # Cache corruption, continue to backend

            self.metrics.fact_misses += 1

        # Step 2: Execute backend search
        results = []
        backend_used = backend

        if backend == SearchBackend.QDRANT and self.qdrant_client:
            results = await self._search_qdrant(query, limit, **kwargs)
            self.metrics.qdrant_calls += 1

        elif backend == SearchBackend.HYBRID and self.nmf_instance:
            results = await self._search_hybrid(query, limit, **kwargs)
            self.metrics.hybrid_calls += 1

        elif backend == SearchBackend.SEMANTIC and self.nmf_instance:
            results = await self._search_semantic(query, limit, **kwargs)
            self.metrics.qdrant_calls += 1

        else:
            # Fallback to direct memory search
            results = await self._search_direct(query, limit)
            backend_used = SearchBackend.FACT_CACHE

        # Step 3: Apply ART category boosting (MIRAS integration)
        art_boost_applied = False
        if self.enable_art_boost and results:
            original_count = len(results)
            results = self._apply_art_boost(results)
            art_boost_applied = any(r.get('art_boost', {}).get('boost_applied') for r in results)
            if art_boost_applied:
                logger.debug(f"ART boost applied to {sum(1 for r in results if r.get('art_boost'))} of {original_count} results")

        # Step 4: Cache result if enabled
        if self.cache_semantic_results and self.fact_wrapper and results:
            result_json = json.dumps(results, default=str)
            await self.fact_wrapper.cache.store(
                query,
                result_json,
                {"limit": limit, **kwargs},
                ttl_seconds=self.cache_ttl_seconds
            )

        total_latency = (time.perf_counter() - start) * 1000
        self.metrics.total_latency_ms += total_latency

        return SearchResult(
            results=results,
            backend=backend_used,
            latency_ms=total_latency,
            from_cache=False,
            query=query,
            metadata={
                "cached_for_future": self.cache_semantic_results,
                "art_boost_applied": art_boost_applied
            }
        )

    async def _search_qdrant(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute Qdrant vector search."""
        if not self.qdrant_client:
            return []

        try:
            # Use NMF for embedding generation if available
            if self.nmf_instance:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                embedding = model.encode(query).tolist()

                results = self.qdrant_client.search(
                    collection_name="enhanced_memories",
                    query_vector=embedding,
                    limit=limit,
                    **kwargs
                )

                return [
                    {
                        "id": str(r.id),
                        "score": r.score,
                        "payload": r.payload
                    }
                    for r in results
                ]
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}")

        return []

    async def _search_hybrid(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute hybrid BM25 + Vector search."""
        if not self.nmf_instance:
            return await self._search_direct(query, limit)

        try:
            # Use NMF's hybrid search if available
            if hasattr(self.nmf_instance, 'hybrid_search'):
                results = await self.nmf_instance.hybrid_search(query, limit=limit)
                return results
        except Exception as e:
            logger.warning(f"Hybrid search failed: {e}")

        return await self._search_direct(query, limit)

    async def _search_semantic(
        self,
        query: str,
        limit: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute semantic search via NMF."""
        if not self.nmf_instance:
            return await self._search_direct(query, limit)

        try:
            if hasattr(self.nmf_instance, 'recall'):
                results = await self.nmf_instance.recall(query, mode="semantic", limit=limit)
                return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")

        return await self._search_direct(query, limit)

    async def _search_direct(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Direct SQLite search fallback."""
        import sqlite3

        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(str(db_path))
            # First check table schema
            cursor = conn.execute("PRAGMA table_info(entities)")
            columns = [row[1] for row in cursor.fetchall()]

            # Build query based on available columns
            if 'compressed_data' in columns:
                # New schema
                cursor = conn.execute(
                    """
                    SELECT id, name, entity_type, created_at
                    FROM entities
                    WHERE name LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (f"%{query}%", limit)
                )
            else:
                # Legacy schema
                cursor = conn.execute(
                    """
                    SELECT id, name, entity_type, created_at
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
                    "id": row[0],
                    "name": row[1],
                    "entity_type": row[2],
                    "created_at": row[3]
                })
            conn.close()
            return results
        except Exception as e:
            logger.warning(f"Direct search failed: {e}")
            return []

    def get_metrics(self) -> Dict[str, Any]:
        """Get search performance metrics."""
        return {
            "fact_hit_rate": self.metrics.fact_hit_rate,
            "fact_hits": self.metrics.fact_hits,
            "fact_misses": self.metrics.fact_misses,
            "qdrant_calls": self.metrics.qdrant_calls,
            "hybrid_calls": self.metrics.hybrid_calls,
            "total_queries": self.metrics.total_queries,
            "avg_latency_ms": self.metrics.avg_latency_ms,
            "total_latency_ms": self.metrics.total_latency_ms
        }

    async def warm_cache(
        self,
        common_queries: List[str],
        limit: int = 10,
        backend: SearchBackend = SearchBackend.FACT_CACHE
    ) -> Dict[str, Any]:
        """
        Pre-warm cache with common queries.

        Args:
            common_queries: List of queries to warm
            limit: Results per query
            backend: Backend to use for warming

        Returns:
            Warming statistics
        """
        start = time.perf_counter()
        warmed = 0
        failed = 0

        for query in common_queries:
            try:
                await self.search(query, limit=limit, backend=backend, bypass_cache=True)
                warmed += 1
            except Exception as e:
                logger.warning(f"Failed to warm cache for '{query}': {e}")
                failed += 1

        total_time = (time.perf_counter() - start) * 1000

        return {
            "queries_warmed": warmed,
            "queries_failed": failed,
            "total_time_ms": total_time,
            "avg_time_per_query_ms": total_time / len(common_queries) if common_queries else 0
        }


# Global instance
_unified_api: Optional[UnifiedSearchAPI] = None


def get_unified_search_api(**kwargs) -> UnifiedSearchAPI:
    """Get or create global unified search API."""
    global _unified_api
    if _unified_api is None:
        _unified_api = UnifiedSearchAPI(**kwargs)
    return _unified_api


# MCP Tool Registration
def register_unified_search_tools(app, nmf_instance=None, qdrant_client=None):
    """Register unified search tools with FastMCP app."""

    api = get_unified_search_api(nmf_instance=nmf_instance, qdrant_client=qdrant_client)

    @app.tool()
    async def unified_search(
        query: str,
        limit: int = 10,
        backend: str = "fact_cache"
    ) -> Dict[str, Any]:
        """
        Unified search with FACT cache and Qdrant fallback.

        Intelligent routing:
        - First checks FACT cache (<1ms)
        - Falls back to Qdrant on miss
        - Caches results for future queries

        Args:
            query: Search query
            limit: Maximum results (default: 10)
            backend: Search backend - fact_cache, qdrant, hybrid, semantic

        Returns:
            Search results with performance metrics
        """
        backend_enum = SearchBackend(backend) if backend in [b.value for b in SearchBackend] else SearchBackend.FACT_CACHE

        result = await api.search(query, limit=limit, backend=backend_enum)

        return {
            "results": result.results,
            "result_count": len(result.results),
            "backend": result.backend.value,
            "latency_ms": round(result.latency_ms, 2),
            "from_cache": result.from_cache,
            "metrics": api.get_metrics()
        }

    @app.tool()
    async def unified_search_metrics() -> Dict[str, Any]:
        """
        Get unified search performance metrics.

        Shows cache hit rates, latency, and backend usage.
        """
        return api.get_metrics()

    @app.tool()
    async def unified_search_warm(
        queries: List[str],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Warm the unified search cache with common queries.

        Pre-populates cache for faster subsequent access.

        Args:
            queries: List of common queries to warm
            limit: Results per query (default: 10)

        Returns:
            Warming statistics
        """
        return await api.warm_cache(queries, limit=limit)

    logger.info("Unified Search API tools registered")
    return api


if __name__ == "__main__":
    # Test the unified API
    import asyncio

    async def test():
        api = UnifiedSearchAPI()

        # Test search
        result = await api.search("test query", limit=5)
        print(f"Search result: {result}")
        print(f"Backend: {result.backend.value}")
        print(f"Latency: {result.latency_ms:.2f}ms")
        print(f"From cache: {result.from_cache}")
        print(f"Metrics: {api.get_metrics()}")

    asyncio.run(test())
