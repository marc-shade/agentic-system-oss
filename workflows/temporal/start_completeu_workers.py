#!/usr/bin/env python3
"""
Start Completeu-Server Temporal Workers
=========================================

Comprehensive worker configuration for completeu-server (Mac Studio)
Runs all workflows appropriate for the orchestrator/research/memory node.

Node Role: Orchestrator + Research + Memory Hub + AGI + Hardware Integration
Platform: macOS (Darwin)
Storage: /Volumes/SSDRAID0/agentic-system

Tiers Deployed:
- Tier 0: Essential cluster infrastructure (health, coordination, memory sync)
- Tier 1: Orchestration (task routing, queue processing, goal decomposition)
- Tier 2: Memory management (consolidation, autonomous manager, pattern learning)
- Tier 3: Research (backup for macbook-air)
- Tier 5: System optimization (self-improvement, deep learning)
- Tier 6: Hardware integration (Arduino Surface)

STATUS: Production Ready
Created: 2025-11-24
"""

import asyncio
import logging
import os
import platform
import socket
from pathlib import Path
from temporalio.client import Client
from temporalio.worker import Worker


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent.parent


# Platform detection
SYSTEM = platform.system()
HOSTNAME = socket.gethostname()

# Dynamic storage path detection
BASE_DIR = _get_storage_base()

