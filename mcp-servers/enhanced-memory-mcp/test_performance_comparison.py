#!/usr/bin/env python3
"""
Performance Comparison: FACT Cache vs Direct Search

Benchmarks:
1. FACT cache hit latency
2. Direct SQLite search latency
3. Cache miss + search + cache store latency
4. Hit rate over repeated queries
"""

import asyncio
import json
import time
import sys
import statistics
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from fact_integration import FACTCacheManager, FACTEnhancedMemoryWrapper
from unified_search_api import UnifiedSearchAPI, SearchBackend


async def benchmark_cache_hits(iterations: int = 100) -> dict:
    """Benchmark pure cache hit performance."""
    print(f"\n=== Benchmark: Cache Hit Latency ({iterations} iterations) ===")

    cache = FACTCacheManager(
        db_path=Path("/tmp/fact_bench_cache.db"),
        min_tokens=10
    )

    # Pre-populate cache
    test_query = "benchmark query for performance testing"
    test_result = json.dumps({
        "results": [{"name": f"result_{i}", "score": 0.9} for i in range(10)]
    })
    await cache.store(test_query, test_result)

    # Benchmark cache hits
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = await cache.get(test_query)
        latency_us = (time.perf_counter() - start) * 1_000_000  # microseconds
        latencies.append(latency_us)

    avg = statistics.mean(latencies)
    median = statistics.median(latencies)
    p95 = sorted(latencies)[int(iterations * 0.95)]
    p99 = sorted(latencies)[int(iterations * 0.99)]

    print(f"  Avg:    {avg:.2f} µs ({avg/1000:.3f} ms)")
    print(f"  Median: {median:.2f} µs ({median/1000:.3f} ms)")
    print(f"  P95:    {p95:.2f} µs ({p95/1000:.3f} ms)")
    print(f"  P99:    {p99:.2f} µs ({p99/1000:.3f} ms)")

    return {
        "avg_us": avg,
        "median_us": median,
        "p95_us": p95,
        "p99_us": p99
    }


async def benchmark_direct_search(iterations: int = 50) -> dict:
    """Benchmark direct SQLite search (no cache)."""
    print(f"\n=== Benchmark: Direct SQLite Search ({iterations} iterations) ===")

    # Ensure database exists
    db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
    if not db_path.exists():
        print("  ⚠ Memory database not found - skipping direct search benchmark")
        return {"skipped": True}

    import sqlite3

    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            """
            SELECT e.id, e.name, e.entity_type
            FROM entities e
            WHERE e.name LIKE ?
            ORDER BY e.created_at DESC
            LIMIT 10
            """,
            ("%test%",)
        )
        results = cursor.fetchall()
        conn.close()

        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

    avg = statistics.mean(latencies)
    median = statistics.median(latencies)
    p95 = sorted(latencies)[int(iterations * 0.95)]
    p99 = sorted(latencies)[int(iterations * 0.99)]

    print(f"  Avg:    {avg:.2f} ms")
    print(f"  Median: {median:.2f} ms")
    print(f"  P95:    {p95:.2f} ms")
    print(f"  P99:    {p99:.2f} ms")

    return {
        "avg_ms": avg,
        "median_ms": median,
        "p95_ms": p95,
        "p99_ms": p99
    }


async def benchmark_unified_api(iterations: int = 50) -> dict:
    """Benchmark unified search API with cache warming."""
    print(f"\n=== Benchmark: Unified Search API ({iterations} iterations) ===")

    api = UnifiedSearchAPI()

    # First pass: cache misses (cold)
    cold_latencies = []
    queries = [f"test query {i}" for i in range(iterations)]

    print("  Phase 1: Cold cache (misses)...")
    for query in queries:
        start = time.perf_counter()
        result = await api.search(query, limit=5)
        latency_ms = (time.perf_counter() - start) * 1000
        cold_latencies.append(latency_ms)

    # Second pass: cache hits (warm)
    warm_latencies = []
    print("  Phase 2: Warm cache (hits)...")
    for query in queries:
        start = time.perf_counter()
        result = await api.search(query, limit=5)
        latency_ms = (time.perf_counter() - start) * 1000
        warm_latencies.append(latency_ms)

    cold_avg = statistics.mean(cold_latencies)
    warm_avg = statistics.mean(warm_latencies)
    speedup = cold_avg / warm_avg if warm_avg > 0 else float('inf')

    print(f"\n  Cold cache (misses):")
    print(f"    Avg: {cold_avg:.2f} ms")

    print(f"  Warm cache (hits):")
    print(f"    Avg: {warm_avg:.2f} ms")

    print(f"\n  Speedup: {speedup:.1f}x")

    metrics = api.get_metrics()
    print(f"  Hit rate: {metrics['fact_hit_rate']:.0%}")

    return {
        "cold_avg_ms": cold_avg,
        "warm_avg_ms": warm_avg,
        "speedup": speedup,
        "hit_rate": metrics['fact_hit_rate']
    }


