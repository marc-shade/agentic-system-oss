#!/usr/bin/env python3
"""
Researcher Worker - macbook-air
Runs research, analysis, and documentation workflows

Assigned Workflows:
1. Overnight Research (10PM-7AM daily)
2. Pattern Learning (daily)
3. Goal Decomposition (on-demand)
4. Memory Consolidation (nightly)

Usage:
    python3 start_researcher_workers.py
"""

import asyncio
import logging
import sys
import os

# Dynamic path setup
BASE_DIR = os.getenv("AGENTIC_SYSTEM_PATH", "~/agentic-system")
BASE_DIR = os.path.expanduser(BASE_DIR)  # Expand ~ for macbook-air
SCRIPT_DIR = os.path.join(BASE_DIR, "workflows", "temporal")
sys.path.insert(0, SCRIPT_DIR)

from temporalio.client import Client
from temporalio.worker import Worker

# Import researcher workflows
from overnight_research_workflow import (
    OvernightResearchWorkflow
)
# overnight_research uses string-based activity names

from pattern_learning_workflow import (
    PatternLearningWorkflow,
    extract_patterns_from_outcomes,
    validate_patterns,
    propose_improvements_from_patterns,
    apply_improvements_safely
)

from goal_decomposition_workflow import (
    GoalDecompositionWorkflow,
    analyze_goal,
    decompose_goal_into_tasks,
    create_goal_in_runtime,
    create_tasks_in_runtime,
    schedule_task_execution
)

from memory_consolidation_workflow import (
    MemoryConsolidationWorkflow,
    run_pattern_extraction,
    run_causal_discovery,
    run_memory_compression,
    run_memory_curation,
    get_consolidation_statistics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start all researcher workflows"""
    logger.info("=" * 60)
    logger.info("RESEARCHER WORKER - macbook-air")
    logger.info("=" * 60)

    # Connect to orchestrator's Temporal server
    temporal_host = os.getenv("TEMPORAL_ADDRESS", "192.168.1.16:7233")
    try:
        client = await Client.connect(temporal_host)
        logger.info(f"✅ Connected to Temporal server ({temporal_host})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Temporal: {e}")
        return

    logger.info("")
    logger.info("Researcher Workflows:")
    logger.info("  1. Overnight Research (10PM-7AM daily)")
    logger.info("  2. Pattern Learning (daily)")
    logger.info("  3. Goal Decomposition (on-demand)")
    logger.info("  4. Memory Consolidation (nightly)")
    logger.info("")

    workers = [
        Worker(
            client,
            task_queue="overnight-research",
            workflows=[OvernightResearchWorkflow]
            # Activities registered separately via string names
        ),
        Worker(
            client,
            task_queue="pattern-learning",
            workflows=[PatternLearningWorkflow],
            activities=[
                extract_patterns_from_outcomes,
                validate_patterns,
                propose_improvements_from_patterns,
                apply_improvements_safely
            ]
        ),
        Worker(
            client,
            task_queue="goal-decomposition",
            workflows=[GoalDecompositionWorkflow],
            activities=[
                analyze_goal,
                decompose_goal_into_tasks,
                create_goal_in_runtime,
                create_tasks_in_runtime,
                schedule_task_execution
            ]
        ),
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
        )
    ]

    logger.info("Starting all researcher workers...")
    logger.info("")

    try:
        await asyncio.gather(*[worker.run() for worker in workers])
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Researcher workers stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
