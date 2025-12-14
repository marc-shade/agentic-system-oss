#!/usr/bin/env python3
"""
Start All AGI Workflows - Master Worker Script
===============================================

Starts all Temporal workflow workers for complete AGI operation:

EXISTING WORKFLOWS:
1. Autonomous Memory Manager (hourly)
2. Memory Consolidation (nightly)
3. Overnight Research (10PM-7AM)
4. Claude Deep Learning Optimizer (every 6h)
5. System Optimization (on-demand)

NEW CRITICAL WORKFLOWS:
6. Cluster Memory Sync (every 15 min)
7. Cluster Task Orchestration (continuous)
8. Goal Decomposition (on-demand)
9. Recursive Self-Improvement (weekly + on-demand)

Total: 9 workflows for full autonomous AGI operation

Usage:
    python3 start_all_agi_workers.py

    # Or start specific worker:
    python3 start_all_agi_workers.py --worker cluster-memory-sync

"""

import asyncio
import logging
import argparse
import sys
import os
from pathlib import Path

# Dynamic path detection for cross-node compatibility (sandbox-safe)
_current_file = os.path.abspath(__file__)
_script_dir = os.path.dirname(_current_file)
BASE_DIR = os.path.dirname(os.path.dirname(_script_dir))  # agentic-system root
WORKFLOWS_DIR = os.path.join(BASE_DIR, "workflows", "temporal")

# Ensure paths are correct
sys.path.insert(0, str(WORKFLOWS_DIR))

from temporalio.client import Client
from temporalio.worker import Worker

# Import all workflows
from autonomous_memory_manager import (
    AutonomousMemoryManagerWorkflow,
    curate_memories,
    analyze_distribution,
    optimize_tiers,
    get_memory_usage_patterns
)

from memory_consolidation_workflow import (
    MemoryConsolidationWorkflow,
    run_pattern_extraction,
    run_causal_discovery,
    run_memory_compression,
    run_memory_curation,
    get_consolidation_statistics
)

from overnight_research_workflow import OvernightResearchWorkflow
from claude_deep_learning_optimizer import (
    ClaudeDeepLearningWorkflow,
    collect_performance_metrics,
    analyze_usage_patterns,
    generate_optimizations,
    apply_optimizations,
    verify_optimizations,
    analyze_and_optimize,
    store_learning_record
)
from system_optimization_workflow import (
    SystemOptimizationWorkflow,
    collect_performance_metrics as analyze_system_resources,
    analyze_bottlenecks as identify_bottlenecks,
    apply_optimizations as execute_optimization
)

from cluster_memory_sync_workflow import (
    ClusterMemorySyncWorkflow,
    discover_active_nodes,
    collect_shared_memories,
    detect_memory_conflicts,
    resolve_conflicts,
    sync_to_node,
    verify_sync,
    record_sync_metrics
)

from cluster_task_orchestration_workflow import (
    ClusterTaskOrchestrationWorkflow,
    fetch_pending_tasks,
    analyze_task_requirements,
    select_optimal_node,
    execute_task_on_node,
    update_task_status,
    record_task_metrics
)

from goal_decomposition_workflow import (
    GoalDecompositionWorkflow,
    analyze_goal,
    decompose_goal_into_tasks,
    create_goal_in_runtime,
    create_tasks_in_runtime,
    schedule_task_execution
)

