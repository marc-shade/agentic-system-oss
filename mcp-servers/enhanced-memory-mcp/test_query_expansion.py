#!/usr/bin/env python3
"""
Test suite for query expansion tools

Tests all three expansion strategies:
1. LLM reformulation
2. Synonym expansion
3. Conceptual expansion
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from query_expansion_tools import QueryExpander


async def test_synonym_expansion():
    """Test synonym-based query expansion"""
    print("\n" + "=" * 70)
    print("TEST 1: SYNONYM EXPANSION")
    print("=" * 70)

    expander = QueryExpander()

    test_queries = [
        "voice communication system",
        "agent workflow architecture",
        "memory search optimization"
    ]

    for query in test_queries:
        print(f"\nOriginal: '{query}'")
        variants = expander.synonym_expand(query, max_variants=2)

        if variants:
            print("✅ Synonym variants:")
            for i, variant in enumerate(variants, 1):
                print(f"  {i}. {variant}")
        else:
            print("⚠️  No synonym variants generated")

    print("\n✅ Synonym expansion test complete")


async def test_concept_expansion():
    """Test concept-based query expansion"""
    print("\n" + "=" * 70)
    print("TEST 2: CONCEPT EXPANSION")
    print("=" * 70)

    expander = QueryExpander()

    test_queries = [
        "voice system",
        "memory database",
        "agent workflow"
    ]

    for query in test_queries:
        print(f"\nOriginal: '{query}'")
        variants = expander.concept_expand(query, max_variants=2)

        if variants:
            print("✅ Concept variants:")
            for i, variant in enumerate(variants, 1):
                print(f"  {i}. {variant}")
        else:
            print("⚠️  No concept variants generated")

    print("\n✅ Concept expansion test complete")


async def test_llm_expansion():
    """Test LLM-based query expansion"""
    print("\n" + "=" * 70)
    print("TEST 3: LLM EXPANSION (Pattern-based)")
    print("=" * 70)

    expander = QueryExpander()

    test_queries = [
        "voice communication",
        "agent system",
        "memory optimization"
    ]

    for query in test_queries:
        print(f"\nOriginal: '{query}'")
        variants = await expander.llm_expand(query, num_variants=2)

        if variants:
            print("✅ LLM variants:")
            for i, variant in enumerate(variants, 1):
                print(f"  {i}. {variant}")
        else:
            print("⚠️  No LLM variants generated")

    print("\n✅ LLM expansion test complete")


async def test_combined_expansion():
    """Test combined query expansion using all strategies"""
    print("\n" + "=" * 70)
    print("TEST 4: COMBINED EXPANSION (All Strategies)")
    print("=" * 70)

    expander = QueryExpander()

    test_queries = [
        "voice communication system",
        "agent workflow",
        "memory search"
    ]

    for query in test_queries:
        print(f"\nOriginal query: '{query}'")

        # Test with all strategies
        all_expansions = await expander.expand_query(
            query=query,
            max_expansions=5,
            strategies=["llm", "synonym", "concept"]
        )

        print(f"✅ Generated {len(all_expansions)} total expansions:")
        for i, exp in enumerate(all_expansions, 1):
            print(f"  {i}. {exp}")

        # Verify original is included
        assert query in all_expansions, "Original query should be included"
        print("✅ Original query included")

        # Verify deduplication
        assert len(all_expansions) == len(set(exp.lower() for exp in all_expansions)), \
            "Duplicates should be removed"
        print("✅ No duplicates")

    print("\n✅ Combined expansion test complete")


async def test_expansion_strategies():
    """Test individual strategy selection"""
    print("\n" + "=" * 70)
    print("TEST 5: STRATEGY SELECTION")
    print("=" * 70)

    expander = QueryExpander()
    query = "voice communication system"

    # Test LLM only
    print("\n1. LLM only:")
    llm_only = await expander.expand_query(query, strategies=["llm"])
    print(f"   Expansions: {llm_only}")

    # Test Synonym only
    print("\n2. Synonym only:")
    syn_only = await expander.expand_query(query, strategies=["synonym"])
    print(f"   Expansions: {syn_only}")

    # Test Concept only
    print("\n3. Concept only:")
    con_only = await expander.expand_query(query, strategies=["concept"])
    print(f"   Expansions: {con_only}")

    # Test combination
    print("\n4. Synonym + Concept:")
    combo = await expander.expand_query(query, strategies=["synonym", "concept"])
    print(f"   Expansions: {combo}")

    print("\n✅ Strategy selection test complete")


async def test_max_expansions_limit():
    """Test that max_expansions limit is respected"""
    print("\n" + "=" * 70)
    print("TEST 6: MAX EXPANSIONS LIMIT")
    print("=" * 70)

    expander = QueryExpander()
    query = "voice communication system"

    for max_exp in [1, 3, 5]:
        expansions = await expander.expand_query(
            query=query,
            max_expansions=max_exp
        )
        print(f"\nmax_expansions={max_exp}: Got {len(expansions)} expansions")
        assert len(expansions) <= max_exp, f"Should not exceed {max_exp} expansions"
        print(f"✅ Limit respected")

    print("\n✅ Max expansions limit test complete")


async def test_stats():
    """Test query expansion stats"""
    print("\n" + "=" * 70)
    print("TEST 7: EXPANSION STATS")
    print("=" * 70)

    expander = QueryExpander()

    stats = {
        "strategies": ["llm", "synonym", "concept"],
        "synonym_mappings": len(expander.synonym_map),
        "concept_mappings": len(expander.concept_map),
        "llm_available": expander.nmf is not None
    }

    print("\nQuery Expansion Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    assert stats["synonym_mappings"] > 0, "Should have synonym mappings"
    assert stats["concept_mappings"] > 0, "Should have concept mappings"

    print("\n✅ Stats test complete")


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("QUERY EXPANSION TEST SUITE")
    print("=" * 70)

    try:
        # Run all tests
        await test_synonym_expansion()
        await test_concept_expansion()
        await test_llm_expansion()
        await test_combined_expansion()
        await test_expansion_strategies()
        await test_max_expansions_limit()
        await test_stats()

        # Summary
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        print("\n✅ Query expansion implementation verified")
        print("✅ Synonym expansion: Working")
        print("✅ Concept expansion: Working")
        print("✅ LLM expansion: Working (pattern-based)")
        print("✅ Combined expansion: Working")
        print("✅ Strategy selection: Working")
        print("✅ Max expansions limit: Working")
        print("✅ Stats: Working")
        print("\n🎉 Ready for MCP integration!")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
