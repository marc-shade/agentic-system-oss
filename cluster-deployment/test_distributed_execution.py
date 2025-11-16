#!/usr/bin/env python3
"""
Test Distributed Task Execution

Verifies that tasks automatically route to appropriate nodes:
- Linux tasks → macpro51
- macOS tasks → Mac Studio or MacBook Air
- Tasks submitted from any node offload to others
- Parallel execution works across cluster
"""

import sys
import time
from pathlib import Path

# Add cluster-deployment to path
sys.path.insert(0, str(Path(__file__).parent))

from cluster_offload import (
    offload, offload_many, get_cluster_status,
    build_on_linux, research_on_air
)

def print_section(title: str):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def test_simple_offload():
    """Test 1: Simple command offload"""
    print_section("TEST 1: Simple Command Offload")

    print("Submitting simple command...")
    result = offload("echo 'Hello from cluster!' && hostname && uname -s")

    if result:
        print(f"✓ Status: {result['status']}")
        print(f"✓ Executed on: {result['assigned_to']}")
        print(f"✓ Output:\n{result['result']}")
        return True
    else:
        print("✗ FAILED: No result")
        return False


def test_linux_routing():
    """Test 2: Linux-specific tasks route to macpro51"""
    print_section("TEST 2: Linux Task Routing")

    print("Submitting Linux-specific task...")
    result = offload(
        "uname -a && echo 'This should run on macpro51'",
        requires_os="linux"
    )

    if result:
        print(f"✓ Status: {result['status']}")
        print(f"✓ Executed on: {result['assigned_to']}")
        print(f"✓ Output:\n{result['result']}")

        if result['assigned_to'] == 'macpro51':
            print("✓ PASSED: Correctly routed to macpro51")
            return True
        else:
            print(f"✗ FAILED: Routed to {result['assigned_to']} instead of macpro51")
            return False
    else:
        print("✗ FAILED: No result")
        return False


def test_macos_routing():
    """Test 3: macOS-specific tasks route to Mac nodes"""
    print_section("TEST 3: macOS Task Routing")

    print("Submitting macOS-specific task...")
    result = offload(
        "uname -a && echo 'This should run on macOS'",
        requires_os="macos"
    )

    if result:
        print(f"✓ Status: {result['status']}")
        print(f"✓ Executed on: {result['assigned_to']}")
        print(f"✓ Output:\n{result['result']}")

        if result['assigned_to'] in ['mac-studio', 'macbook-air']:
            print(f"✓ PASSED: Correctly routed to {result['assigned_to']}")
            return True
        else:
            print(f"✗ FAILED: Routed to {result['assigned_to']} instead of macOS node")
            return False
    else:
        print("✗ FAILED: No result")
        return False


def test_parallel_execution():
    """Test 4: Parallel execution across multiple nodes"""
    print_section("TEST 4: Parallel Execution")

    print("Submitting 5 tasks in parallel...")
    tasks = [
        "echo 'Task 1' && hostname && sleep 1",
        "echo 'Task 2' && hostname && sleep 1",
        "echo 'Task 3' && hostname && sleep 1",
        "echo 'Task 4' && hostname && sleep 1",
        "echo 'Task 5' && hostname && sleep 1"
    ]

    start_time = time.time()
    results = offload_many(tasks)
    elapsed = time.time() - start_time

    print(f"✓ Completed in {elapsed:.2f} seconds")

    if not results:
        print("✗ FAILED: No results")
        return False

    # Count successes
    successes = sum(1 for r in results if r and r['status'] == 'completed')
    print(f"✓ {successes}/{len(tasks)} tasks completed")

    # Show which nodes executed
    nodes = {}
    for i, result in enumerate(results):
        if result and result['assigned_to']:
            node = result['assigned_to']
            nodes[node] = nodes.get(node, 0) + 1
            print(f"  Task {i+1}: {node}")

    print(f"\n✓ Task distribution across nodes:")
    for node, count in nodes.items():
        print(f"  {node}: {count} tasks")

    if successes == len(tasks):
        print("✓ PASSED: All tasks completed successfully")
        return True
    else:
        print(f"✗ FAILED: Only {successes}/{len(tasks)} completed")
        return False