async def benchmark_compression_savings(iterations: int = 20) -> dict:
    """Benchmark compression savings on large results."""
    print(f"\n=== Benchmark: Compression Savings ({iterations} iterations) ===")

    cache = FACTCacheManager(
        db_path=Path("/tmp/fact_compress_bench.db"),
        min_tokens=10
    )

    total_original = 0
    total_compressed = 0

    for i in range(iterations):
        # Generate large result
        result = json.dumps({
            "results": [
                {
                    "name": f"entity_{j}",
                    "observations": [f"observation_{k}" * 50 for k in range(20)]
                }
                for j in range(50)
            ]
        })

        original_size = len(result.encode())
        total_original += original_size

        await cache.store(f"large_query_{i}", result)

    metrics = cache.get_metrics()
    compression_ratio = 1 - (metrics['bytes_saved_by_compression'] / total_original) if total_original > 0 else 1

    print(f"  Total original size: {total_original:,} bytes ({total_original/1024/1024:.2f} MB)")
    print(f"  Bytes saved: {metrics['bytes_saved_by_compression']:,} bytes")
    print(f"  Compression ratio: {compression_ratio:.0%}")
    print(f"  Compressions performed: {metrics['compressions']}")

    return {
        "total_original_bytes": total_original,
        "bytes_saved": metrics['bytes_saved_by_compression'],
        "compression_ratio": compression_ratio
    }


async def benchmark_hit_rate_simulation(total_queries: int = 200, unique_ratio: float = 0.3) -> dict:
    """Simulate realistic query patterns to measure hit rate."""
    print(f"\n=== Benchmark: Hit Rate Simulation ({total_queries} queries, {unique_ratio:.0%} unique) ===")

    cache = FACTCacheManager(
        db_path=Path("/tmp/fact_hitrate_bench.db"),
        min_tokens=10
    )

    # Generate query pool (some queries repeat)
    unique_count = int(total_queries * unique_ratio)
    query_pool = [f"query_type_{i}" for i in range(unique_count)]

    import random
    queries = [random.choice(query_pool) for _ in range(total_queries)]

    # Execute queries
    for query in queries:
        cached = await cache.get(query)
        if cached is None:
            # Simulate search result
            result = json.dumps({"results": [{"name": query, "score": 0.9}]})
            await cache.store(query, result)

    metrics = cache.get_metrics()

    print(f"  Total queries: {metrics['total_queries']}")
    print(f"  Cache hits: {metrics['hits']}")
    print(f"  Cache misses: {metrics['misses']}")
    print(f"  Hit rate: {metrics['hit_rate']:.1%}")

    return {
        "total_queries": metrics['total_queries'],
        "hits": metrics['hits'],
        "misses": metrics['misses'],
        "hit_rate": metrics['hit_rate']
    }


async def run_all_benchmarks():
    """Run all performance benchmarks."""
    print("=" * 70)
    print("FACT Integration Performance Benchmarks")
    print("=" * 70)

    results = {}

    # Run benchmarks
    results['cache_hits'] = await benchmark_cache_hits()
    results['direct_search'] = await benchmark_direct_search()
    results['unified_api'] = await benchmark_unified_api()
    results['compression'] = await benchmark_compression_savings()
    results['hit_rate'] = await benchmark_hit_rate_simulation()

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    cache_hit_ms = results['cache_hits']['avg_us'] / 1000
    print(f"\n  Cache hit latency:     {cache_hit_ms:.3f} ms")

    if not results['direct_search'].get('skipped'):
        direct_ms = results['direct_search']['avg_ms']
        print(f"  Direct search latency: {direct_ms:.2f} ms")
        print(f"  Cache speedup:         {direct_ms / cache_hit_ms:.0f}x")

    print(f"\n  Unified API speedup:   {results['unified_api']['speedup']:.1f}x")
    print(f"  Simulated hit rate:    {results['hit_rate']['hit_rate']:.1%}")
    print(f"  Compression savings:   {(1 - results['compression']['compression_ratio']):.0%}")

    # Performance targets
    print("\n  Performance Targets:")
    targets_met = 0

    if cache_hit_ms < 1:
        print("    ✓ Cache hit < 1ms")
        targets_met += 1
    else:
        print("    ✗ Cache hit < 1ms (not met)")

    if results['unified_api']['speedup'] > 10:
        print("    ✓ Speedup > 10x")
        targets_met += 1
    else:
        print(f"    ✗ Speedup > 10x (got {results['unified_api']['speedup']:.1f}x)")

    if results['hit_rate']['hit_rate'] > 0.7:
        print("    ✓ Hit rate > 70%")
        targets_met += 1
    else:
        print(f"    ✗ Hit rate > 70% (got {results['hit_rate']['hit_rate']:.0%})")

    print(f"\n  Targets met: {targets_met}/3")

    return results


if __name__ == "__main__":
    results = asyncio.run(run_all_benchmarks())
