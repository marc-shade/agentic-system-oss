#!/usr/bin/env python3
"""
Test Claude-Flow integration across the entire cluster
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))
from claude_flow_integration import ClaudeFlowCluster


def main():
    print("🧪 Testing Claude-Flow Cluster Integration")
    print("=" * 60)
    print()

    cluster = ClaudeFlowCluster()

    # Test 1: Basic command execution
    print("Test 1: Execute basic status command")
    try:
        result = cluster.execute_claude_flow_command("--version")
        print(f"  ✓ Status: {result.get('status')}")
        print(f"  ✓ Executed on: {result.get('node_id')}")
        output = result.get('output', '')
        if output:
            print(f"  ✓ Version: {output[:100]}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 2: Swarm agent spawning
    print("\nTest 2: Spawn multi-agent swarm")
    try:
        result = cluster.spawn_agent_swarm(
            agent_types=["coder", "reviewer", "tester"],
            task="Analyze system architecture",
            topology="hierarchical"
        )
        print(f"  ✓ Spawned {result.get('agents_spawned')} agents")
        print(f"  ✓ Results: {len(result.get('results', []))} tasks completed")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 3: SPARC workflow
    print("\nTest 3: SPARC TDD workflow")
    try:
        result = cluster.run_sparc_workflow(
            "Add logging system to distributed execution",
            mode="spec-pseudocode"
        )
        print(f"  ✓ Status: {result.get('status')}")
        print(f"  ✓ Executed on: {result.get('node_id')}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 4: Distributed code review
    print("\nTest 4: Distributed code review")
    try:
        result = cluster.distributed_code_review(
            files=[
                "cluster_offload.py",
                "claude_flow_integration.py"
            ],
            review_type="quality"
        )
        print(f"  ✓ Reviewed {result.get('files_reviewed')} files")
        print(f"  ✓ Review type: {result.get('review_type')}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    # Test 5: Cluster status
    print("\nTest 5: Get cluster status")
    try:
        status = cluster.get_swarm_status()
        print(f"  ✓ Status retrieved")
        print(f"  ✓ Data: {json.dumps(status, indent=2)[:200]}...")
    except Exception as e:
        print(f"  ✗ Failed: {e}")

    print("\n" + "=" * 60)
    print("✅ Claude-Flow cluster integration tests complete!")
    print()
    print("Available capabilities:")
    print("  • Multi-agent swarm orchestration")
    print("  • SPARC TDD workflows")
    print("  • Distributed code review")
    print("  • Hive-mind intelligence coordination")
    print("  • 54+ specialized agents")
    print("  • Persistent memory with AgentDB")
    print()


if __name__ == "__main__":
    main()
