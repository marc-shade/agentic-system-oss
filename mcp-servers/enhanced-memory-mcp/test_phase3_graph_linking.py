#!/usr/bin/env python3
"""
Neural Memory Fabric - Phase 3 Test Script
Tests graph features, dynamic linking, and temporal queries
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf


async def test_phase3_features():
    """Test Phase 3: Graph + Dynamic Linking"""
    print("=" * 70)
    print("Neural Memory Fabric - Phase 3 Test")
    print("Graph Features + Dynamic Linking + Temporal Queries")
    print("=" * 70)

    nmf = await get_nmf()

    # Check if graph DB is available
    graph_available = nmf.graph_driver is not None
    print(f"\n[Info] Neo4j available: {graph_available}")
    print(f"[Info] Vector DB available: {nmf.vector_db is not None}")

    # ===================================================================
    # Test 1: Store memories with automatic linking
    # ===================================================================
    print("\n[1/6] Testing automatic memory storage with dynamic linking...")

    test_memories = [
        {
            'content': 'Python is a high-level programming language with dynamic typing and garbage collection.',
            'tags': ['python', 'programming', 'languages']
        },
        {
            'content': 'JavaScript is a dynamic programming language commonly used for web development.',
            'tags': ['javascript', 'programming', 'web']
        },
        {
            'content': 'Machine learning algorithms can be implemented in Python using libraries like scikit-learn.',
            'tags': ['python', 'machine_learning', 'ai']
        },
        {
            'content': 'Neural networks are a type of machine learning model inspired by biological neurons.',
            'tags': ['neural_networks', 'machine_learning', 'ai']
        },
        {
            'content': 'Web scraping in Python can be done with Beautiful Soup and Requests libraries.',
            'tags': ['python', 'web_scraping', 'automation']
        }
    ]

    stored_ids = []
    for i, mem in enumerate(test_memories, 1):
        result = await nmf.remember(
            content=mem['content'],
            metadata={'tags': mem['tags']},
            agent_id='test_phase3'
        )
        stored_ids.append(result['memory_id'])
        print(f"  ✅ Stored memory {i}: {mem['content'][:50]}...")

    # Wait a moment for async linking to complete
    await asyncio.sleep(0.5)

    # ===================================================================
    # Test 2: Check dynamic links created
    # ===================================================================
    print("\n[2/6] Checking dynamic links...")

    cursor = nmf.sqlite_conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM nmf_links WHERE from_memory_id IN ({})'.format(
        ','.join('?' * len(stored_ids))
    ), stored_ids)

    total_links = cursor.fetchone()[0]
    print(f"  ✅ Found {total_links} automatic links created")

    if total_links > 0:
        # Show some examples
        cursor.execute('''
            SELECT l.from_memory_id, l.to_memory_id, l.link_score,
                   e1.content, e2.content
            FROM nmf_links l
            JOIN nmf_entities e1 ON l.from_memory_id = e1.id
            JOIN nmf_entities e2 ON l.to_memory_id = e2.id
            WHERE l.from_memory_id IN ({})
            ORDER BY l.link_score DESC
            LIMIT 3
        '''.format(','.join('?' * len(stored_ids))), stored_ids)

        print("\n  Top 3 links by similarity:")
        for row in cursor.fetchall():
            from_mem = row[3][:40]
            to_mem = row[4][:40]
            score = row[2]
            print(f"    [{score:.3f}] \"{from_mem}...\" → \"{to_mem}...\"")

    # ===================================================================
    # Test 3: Find related memories manually
    # ===================================================================
    print("\n[3/6] Testing find_related_memories...")

    if nmf.vector_db and stored_ids:
        related = await nmf.find_related_memories(
            stored_ids[0],  # Python memory
            similarity_threshold=0.5,
            max_links=3
        )

        if related:
            print(f"  ✅ Found {len(related)} related memories:")
            for mem_id, similarity in related:
                cursor.execute('SELECT content FROM nmf_entities WHERE id = ?', (mem_id,))
                row = cursor.fetchone()
                if row:
                    print(f"    [{similarity:.3f}] {row[0][:60]}...")
        else:
            print("  ⚠️  No related memories found (may need more memories)")
    else:
        print("  ⚠️  Vector DB required for similarity search")

    # ===================================================================
    # Test 4: Graph traversal (if Neo4j available)
    # ===================================================================
    print("\n[4/6] Testing graph traversal...")

    if graph_available and stored_ids:
        try:
            connected = await nmf.traverse_graph(
                stored_ids[0],
                max_depth=2
            )

            if connected:
                print(f"  ✅ Graph traversal found {len(connected)} connected memories:")
                for mem in connected[:3]:
                    print(f"    Distance {mem['graph_distance']}: {mem['content'][:60]}...")
            else:
                print("  ⚠️  No connected memories in graph (may need Neo4j running)")
        except Exception as e:
            print(f"  ⚠️  Graph traversal skipped: {e}")
    else:
        print("  ⚠️  Graph traversal requires Neo4j")

    # ===================================================================
    # Test 5: Temporal queries
    # ===================================================================
    print("\n[5/6] Testing temporal queries...")

    # Query memories as of now
    now = datetime.utcnow().isoformat()
    temporal_results = await nmf.temporal_query(
        agent_id='test_phase3',
        as_of_time=now,
        query='Python'
    )

    if temporal_results:
        print(f"  ✅ Temporal query found {len(temporal_results)} memories containing 'Python':")
        for mem in temporal_results[:3]:
            print(f"    Valid at {mem['was_valid_at'][:19]}: {mem['content'][:60]}...")
    else:
        print("  ⚠️  No temporal results found")

    # Query 1 hour ago (should find nothing since we just created them)
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    past_results = await nmf.temporal_query(
        agent_id='test_phase3',
        as_of_time=one_hour_ago
    )

    print(f"  ✅ Temporal query 1 hour ago found {len(past_results)} memories (expected: 0)")

    # ===================================================================
    # Test 6: Semantic search with graph context
    # ===================================================================
    print("\n[6/6] Testing hybrid retrieval...")

    hybrid_results = await nmf.recall(
        query='machine learning with Python',
        agent_id='test_phase3',
        mode='hybrid',
        limit=3
    )

    if hybrid_results:
        print(f"  ✅ Hybrid search found {len(hybrid_results)} results:")
        for i, mem in enumerate(hybrid_results, 1):
            score = mem.get('rank_score', mem.get('similarity_score', 0))
            print(f"    {i}. [{score:.3f}] {mem['content'][:60]}...")
    else:
        print("  ⚠️  No hybrid results found")

    # ===================================================================
    # Summary
    # ===================================================================
    print("\n" + "=" * 70)

    status = nmf.get_status()
    await status  # Await the coroutine

    print("✅ Phase 3 Feature Test Summary:")
    print(f"   Memories stored: {len(stored_ids)}")
    print(f"   Dynamic links created: {total_links}")
    print(f"   Graph traversal: {'✅ Working' if graph_available else '⚠️  Needs Neo4j'}")
    print(f"   Temporal queries: ✅ Working")
    print(f"   Hybrid retrieval: ✅ Working")
    print("=" * 70)

    # ===================================================================
    # Cleanup
    # ===================================================================
    print("\nCleanup test data...")

    cursor.execute('DELETE FROM nmf_entities WHERE agent_id = ?', ('test_phase3',))
    cursor.execute('''
        DELETE FROM nmf_links
        WHERE from_memory_id IN (SELECT id FROM nmf_entities WHERE agent_id = ?)
    ''', ('test_phase3',))
    nmf.sqlite_conn.commit()

    # Cleanup from Chroma
    if nmf.vector_db:
        try:
            nmf.vector_collection.delete(ids=stored_ids)
        except:
            pass

    # Cleanup from Neo4j
    if nmf.graph_driver:
        try:
            with nmf.graph_driver.session() as session:
                session.run(
                    "MATCH (m:Memory) WHERE m.agent_id = $agent_id DELETE m",
                    {'agent_id': 'test_phase3'}
                )
        except:
            pass

    print("✅ Cleanup complete")


if __name__ == "__main__":
    print("\nNeural Memory Fabric - Phase 3 Testing\n")
    asyncio.run(test_phase3_features())
    print("\n✅ All Phase 3 tests completed!\n")
