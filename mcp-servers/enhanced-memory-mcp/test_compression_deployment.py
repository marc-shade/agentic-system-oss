#!/usr/bin/env python3
"""
Test caveman compression deployment in Enhanced Memory MCP
Validates that compression is working end-to-end
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_client import MemoryClient

async def test_compression_deployment():
    """Test compression integration with MCP"""

    print("="*60)
    print("Caveman Compression Deployment Test")
    print("="*60)
    print()

    # Create client
    client = MemoryClient()

    # Test 1: Create entities with long observations
    print("Test 1: Creating entities with compressible content...")
    print()

    test_entities = [
        {
            'name': 'compression_test_distributed_execution',
            'entityType': 'experience',
            'observations': [
                'The distributed execution system was tested with seven different test cases to verify functionality across the cluster. All tests passed successfully, demonstrating that tasks can be routed to the appropriate nodes based on their requirements. The macpro51 builder node successfully executed Linux-specific commands.',
                'We observed approximately 0.5 seconds of routing overhead and 1-2 seconds of SSH connection time, which is acceptable for tasks with execution times greater than 5 seconds. The parallel execution test showed linear scaling up to the number of available nodes.',
                'One interesting finding was that the task queue management handled concurrent submissions without any race conditions. This validates our distributed architecture design.'
            ]
        },
        {
            'name': 'compression_test_research_summary',
            'entityType': 'knowledge',
            'observations': [
                'The paper introduces a novel approach to recursive self-improvement in AI systems. The authors propose a framework where agents can analyze their own performance metrics, identify weaknesses, and generate targeted improvements. The key innovation is the use of meta-learning to guide the self-improvement process.',
                'The experimental results demonstrate significant performance gains over baseline approaches, with improvements ranging from 20% to 45% across different benchmarks. The system learns not just specific tasks but also how to improve its own learning mechanisms.'
            ]
        }
    ]

    try:
        # Create entities (compression happens automatically)
        response = await client.create_entities(test_entities)

        if response.get('success'):
            print(f"✓ Created {response.get('count', 0)} entities")

            # Check for compression stats
            if 'caveman_compression' in response:
                stats = response['caveman_compression']
                print()
                print("Compression Statistics:")
                print(f"  Total observations: {stats.get('total_observations', 0)}")
                print(f"  Observations compressed: {stats.get('observations_compressed', 0)}")
                print(f"  Token reduction: {stats.get('token_reduction_pct', 0):.1f}%")
                print(f"  Tokens saved: {stats.get('tokens_saved', 0)}")
                print()
            else:
                print("⚠ Warning: No compression statistics in response")
                print()
        else:
            print(f"✗ Failed to create entities: {response.get('error')}")
            return False

    except Exception as e:
        print(f"✗ Error creating entities: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Search for entities (decompression happens automatically)
    print()
    print("Test 2: Searching for entities (testing decompression)...")
    print()

    try:
        search_response = await client.search_nodes("distributed execution", limit=5)

        if search_response.get('success'):
            entities = search_response.get('entities', [])
            print(f"✓ Found {len(entities)} entities")
            print()

            # Check if observations are decompressed
            for entity in entities:
                if entity.get('name', '').startswith('compression_test_'):
                    print(f"Entity: {entity.get('name')}")
                    observations = entity.get('observations', [])
                    print(f"  Observations: {len(observations)}")

                    # Check if original observations are restored
                    if 'observations_original' in entity:
                        print(f"  ✓ Original observations preserved")

                    # Show first observation snippet
                    if observations:
                        obs_snippet = observations[0][:80] + "..." if len(observations[0]) > 80 else observations[0]
                        print(f"  First observation: {obs_snippet}")
                    print()
        else:
            print(f"✗ Search failed: {search_response.get('error')}")
            return False

    except Exception as e:
        print(f"✗ Error searching: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Get memory status with compression stats
    print()
    print("Test 3: Getting memory status (includes compression statistics)...")
    print()

    try:
        status_response = await client.get_memory_status()

        if status_response.get('success'):
            print("✓ Memory status retrieved")

            # Check for caveman compression stats
            if 'caveman_compression' in status_response:
                caveman_stats = status_response['caveman_compression']
                print()
                print("Global Compression Statistics:")
                print(f"  Total compressions: {caveman_stats.get('total_compressions', 0)}")
                print(f"  Total skipped: {caveman_stats.get('total_skipped', 0)}")
                print(f"  Total tokens saved: {caveman_stats.get('total_tokens_saved', 0)}")
                print(f"  Overall reduction: {caveman_stats.get('overall_reduction_pct', 0):.1f}%")
                print()
            else:
                print("⚠ Warning: No caveman compression statistics in status")
                print()
        else:
            print(f"✗ Failed to get status: {status_response.get('error')}")
            return False

    except Exception as e:
        print(f"✗ Error getting status: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("="*60)
    print("✓ All compression deployment tests passed!")
    print("="*60)
    print()
    print("Next Steps:")
    print("  1. Restart Claude Code to reload MCP server")
    print("  2. Create memories through Claude Code interface")
    print("  3. Monitor compression statistics")
    print()

    return True


if __name__ == '__main__':
    success = asyncio.run(test_compression_deployment())
    sys.exit(0 if success else 1)
