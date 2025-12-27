#!/usr/bin/env python3
"""
Start All Temporal Workers
Runs all autonomous workflow workers in a single process

Workers:
- Memory Consolidation Worker (memory-consolidation queue)
- Autonomous Memory Manager Worker (memory-manager queue)
- System Optimization Worker (system-optimization queue)
- Model Discovery Worker (model-discovery queue)
- Visual Perception Worker (visual-perception queue)
- Visual Memory Consolidation Worker (visual-memory-consolidation queue)
- Cross-Modal Integration Worker (cross-modal queue)
- Librarian Consolidation Worker (librarian-consolidation queue)

STATUS: Production Ready
"""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Import all workflows and activities
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/workflows/temporal')

from memory_consolidation_workflow import (
    MemoryConsolidationWorkflow,
    run_pattern_extraction,
    run_causal_discovery,
    run_memory_compression,
    run_memory_curation,
    get_consolidation_statistics
)

from autonomous_memory_manager import (
    AutonomousMemoryManagerWorkflow,
    curate_memories,
    analyze_distribution,
    optimize_tiers,
    get_memory_usage_patterns
)

from system_optimization_workflow import (
    SystemOptimizationWorkflow,
    collect_performance_metrics,
    analyze_bottlenecks,
    apply_optimizations,
    record_optimization_outcome
)

from model_discovery_workflow import (
    ModelDiscoveryWorkflow,
    discover_cli_versions,
    discover_active_model,
    store_discovery_results,
    compare_with_previous
)

from visual_perception_workflow import (
    VisualPerceptionWorkflow,
    VisualMonitoringWorkflow,
    capture_screenshot,
    analyze_image,
    detect_visual_changes,
    store_visual_observation,
    batch_analyze_images
)

from visual_memory_consolidation_workflow import (
    VisualMemoryConsolidationWorkflow,
    get_daily_visual_memories,
    cluster_visual_memories,
    extract_visual_patterns,
    prune_low_value_memories,
    strengthen_visual_concepts,
    generate_consolidation_summary
)

from cross_modal_workflow import (
    CrossModalIntegrationWorkflow,
    CrossModalContextWorkflow,
    discover_correlations,
    extract_cross_modal_patterns,
    build_unified_context,
    maintain_memory_coherence,
    store_cross_modal_summary,
    sync_to_enhanced_memory
)

from librarian_consolidation_workflow import (
    LibrarianConsolidationWorkflow,
    run_librarian_consolidation,
    get_learnings_block,
    notify_consolidation_complete
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run all workflow workers"""
    client = await Client.connect("localhost:7233")
    
    # Create workers for each task queue
    workers = [
        Worker(
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
        ),
        Worker(
            client,
            task_queue="memory-manager",
            workflows=[AutonomousMemoryManagerWorkflow],
            activities=[
                curate_memories,
                analyze_distribution,
                optimize_tiers,
                get_memory_usage_patterns
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
            task_queue="model-discovery",
            workflows=[ModelDiscoveryWorkflow],
            activities=[
                discover_cli_versions,
                discover_active_model,
                store_discovery_results,
                compare_with_previous
            ]
        ),
        Worker(
            client,
            task_queue="visual-perception",
            workflows=[VisualPerceptionWorkflow, VisualMonitoringWorkflow],
            activities=[
                capture_screenshot,
                analyze_image,
                detect_visual_changes,
                store_visual_observation,
                batch_analyze_images
            ]
        ),
        Worker(
            client,
            task_queue="visual-memory-consolidation",
            workflows=[VisualMemoryConsolidationWorkflow],
            activities=[
                get_daily_visual_memories,
                cluster_visual_memories,
                extract_visual_patterns,
                prune_low_value_memories,
                strengthen_visual_concepts,
                generate_consolidation_summary
            ]
        ),
        Worker(
            client,
            task_queue="cross-modal",
            workflows=[CrossModalIntegrationWorkflow, CrossModalContextWorkflow],
            activities=[
                discover_correlations,
                extract_cross_modal_patterns,
                build_unified_context,
                maintain_memory_coherence,
                store_cross_modal_summary,
                sync_to_enhanced_memory
            ]
        ),
        Worker(
            client,
            task_queue="librarian-consolidation",
            workflows=[LibrarianConsolidationWorkflow],
            activities=[
                run_librarian_consolidation,
                get_learnings_block,
                notify_consolidation_complete
            ]
        )
    ]
    
    logger.info("="*60)
    logger.info("Starting all autonomous workflow workers...")
    logger.info("="*60)
    logger.info("Workers:")
    logger.info("  - Memory Consolidation (queue: memory-consolidation)")
    logger.info("  - Memory Manager (queue: memory-manager)")
    logger.info("  - System Optimization (queue: system-optimization)")
    logger.info("  - Model Discovery (queue: model-discovery)")
    logger.info("  - Visual Perception (queue: visual-perception)")
    logger.info("  - Visual Memory Consolidation (queue: visual-memory-consolidation)")
    logger.info("  - Cross-Modal Integration (queue: cross-modal)")
    logger.info("  - Librarian Consolidation (queue: librarian-consolidation)")
    logger.info("="*60)
    
    # Run all workers concurrently
    await asyncio.gather(*[worker.run() for worker in workers])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Workers stopped by user")
