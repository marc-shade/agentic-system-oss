#!/usr/bin/env python3
"""Example usage of semantic cache with various scenarios"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from semantic_cache_module import SemanticCache
import time
import json

def demo_basic_usage():
    """Basic cache usage demonstration"""
    print("\n" + "="*70)
    print("DEMO 1: Basic Semantic Cache Usage")
    print("="*70)

    cache = SemanticCache(
        similarity_threshold=0.90,
        ttl_hours=24,
        db_path="/tmp/demo_cache.db"
    )

    # Simulate Q&A system
    queries = [
        "How do I implement a binary search algorithm?",
        "What is the time complexity of quicksort?",
        "Explain how hash tables work",
    ]

    responses = [
        "Binary search repeatedly divides the search space in half...",
        "Quicksort has O(n log n) average time complexity...",
        "Hash tables use hash functions to map keys to values...",
    ]

    print("\n1. Initial queries (cache misses expected):")
    for query, response in zip(queries, responses):
        result = cache.get(query)
        if not result:
            print(f"   ✗ MISS: {query[:50]}...")
            cache.store(query, response)

    print("\n2. Similar queries (cache hits expected):")
    similar_queries = [
        "How to write binary search?",
        "What's the runtime of quicksort?",
        "How do hash maps function?",
    ]

    for query in similar_queries:
        result = cache.get(query)
        if result:
            cached_response, similarity = result
            print(f"   ✓ HIT: {query[:50]}...")
            print(f"     Similarity: {similarity:.4f}")
        else:
            print(f"   ✗ MISS: {query[:50]}...")

    print("\n3. Cache Statistics:")
    stats = cache.get_stats()
    print(f"   Hit rate: {stats['session_stats']['hit_rate']}")
    print(f"   Total entries: {stats['total_entries']}")


def demo_performance_comparison():
    """Demonstrate performance improvement"""
    print("\n" + "="*70)
    print("DEMO 2: Performance Comparison")
    print("="*70)

    cache = SemanticCache(
        similarity_threshold=0.90,
        db_path="/tmp/perf_cache.db"
    )

    # Simulate expensive operation
    def expensive_operation(query):
        """Simulate LLM API call"""
        time.sleep(0.5)  # Simulate 500ms latency
        return f"Response for: {query}"

    query = "Explain the concept of recursion in programming"

    # First call - cache miss
    print("\n1. First call (cache miss):")
    start = time.time()
    result = cache.get(query)
    if not result:
        response = expensive_operation(query)
        cache.store(query, response)
    miss_time = (time.time() - start) * 1000
    print(f"   Time: {miss_time:.1f}ms")

    # Second call - cache hit
    print("\n2. Similar query (cache hit):")
    similar = "What is recursion in programming?"
    start = time.time()
    result = cache.get(similar)
    if result:
        response, similarity = result
        hit_time = (time.time() - start) * 1000
        print(f"   Time: {hit_time:.1f}ms")
        print(f"   Similarity: {similarity:.4f}")
        print(f"   Speedup: {miss_time/hit_time:.1f}x faster")


def demo_context_aware_caching():
    """Demonstrate context-aware caching"""
    print("\n" + "="*70)
    print("DEMO 3: Context-Aware Caching")
    print("="*70)

    cache = SemanticCache(
        similarity_threshold=0.90,
        db_path="/tmp/context_cache.db"
    )

    # Same query, different contexts
    query = "What is a good approach?"

    contexts = [
        "software development",
        "machine learning optimization",
        "database design",
    ]

    print("\n1. Storing with different contexts:")
    for ctx in contexts:
        response = f"For {ctx}, a good approach is..."
        cache.store(query, response, context=ctx)
        print(f"   ✓ Stored: '{query}' (context: {ctx})")

    print("\n2. Retrieving with context:")
    # Note: Current implementation doesn't filter by context on retrieval
    # This is a demonstration of how context hashing works
    result = cache.get(query)
    if result:
        response, similarity = result
        print(f"   ✓ Retrieved (similarity: {similarity:.4f})")
        print(f"   Response: {response}")


def demo_search_functionality():
    """Demonstrate similarity search"""
    print("\n" + "="*70)
    print("DEMO 4: Similarity Search")
    print("="*70)

    cache = SemanticCache(
        similarity_threshold=0.85,
        db_path="/tmp/search_cache.db"
    )

    # Populate cache with various topics
    knowledge = [
        ("How does machine learning work?", "ML uses algorithms to learn patterns from data..."),
        ("What is deep learning?", "Deep learning uses neural networks with multiple layers..."),
        ("Explain neural networks", "Neural networks are inspired by biological neurons..."),
        ("How do hash tables work?", "Hash tables use hash functions for O(1) lookup..."),
        ("What is Big O notation?", "Big O describes algorithm time complexity..."),
    ]

    print("\n1. Populating cache:")
    for query, response in knowledge:
        cache.store(query, response)
        print(f"   ✓ {query[:50]}")

    # Search for similar queries
    print("\n2. Searching for ML-related queries:")
    search_query = "Tell me about artificial intelligence"
    results = cache.search_similar(search_query, top_k=3)

    for i, (query, response, similarity) in enumerate(results, 1):
        print(f"\n   {i}. Similarity: {similarity:.4f}")
        print(f"      Query: {query}")
        print(f"      Response: {response[:60]}...")


def demo_cleanup_and_maintenance():
    """Demonstrate cache maintenance"""
    print("\n" + "="*70)
    print("DEMO 5: Cache Cleanup and Maintenance")
    print("="*70)

    # Create cache with short TTL
    cache = SemanticCache(
        similarity_threshold=0.90,
        ttl_hours=1,  # 1 hour TTL
        db_path="/tmp/cleanup_cache.db"
    )

    # Add some entries
    print("\n1. Adding entries:")
    for i in range(5):
        cache.store(f"Query {i}", f"Response {i}")
    print(f"   Added 5 entries")

    # Check stats
    stats = cache.get_stats()
    print(f"\n2. Before cleanup:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Valid entries: {stats['valid_entries']}")

    # Cleanup
    deleted = cache.cleanup()
    print(f"\n3. After cleanup:")
    print(f"   Deleted {deleted} expired entries")

    stats = cache.get_stats()
    print(f"   Remaining entries: {stats['total_entries']}")


def demo_integration_pattern():
    """Show integration pattern with AI system"""
    print("\n" + "="*70)
    print("DEMO 6: Integration Pattern")
    print("="*70)

    class MockAISystem:
        """Mock AI system with semantic caching"""

        def __init__(self):
            self.cache = SemanticCache(
                similarity_threshold=0.90,
                db_path="/tmp/ai_system_cache.db"
            )
            self.api_calls = 0

        def ask(self, question: str) -> str:
            """Ask question with automatic caching"""
            # Check cache first
            result = self.cache.get(question)
            if result:
                response, similarity = result
                print(f"   [CACHED] Similarity: {similarity:.4f}")
                return response

            # Cache miss - make expensive API call
            self.api_calls += 1
            print(f"   [API CALL #{self.api_calls}]")
            response = f"AI Response to: {question}"

            # Store in cache
            self.cache.store(question, response)
            return response

        def get_stats(self):
            """Get usage statistics"""
            cache_stats = self.cache.get_stats()
            return {
                "api_calls": self.api_calls,
                "cache_hits": cache_stats['session_stats']['hits'],
                "cache_hit_rate": cache_stats['session_stats']['hit_rate'],
            }

    # Use the system
    print("\n1. Creating AI system with caching:")
    ai = MockAISystem()

    questions = [
        "What is Python?",
        "Explain Python programming language",  # Similar to above
        "How does React work?",
        "What is the React framework?",  # Similar to above
        "What is Python?",  # Exact duplicate
    ]

    print("\n2. Asking questions:")
    for q in questions:
        print(f"\nQ: {q}")
        response = ai.ask(q)
        print(f"A: {response}")

    print("\n3. System Statistics:")
    stats = ai.get_stats()
    print(f"   Total API calls: {stats['api_calls']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache hit rate: {stats['cache_hit_rate']}")
    print(f"   Cost savings: {(1 - stats['api_calls']/len(questions))*100:.1f}%")


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print("SEMANTIC CACHE USAGE EXAMPLES")
    print("="*70)

    demos = [
        demo_basic_usage,
        demo_performance_comparison,
        demo_context_aware_caching,
        demo_search_functionality,
        demo_cleanup_and_maintenance,
        demo_integration_pattern,
    ]

    for demo in demos:
        try:
            demo()
            time.sleep(1)  # Brief pause between demos
        except Exception as e:
            print(f"\n   ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("All demonstrations complete!")
    print("="*70)


if __name__ == "__main__":
    main()
