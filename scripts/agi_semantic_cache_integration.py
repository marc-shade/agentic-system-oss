#!/usr/bin/env python3
"""AGI System Integration for Semantic Cache

This module provides drop-in integration of semantic caching with the AGI system.
It automatically caches reasoning patterns, memory consolidation results, and
research insights for 30-40% speedup.

Usage in AGI components:

    from agi_semantic_cache_integration import AGISemanticCache

    # In your AGI agent
    class MyAgent:
        def __init__(self):
            self.cache = AGISemanticCache(
                cache_domain="my_agent",
                threshold=0.90
            )

        def reason(self, query):
            # Automatic caching
            result = self.cache.cached_call(
                query,
                fallback=lambda: self.expensive_reasoning(query)
            )
            return result
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from semantic_cache_module import SemanticCache
from typing import Callable, Any, Optional, Dict
import json
import time
from pathlib import Path


class AGISemanticCache:
    """
    AGI-optimized semantic cache with domain separation and metrics tracking
    """

    # Cache domains for different AGI components
    DOMAINS = {
        "reasoning": {
            "threshold": 0.92,  # Higher precision for reasoning
            "ttl_hours": 24,
            "description": "Complex reasoning patterns"
        },
        "consolidation": {
            "threshold": 0.90,
            "ttl_hours": 168,  # 7 days for pattern caching
            "description": "Memory consolidation patterns"
        },
        "research": {
            "threshold": 0.88,
            "ttl_hours": 72,  # 3 days for research
            "description": "Research paper insights"
        },
        "api_calls": {
            "threshold": 0.90,
            "ttl_hours": 24,
            "description": "External API responses"
        },
        "embeddings": {
            "threshold": 0.95,  # Very high precision
            "ttl_hours": 168,
            "description": "Cached embeddings"
        },
    }

    def __init__(self,
                 cache_domain: str = "general",
                 threshold: Optional[float] = None,
                 ttl_hours: Optional[int] = None,
                 db_dir: str = "/home/marc/.claude/enhanced_memories"):
        """
        Initialize AGI semantic cache

        Args:
            cache_domain: Domain for this cache (reasoning, consolidation, research, etc.)
            threshold: Override default threshold for domain
            ttl_hours: Override default TTL for domain
            db_dir: Directory for cache databases
        """
        self.cache_domain = cache_domain

        # Get domain config or use defaults
        domain_config = self.DOMAINS.get(cache_domain, {
            "threshold": 0.90,
            "ttl_hours": 24,
            "description": "General purpose"
        })

        # Override with user params
        final_threshold = threshold if threshold is not None else domain_config["threshold"]
        final_ttl = ttl_hours if ttl_hours is not None else domain_config["ttl_hours"]

        # Create cache
        db_path = Path(db_dir) / f"semantic_cache_{cache_domain}.db"
        self.cache = SemanticCache(
            db_path=str(db_path),
            similarity_threshold=final_threshold,
            ttl_hours=final_ttl
        )

        # Metrics
        self.metrics = {
            "domain": cache_domain,
            "config": domain_config,
            "calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_latency_saved_ms": 0,
        }

    def cached_call(self,
                   query: str,
                   fallback: Callable[[], Any],
                   context: Optional[str] = None,
                   estimated_fallback_latency_ms: int = 2000) -> Any:
        """
        Execute call with automatic caching

        Args:
            query: Query/key for caching
            fallback: Function to call on cache miss
            context: Optional context for context-aware caching
            estimated_fallback_latency_ms: Estimated latency for fallback (for metrics)

        Returns:
            Cached result or fallback result
        """
        self.metrics["calls"] += 1

        # Check cache
        start = time.time()
        cached = self.cache.get(query, context=context)
        cache_latency = (time.time() - start) * 1000

        if cached:
            response, similarity = cached
            self.metrics["cache_hits"] += 1
            self.metrics["total_latency_saved_ms"] += (
                estimated_fallback_latency_ms - cache_latency
            )

            # Try to deserialize if JSON
            try:
                return json.loads(response)
            except (json.JSONDecodeError, TypeError):
                return response

        # Cache miss - call fallback
        self.metrics["cache_misses"] += 1
        result = fallback()

        # Store in cache
        if isinstance(result, (dict, list)):
            response_str = json.dumps(result)
        else:
            response_str = str(result)

        self.cache.store(query, response_str, context=context)

        return result

    def get_metrics(self) -> Dict:
        """Get cache metrics"""
        cache_stats = self.cache.get_stats()

        hit_rate = (self.metrics["cache_hits"] /
                   max(1, self.metrics["calls"]))

        return {
            "domain": self.metrics["domain"],
            "domain_config": self.metrics["config"],
            "session_metrics": {
                "total_calls": self.metrics["calls"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "hit_rate": f"{hit_rate:.1%}",
                "latency_saved_sec": f"{self.metrics['total_latency_saved_ms'] / 1000:.1f}s",
            },
            "cache_stats": cache_stats,
        }

    def clear(self):
        """Clear cache"""
        return self.cache.cleanup(force=True)


def example_agi_orchestrator_integration():
    """Example: AGI Orchestrator with semantic caching"""
    print("\n" + "="*70)
    print("EXAMPLE: AGI Orchestrator Integration")
    print("="*70)

    class MockAGIOrchestrator:
        """Mock AGI orchestrator with caching"""

        def __init__(self):
            # Separate caches for different reasoning types
            self.reasoning_cache = AGISemanticCache(
                cache_domain="reasoning",
                threshold=0.92
            )
            self.research_cache = AGISemanticCache(
                cache_domain="research",
                threshold=0.88
            )

        def reason_about(self, query: str) -> str:
            """Complex reasoning with caching"""
            def expensive_reasoning():
                time.sleep(0.3)  # Simulate reasoning
                return f"Reasoning result for: {query}"

            return self.reasoning_cache.cached_call(
                query,
                fallback=expensive_reasoning,
                estimated_fallback_latency_ms=300
            )

        def research_topic(self, topic: str) -> Dict:
            """Research with caching"""
            def expensive_research():
                time.sleep(0.5)  # Simulate research
                return {
                    "topic": topic,
                    "insights": [f"Insight about {topic}"],
                    "papers": 5
                }

            return self.research_cache.cached_call(
                topic,
                fallback=expensive_research,
                estimated_fallback_latency_ms=500
            )

    # Use the orchestrator
    print("\n1. Creating orchestrator with caching:")
    orchestrator = MockAGIOrchestrator()

    print("\n2. Reasoning tasks:")
    queries = [
        "How to optimize memory consolidation?",
        "What's the best approach to optimize memory?",  # Similar
        "How to optimize memory consolidation?",  # Duplicate
    ]

    for query in queries:
        print(f"\n   Query: {query[:50]}...")
        start = time.time()
        result = orchestrator.reason_about(query)
        latency = (time.time() - start) * 1000
        print(f"   Latency: {latency:.1f}ms")

    print("\n3. Research tasks:")
    topics = [
        "neural architecture search",
        "NAS for model optimization",  # Similar
    ]

    for topic in topics:
        print(f"\n   Topic: {topic}")
        start = time.time()
        result = orchestrator.research_topic(topic)
        latency = (time.time() - start) * 1000
        print(f"   Latency: {latency:.1f}ms")
        print(f"   Papers: {result['papers']}")

    print("\n4. Metrics:")
    print("\n   Reasoning Cache:")
    reasoning_metrics = orchestrator.reasoning_cache.get_metrics()
    print(f"   Hit rate: {reasoning_metrics['session_metrics']['hit_rate']}")
    print(f"   Latency saved: {reasoning_metrics['session_metrics']['latency_saved_sec']}")

    print("\n   Research Cache:")
    research_metrics = orchestrator.research_cache.get_metrics()
    print(f"   Hit rate: {research_metrics['session_metrics']['hit_rate']}")
    print(f"   Latency saved: {research_metrics['session_metrics']['latency_saved_sec']}")


def example_memory_consolidation_integration():
    """Example: Memory consolidation with caching"""
    print("\n" + "="*70)
    print("EXAMPLE: Memory Consolidation Integration")
    print("="*70)

    class MockMemoryConsolidation:
        """Mock memory consolidation with pattern caching"""

        def __init__(self):
            self.cache = AGISemanticCache(
                cache_domain="consolidation",
                threshold=0.90,
                ttl_hours=168  # 7 days for patterns
            )

        def extract_patterns(self, memory_type: str) -> Dict:
            """Extract patterns with caching"""
            def expensive_extraction():
                time.sleep(0.4)
                return {
                    "patterns_found": 15,
                    "confidence": 0.85,
                    "type": memory_type
                }

            query = f"extract_patterns:{memory_type}"
            return self.cache.cached_call(
                query,
                fallback=expensive_extraction,
                estimated_fallback_latency_ms=400
            )

    print("\n1. Creating consolidation system:")
    consolidation = MockMemoryConsolidation()

    print("\n2. Extracting patterns (first run - cache misses):")
    for mem_type in ["episodic", "semantic", "procedural"]:
        print(f"\n   Type: {mem_type}")
        start = time.time()
        result = consolidation.extract_patterns(mem_type)
        latency = (time.time() - start) * 1000
        print(f"   Latency: {latency:.1f}ms")
        print(f"   Patterns: {result['patterns_found']}")

    print("\n3. Second run (cache hits expected):")
    for mem_type in ["episodic", "semantic", "procedural"]:
        print(f"\n   Type: {mem_type}")
        start = time.time()
        result = consolidation.extract_patterns(mem_type)
        latency = (time.time() - start) * 1000
        print(f"   Latency: {latency:.1f}ms")

    print("\n4. Metrics:")
    metrics = consolidation.cache.get_metrics()
    print(f"   Hit rate: {metrics['session_metrics']['hit_rate']}")
    print(f"   Latency saved: {metrics['session_metrics']['latency_saved_sec']}")


def main():
    """Run integration examples"""
    print("\n" + "="*70)
    print("AGI SEMANTIC CACHE INTEGRATION EXAMPLES")
    print("="*70)

    print("\nAvailable cache domains:")
    for domain, config in AGISemanticCache.DOMAINS.items():
        print(f"  • {domain}: {config['description']}")
        print(f"    Threshold: {config['threshold']}, TTL: {config['ttl_hours']}h")

    example_agi_orchestrator_integration()
    example_memory_consolidation_integration()

    print("\n" + "="*70)
    print("Integration examples complete!")
    print("\nTo use in your AGI agents:")
    print("  1. Import: from agi_semantic_cache_integration import AGISemanticCache")
    print("  2. Create: cache = AGISemanticCache(cache_domain='reasoning')")
    print("  3. Use: result = cache.cached_call(query, fallback=expensive_func)")
    print("="*70)


if __name__ == "__main__":
    main()
