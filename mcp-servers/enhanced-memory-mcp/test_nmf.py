#!/usr/bin/env python3
"""
Neural Memory Fabric - Phase 1 Test Script
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from neural_memory_fabric import NeuralMemoryFabric, get_nmf


async def test_nmf_phase1():
    """Test Phase 1 functionality"""
    print("=" * 70)
    print("Neural Memory Fabric - Phase 1 Test")
    print("=" * 70)

    # Initialize NMF
    print("\n[1/7] Initializing Neural Memory Fabric...")
    try:
        nmf = await get_nmf()
        print("✅ NMF initialized")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    # Test 1: Store a memory
    print("\n[2/7] Testing memory storage...")
    try:
        result = await nmf.remember(
            content="Neural Memory Fabric combines temporal graphs, memory blocks, and dynamic linking for the most advanced agentic memory system.",
            metadata={
                'tags': ['memory', 'architecture', 'nmf'],
                'category': 'system_knowledge'
            },
            agent_id="test_agent"
        )
        print(f"✅ Memory stored: {result['memory_id']}")
        memory_id_1 = result['memory_id']
    except Exception as e:
        print(f"❌ Storage failed: {e}")
        return False

    # Test 2: Store another memory
    print("\n[3/7] Testing multiple memory storage...")
    try:
        result = await nmf.remember(
            content="Letta introduces memory blocks as discrete, editable units that agents can manage through a filesystem-like API.",
            metadata={
                'tags': ['letta', 'memory_blocks'],
                'category': 'research'
            },
            agent_id="test_agent"
        )
        print(f"✅ Second memory stored: {result['memory_id']}")
        memory_id_2 = result['memory_id']
    except Exception as e:
        print(f"❌ Second storage failed: {e}")
        return False

    # Test 3: Recall memories
    print("\n[4/7] Testing memory recall...")
    try:
        results = await nmf.recall(
            query="memory system",
            agent_id="test_agent",
            limit=5
        )
        print(f"✅ Recalled {len(results)} memories")
        for i, mem in enumerate(results, 1):
            print(f"   {i}. {mem['content'][:60]}...")
    except Exception as e:
        print(f"❌ Recall failed: {e}")
        return False

    # Test 4: Memory blocks
    print("\n[5/7] Testing memory blocks...")
    try:
        # Create identity block
        result = await nmf.edit_block(
            agent_id="test_agent",
            block_name="identity",
            new_value="I am a test agent exploring the Neural Memory Fabric system."
        )
        print(f"✅ Identity block created")

        # Read it back
        block = await nmf.open_block("test_agent", "identity")
        if block['success']:
            print(f"✅ Identity block retrieved: {block['value'][:50]}...")
        else:
            print(f"❌ Block retrieval failed: {block.get('error')}")
    except Exception as e:
        print(f"❌ Memory blocks failed: {e}")
        return False

    # Test 5: System status
    print("\n[6/7] Testing system status...")
    try:
        status = await nmf.get_status()
        print(f"✅ System status retrieved:")
        print(f"   Total memories: {status['total_memories']}")
        print(f"   Total links: {status['total_links']}")
        print(f"   Backends active:")
        for backend, active in status['backends'].items():
            symbol = "✅" if active else "⚠️ "
            print(f"     {symbol} {backend}")
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

    # Test 6: Backend verification
    print("\n[7/7] Verifying backends...")
    errors = []

    # SQLite
    if nmf.sqlite_conn:
        print("   ✅ SQLite: Connected")
    else:
        errors.append("SQLite not connected")

    # Vector DB
    if nmf.vector_db:
        print("   ✅ Chroma: Connected")
    else:
        print("   ⚠️  Chroma: Not installed (optional)")

    # Graph DB
    if nmf.graph_driver:
        print("   ✅ Neo4j: Connected")
    else:
        print("   ⚠️  Neo4j: Not connected (optional)")

    # Redis
    if nmf.redis_client:
        print("   ✅ Redis: Connected")
    else:
        print("   ⚠️  Redis: Not connected (optional)")

    # Summary
    print("\n" + "=" * 70)
    if errors:
        print("⚠️  Phase 1 completed with warnings:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Phase 1: ALL TESTS PASSED")
    print("=" * 70)

    return True


async def cleanup():
    """Cleanup test data"""
    print("\n[Cleanup] Removing test data...")
    nmf = await get_nmf()

    cursor = nmf.sqlite_conn.cursor()
    cursor.execute("DELETE FROM nmf_entities WHERE agent_id = 'test_agent'")
    cursor.execute("DELETE FROM nmf_memory_blocks WHERE agent_id = 'test_agent'")
    nmf.sqlite_conn.commit()

    print("✅ Test data cleaned up")


if __name__ == "__main__":
    print("\nNeural Memory Fabric - Phase 1 Testing\n")

    # Run tests
    success = asyncio.run(test_nmf_phase1())

    # Cleanup
    if success:
        try:
            cleanup_choice = input("\nCleanup test data? (y/n): ").lower()
            if cleanup_choice == 'y':
                asyncio.run(cleanup())
        except (EOFError, KeyboardInterrupt):
            print("\n\nSkipping cleanup (run manually if needed)")

    sys.exit(0 if success else 1)
