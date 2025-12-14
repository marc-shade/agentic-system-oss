#!/usr/bin/env python3
"""
Test caveman compression in cluster memory system
"""

import sys
from pathlib import Path

# Add cluster-deployment to path
sys.path.insert(0, str(Path(__file__).parent))

from cluster_memory import ClusterMemoryManager

def test_cluster_compression():
    """Test compression in cluster memory"""

    print("="*60)
    print("Cluster Memory Compression Test")
    print("="*60)
    print()

    # Initialize cluster memory manager
    node_config = Path.home() / ".claude" / "node-config.json"
    if not node_config.exists():
        print(f"⚠ Node config not found: {node_config}")
        print("Using default test configuration...")
        # Create minimal config for testing
        node_config.parent.mkdir(parents=True, exist_ok=True)
        import json
        test_config = {
            "node_id": "macpro51",
            "memory": {
                "local_db": "/mnt/agentic-system/databases/mcp/enhanced_memories.db",
                "personal_db": "/mnt/agentic-system/databases/cluster/nodes/macpro51/personal_memories.db",
                "shared_db": "/mnt/agentic-system/databases/cluster/shared_memories.db"
            }
        }
        with open(node_config, 'w') as f:
            json.dump(test_config, f, indent=2)
        print(f"✓ Created test config: {node_config}")
        print()

    manager = ClusterMemoryManager(node_config)
    print(f"✓ Initialized cluster memory manager for: {manager.node_id}")
    print()

    # Test 1: Create personal memory (should NOT compress)
    print("Test 1: Personal memory (no compression)...")
    result1 = manager.create_entity(
        name="test_personal_memory",
        entity_type="test",
        observations=[
            "This is a personal memory that should not be compressed because it's node-specific."
        ],
        scope="personal"
    )
    print(f"  Result: {result1['success']}")
    print(f"  Compression: {result1['compression']}")
    print()

    # Test 2: Create small shared memory (should NOT compress - too short)
    print("Test 2: Small shared memory (too short to compress)...")
    result2 = manager.create_entity(
        name="test_small_shared",
        entity_type="test",
        observations=["Small observation."],
        scope="shared"
    )
    print(f"  Result: {result2['success']}")
    print(f"  Compression: {result2['compression']}")
    print()

    # Test 3: Create large shared memory (SHOULD compress)
    print("Test 3: Large shared memory (should compress)...")
    result3 = manager.create_entity(
        name="test_large_shared",
        entity_type="knowledge",
        observations=[
            "The distributed execution system was tested with seven different test cases to verify functionality across the entire cluster. All tests passed successfully, demonstrating that tasks can be routed to the appropriate nodes based on their specific requirements and capabilities.",
            "We observed approximately 0.5 seconds of routing overhead and 1-2 seconds of SSH connection time, which is acceptable for tasks with execution times greater than 5 seconds. The parallel execution test showed linear scaling up to the number of available nodes in the cluster.",
            "One particularly interesting finding was that the task queue management handled concurrent submissions without any race conditions. This validates our distributed architecture design and demonstrates the robustness of our implementation."
        ],
        scope="shared"
    )
    print(f"  Result: {result3['success']}")
    print(f"  Compression enabled: {result3['compression'].get('enabled', False)}")
    if result3['compression'].get('enabled'):
        stats = result3['compression']
        print(f"  Observations compressed: {stats.get('observations_compressed', 0)}/{stats.get('total_observations', 0)}")
        print(f"  Token reduction: {stats.get('token_reduction_pct', 0):.1f}%")
        print(f"  Tokens saved: {stats.get('tokens_saved', 0)}")
    print()

    # Test 4: Search for memories
    print("Test 4: Searching for test memories...")
    results = manager.search_entities("test", scope="all")
    print(f"  Found {len(results)} entities")
    for result in results:
        print(f"    - {result.get('name')} ({result.get('scope', 'unknown')} scope)")
    print()

    print("="*60)
    print("✓ Cluster memory compression test complete!")
    print("="*60)
    print()

if __name__ == '__main__':
    test_cluster_compression()
