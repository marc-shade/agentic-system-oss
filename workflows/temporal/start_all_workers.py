#!/usr/bin/env python3
"""
Start All Temporal Workers
Runs all autonomous workflow workers in a single process

Workers:
- Memory Consolidation Worker (memory-consolidation queue)
- Autonomous Memory Manager Worker (memory-manager queue)
- System Optimization Worker (system-optimization queue)

STATUS: Production Ready
"""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Import all workflows and activities
import sys
sys.path.insert(0, '/home/marc/agentic-system/workflows/temporal')

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
        )
    ]
    
    logger.info("="*60)
    logger.info("Starting all autonomous workflow workers...")
    logger.info("="*60)
    logger.info("Workers:")
    logger.info("  - Memory Consolidation (queue: memory-consolidation)")
    logger.info("  - Memory Manager (queue: memory-manager)")
    logger.info("  - System Optimization (queue: system-optimization)")
    logger.info("="*60)
    
    # Run all workers concurrently
    await asyncio.gather(*[worker.run() for worker in workers])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Workers stopped by user")
