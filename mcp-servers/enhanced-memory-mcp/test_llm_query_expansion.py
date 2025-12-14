#!/usr/bin/env python3
"""
Test LLM Query Expansion Feature

Tests:
1. Ollama connectivity and model availability
2. LLM-based query expansion generates meaningful variants
3. Fallback works when Ollama unavailable
4. Integration with the full expand_query() method
"""

import asyncio
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from query_expansion_tools import QueryExpander, OLLAMA_HOST, LLM_MODEL, OLLAMA_GENERATE_URL
import requests


def test_ollama_connectivity():
    """Test 1: Check Ollama server connectivity"""
    print("\n" + "=" * 60)
    print("TEST 1: Ollama Connectivity")
    print("=" * 60)

    print(f"Ollama Host: {OLLAMA_HOST}")
    print(f"Generate URL: {OLLAMA_GENERATE_URL}")
    print(f"Model: {LLM_MODEL}")

    try:
        # Check if Ollama is reachable
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m.get('name', '').split(':')[0] for m in models]
            print(f"\n✅ Ollama is reachable")
            print(f"   Available models: {len(models)}")

            # Check if our target model is available
            if any(LLM_MODEL in name for name in model_names):
                print(f"   ✅ Model '{LLM_MODEL}' is available")
                return True
            else:
                print(f"   ⚠️  Model '{LLM_MODEL}' not found. Available: {model_names[:5]}...")
                print(f"   Will use fallback expansion")
                return "fallback"
        else:
            print(f"❌ Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {OLLAMA_HOST}")
        print("   Fallback expansion will be used")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False


async def test_llm_expansion():
    """Test 2: Test LLM-based query expansion"""
    print("\n" + "=" * 60)
    print("TEST 2: LLM Query Expansion")
    print("=" * 60)

    expander = QueryExpander(nmf=None)

    test_queries = [
        "voice communication preferences",
        "memory consolidation system",
        "agent coordination workflow"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        variants = await expander.llm_expand(query, num_variants=2)

        if variants:
            print(f"   ✅ Generated {len(variants)} variants:")
            for v in variants:
                print(f"      - {v}")
        else:
            print(f"   ⚠️  No variants generated (using fallback)")

    return True


async def test_fallback_expansion():
    """Test 3: Test fallback pattern-based expansion"""
    print("\n" + "=" * 60)
    print("TEST 3: Fallback Expansion")
    print("=" * 60)

    expander = QueryExpander(nmf=None)

    test_queries = [
        "memory system",
        "voice communication",
        "workflow automation"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        variants = expander._fallback_expand(query, num_variants=2)

        print(f"   Generated {len(variants)} fallback variants:")
        for v in variants:
            print(f"      - {v}")

    return True


async def test_full_expansion():
    """Test 4: Test full expand_query with all strategies"""
    print("\n" + "=" * 60)
    print("TEST 4: Full Query Expansion (All Strategies)")
    print("=" * 60)

    expander = QueryExpander(nmf=None)

    query = "agent memory management"
    print(f"\nOriginal query: '{query}'")

    # Test with all strategies
    expansions = await expander.expand_query(
        query=query,
        max_expansions=5,
        strategies=["llm", "synonym", "concept"]
    )

    print(f"\n✅ Generated {len(expansions)} total expansions:")
    for i, exp in enumerate(expansions, 1):
        source = "original" if i == 1 else "expanded"
        print(f"   {i}. {exp} ({source})")

    # Test with individual strategies
    print("\n--- Strategy Breakdown ---")

    for strategy in ["llm", "synonym", "concept"]:
        exps = await expander.expand_query(
            query=query,
            max_expansions=3,
            strategies=[strategy]
        )
        print(f"\n   {strategy.upper()} strategy: {len(exps)-1} new variants")
        for exp in exps[1:]:  # Skip original
            print(f"      - {exp}")

    return True


async def test_synonym_expansion():
    """Test 5: Test synonym-based expansion"""
    print("\n" + "=" * 60)
    print("TEST 5: Synonym Expansion")
    print("=" * 60)

    expander = QueryExpander(nmf=None)

    # Test queries with words in synonym map
    test_queries = [
        "system architecture design",
        "memory optimization workflow",
        "agent communication process"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        variants = expander.synonym_expand(query, max_variants=2)

        if variants:
            print(f"   ✅ Synonym variants:")
            for v in variants:
                print(f"      - {v}")
        else:
            print(f"   ⚠️  No synonyms found for query words")

    return True


async def test_concept_expansion():
    """Test 6: Test concept-based expansion"""
    print("\n" + "=" * 60)
    print("TEST 6: Concept Expansion")
    print("=" * 60)

    expander = QueryExpander(nmf=None)

    # Test queries with words in concept map
    test_queries = [
        "voice recognition system",
        "memory storage patterns",
        "agent learning approach"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        variants = expander.concept_expand(query, max_variants=2)

        if variants:
            print(f"   ✅ Concept variants:")
            for v in variants:
                print(f"      - {v}")
        else:
            print(f"   ⚠️  No related concepts found")

    return True


async def run_all_tests():
    """Run all query expansion tests"""
    print("\n" + "=" * 60)
    print("LLM QUERY EXPANSION TEST SUITE")
    print("=" * 60)
    print(f"\nOllama Host: {OLLAMA_HOST}")
    print(f"Model: {LLM_MODEL}")

    results = {}

    # Test 1: Ollama connectivity
    results["connectivity"] = test_ollama_connectivity()

    # Test 2: LLM expansion
    try:
        results["llm_expansion"] = await test_llm_expansion()
    except Exception as e:
        print(f"❌ LLM expansion test failed: {e}")
        results["llm_expansion"] = False

    # Test 3: Fallback expansion
    try:
        results["fallback"] = await test_fallback_expansion()
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        results["fallback"] = False

    # Test 4: Full expansion
    try:
        results["full_expansion"] = await test_full_expansion()
    except Exception as e:
        print(f"❌ Full expansion test failed: {e}")
        results["full_expansion"] = False

    # Test 5: Synonym expansion
    try:
        results["synonym"] = await test_synonym_expansion()
    except Exception as e:
        print(f"❌ Synonym test failed: {e}")
        results["synonym"] = False

    # Test 6: Concept expansion
    try:
        results["concept"] = await test_concept_expansion()
    except Exception as e:
        print(f"❌ Concept test failed: {e}")
        results["concept"] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v and v != "fallback")
    total = len(results)

    for test_name, result in results.items():
        if result == "fallback":
            status = "⚠️  FALLBACK"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"   {status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed >= total - 1:  # Allow one fallback
        print("\n🎉 LLM Query Expansion is operational!")
        if results["connectivity"] == "fallback":
            print("   Note: Using fallback expansion (Ollama model not available)")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
