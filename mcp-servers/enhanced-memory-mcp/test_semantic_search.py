#!/usr/bin/env python3
"""
Test semantic search capabilities
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf


async def test_semantic_search():
    """Test semantic search with real queries"""
    print("=" * 70)
    print("Neural Memory Fabric - Semantic Search Test")
    print("=" * 70)

    nmf = await get_nmf()

    # Store diverse memories
    print("\n[1/4] Storing test memories...")

    memories = [
        ("The Neural Memory Fabric combines temporal knowledge graphs with memory blocks for advanced agentic intelligence.", ["architecture", "nmf"]),
        ("Letta introduces memory blocks as discrete, editable units with a filesystem-like API.", ["letta", "memory_blocks"]),
        ("Zep uses bi-temporal tracking to maintain historical validity intervals on graph relationships.", ["zep", "temporal", "graphs"]),
        ("A-MEM implements Zettelkasten-inspired dynamic linking where new memories automatically connect to related existing memories.", ["a-mem", "linking"]),
        ("Phase 1 implementation includes SQLite, Chroma, and Redis with 7 MCP tools integrated.", ["implementation", "phase1"]),
        ("Vector embeddings enable semantic similarity search across unstructured memory content.", ["embeddings", "semantic"]),
        ("The migration to FILES drive relocated 132 MCP servers totaling 8.1GB successfully.", ["migration", "mcp"]),
    ]

    stored_ids = []
    for content, tags in memories:
        result = await nmf.remember(
            content=content,
            metadata={'tags': tags},
            agent_id="test_semantic"
        )
        stored_ids.append(result['memory_id'])
        print(f"  ✅ Stored: {content[:50]}...")

    # Test queries
    print("\n[2/4] Testing semantic queries...")

    test_queries = [
        ("temporal tracking", "Should find Zep memory"),
        ("connecting memories together", "Should find A-MEM memory"),
        ("editable memory", "Should find Letta memory"),
        ("files and storage", "Should find migration memory"),
    ]

    for query, expected in test_queries:
        print(f"\n  Query: '{query}'")
        print(f"  Expected: {expected}")

        results = await nmf.recall(
            query=query,
            agent_id="test_semantic",
            mode="semantic",
            limit=3
        )

        if results:
            print(f"  ✅ Found {len(results)} results:")
            for i, r in enumerate(results, 1):
                similarity = r.get('similarity_score', 0)
                print(f"     {i}. [{similarity:.3f}] {r['content'][:60]}...")
        else:
            print("  ❌ No results found")

    # Test hybrid search
    print("\n[3/4] Testing hybrid search...")

    hybrid_query = "memory architecture"
    print(f"  Query: '{hybrid_query}'")

    results = await nmf.recall(
        query=hybrid_query,
        agent_id="test_semantic",
        mode="hybrid",
        limit=5
    )

    print(f"  ✅ Hybrid found {len(results)} results:")
    for i, r in enumerate(results, 1):
        source = r.get('source', 'unknown')
        score = r.get('rank_score', r.get('similarity_score', 0))
        print(f"     {i}. [{source}] [{score:.3f}] {r['content'][:50]}...")

    # Performance comparison
    print("\n[4/4] Performance comparison...")

    import time

    # SQL search
    start = time.time()
    sql_results = await nmf.recall(query="memory", agent_id="test_semantic", mode="temporal", limit=5)
    sql_time = (time.time() - start) * 1000

    # Semantic search
    start = time.time()
    semantic_results = await nmf.recall(query="memory", agent_id="test_semantic", mode="semantic", limit=5)
    semantic_time = (time.time() - start) * 1000

    # Hybrid search
    start = time.time()
    hybrid_results = await nmf.recall(query="memory", agent_id="test_semantic", mode="hybrid", limit=5)
    hybrid_time = (time.time() - start) * 1000

    print(f"  SQL search:      {sql_time:>6.1f}ms ({len(sql_results)} results)")
    print(f"  Semantic search: {semantic_time:>6.1f}ms ({len(semantic_results)} results)")
    print(f"  Hybrid search:   {hybrid_time:>6.1f}ms ({len(hybrid_results)} results)")

    print("\n" + "=" * 70)
    print("✅ Semantic search test complete!")
    print("=" * 70)

    # Cleanup
    print("\nCleanup test memories...")
    cursor = nmf.sqlite_conn.cursor()
    cursor.execute("DELETE FROM nmf_entities WHERE agent_id = 'test_semantic'")
    nmf.sqlite_conn.commit()

    # Also cleanup from Chroma
    if nmf.vector_db:
        try:
            nmf.vector_collection.delete(ids=stored_ids)
        except:
            pass

    print("✅ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(test_semantic_search())