# Add workflow directory to path
import sys
sys.path.insert(0, str(BASE_DIR / "workflows" / "temporal"))
sys.path.insert(0, str(BASE_DIR / "cluster-deployment"))
sys.path.insert(0, str(BASE_DIR / "intelligent-agents"))
sys.path.insert(0, str(BASE_DIR / "mcp-servers" / "enhanced-memory-mcp"))
sys.path.insert(0, str(BASE_DIR / "mcp-servers" / "agi-mcp"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TIER 0: Essential Cluster Infrastructure
# ============================================================================

try:
    from cluster_health_monitoring_workflow import (
        ClusterHealthMonitoringWorkflow,
        check_node_heartbeats,
        update_node_status,
        attempt_node_recovery,
        send_health_alerts
    )
    TIER0_HEALTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Cluster health monitoring not available: {e}")
    TIER0_HEALTH_AVAILABLE = False

try:
    from cluster_coordination_workflow import (
        ClusterCoordinationWorkflow,
        monitor_node_health,
        distribute_task,
        handle_node_failure,
        sync_shared_memory,
        balance_workload
    )
    TIER0_COORDINATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Cluster coordination not available: {e}")
    TIER0_COORDINATION_AVAILABLE = False

try:
    from cluster_memory_sync_workflow import (
        ClusterMemorySyncWorkflow,
        collect_personal_memories,
        merge_to_shared_memory,
        distribute_shared_updates,
        resolve_memory_conflicts
    )
    TIER0_MEMORY_SYNC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Cluster memory sync not available: {e}")
    TIER0_MEMORY_SYNC_AVAILABLE = False

# ============================================================================
# TIER 1: Orchestration & Task Management
# ============================================================================

try:
    from cluster_task_orchestration_workflow import (
        ClusterTaskOrchestrationWorkflow,
        pull_task_from_queue,
        analyze_task_requirements,
        select_optimal_node,
        execute_task_on_node,
        monitor_task_execution,
        handle_task_failure,
        update_performance_metrics
    )
    TIER1_ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Task orchestration not available: {e}")
    TIER1_ORCHESTRATION_AVAILABLE = False

try:
    from task_queue_processor_workflow import (
        TaskQueueProcessorWorkflow,
        get_next_queued_task,
        process_task,
        update_task_status
    )
    TIER1_QUEUE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Task queue processor not available: {e}")
    TIER1_QUEUE_AVAILABLE = False

try:
    from goal_decomposition_workflow import (
        GoalDecompositionWorkflow,
        decompose_goal,
        create_task_dependencies,
        validate_task_structure
    )
    TIER1_GOALS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Goal decomposition not available: {e}")
    TIER1_GOALS_AVAILABLE = False

# ============================================================================
# TIER 2: Memory Management
# ============================================================================

try:
    from memory_consolidation_workflow import (
        MemoryConsolidationWorkflow,
        run_pattern_extraction,
        run_causal_discovery,
        run_memory_compression,
        run_memory_curation,
        get_consolidation_statistics
    )
    TIER2_CONSOLIDATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Memory consolidation not available: {e}")
    TIER2_CONSOLIDATION_AVAILABLE = False

try:
    from autonomous_memory_manager import (
        AutonomousMemoryManagerWorkflow,
        curate_memories,
        analyze_distribution,
        optimize_tiers,
        get_memory_usage_patterns
    )
    TIER2_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Autonomous memory manager not available: {e}")
    TIER2_MANAGER_AVAILABLE = False

try:
    from pattern_learning_workflow import (
        PatternLearningWorkflow,
        extract_patterns_from_outcomes,
        validate_patterns,
        propose_improvements,
        apply_improvement,
        record_pattern_learning_outcome
    )
    TIER2_PATTERN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Pattern learning not available: {e}")
    TIER2_PATTERN_AVAILABLE = False

# ============================================================================
# TIER 3: Research (Backup)
# ============================================================================

try:
    from overnight_research_workflow import (
        OvernightResearchWorkflow,
        execute_research_task,
        compile_findings,
        store_research_results
    )
    TIER3_RESEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Overnight research not available: {e}")
    TIER3_RESEARCH_AVAILABLE = False

try:
    from overnight_research_workflow_enhanced import (
        OvernightResearchEnhancedWorkflow,
        enhanced_research_task,
        integrate_with_memory,
        generate_research_report
    )
    TIER3_RESEARCH_ENHANCED_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Enhanced research not available: {e}")
    TIER3_RESEARCH_ENHANCED_AVAILABLE = False

# ============================================================================
# TIER 5: System Optimization & AGI
# ============================================================================

try:
    from system_optimization_workflow import (
        SystemOptimizationWorkflow,
        collect_performance_metrics,
        analyze_bottlenecks,
        apply_optimizations,
        record_optimization_outcome
    )
    TIER5_OPTIMIZATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"System optimization not available: {e}")
    TIER5_OPTIMIZATION_AVAILABLE = False

try:
    from recursive_self_improvement_workflow import (
        RecursiveSelfImprovementWorkflow,
        start_improvement_cycle,
        assess_baseline_performance,
        identify_weaknesses,
        research_solutions,
        plan_improvements,
        implement_improvement,
        validate_improvement,
        consolidate_learnings
    )
    TIER5_SELF_IMPROVEMENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Recursive self-improvement not available: {e}")
    TIER5_SELF_IMPROVEMENT_AVAILABLE = False

try:
    from claude_deep_learning_optimizer import (
        ClaudeDeepLearningOptimizer,
        analyze_learning_patterns,
        optimize_model_usage,
        track_learning_outcomes
    )
    TIER5_DEEP_LEARNING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Deep learning optimizer not available: {e}")
    TIER5_DEEP_LEARNING_AVAILABLE = False

# ============================================================================
# TIER 6: Hardware Integration
# ============================================================================

try:
    from arduino_status_rotation_workflow import (
        ArduinoStatusRotationWorkflow,
        get_system_status,
        update_arduino_display,
        check_arduino_connection
    )
    TIER6_ARDUINO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Arduino status rotation not available: {e}")
    TIER6_ARDUINO_AVAILABLE = False


async def main():
    """Run all completeu-server workflow workers"""

    logger.info("="*80)
    logger.info("Starting Completeu-Server Temporal Workers")
    logger.info("="*80)
    logger.info(f"Platform: {SYSTEM}")
    logger.info(f"Hostname: {HOSTNAME}")
    logger.info(f"Base Directory: {BASE_DIR}")
    logger.info(f"Temporal Address: localhost:7233")
    logger.info("="*80)

    # Connect to Temporal server
    client = await Client.connect("localhost:7233")

    workers = []

    # ========================================================================
    # TIER 0: Essential Cluster Infrastructure
    # ========================================================================

    if TIER0_HEALTH_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="cluster-health",
            workflows=[ClusterHealthMonitoringWorkflow],
            activities=[
                check_node_heartbeats,
                update_node_status,
                attempt_node_recovery,
                send_health_alerts
            ]
        ))
        logger.info("✅ Tier 0: Cluster Health Monitoring")
    else:
        logger.warning("⚠️  Tier 0: Cluster Health Monitoring - UNAVAILABLE")

    if TIER0_COORDINATION_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="cluster-coordination",
            workflows=[ClusterCoordinationWorkflow],
            activities=[
                monitor_node_health,
                distribute_task,
                handle_node_failure,
                sync_shared_memory,
                balance_workload
            ]
        ))
        logger.info("✅ Tier 0: Cluster Coordination")
    else:
        logger.warning("⚠️  Tier 0: Cluster Coordination - UNAVAILABLE")

    if TIER0_MEMORY_SYNC_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="cluster-memory-sync",
            workflows=[ClusterMemorySyncWorkflow],
            activities=[
                collect_personal_memories,
                merge_to_shared_memory,
                distribute_shared_updates,
                resolve_memory_conflicts
            ]
        ))
        logger.info("✅ Tier 0: Cluster Memory Sync")
    else:
        logger.warning("⚠️  Tier 0: Cluster Memory Sync - UNAVAILABLE")

    # ========================================================================
    # TIER 1: Orchestration & Task Management
    # ========================================================================

    if TIER1_ORCHESTRATION_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="task-orchestration",
            workflows=[ClusterTaskOrchestrationWorkflow],
            activities=[
                pull_task_from_queue,
                analyze_task_requirements,
                select_optimal_node,
                execute_task_on_node,
                monitor_task_execution,
                handle_task_failure,
                update_performance_metrics
            ]
        ))
        logger.info("✅ Tier 1: Task Orchestration")
    else:
        logger.warning("⚠️  Tier 1: Task Orchestration - UNAVAILABLE")

    if TIER1_QUEUE_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="task-queue",
            workflows=[TaskQueueProcessorWorkflow],
            activities=[
                get_next_queued_task,
                process_task,
                update_task_status
            ]
        ))
        logger.info("✅ Tier 1: Task Queue Processor")
    else:
        logger.warning("⚠️  Tier 1: Task Queue Processor - UNAVAILABLE")

    if TIER1_GOALS_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="goal-decomposition",
            workflows=[GoalDecompositionWorkflow],
            activities=[
                decompose_goal,
                create_task_dependencies,
                validate_task_structure
            ]
        ))
        logger.info("✅ Tier 1: Goal Decomposition")
    else:
        logger.warning("⚠️  Tier 1: Goal Decomposition - UNAVAILABLE")

    # ========================================================================
    # TIER 2: Memory Management
    # ========================================================================

    if TIER2_CONSOLIDATION_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="memory-consolidation",
            workflows=[MemoryConsolidationWorkflow],
            activities=[
                run_pattern_extraction,
                run_causal_discovery,
                run_memory_compression,
                run_memory_curation,
                get_consolidation_statistics
            ]
        ))
        logger.info("✅ Tier 2: Memory Consolidation")
    else:
        logger.warning("⚠️  Tier 2: Memory Consolidation - UNAVAILABLE")

    if TIER2_MANAGER_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="memory-manager",
            workflows=[AutonomousMemoryManagerWorkflow],
            activities=[
                curate_memories,
                analyze_distribution,
                optimize_tiers,
                get_memory_usage_patterns
            ]
        ))
        logger.info("✅ Tier 2: Autonomous Memory Manager")
    else:
        logger.warning("⚠️  Tier 2: Autonomous Memory Manager - UNAVAILABLE")

    if TIER2_PATTERN_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="pattern-learning",
            workflows=[PatternLearningWorkflow],
            activities=[
                extract_patterns_from_outcomes,
                validate_patterns,
                propose_improvements,
                apply_improvement,
                record_pattern_learning_outcome
            ]
        ))
        logger.info("✅ Tier 2: Pattern Learning")
    else:
        logger.warning("⚠️  Tier 2: Pattern Learning - UNAVAILABLE")

    # ========================================================================
    # TIER 3: Research (Backup)
    # ========================================================================

    if TIER3_RESEARCH_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="research",
            workflows=[OvernightResearchWorkflow],
            activities=[
                execute_research_task,
                compile_findings,
                store_research_results
            ]
        ))
        logger.info("✅ Tier 3: Overnight Research (backup)")
    else:
        logger.warning("⚠️  Tier 3: Overnight Research - UNAVAILABLE")

    if TIER3_RESEARCH_ENHANCED_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="research-enhanced",
            workflows=[OvernightResearchEnhancedWorkflow],
            activities=[
                enhanced_research_task,
                integrate_with_memory,
                generate_research_report
            ]
        ))
        logger.info("✅ Tier 3: Enhanced Research (backup)")
    else:
        logger.warning("⚠️  Tier 3: Enhanced Research - UNAVAILABLE")

    # ========================================================================
    # TIER 5: System Optimization & AGI
    # ========================================================================

    if TIER5_OPTIMIZATION_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="system-optimization",
            workflows=[SystemOptimizationWorkflow],
            activities=[
                collect_performance_metrics,
                analyze_bottlenecks,
                apply_optimizations,
                record_optimization_outcome
            ]
        ))
        logger.info("✅ Tier 5: System Optimization")
    else:
        logger.warning("⚠️  Tier 5: System Optimization - UNAVAILABLE")

    if TIER5_SELF_IMPROVEMENT_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="self-improvement",
            workflows=[RecursiveSelfImprovementWorkflow],
            activities=[
                start_improvement_cycle,
                assess_baseline_performance,
                identify_weaknesses,
                research_solutions,
                plan_improvements,
                implement_improvement,
                validate_improvement,
                consolidate_learnings
            ]
        ))
        logger.info("✅ Tier 5: Recursive Self-Improvement")
    else:
        logger.warning("⚠️  Tier 5: Recursive Self-Improvement - UNAVAILABLE")

    if TIER5_DEEP_LEARNING_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="deep-learning",
            workflows=[ClaudeDeepLearningOptimizer],
            activities=[
                analyze_learning_patterns,
                optimize_model_usage,
                track_learning_outcomes
            ]
        ))
        logger.info("✅ Tier 5: Deep Learning Optimizer")
    else:
        logger.warning("⚠️  Tier 5: Deep Learning Optimizer - UNAVAILABLE")

    # ========================================================================
    # TIER 6: Hardware Integration
    # ========================================================================

    if TIER6_ARDUINO_AVAILABLE:
        workers.append(Worker(
            client,
            task_queue="arduino-status",
            workflows=[ArduinoStatusRotationWorkflow],
            activities=[
                get_system_status,
                update_arduino_display,
                check_arduino_connection
            ]
        ))
        logger.info("✅ Tier 6: Arduino Status Rotation")
    else:
        logger.warning("⚠️  Tier 6: Arduino Status Rotation - UNAVAILABLE")

    # ========================================================================
    # Summary and Start
    # ========================================================================

    logger.info("="*80)
    logger.info(f"Total Workers: {len(workers)}")
    logger.info("="*80)
    logger.info("Worker Queues:")
    for i, worker in enumerate(workers, 1):
        logger.info(f"  {i}. {worker.task_queue}")
    logger.info("="*80)
    logger.info("Starting all workers...")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*80)

    if not workers:
        logger.error("No workers available! Check workflow imports.")
        return

    # Run all workers concurrently
    await asyncio.gather(*[worker.run() for worker in workers])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("")
        logger.info("="*80)
        logger.info("Workers stopped by user")
        logger.info("="*80)
    except Exception as e:
        logger.error(f"Worker startup failed: {e}", exc_info=True)