from recursive_self_improvement_workflow import (
    RecursiveSelfImprovementWorkflow,
    start_improvement_cycle,
    assess_baseline_performance,
    research_improvement_strategies,
    apply_improvement_strategies,
    validate_improvements,
    consolidate_learnings
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


WORKFLOW_CONFIGS = {
    "memory-manager": {
        "task_queue": "autonomous-memory-manager",
        "workflows": [AutonomousMemoryManagerWorkflow],
        "activities": [curate_memories, analyze_distribution, optimize_tiers, get_memory_usage_patterns],
        "description": "Hourly memory tier management"
    },
    "memory-consolidation": {
        "task_queue": "memory-consolidation",
        "workflows": [MemoryConsolidationWorkflow],
        "activities": [run_pattern_extraction, run_causal_discovery, run_memory_compression, run_memory_curation, get_consolidation_statistics],
        "description": "Nightly sleep-like consolidation"
    },
    "overnight-research": {
        "task_queue": "overnight-research",
        "workflows": [OvernightResearchWorkflow],
        "activities": [],
        "description": "Overnight research (10PM-7AM)"
    },
    "deep-learning-optimizer": {
        "task_queue": "claude-optimization",
        "workflows": [ClaudeDeepLearningWorkflow],
        "activities": [collect_performance_metrics, analyze_usage_patterns, generate_optimizations, apply_optimizations, verify_optimizations, analyze_and_optimize, store_learning_record],
        "description": "Claude optimization (every 6h)"
    },
    "system-optimization": {
        "task_queue": "system-optimization",
        "workflows": [SystemOptimizationWorkflow],
        "activities": [analyze_system_resources, identify_bottlenecks, execute_optimization],
        "description": "System optimization (on-demand)"
    },
    "cluster-memory-sync": {
        "task_queue": "cluster-memory-sync",
        "workflows": [ClusterMemorySyncWorkflow],
        "activities": [discover_active_nodes, collect_shared_memories, detect_memory_conflicts, resolve_conflicts, sync_to_node, verify_sync, record_sync_metrics],
        "description": "⭐ NEW: Cluster memory sync (every 15 min)"
    },
    "cluster-task-orchestration": {
        "task_queue": "cluster-task-orchestration",
        "workflows": [ClusterTaskOrchestrationWorkflow],
        "activities": [fetch_pending_tasks, analyze_task_requirements, select_optimal_node, execute_task_on_node, update_task_status, record_task_metrics],
        "description": "⭐ NEW: Distributed task routing (continuous)"
    },
    "goal-decomposition": {
        "task_queue": "goal-decomposition",
        "workflows": [GoalDecompositionWorkflow],
        "activities": [analyze_goal, decompose_goal_into_tasks, create_goal_in_runtime, create_tasks_in_runtime, schedule_task_execution],
        "description": "⭐ NEW: Auto-planning (on-demand)"
    },
    "recursive-self-improvement": {
        "task_queue": "recursive-self-improvement",
        "workflows": [RecursiveSelfImprovementWorkflow],
        "activities": [start_improvement_cycle, assess_baseline_performance, research_improvement_strategies, apply_improvement_strategies, validate_improvements, consolidate_learnings],
        "description": "⭐ NEW: Self-improvement cycles (weekly)"
    }
}


async def start_worker(worker_name: str, client: Client):
    """Start a specific workflow worker"""
    config = WORKFLOW_CONFIGS.get(worker_name)

    if not config:
        logger.error(f"Unknown worker: {worker_name}")
        return

    logger.info(f"Starting {worker_name} worker...")
    logger.info(f"  Description: {config['description']}")
    logger.info(f"  Task Queue: {config['task_queue']}")
    logger.info(f"  Workflows: {len(config['workflows'])}")
    logger.info(f"  Activities: {len(config['activities'])}")

    worker = Worker(
        client,
        task_queue=config["task_queue"],
        workflows=config["workflows"],
        activities=config["activities"]
    )

    await worker.run()


async def start_all_workers():
    """Start all workflow workers concurrently"""
    logger.info("=" * 60)
    logger.info("STARTING ALL AGI WORKFLOWS")
    logger.info("=" * 60)
    logger.info("")

    # Connect to Temporal
    try:
        client = await Client.connect("localhost:7233")
        logger.info("✅ Connected to Temporal server (localhost:7233)")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        logger.error("   Make sure Temporal server is running:")
        logger.error("   temporal server start-dev")
        return

    logger.info("")
    logger.info("Workflow Workers:")
    logger.info("")

    # List all workflows
    for i, (name, config) in enumerate(WORKFLOW_CONFIGS.items(), 1):
        status = "⭐ NEW" if "NEW:" in config["description"] else "  "
        logger.info(f"{status} {i}. {name:<30} - {config['description']}")

    logger.info("")
    logger.info("Starting all workers concurrently...")
    logger.info("")

    # Start all workers in parallel
    tasks = [
        start_worker(worker_name, client)
        for worker_name in WORKFLOW_CONFIGS.keys()
    ]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Received shutdown signal, stopping workers...")
    except Exception as e:
        logger.error(f"Worker error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Start AGI workflow workers")
    parser.add_argument(
        "--worker",
        help="Start specific worker (or 'all' for all workers)",
        choices=list(WORKFLOW_CONFIGS.keys()) + ["all"],
        default="all"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available workers"
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable Workers:")
        print("=" * 60)
        for i, (name, config) in enumerate(WORKFLOW_CONFIGS.items(), 1):
            status = "⭐ NEW" if "NEW:" in config["description"] else "  "
            print(f"{status} {i}. {name}")
            print(f"      {config['description']}")
            print(f"      Queue: {config['task_queue']}")
            print()
        return

    if args.worker == "all":
        asyncio.run(start_all_workers())
    else:
        async def run_single():
            client = await Client.connect("localhost:7233")
            await start_worker(args.worker, client)

        asyncio.run(run_single())


if __name__ == "__main__":
    main()
