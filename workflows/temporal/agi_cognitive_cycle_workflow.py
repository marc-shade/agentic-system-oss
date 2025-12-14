#!/usr/bin/env python3
"""
AGI Cognitive Cycle Workflow
=============================

Runs the 6-phase AGI orchestrator cognitive loop via Temporal workflow:
1. PERCEIVE - Gather context, load high-salience memories
2. REASON - Apply meta-strategies, check similar past actions
3. ACT - Execute with outcome tracking
4. LEARN - Store experiences, identify patterns
5. REFLECT - Run sharpening, meta-cognition
6. IMPROVE - Recursive improvement, extract meta-strategies

Uses the AGIOrchestrator from the agi module which implements
all phases with proper memory and cluster brain integration.

Schedule: Every 2 hours
STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
import sys
import os

# Dynamic path detection for cross-node compatibility
_current_file = os.path.abspath(__file__)
_workflows_dir = os.path.dirname(_current_file)
_base_dir = os.path.dirname(os.path.dirname(_workflows_dir))
_mcp_memory_dir = os.path.join(_base_dir, "mcp-servers", "enhanced-memory-mcp")

sys.path.insert(0, _mcp_memory_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def run_agi_cognitive_cycle(mode: str = "full") -> Dict[str, Any]:
    """
    Run the full AGI cognitive cycle using the orchestrator.

    The AGIOrchestrator implements:
    - PERCEIVE: Load memories, context, goals, gaps
    - REASON: Apply meta-strategies, check similar actions
    - ACT: Execute with outcome tracking
    - LEARN: Pattern extraction, causal discovery
    - REFLECT: Sharpening, metacognitive state
    - IMPROVE: Recursive improvement, cluster brain sharing
    """
    try:
        from agi import get_agi_orchestrator

        orchestrator = get_agi_orchestrator()

        # Run the cognitive cycle with optional context
        result = orchestrator.run_cognitive_cycle(
            task_context={"mode": mode, "triggered_by": "temporal_workflow"},
            auto_improve=True
        )

        # Map CognitiveCycleResult attributes to our response format
        cycle_result = {
            "timestamp": datetime.now().isoformat(),
            "cycle_id": result.cycle_id,
            "success": result.success_score >= 0.5,
            "success_score": result.success_score,
            "phases_completed": len(result.state_transitions),
            "actions_taken": len(result.actions_taken),
            "learnings_recorded": len(result.learnings_captured.get("patterns", [])) if isinstance(result.learnings_captured, dict) else 0,
            "improvements_proposed": len(result.improvements_made.get("strategies", [])) if isinstance(result.improvements_made, dict) else 0,
            "cycle_duration_ms": result.cycle_duration_ms,
            "error": None
        }

        logger.info(f"AGI Cognitive Cycle complete: {cycle_result}")
        return cycle_result

    except Exception as e:
        logger.error(f"AGI Cognitive Cycle failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "success_score": 0.0,
            "error": str(e),
            "phases_completed": 0
        }


@activity.defn
async def share_cycle_with_cluster(cycle_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Share cognitive cycle results with cluster brain.
    """
    try:
        from cluster_brain import get_cluster_brain

        brain = get_cluster_brain()

        # Add learning about this cycle
        if cycle_result.get("success", False):
            learning_text = (
                f"Cognitive cycle {cycle_result.get('cycle_id', 'unknown')} completed: "
                f"{cycle_result.get('phases_completed', 0)} phases, "
                f"{cycle_result.get('learnings_recorded', 0)} learnings, "
                f"{cycle_result.get('improvements_proposed', 0)} improvements proposed"
            )

            learning_id = brain.add_learning(
                learning=learning_text,
                category="cognitive-cycle",
                source_task="agi_cognitive_cycle_workflow",
                success_score=1.0 if cycle_result.get("success") else 0.5,
                applies_to=["builder", "orchestrator", "researcher", "inference"]
            )

            return {
                "shared": True,
                "learning_id": learning_id,
                "message": learning_text
            }
        else:
            return {
                "shared": False,
                "reason": "Cycle did not succeed"
            }

    except Exception as e:
        logger.warning(f"Could not share with cluster brain: {e}")
        return {
            "shared": False,
            "error": str(e)
        }


