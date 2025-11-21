#!/usr/bin/env python3
"""
Test SAFLA Integration with Qdrant
Verifies Neural Memory Fabric (NMF) can connect to Qdrant and perform operations
"""

import sys
import json
import asyncio
from pathlib import Path

# Add enhanced-memory-mcp to path
sys.path.insert(0, str(Path("/mnt/agentic-system/mcp-servers/enhanced-memory-mcp")))

def test_qdrant_connection():
    """Test basic Qdrant connection"""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()

        print("✅ Qdrant connection successful")
        print(f"   Collections: {len(collections.collections)}")

        return True
    except ImportError:
        print("❌ qdrant-client not installed")
        print("   Install with: pip install qdrant-client")
        return False
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        return False

async def test_nmf_integration_async():
    """Test Neural Memory Fabric integration (async)"""
    try:
        from neural_memory_fabric import NeuralMemoryFabric

        # Initialize NMF with config file
        config_path = "/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/nmf_config.yaml"

        nmf = NeuralMemoryFabric(config_path=config_path)
        await nmf.initialize()

        print("✅ Neural Memory Fabric initialized with Qdrant")

        # Test storing a memory
        result = await nmf.remember(
            content='Qdrant integration test - SAFLA vector search operational',
            metadata={'tags': ['test', 'qdrant', 'safla']},
            agent_id='test_agent'
        )

        print(f"✅ Test memory stored (ID: {result.get('memory_id')})")

        # Test retrieving memory
        results = await nmf.recall(
            query='Qdrant integration',
            mode='semantic',
            limit=5
        )

        print(f"✅ Semantic search successful ({len(results)} results)")

        if results and 'Qdrant integration test' in results[0].get('content', ''):
            print("✅ Test memory retrieved correctly")

        return True

    except ImportError as e:
        print(f"❌ NMF import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ NMF integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nmf_integration():
    """Wrapper to run async NMF test"""
    return asyncio.run(test_nmf_integration_async())

def test_safla_orchestrator():
    """Test SAFLA 4-tier memory orchestrator"""
    try:
        from safla_orchestrator import SAFLAOrchestrator

        db_path = Path("/mnt/agentic-system/databases/mcp/enhanced_memories.db")

        safla = SAFLAOrchestrator(db_path)

        print("✅ SAFLA Orchestrator initialized")

        # Test working memory
        working_id = safla.add_to_working_memory(
            context_key='test_context',
            content='Test working memory entry',
            priority=5,
            ttl_minutes=60
        )

        print(f"✅ Working memory operational (ID: {working_id})")

        # Test episodic memory
        episode_id = safla.add_episode(
            event_type='test_event',
            episode_data={'test': 'data'},
            significance_score=0.8
        )

        print(f"✅ Episodic memory operational (ID: {episode_id})")

        # Test semantic memory
        concept_id = safla.add_concept(
            concept_name='test_concept',
            concept_type='pattern',
            definition='Test concept definition',
            confidence_score=0.9
        )

        print(f"✅ Semantic memory operational (ID: {concept_id})")

        # Test procedural memory
        skill_id = safla.add_skill(
            skill_name='test_skill',
            skill_category='testing',
            procedure_steps=['step1', 'step2', 'step3']
        )

        print(f"✅ Procedural memory operational (ID: {skill_id})")

        return True

    except Exception as e:
        print(f"❌ SAFLA orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("SAFLA + Qdrant Integration Test")
    print("=" * 60)
    print()

    results = {
        'qdrant_connection': test_qdrant_connection(),
        'nmf_integration': test_nmf_integration(),
        'safla_orchestrator': test_safla_orchestrator()
    }

    print()
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(results.values())

    print()
    if all_passed:
        print("🎉 All tests passed! SAFLA + Qdrant fully operational")
        return 0
    else:
        print("⚠️  Some tests failed. Check logs above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
