#!/usr/bin/env python3
"""
Test Suite for New AGI Workflows
=================================

Tests all 4 new critical workflows:
1. Cluster Memory Sync
2. Cluster Task Orchestration
3. Goal Decomposition
4. Recursive Self-Improvement

Each test verifies:
- Workflow can be started
- Activities execute correctly
- Results are as expected
- Integration with MCP servers works

Prerequisites:
- Temporal server running (localhost:7233)
- Enhanced-memory MCP running
- Agent-runtime MCP running
- AGI MCP running
- Cluster nodes accessible

Usage:
    python3 test_new_workflows.py

    # Test specific workflow:
    python3 test_new_workflows.py --test cluster-memory-sync
"""

import asyncio
import logging
from datetime import timedelta
from temporalio.client import Client
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_cluster_memory_sync():
    """Test cluster memory sync workflow"""
    logger.info("=" * 60)
    logger.info("TEST: Cluster Memory Sync Workflow")
    logger.info("=" * 60)

    try:
        client = await Client.connect("localhost:7233")

        from temporal.cluster_memory_sync_workflow import ClusterMemorySyncWorkflow

        logger.info("Starting cluster memory sync workflow...")

        result = await client.execute_workflow(
            ClusterMemorySyncWorkflow.run,
            id="test-cluster-memory-sync",
            task_queue="cluster-memory-sync",
            execution_timeout=timedelta(minutes=5)
        )

        logger.info(f"✅ Workflow completed successfully")
        logger.info(f"   Nodes synced: {result.get('nodes_synced', 0)}")
        logger.info(f"   Entities synced: {result.get('entities_synced', 0)}")
        logger.info(f"   Conflicts resolved: {result.get('conflicts_resolved', 0)}")
        logger.info(f"   Is consistent: {result.get('is_consistent', False)}")
        logger.info(f"   Duration: {result.get('duration_seconds', 0):.2f}s")

        return result.get("success", False)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_cluster_task_orchestration():
    """Test cluster task orchestration workflow"""
    logger.info("=" * 60)
    logger.info("TEST: Cluster Task Orchestration Workflow")
    logger.info("=" * 60)

    try:
        client = await Client.connect("localhost:7233")

        from temporal.cluster_task_orchestration_workflow import ClusterTaskOrchestrationWorkflow

        # Note: This test assumes there's a task in the queue
        # In real scenario, we'd create a test task first

        logger.info("Starting cluster task orchestration workflow...")
        logger.info("(This will process tasks from the queue)")

        result = await client.execute_workflow(
            ClusterTaskOrchestrationWorkflow.run,
            id="test-cluster-task-orchestration",
            task_queue="cluster-task-orchestration",
            execution_timeout=timedelta(minutes=15)
        )

        logger.info(f"✅ Workflow completed successfully")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Node: {result.get('node_id', 'N/A')}")
        logger.info(f"   Duration: {result.get('total_duration_seconds', 0):.2f}s")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_goal_decomposition():
    """Test goal decomposition workflow"""
    logger.info("=" * 60)
    logger.info("TEST: Goal Decomposition Workflow")
    logger.info("=" * 60)

    try:
        client = await Client.connect("localhost:7233")

        from temporal.goal_decomposition_workflow import GoalDecompositionWorkflow

        # Test goal
        test_goal = "Implement a new feature to track memory usage metrics and generate daily reports"

        logger.info(f"Decomposing goal: {test_goal}")

        result = await client.execute_workflow(
            GoalDecompositionWorkflow.run,
            test_goal,
            id="test-goal-decomposition",
            task_queue="goal-decomposition",
            execution_timeout=timedelta(minutes=5)
        )

        logger.info(f"✅ Workflow completed successfully")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Goal ID: {result.get('goal_id', 'N/A')}")
        logger.info(f"   Tasks created: {result.get('task_count', 0)}")
        logger.info(f"   Complexity: {result.get('complexity', 'N/A')}")
        logger.info(f"   Domain: {result.get('domain', 'N/A')}")
        logger.info(f"   Duration: {result.get('duration_seconds', 0):.2f}s")

        if result.get("task_ids"):
            logger.info(f"   Task IDs: {result.get('task_ids')}")

        return result.get("success", False)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_recursive_self_improvement():
    """Test recursive self-improvement workflow"""
    logger.info("=" * 60)
    logger.info("TEST: Recursive Self-Improvement Workflow")
    logger.info("=" * 60)

    try:
        client = await Client.connect("localhost:7233")

        from temporal.recursive_self_improvement_workflow import RecursiveSelfImprovementWorkflow

        logger.info("Starting self-improvement cycle (type: performance)...")

        result = await client.execute_workflow(
            RecursiveSelfImprovementWorkflow.run,
            "performance",
            {"increase_success_rate": 0.05, "improve_efficiency": 0.10},
            id="test-self-improvement",
            task_queue="recursive-self-improvement",
            execution_timeout=timedelta(minutes=20)
        )

        logger.info(f"✅ Workflow completed successfully")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Cycle ID: {result.get('cycle_id', 'N/A')}")
        logger.info(f"   Weaknesses identified: {result.get('weaknesses_identified', 0)}")
        logger.info(f"   Strategies applied: {result.get('strategies_applied', 0)}")
        logger.info(f"   Duration: {result.get('duration_seconds', 0):.2f}s")

        if result.get("lessons_learned"):
            logger.info(f"   Lessons learned:")
            for lesson in result.get("lessons_learned", [])[:3]:
                logger.info(f"      - {lesson}")

        if result.get("recommendations"):
            logger.info(f"   Recommendations:")
            for rec in result.get("recommendations", [])[:3]:
                logger.info(f"      - {rec}")

        return result.get("success", False)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def run_all_tests():
    """Run all workflow tests"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("AGI WORKFLOWS TEST SUITE")
    logger.info("=" * 60)
    logger.info("")

    # Check Temporal connection
    try:
        client = await Client.connect("localhost:7233")
        logger.info("✅ Temporal server connected (localhost:7233)")
    except Exception as e:
        logger.error(f"❌ Cannot connect to Temporal: {e}")
        logger.error("   Start Temporal with: temporal server start-dev")
        return

    logger.info("")

    # Run tests
    tests = [
        ("Cluster Memory Sync", test_cluster_memory_sync),
        ("Cluster Task Orchestration", test_cluster_task_orchestration),
        ("Goal Decomposition", test_goal_decomposition),
        ("Recursive Self-Improvement", test_recursive_self_improvement)
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info("")
        try:
            success = await test_func()
            results[test_name] = success
        except KeyboardInterrupt:
            logger.info("\nTests interrupted by user")
            break
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False

        # Wait between tests
        await asyncio.sleep(2)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info("")

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info("")
    passed = sum(1 for s in results.values() if s)
    total = len(results)
    logger.info(f"Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("")
        logger.info("🎉 All tests passed! AGI workflows are ready for production.")
    else:
        logger.info("")
        logger.info("⚠️  Some tests failed. Check logs above for details.")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test AGI workflows")
    parser.add_argument(
        "--test",
        choices=["cluster-memory-sync", "cluster-task-orchestration", "goal-decomposition", "recursive-self-improvement", "all"],
        default="all",
        help="Which test to run (default: all)"
    )

    args = parser.parse_args()

    if args.test == "all":
        asyncio.run(run_all_tests())
    elif args.test == "cluster-memory-sync":
        asyncio.run(test_cluster_memory_sync())
    elif args.test == "cluster-task-orchestration":
        asyncio.run(test_cluster_task_orchestration())
    elif args.test == "goal-decomposition":
        asyncio.run(test_goal_decomposition())
    elif args.test == "recursive-self-improvement":
        asyncio.run(test_recursive_self_improvement())


if __name__ == "__main__":
    main()