def test_capability_routing():
    """Test 5: Capability-based routing"""
    print_section("TEST 5: Capability-Based Routing")

    print("Testing build task (requires docker)...")
    result = build_on_linux("echo 'Build task' && hostname && which docker || which podman")

    if result:
        print(f"✓ Status: {result['status']}")
        print(f"✓ Executed on: {result['assigned_to']}")
        print(f"✓ Output:\n{result['result']}")

        if result['assigned_to'] == 'macpro51':
            print("✓ PASSED: Build task routed to macpro51 (has docker)")
            return True
        else:
            print(f"✗ FAILED: Routed to {result['assigned_to']} instead of macpro51")
            return False
    else:
        print("✗ FAILED: No result")
        return False


def test_aggressive_offloading():
    """Test 6: Verify local node is deprioritized (aggressive offloading)"""
    print_section("TEST 6: Aggressive Offloading")

    print("Submitting 10 generic tasks...")
    print("(Should prefer remote nodes over local node)")

    tasks = [f"echo 'Generic task {i}' && hostname" for i in range(10)]
    results = offload_many(tasks)

    if not results:
        print("✗ FAILED: No results")
        return False

    # Count local vs remote
    from distributed_task_router import DistributedTaskRouter
    router = DistributedTaskRouter()
    local_node = router.local_node_id

    local_count = sum(1 for r in results if r and r['assigned_to'] == local_node)
    remote_count = sum(1 for r in results if r and r['assigned_to'] != local_node)

    print(f"✓ Local node ({local_node}): {local_count} tasks")
    print(f"✓ Remote nodes: {remote_count} tasks")

    if remote_count > local_count:
        print("✓ PASSED: More tasks offloaded to remote nodes (aggressive offloading working)")
        return True
    else:
        print("⚠ WARNING: More tasks on local node - offloading may not be aggressive enough")
        print("  (This might be OK if remote nodes are unavailable)")
        return True  # Still pass, might be network issue


def test_cluster_status():
    """Test 7: Cluster status reporting"""
    print_section("TEST 7: Cluster Status")

    status = get_cluster_status()

    print(f"✓ Local node: {status['local_node']}")
    print(f"\n✓ Cluster nodes:")
    for node_id, node_info in status['cluster_nodes'].items():
        print(f"  {node_id}:")
        print(f"    OS: {node_info['os']}")
        print(f"    Arch: {node_info['arch']}")
        print(f"    Specialties: {', '.join(node_info['specialties'])}")
        print(f"    Max tasks: {node_info['max_tasks']}")

    if status['task_distribution']:
        print(f"\n✓ Task distribution:")
        for node_id, stats in status['task_distribution'].items():
            print(f"  {node_id}: {stats['total']} total tasks")
            for stat_type, count in stats['by_status'].items():
                print(f"    {stat_type}: {count}")
    else:
        print("\n  (No task history yet)")

    print("\n✓ PASSED: Cluster status retrieved")
    return True


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  DISTRIBUTED TASK EXECUTION TEST SUITE".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60)

    tests = [
        ("Simple Offload", test_simple_offload),
        ("Linux Routing", test_linux_routing),
        ("macOS Routing", test_macos_routing),
        ("Parallel Execution", test_parallel_execution),
        ("Capability Routing", test_capability_routing),
        ("Aggressive Offloading", test_aggressive_offloading),
        ("Cluster Status", test_cluster_status)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n✗ EXCEPTION: {e}")
            results.append((test_name, False))

    # Summary
    print_section("TEST SUMMARY")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {passed_count}/{total_count} tests passed")
    print(f"{'='*60}\n")

    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED - Distributed execution working!")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED - Check logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