@activity.defn
async def record_cycle_metrics(cycle_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record cognitive cycle metrics for performance tracking.
    """
    try:
        # Update agent performance metrics
        from agi import PerformanceTracker

        tracker = PerformanceTracker()

        # Record cycle completion
        if cycle_result.get("success", False):
            tracker.record_metric(
                "cognitive_cycle_success",
                1.0,
                {"cycle_id": cycle_result.get("cycle_id", "unknown")}
            )
            tracker.record_metric(
                "phases_completed",
                cycle_result.get("phases_completed", 0),
                {"cycle_id": cycle_result.get("cycle_id", "unknown")}
            )
        else:
            tracker.record_metric(
                "cognitive_cycle_success",
                0.0,
                {"cycle_id": cycle_result.get("cycle_id", "unknown"), "error": cycle_result.get("error", "")}
            )

        return {
            "metrics_recorded": True,
            "cycle_success": cycle_result.get("success", False)
        }

    except Exception as e:
        logger.warning(f"Could not record metrics: {e}")
        return {
            "metrics_recorded": False,
            "error": str(e)
        }


@workflow.defn
class AGICognitiveCycleWorkflow:
    """
    Main AGI Cognitive Cycle Workflow

    Runs the 6-phase cognitive loop via AGIOrchestrator:
    PERCEIVE → REASON → ACT → LEARN → REFLECT → IMPROVE

    Then shares results with cluster and records metrics.
    """

    @workflow.run
    async def run(self, mode: str = "full") -> Dict[str, Any]:
        """
        Execute AGI cognitive cycle workflow.

        Args:
            mode: "full" for all phases, "quick" for essential phases only
        """
        logger.info(f"Starting AGI Cognitive Cycle Workflow (mode: {mode})")

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            maximum_interval=timedelta(minutes=2),
            maximum_attempts=3
        )

        # Run the main cognitive cycle
        cycle_result = await workflow.execute_activity(
            run_agi_cognitive_cycle,
            args=[mode],
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=retry_policy
        )

        # Share with cluster brain (parallel with metrics)
        cluster_result, metrics_result = await asyncio.gather(
            workflow.execute_activity(
                share_cycle_with_cluster,
                args=[cycle_result],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy
            ),
            workflow.execute_activity(
                record_cycle_metrics,
                args=[cycle_result],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy
            )
        )

        result = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle_result,
            "cluster_shared": cluster_result.get("shared", False),
            "metrics_recorded": metrics_result.get("metrics_recorded", False),
            "overall_success": cycle_result.get("success", False)
        }

        logger.info(f"AGI Cognitive Cycle Workflow complete: {result}")
        return result


async def run_worker():
    """Run the Temporal worker for cognitive cycle"""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="agi-cognitive-cycle",
        workflows=[AGICognitiveCycleWorkflow],
        activities=[
            run_agi_cognitive_cycle,
            share_cycle_with_cluster,
            record_cycle_metrics
        ]
    )

    logger.info("AGI Cognitive Cycle worker started on queue: agi-cognitive-cycle")
    await worker.run()


async def run_once():
    """Run a single cognitive cycle (for testing)"""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        AGICognitiveCycleWorkflow.run,
        "full",
        id=f"agi-cognitive-cycle-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="agi-cognitive-cycle"
    )

    logger.info(f"Cognitive cycle result: {result}")
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AGI Cognitive Cycle Workflow")
    parser.add_argument("--mode", choices=["worker", "once"], default="worker",
                       help="Run as worker or execute once")

    args = parser.parse_args()

    if args.mode == "worker":
        asyncio.run(run_worker())
    else:
        asyncio.run(run_once())
