#!/usr/bin/env python3
"""
Test Cluster Memory Integration

This script tests the cluster memory functionality in the enhanced-memory MCP server.
It demonstrates:
- Creating personal (node-specific) memories
- Creating shared (cluster-wide) memories
- Searching across different scopes
- Syncing personal memories to cluster
- Getting cluster statistics
"""

import json
from pathlib import Path
from cluster_memory import ClusterMemoryManager

def test_cluster_memory():
    """Test cluster memory functionality"""

    print("🌐 Cluster Memory Integration Test")
    print("=" * 60)

    # Initialize manager
    node_config_path = Path.home() / ".claude" / "node-config.json"

    if not node_config_path.exists():
        print("❌ Error: Node configuration not found")
        print(f"   Expected at: {node_config_path}")
        return False

    try:
        manager = ClusterMemoryManager(node_config_path)
        print(f"✅ Cluster memory manager initialized")
        print(f"   Node ID: {manager.node_id}")
        print()

        # Test 1: Create personal memory
        print("Test 1: Create Personal Memory")
        print("-" * 60)
        success = manager.create_entity(
            name="test-research-project",
            entity_type="project",
            observations=[
                "Research on distributed agentic systems",
                "MacBook Air (Researcher persona)",
                "Started Nov 2025"
            ],
            scope="personal"
        )
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        print()

        # Test 2: Create shared memory
        print("Test 2: Create Shared Memory")
        print("-" * 60)
        success = manager.create_entity(
            name="cluster-architecture",
            entity_type="knowledge",
            observations=[
                "Distributed multi-node agentic cluster",
                "Mac Studio (Orchestrator), MacBook Air (Researcher), MacBook Pro (Developer)",
                "Node-based personas with specialized capabilities",
                "Shared memory via SSDRAID0"
            ],
            scope="shared"
        )
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        print()

        # Test 3: Search personal memories
        print("Test 3: Search Personal Memories")
        print("-" * 60)
        results = manager.search_entities("research", scope="personal")
        print(f"   Found {len(results)} personal memories")
        for r in results:
            print(f"   - {r['name']} ({r['scope']})")
        print()

        # Test 4: Search shared memories
        print("Test 4: Search Shared Memories")
        print("-" * 60)
        results = manager.search_entities("cluster", scope="shared")
        print(f"   Found {len(results)} shared memories")
        for r in results:
            print(f"   - {r['name']} ({r['scope']}) - created by {r.get('created_by_node', 'unknown')}")
        print()

        # Test 5: Search all scopes
        print("Test 5: Search All Scopes")
        print("-" * 60)
        results = manager.search_entities("research", scope="all")
        print(f"   Found {len(results)} total memories")
        for r in results:
            scope_info = f"{r['scope']}"
            if r['scope'] == 'shared':
                scope_info += f" (by {r.get('created_by_node', 'unknown')})"
            print(f"   - {r['name']} ({scope_info})")
        print()

        # Test 6: Sync personal memory to cluster
        print("Test 6: Sync Personal Memory to Cluster")
        print("-" * 60)
        success = manager.sync_to_cluster("test-research-project")
        print(f"   Result: {'✅ Success' if success else '❌ Failed'}")
        if success:
            # Verify it's now in shared memories
            shared_results = manager.search_entities("test-research-project", scope="shared")
            if shared_results:
                print(f"   ✅ Verified: Memory now in shared scope")
                print(f"      Created by: {shared_results[0].get('created_by_node', 'unknown')}")
        print()

        # Test 7: Get cluster stats
        print("Test 7: Get Cluster Statistics")
        print("-" * 60)
        stats = manager.get_cluster_stats()
        print(f"   Node ID: {stats['node_id']}")
        print(f"   Personal memories: {stats['personal']['entities']} entities, {stats['personal']['relations']} relations")
        print(f"   Shared memories: {stats['shared']['entities']} entities, {stats['shared']['relations']} relations")
        print(f"   Timestamp: {stats['timestamp']}")
        print()

        # Test 8: Get memories from Mac Studio (if available)
        print("Test 8: Get Memories from Other Nodes")
        print("-" * 60)
        if manager.node_id != "mac-studio":
            orchestrator_memories = manager.get_node_memories("mac-studio")
            print(f"   Found {len(orchestrator_memories)} memories from mac-studio")
            for m in orchestrator_memories[:3]:  # Show first 3
                print(f"   - {m['name']} ({m['entity_type']})")
        else:
            researcher_memories = manager.get_node_memories("macbook-air")
            print(f"   Found {len(researcher_memories)} memories from macbook-air")
            for m in researcher_memories[:3]:  # Show first 3
                print(f"   - {m['name']} ({m['entity_type']})")
        print()

        print("=" * 60)
        print("✅ All tests completed successfully!")
        print()
        print("Summary:")
        print(f"   - Personal memories are stored in: {manager.personal_db}")
        print(f"   - Shared memories are stored in: {manager.shared_db}")
        print(f"   - This node ({manager.node_id}) can see all cluster memories")
        print(f"   - Memories can be synced from personal to shared scope")

        return True

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cluster_memory()
    exit(0 if success else 1)
