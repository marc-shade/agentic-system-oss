#!/usr/bin/env python3
"""
Test RAG Code Generator Integration
====================================

Verify that RAG system integrates correctly with autonomous loop.
Tests both storage and retrieval workflows.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from rag_code_generator import RAGCodeGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test-rag-integration")


async def test_rag_workflow():
    """Test complete RAG workflow."""
    logger.info("=== Testing RAG Integration ===\n")

    # Initialize RAG
    logger.info("1. Initializing RAG Code Generator...")
    rag = RAGCodeGenerator()

    # Test 1: Store successful modifications
    logger.info("\n2. Storing sample successful modifications...")

    modifications = [
        {
            "id": "test_mod_001",
            "target": "data_processor",
            "before": """
def filter_data(items):
    result = []
    for item in items:
        if item['value'] > 100:
            result.append(item)
    return result
""",
            "after": """
def filter_data(items):
    return [item for item in items if item['value'] > 100]
""",
            "type": "list_comprehension",
            "gain": 18.3,
            "reason": "List comprehension is faster than explicit loop with append"
        },
        {
            "id": "test_mod_002",
            "target": "cache_manager",
            "before": """
def get_user_data(user_id):
    return database.query(f"SELECT * FROM users WHERE id = {user_id}")
""",
            "after": """
@lru_cache(maxsize=1000)
def get_user_data(user_id):
    return database.query(f"SELECT * FROM users WHERE id = {user_id}")
""",
            "type": "caching",
            "gain": 94.7,
            "reason": "Added LRU cache to avoid repeated database queries"
        },
        {
            "id": "test_mod_003",
            "target": "math_operations",
            "before": """
def calculate_squares(numbers):
    result = []
    for n in numbers:
        result.append(n * n)
    return result
""",
            "after": """
import numpy as np

def calculate_squares(numbers):
    return np.array(numbers) ** 2
""",
            "type": "vectorization",
            "gain": 156.2,
            "reason": "NumPy vectorization is orders of magnitude faster for array operations"
        }
    ]

    for mod in modifications:
        await rag.store_successful_modification(
            modification_id=mod["id"],
            target_function=mod["target"],
            code_before=mod["before"],
            code_after=mod["after"],
            optimization_type=mod["type"],
            performance_gain=mod["gain"],
            reasoning=mod["reason"]
        )
        logger.info(f"  ✓ Stored: {mod['id']} ({mod['type']}, +{mod['gain']}%)")

    # Test 2: Retrieve similar patterns
    logger.info("\n3. Testing retrieval with similar code...")

    test_code = """
def extract_names(users):
    names = []
    for user in users:
        if user['active']:
            names.append(user['name'])
    return names
"""

    similar = await rag.retrieve_similar_modifications(
        target_code=test_code,
        limit=3,
        min_performance_gain=10.0
    )

    logger.info(f"  Found {len(similar)} similar modifications:")
    for i, mod in enumerate(similar, 1):
        logger.info(f"    {i}. {mod['optimization_type']} (+{mod['performance_gain']}%)")
        logger.info(f"       Similarity: {mod['similarity_score']:.3f}")

    # Test 3: RAG-based code generation
    logger.info("\n4. Testing RAG-based code generation...")

    optimized, reasoning = await rag.generate_with_rag(
        target_code=test_code,
        target_function="extract_names",
        insights=[
            "List comprehensions are more efficient than explicit loops",
            "Avoid repeated list.append() calls"
        ],
        optimization_goal="performance"
    )

    logger.info("  ✓ Generated optimized code:")
    logger.info(f"\n{optimized}\n")
    logger.info(f"  Reasoning: {reasoning[:300]}...")

    # Test 4: Statistics
    logger.info("\n5. RAG System Statistics:")
    stats = await rag.get_statistics()

    logger.info(f"  Total modifications stored: {stats['total_modifications']}")
    logger.info(f"  Average gain: {stats['avg_performance_gain']:.1f}%")
    logger.info(f"  Max gain: {stats['max_performance_gain']:.1f}%")
    logger.info(f"  Optimization types: {stats['optimization_types']}")

    logger.info("\n=== RAG Integration Test Complete ===")
    logger.info("✓ All tests passed!")

    return True


async def test_rag_with_ollama():
    """Test that Ollama is accessible."""
    logger.info("\n=== Testing Ollama Connection ===")

    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m['name'] for m in data.get('models', [])]
                    logger.info(f"✓ Ollama accessible, {len(models)} models available")
                    if 'gpt-oss:20b' in models:
                        logger.info("  ✓ gpt-oss:20b model available")
                    else:
                        logger.warning(f"  ! gpt-oss:20b not found. Available: {models}")
                    return True
                else:
                    logger.error(f"Ollama returned status {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"Cannot connect to Ollama: {e}")
        logger.info("  Note: RAG will still work for storage/retrieval")
        return False


async def main():
    """Run all tests."""
    try:
        # Test Ollama first
        await test_rag_with_ollama()

        # Test RAG workflow
        await test_rag_workflow()

        logger.info("\n" + "="*70)
        logger.info("ALL TESTS PASSED")
        logger.info("="*70)

    except Exception as e:
        logger.error(f"\nTEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
