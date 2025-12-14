#!/usr/bin/env python3
"""
Live test of caveman compression in production Enhanced Memory MCP
Tests compression by creating real entities and checking statistics
"""

import asyncio
import sys
import json
from pathlib import Path

# Add MCP path
sys.path.insert(0, str(Path(__file__).parent / 'mcp-servers' / 'enhanced-memory-mcp'))

from memory_client import MemoryClient

async def test_live_compression():
    """Test compression with real entity creation"""

    print("="*70)
    print("LIVE COMPRESSION TEST - Enhanced Memory MCP")
    print("="*70)
    print()

    client = MemoryClient()

    # Test 1: Create entity with long compressible observations
    print("Test 1: Creating entity with compressible observations...")
    print("-"*70)

    test_entities = [
        {
            'name': 'compression_live_test_distributed_system',
            'entityType': 'experience',
            'observations': [
                'The distributed execution system was successfully tested with seven different test cases to verify comprehensive functionality across the entire cluster infrastructure. All tests passed successfully, demonstrating that tasks can be intelligently routed to the appropriate nodes based on their specific requirements and available capabilities.',
                'We carefully observed approximately 0.5 seconds of routing overhead and between 1 to 2 seconds of SSH connection establishment time, which is completely acceptable for tasks with execution times that are greater than 5 seconds. The parallel execution test clearly showed linear scaling characteristics up to the total number of available nodes in the cluster.',
                'One particularly interesting and noteworthy finding was that the task queue management system handled multiple concurrent submissions without experiencing any race conditions whatsoever. This outcome validates our carefully designed distributed architecture and demonstrates the fundamental robustness of our implementation approach.'
            ]
        }
    ]

    try:
        response = await client.create_entities(test_entities)

        print(f"Success: {response.get('success', False)}")
        print(f"Created: {response.get('created', 0)} entities")
        print()

        # Check for compression statistics
        if 'caveman_compression' in response:
            print("✓ COMPRESSION STATISTICS FOUND!")
            print("-"*70)
            stats = response['caveman_compression']
            print(f"  Total observations: {stats.get('total_observations', 0)}")
            print(f"  Observations compressed: {stats.get('observations_compressed', 0)}")
            print(f"  Token reduction: {stats.get('token_reduction_pct', 0):.1f}%")
            print(f"  Tokens saved: {stats.get('tokens_saved', 0)}")
            print()

            if stats.get('observations_compressed', 0) > 0:
                print("✅ COMPRESSION IS WORKING!")
            else:
                print("⚠️  No observations were compressed (may be below threshold)")
        else:
            print("❌ NO COMPRESSION STATISTICS IN RESPONSE")
            print("   This means compression layer may not be active")
            print()
            print("Response keys:", list(response.keys()))

        print()

    except Exception as e:
        print(f"❌ Error creating entities: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Check memory status for global compression stats
    print()
    print("Test 2: Checking global compression statistics...")
    print("-"*70)

    try:
        status = await client.get_memory_status()

        if status.get('success'):
            print("✓ Memory status retrieved")
            print()

            if 'caveman_compression' in status:
                print("✓ GLOBAL COMPRESSION STATS FOUND!")
                print("-"*70)
                caveman = status['caveman_compression']
                print(f"  Total compressions: {caveman.get('total_compressions', 0)}")
                print(f"  Total skipped: {caveman.get('total_skipped', 0)}")
                print(f"  Total tokens saved: {caveman.get('total_tokens_saved', 0)}")
                print(f"  Overall reduction: {caveman.get('overall_reduction_pct', 0):.1f}%")
                print()

                if caveman.get('total_compressions', 0) > 0:
                    print("✅ COMPRESSION SYSTEM ACTIVE AND TRACKING!")
                else:
                    print("⚠️  No compressions recorded yet")
            else:
                print("❌ NO CAVEMAN COMPRESSION STATS IN STATUS")
                print()
                print("Available status keys:", list(status.keys()))
        else:
            print(f"❌ Failed to get status: {status.get('error')}")

    except Exception as e:
        print(f"❌ Error getting status: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    print("="*70)
    print("LIVE COMPRESSION TEST COMPLETE")
    print("="*70)
    print()

    return True

if __name__ == '__main__':
    success = asyncio.run(test_live_compression())
    sys.exit(0 if success else 1)
