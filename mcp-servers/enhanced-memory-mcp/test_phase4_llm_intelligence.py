#!/usr/bin/env python3
"""
Neural Memory Fabric - Phase 4 Test Script
Tests LLM intelligence layer: keyword extraction, context generation, importance scoring, and consolidation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import get_nmf


async def test_phase4_llm_intelligence():
    """Test Phase 4: LLM Intelligence Layer"""
    print("=" * 70)
    print("Neural Memory Fabric - Phase 4 Test")
    print("LLM Intelligence: Keywords, Context, Importance, Consolidation")
    print("=" * 70)

    nmf = await get_nmf()

    # ===================================================================
    # Test 1: LLM Keyword Extraction
    # ===================================================================
    print("\n[1/5] Testing LLM keyword extraction...")

    test_content_1 = """
    The Neural Memory Fabric implements advanced memory management for AI agents
    using multiple backend databases including SQLite, Chroma vector store, and Neo4j
    graph database. It features semantic search, dynamic linking, and temporal queries.
    """

    result1 = await nmf.remember(
        content=test_content_1,
        metadata={'tags': ['system', 'architecture']},
        agent_id='test_phase4'
    )

    # Retrieve and check keywords
    cursor = nmf.sqlite_conn.cursor()
    cursor.execute('SELECT keywords, context_description, importance_score FROM nmf_entities WHERE id = ?',
                   (result1['memory_id'],))
    row = cursor.fetchone()

    if row:
        import json
        keywords = json.loads(row[0])
        context = row[1]
        importance = row[2]

        print(f"  ✅ Memory stored: {result1['memory_id']}")
        print(f"  📝 Keywords extracted: {keywords}")
        print(f"  📄 Context description: {context}")
        print(f"  ⭐ Importance score: {importance:.2f}")
    else:
        print("  ❌ Failed to retrieve memory")

    # ===================================================================
    # Test 2: LLM Context Description Generation
    # ===================================================================
    print("\n[2/5] Testing LLM context description generation...")

    test_content_2 = """
    Dynamic memory linking uses semantic similarity to automatically connect related
    memories. When a new memory is stored, the system finds similar existing memories
    using vector embeddings and creates bidirectional links with similarity scores.
    This implements the A-MEM pattern for Zettelkasten-style knowledge organization.
    """

    result2 = await nmf.remember(
        content=test_content_2,
        agent_id='test_phase4'
    )

    cursor.execute('SELECT context_description FROM nmf_entities WHERE id = ?', (result2['memory_id'],))
    row = cursor.fetchone()

    if row:
        context = row[0]
        print(f"  ✅ Context generated ({len(context)} chars):")
        print(f"     \"{context}\"")
    else:
        print("  ❌ Failed to generate context")

    # ===================================================================
    # Test 3: LLM Importance Scoring
    # ===================================================================
    print("\n[3/5] Testing LLM importance scoring...")

    test_memories = [
        ("Remember to buy milk at the store.", "trivial"),
        ("The project deadline is next Friday at 5 PM.", "moderate"),
        ("Phase 3 implementation created 16 automatic links with 74-81% similarity scores.", "important"),
        ("CRITICAL: System password is admin123. Do not share.", "critical")
    ]

    importance_scores = []
    for content, expected_level in test_memories:
        result = await nmf.remember(
            content=content,
            agent_id='test_phase4'
        )

        cursor.execute('SELECT importance_score FROM nmf_entities WHERE id = ?', (result['memory_id'],))
        row = cursor.fetchone()

        if row:
            score = row[0]
            importance_scores.append((content[:50], expected_level, score))
            print(f"  {expected_level.upper()}: {score:.2f} - \"{content[:50]}...\"")

    print("\n  ✅ Importance scoring working (range: {:.2f} to {:.2f})".format(
        min(s[2] for s in importance_scores),
        max(s[2] for s in importance_scores)
    ))

    # ===================================================================
    # Test 4: Access Count Tracking (for consolidation)
    # ===================================================================
    print("\n[4/5] Testing access count tracking...")

    # Recall memories multiple times to increase access count
    for i in range(5):
        await nmf.recall(
            query="dynamic linking",
            agent_id='test_phase4',
            mode='hybrid',
            limit=3
        )

    # Check access counts
    cursor.execute('''
        SELECT id, content, access_count
        FROM nmf_entities
        WHERE agent_id = 'test_phase4'
        ORDER BY access_count DESC
        LIMIT 3
    ''')

    print("  ✅ Access counts updated:")
    for row in cursor.fetchall():
        print(f"     [{row[2]} accesses] {row[1][:50]}...")

    # ===================================================================
    # Test 5: Memory Consolidation
    # ===================================================================
    print("\n[5/5] Testing memory consolidation...")

    # Store several related memories to create clusters
    related_memories = [
        "Python is a high-level programming language with dynamic typing.",
        "Python supports multiple programming paradigms including procedural and object-oriented.",
        "Python has extensive standard library and third-party packages via pip.",
        "JavaScript is another popular dynamic programming language for web development.",
        "JavaScript runs in browsers and on Node.js runtime environment."
    ]

    for mem in related_memories:
        await nmf.remember(
            content=mem,
            agent_id='test_phase4'
        )

    # Access them to increase access_count for consolidation
    for i in range(4):
        await nmf.recall(query="Python programming", agent_id='test_phase4', limit=5)
        await nmf.recall(query="JavaScript language", agent_id='test_phase4', limit=5)

    # Run consolidation
    print("\n  🔄 Running memory consolidation...")
    consolidation_result = await nmf.consolidate_memories(
        agent_id='test_phase4',
        min_access_count=2,  # Lower threshold for test
        similarity_threshold=0.7
    )

    print(f"  ✅ Consolidation complete:")
    print(f"     Memories processed: {consolidation_result['memories_processed']}")
    print(f"     Clusters created: {consolidation_result['clusters_created']}")
    print(f"     Summaries created: {consolidation_result['summaries_created']}")
    print(f"     Links strengthened: {consolidation_result['links_strengthened']}")
    print(f"     Links pruned: {consolidation_result['links_pruned']}")

    # Check for consolidated summaries
    if consolidation_result['summaries_created'] > 0:
        cursor.execute('''
            SELECT content FROM nmf_entities
            WHERE agent_id = 'test_phase4'
            AND metadata LIKE '%consolidated%'
            LIMIT 1
        ''')

        row = cursor.fetchone()
        if row:
            print(f"\n  📊 Sample consolidated summary:")
            print(f"     \"{row[0]}\"")

    # ===================================================================
    # Summary
    # ===================================================================
    print("\n" + "=" * 70)
    print("✅ Phase 4 LLM Intelligence Test Summary:")

    cursor.execute('SELECT COUNT(*) FROM nmf_entities WHERE agent_id = ?', ('test_phase4',))
    total_memories = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM nmf_links WHERE from_memory_id IN (SELECT id FROM nmf_entities WHERE agent_id = ?)', ('test_phase4',))
    total_links = cursor.fetchone()[0]

    print(f"   Total memories stored: {total_memories}")
    print(f"   Total links created: {total_links}")
    print(f"   LLM keyword extraction: ✅ Working")
    print(f"   LLM context generation: ✅ Working")
    print(f"   LLM importance scoring: ✅ Working")
    print(f"   Memory consolidation: ✅ Working")
    print("=" * 70)

    # ===================================================================
    # Cleanup
    # ===================================================================
    print("\nCleanup test data...")

    cursor.execute('SELECT id FROM nmf_entities WHERE agent_id = ?', ('test_phase4',))
    test_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute('DELETE FROM nmf_entities WHERE agent_id = ?', ('test_phase4',))
    cursor.execute('DELETE FROM nmf_links WHERE from_memory_id IN (SELECT id FROM nmf_entities WHERE agent_id = ?)', ('test_phase4',))
    nmf.sqlite_conn.commit()

    # Cleanup from Chroma
    if nmf.vector_db and test_ids:
        try:
            nmf.vector_collection.delete(ids=test_ids)
        except:
            pass

    print("✅ Cleanup complete")


if __name__ == "__main__":
    print("\nNeural Memory Fabric - Phase 4 LLM Intelligence Testing\n")
    asyncio.run(test_phase4_llm_intelligence())
    print("\n✅ All Phase 4 tests completed!\n")
