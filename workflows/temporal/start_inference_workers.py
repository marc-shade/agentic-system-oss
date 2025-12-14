#!/usr/bin/env python3
"""
AI Inference Worker - completeu-server
Runs AI model inference and optimization workflows

Assigned Workflows:
1. Deep Learning Optimizer (every 6 hours)
2. Recursive Self-Improvement (weekly)
3. AI model routing and selection
4. Inference-heavy research tasks

Usage:
    python3 start_inference_workers.py
"""

import asyncio
import logging
import sys
import os

# Dynamic path setup
BASE_DIR = os.getenv("AGENTIC_SYSTEM_PATH", "~/agentic-system")
BASE_DIR = os.path.expanduser(BASE_DIR)  # Expand ~ for completeu-server
SCRIPT_DIR = os.path.join(BASE_DIR, "workflows", "temporal")
sys.path.insert(0, SCRIPT_DIR)

from temporalio.client import Client
from temporalio.worker import Worker

# Import inference workflows
from claude_deep_learning_optimizer import (
    ClaudeDeepLearningWorkflow,
    collect_performance_metrics,
    analyze_and_optimize
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


async def main():
    """Start all inference workflows"""
    logger.info("=" * 60)
    logger.info("AI INFERENCE WORKER - completeu-server")
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
    logger.info("AI Inference Workflows:")
    logger.info("  1. Deep Learning Optimizer (every 6 hours)")
    logger.info("  2. Recursive Self-Improvement (weekly)")
    logger.info("")
    logger.info("Ollama Models Available: 23")
    logger.info("  - Primary inference endpoint for cluster")
    logger.info("")

    workers = [
        Worker(
            client,
            task_queue="deep-learning-optimizer",
            workflows=[ClaudeDeepLearningWorkflow],
            activities=[
                collect_performance_metrics,
                analyze_and_optimize
            ]
        ),
        Worker(
            client,
            task_queue="recursive-self-improvement",
            workflows=[RecursiveSelfImprovementWorkflow],
            activities=[
                start_improvement_cycle,
                assess_baseline_performance,
                research_improvement_strategies,
                apply_improvement_strategies,
                validate_improvements,
                consolidate_learnings
            ]
        )
    ]

    logger.info("Starting all inference workers...")
    logger.info("")

    try:
        await asyncio.gather(*[worker.run() for worker in workers])
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Inference workers stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
