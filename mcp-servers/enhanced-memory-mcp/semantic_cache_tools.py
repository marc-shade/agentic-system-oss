#!/usr/bin/env python3
"""
Semantic Cache MCP Tools - Wire semantic caching into enhanced-memory-mcp

Provides MCP tools for:
- Caching expensive LLM/reasoning results with semantic similarity matching
- 30-40% cache hit rate expected with 0.90-0.92 similarity threshold
- Sub-50ms retrieval vs 2000ms+ API calls

This wires the existing semantic_cache_module.py into the MCP tool ecosystem.
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add scripts path to access semantic cache module
SCRIPTS_PATH = Path("/mnt/agentic-system/scripts")
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

logger = logging.getLogger("semantic_cache_tools")

# Lazy-load semantic cache to avoid startup delays
_cache_instance = None
_agi_cache_instances = {}


def _get_semantic_cache():
    """Lazy-load the semantic cache module."""
    global _cache_instance
    if _cache_instance is None:
        try:
            from semantic_cache_module import SemanticCache
            _cache_instance = SemanticCache(
                similarity_threshold=0.90,
                ttl_hours=24,
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("SemanticCache initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize SemanticCache: {e}")
            raise
    return _cache_instance


def _get_agi_cache(domain: str = "general"):
    """Get or create AGI-optimized cache for a domain."""
    global _agi_cache_instances
    if domain not in _agi_cache_instances:
        try:
            from agi_semantic_cache_integration import AGISemanticCache
            _agi_cache_instances[domain] = AGISemanticCache(cache_domain=domain)
            logger.info(f"AGISemanticCache[{domain}] initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize AGISemanticCache[{domain}]: {e}")
            raise
    return _agi_cache_instances[domain]


def register_semantic_cache_tools(app):
    """Register semantic cache MCP tools."""

    @app.tool()
    async def semantic_cache_get(
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check semantic cache for similar query.

        Returns cached response if similarity >= 0.90 threshold.
        Use this BEFORE expensive LLM/reasoning operations.

        Args:
            query: Query string to search for
            context: Optional context for context-aware matching

        Returns:
            Dict with 'hit' (bool), 'response', 'similarity', 'latency_ms'
        """
        import time
        start = time.time()

        try:
            cache = _get_semantic_cache()
            result = cache.get(query, context=context)
            latency = (time.time() - start) * 1000

            if result:
                response, similarity = result
                return {
                    "hit": True,
                    "response": response,
                    "similarity": round(similarity, 4),
                    "latency_ms": round(latency, 1),
                    "message": f"Cache HIT (similarity: {similarity:.4f})"
                }
            else:
                return {
                    "hit": False,
                    "response": None,
                    "similarity": 0.0,
                    "latency_ms": round(latency, 1),
                    "message": "Cache MISS - proceed with expensive operation"
                }
        except Exception as e:
            return {
                "hit": False,
                "error": str(e),
                "message": "Cache lookup failed - proceed without caching"
            }

    @app.tool()
    async def semantic_cache_store(
        query: str,
        response: str,
        context: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Store query-response pair in semantic cache.

        Call this AFTER successful expensive operations to cache the result.

        Args:
            query: Query that was processed
            response: Result to cache
            context: Optional context for context-aware caching
            metadata: Optional metadata dict

        Returns:
            Dict with 'success', 'message'
        """
        try:
            cache = _get_semantic_cache()
            cache.store(query, response, context=context, metadata=metadata)
            return {
                "success": True,
                "message": f"Stored in cache: {query[:60]}..."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store in cache"
            }

    @app.tool()
    async def semantic_cache_stats() -> Dict[str, Any]:
        """
        Get semantic cache statistics.

        Returns hit rate, entry counts, top cached queries.
        Use to monitor cache effectiveness.

        Returns:
            Dict with comprehensive cache statistics
        """
        try:
            cache = _get_semantic_cache()
            stats = cache.get_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get cache stats"
            }

    @app.tool()
    async def semantic_cache_search(
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Search for top-k most similar cached queries.

        Use for analysis and debugging cache content.
        Does NOT update access stats.

        Args:
            query: Query to search for
            top_k: Number of results to return (default: 5)

        Returns:
            Dict with 'results' list of (query, response, similarity) tuples
        """
        try:
            cache = _get_semantic_cache()
            results = cache.search_similar(query, top_k=top_k)

            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "cached_query": q[:100],
                        "response_preview": r[:200] + "..." if len(r) > 200 else r,
                        "similarity": round(sim, 4)
                    }
                    for q, r, sim in results
                ]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def semantic_cache_cleanup(
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up expired cache entries.

        Args:
            force: If True, delete ALL entries regardless of TTL

        Returns:
            Dict with 'deleted' count
        """
        try:
            cache = _get_semantic_cache()
            deleted = cache.cleanup(force=force)
            return {
                "success": True,
                "deleted": deleted,
                "message": f"Cleaned up {deleted} entries" + (" (FORCE: all entries)" if force else "")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def agi_cached_reasoning(
        query: str,
        domain: str = "reasoning",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AGI-optimized cache check for reasoning tasks.

        Domains have optimized thresholds:
        - reasoning: 0.92 threshold, 24h TTL (high precision)
        - consolidation: 0.90 threshold, 7d TTL (pattern caching)
        - research: 0.88 threshold, 3d TTL (research insights)
        - api_calls: 0.90 threshold, 24h TTL (API responses)
        - embeddings: 0.95 threshold, 7d TTL (cached embeddings)

        Args:
            query: Reasoning query
            domain: Cache domain (reasoning, consolidation, research, api_calls, embeddings)
            context: Optional context

        Returns:
            Dict with 'hit', 'response', 'similarity', 'domain_config'
        """
        import time
        start = time.time()

        try:
            agi_cache = _get_agi_cache(domain)

            # Check cache
            cached = agi_cache.cache.get(query, context=context)
            latency = (time.time() - start) * 1000

            if cached:
                response, similarity = cached
                agi_cache.metrics["cache_hits"] += 1

                # Try to deserialize JSON
                try:
                    parsed_response = json.loads(response)
                except (json.JSONDecodeError, TypeError):
                    parsed_response = response

                return {
                    "hit": True,
                    "response": parsed_response,
                    "similarity": round(similarity, 4),
                    "latency_ms": round(latency, 1),
                    "domain": domain,
                    "domain_config": agi_cache.DOMAINS.get(domain, {}),
                    "message": f"AGI Cache HIT [{domain}] (similarity: {similarity:.4f})"
                }
            else:
                agi_cache.metrics["cache_misses"] += 1
                return {
                    "hit": False,
                    "response": None,
                    "similarity": 0.0,
                    "latency_ms": round(latency, 1),
                    "domain": domain,
                    "domain_config": agi_cache.DOMAINS.get(domain, {}),
                    "message": f"AGI Cache MISS [{domain}] - proceed with expensive operation"
                }
        except Exception as e:
            return {
                "hit": False,
                "error": str(e),
                "domain": domain,
                "message": "AGI cache lookup failed"
            }

    @app.tool()
    async def agi_cache_store_result(
        query: str,
        response: Any,
        domain: str = "reasoning",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store AGI reasoning result in domain-specific cache.

        Args:
            query: The reasoning query
            response: Result to cache (can be dict/list/str)
            domain: Cache domain
            context: Optional context

        Returns:
            Dict with 'success', 'domain'
        """
        try:
            agi_cache = _get_agi_cache(domain)

            # Serialize if needed
            if isinstance(response, (dict, list)):
                response_str = json.dumps(response)
            else:
                response_str = str(response)

            agi_cache.cache.store(query, response_str, context=context)
            agi_cache.metrics["calls"] += 1

            return {
                "success": True,
                "domain": domain,
                "message": f"Stored in AGI cache [{domain}]"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "domain": domain
            }

    @app.tool()
    async def agi_cache_metrics(
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get AGI cache metrics for all or specific domain.

        Args:
            domain: Optional domain filter. If None, returns all domains.

        Returns:
            Dict with domain metrics including hit rate, latency saved
        """
        try:
            if domain:
                agi_cache = _get_agi_cache(domain)
                return {
                    "success": True,
                    "metrics": agi_cache.get_metrics()
                }
            else:
                # Return all initialized domains
                all_metrics = {}
                for d, cache in _agi_cache_instances.items():
                    all_metrics[d] = cache.get_metrics()

                # Also list available domains
                from agi_semantic_cache_integration import AGISemanticCache

                return {
                    "success": True,
                    "initialized_domains": list(_agi_cache_instances.keys()),
                    "available_domains": list(AGISemanticCache.DOMAINS.keys()),
                    "domain_configs": AGISemanticCache.DOMAINS,
                    "metrics": all_metrics
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def semantic_cache_available() -> Dict[str, Any]:
        """
        Check if semantic cache is available and functioning.

        Returns:
            Dict with 'available', 'model_loaded', 'cache_initialized'
        """
        result = {
            "cache_available": False,
            "agi_cache_available": False,
            "model_name": "all-MiniLM-L6-v2",
            "features": [],
            "domains": []
        }

        # Check basic cache
        try:
            cache = _get_semantic_cache()
            result["cache_available"] = True
            result["features"].append("basic_semantic_cache")
        except Exception as e:
            result["cache_error"] = str(e)

        # Check AGI cache
        try:
            from agi_semantic_cache_integration import AGISemanticCache
            result["agi_cache_available"] = True
            result["features"].append("agi_domain_caching")
            result["domains"] = list(AGISemanticCache.DOMAINS.keys())
        except Exception as e:
            result["agi_cache_error"] = str(e)

        result["message"] = (
            "Semantic caching fully available"
            if result["cache_available"] and result["agi_cache_available"]
            else "Semantic caching partially available"
        )

        return result

    logger.info("Registered 9 semantic cache MCP tools")
    return True
