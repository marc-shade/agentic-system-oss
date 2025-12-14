#!/usr/bin/env python3
"""
Orchestrator Worker - mac-studio
Runs coordination and cluster management workflows

Assigned Workflows:
1. Cluster Memory Sync (every 15 min)
2. Cluster Task Orchestration (continuous)
3. Cluster Health Monitoring (every 5 min)
4. System Optimization (on-demand)
5. Memory Manager (hourly)

Usage:
    python3 start_orchestrator_workers.py
"""
import platform

import asyncio
import logging
import sys
from pathlib import Path

# Dynamic path setup
import os
BASE_DIR = os.getenv("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
SCRIPT_DIR = os.path.join(BASE_DIR, "workflows", "temporal")
sys.path.insert(0, SCRIPT_DIR)

from temporalio.client import Client
from temporalio.worker import Worker, WorkflowRunner

# Import orchestrator workflows
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

from cluster_health_monitoring_workflow import (
    ClusterHealthMonitoringWorkflow,
    check_node_heartbeats,
    update_node_status,
    attempt_node_recovery,
    record_health_metrics
)

from system_optimization_workflow import (
    SystemOptimizationWorkflow,
    collect_performance_metrics,
    analyze_bottlenecks,
    apply_optimizations,
    record_optimization_outcome
)

from autonomous_memory_manager import (

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    AutonomousMemoryManagerWorkflow,
    curate_memories,
    analyze_distribution,
    optimize_tiers,
    get_memory_usage_patterns
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start all orchestrator workflows"""
    logger.info("=" * 60)
    logger.info("ORCHESTRATOR WORKER - mac-studio")
    logger.info("=" * 60)

    # Connect to local Temporal server
    try:
        client = await Client.connect("localhost:7233")
        logger.info("✅ Connected to Temporal server (localhost:7233)")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    logger.info("")
    logger.info("Orchestrator Workflows:")
    logger.info("  1. Cluster Memory Sync (every 15 min)")
    logger.info("  2. Cluster Task Orchestration (continuous)")
    logger.info("  3. Cluster Health Monitoring (every 5 min)")
    logger.info("  4. System Optimization (on-demand)")
    logger.info("  5. Memory Manager (hourly)")
    logger.info("")

    # Create workers
    workers = [
        Worker(
            client,
            task_queue="cluster-memory-sync",
            workflows=[ClusterMemorySyncWorkflow],
            activities=[
                discover_active_nodes,
                collect_shared_memories,
                detect_memory_conflicts,
                resolve_conflicts,
                sync_to_node,
                verify_sync,
                record_sync_metrics
            ]
        ),
        Worker(
            client,
            task_queue="cluster-task-orchestration",
            workflows=[ClusterTaskOrchestrationWorkflow],
            activities=[
                fetch_pending_tasks,
                analyze_task_requirements,
                select_optimal_node,
                execute_task_on_node,
                update_task_status,
                record_task_metrics
            ]
        ),
        Worker(
            client,
            task_queue="cluster-health-monitoring",
            workflows=[ClusterHealthMonitoringWorkflow],
            activities=[
                check_node_heartbeats,
                update_node_status,
                attempt_node_recovery,
                record_health_metrics
            ]
        ),
        Worker(
            client,
            task_queue="system-optimization",
            workflows=[SystemOptimizationWorkflow],
            activities=[
                collect_performance_metrics,
                analyze_bottlenecks,
                apply_optimizations,
                record_optimization_outcome
            ]
        ),
        Worker(
            client,
            task_queue="autonomous-memory-manager",
            workflows=[AutonomousMemoryManagerWorkflow],
            activities=[
                curate_memories,
                analyze_distribution,
                optimize_tiers,
                get_memory_usage_patterns
            ]
        )
    ]

    logger.info("Starting all orchestrator workers...")
    logger.info("")

    try:
        await asyncio.gather(*[worker.run() for worker in workers])
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Orchestrator workers stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
