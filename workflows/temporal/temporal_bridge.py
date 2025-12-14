#!/usr/bin/env python3
"""
Temporal Bridge - Connect agent-runtime goals to Temporal workflows

This module provides a simple interface to trigger Temporal workflows
from the agent-runtime MCP or CLI.

Usage:
    # Trigger goal decomposition workflow
    python temporal_bridge.py --goal "Build a new feature for X"

    # Trigger specific workflow
    python temporal_bridge.py --workflow research-to-code --args '["AI agents", "/tmp/output"]'

    # List available workflows
    python temporal_bridge.py --list

Available Workflows:
    - goal-decomposition: Break goals into actionable tasks
    - memory-consolidation: Daily memory consolidation (sleep-like)
    - research-to-code: Research papers → implementation
    - self-improvement: Autonomous self-improvement cycle
    - system-optimization: System performance optimization
    - curiosity-exploration: Autonomous knowledge discovery
    - agi-cognitive-cycle: Full AGI 6-phase cognitive cycle
"""

import asyncio
import argparse
import json
import logging
import os
from datetime import timedelta
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("temporal-bridge")

# Workflow configurations
WORKFLOWS = {
    "goal-decomposition": {
        "workflow": "GoalDecompositionWorkflow",
        "task_queue": "goal-decomposition",
        "description": "Decompose goals into actionable tasks with dependency DAG"
    },
    "memory-consolidation": {
        "workflow": "MemoryConsolidationWorkflow",
        "task_queue": "memory-consolidation",
        "description": "Sleep-like memory consolidation (patterns, compression)"
    },
    "research-to-code": {
        "workflow": "ResearchToCodeWorkflow",
        "task_queue": "research-to-code",
        "description": "Research papers → code implementation pipeline"
    },
    "self-improvement": {
        "workflow": "SelfImprovementFeedbackLoop",
        "task_queue": "self-improvement",
        "description": "Analyze experiments & update strategies"
    },
    "system-optimization": {
        "workflow": "SystemOptimizationWorkflow",
        "task_queue": "system-optimization",
        "description": "System performance optimization"
    },
    "curiosity-exploration": {
        "workflow": "CuriosityExplorationWorkflow",
        "task_queue": "curiosity-exploration",
        "description": "Autonomous knowledge discovery and goal generation"
    },
    "agi-cognitive-cycle": {
        "workflow": "AGICognitiveCycleWorkflow",
        "task_queue": "agi-cognitive-cycle",
        "description": "Full AGI 6-phase cycle: PERCEIVE → REASON → ACT → LEARN → REFLECT → IMPROVE"
    },
    "meta-learning": {
        "workflow": "MetaLearningConsolidationWorkflow",
        "task_queue": "meta-learning",
        "description": "Meta-learning consolidation - learn HOW to learn better"
    },
    "cluster-task-orchestration": {
        "workflow": "ClusterTaskOrchestrationWorkflow",
        "task_queue": "cluster-orchestration",
        "description": "Route tasks across cluster nodes optimally"
    },
    "autonomous-kaggle": {
        "workflow": "AutonomousKaggleWorkflow",
        "task_queue": "autonomous-kaggle",
        "description": "Autonomous Kaggle competition experiments"
    }
}


async def trigger_workflow(
    workflow_name: str,
    args: List[Any] = None,
    workflow_id: str = None,
    timeout_seconds: int = 300
) -> Dict[str, Any]:
    """
    Trigger a Temporal workflow

    Args:
        workflow_name: Key from WORKFLOWS dict or task_queue name
        args: Arguments to pass to workflow
        workflow_id: Optional custom workflow ID
        timeout_seconds: Workflow execution timeout

    Returns:
        Workflow result or status
    """
    try:
        from temporalio.client import Client

        # Connect to Temporal
        client = await Client.connect(
            os.environ.get("TEMPORAL_HOST", "localhost:7233")
        )

        # Get workflow config
        config = WORKFLOWS.get(workflow_name)
        if not config:
            return {
                "success": False,
                "error": f"Unknown workflow: {workflow_name}",
                "available": list(WORKFLOWS.keys())
            }

        # Generate workflow ID if not provided
        if not workflow_id:
            from datetime import datetime
            workflow_id = f"{workflow_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Start workflow
        logger.info(f"Triggering workflow: {config['workflow']}")
        logger.info(f"Task queue: {config['task_queue']}")
        logger.info(f"Args: {args}")

        handle = await client.start_workflow(
            config["workflow"],
            args=args or [],
            id=workflow_id,
            task_queue=config["task_queue"],
            execution_timeout=timedelta(seconds=timeout_seconds)
        )

        logger.info(f"Workflow started: {workflow_id}")

        # Wait for result (with timeout)
        try:
            result = await asyncio.wait_for(
                handle.result(),
                timeout=timeout_seconds
            )
            return {
                "success": True,
                "workflow_id": workflow_id,
                "result": result
            }
        except asyncio.TimeoutError:
            return {
                "success": True,
                "workflow_id": workflow_id,
                "status": "running",
                "message": f"Workflow started but still running after {timeout_seconds}s"
            }

    except ImportError:
        return {
            "success": False,
            "error": "temporalio not installed. Run: pip install temporalio"
        }
    except Exception as e:
        logger.error(f"Failed to trigger workflow: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def trigger_goal_decomposition(goal_description: str) -> Dict[str, Any]:
    """
    Convenience function to trigger goal decomposition workflow

    Args:
        goal_description: Description of the goal to decompose

    Returns:
        Decomposition result with goal_id and task_ids
    """
    return await trigger_workflow(
        "goal-decomposition",
        args=[goal_description],
        timeout_seconds=120
    )


async def list_workflows() -> Dict[str, Any]:
    """List all available workflows with descriptions"""
    return {
        "workflows": {
            name: {
                "task_queue": config["task_queue"],
                "description": config["description"]
            }
            for name, config in WORKFLOWS.items()
        }
    }


async def check_temporal_status() -> Dict[str, Any]:
    """Check if Temporal is running and accessible"""
    try:
        from temporalio.client import Client

        client = await Client.connect(
            os.environ.get("TEMPORAL_HOST", "localhost:7233")
        )

        # Try to list workflows (simple health check)
        count = 0
        async for _ in client.list_workflows(query=""):
            count += 1
            if count >= 5:  # Just check if we can list some
                break

        return {
            "status": "connected",
            "temporal_host": os.environ.get("TEMPORAL_HOST", "localhost:7233"),
            "workflows_accessible": True
        }

    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
            "temporal_host": os.environ.get("TEMPORAL_HOST", "localhost:7233")
        }


# CLI interface
async def main():
    parser = argparse.ArgumentParser(description="Temporal Bridge - Trigger workflows from CLI")

    parser.add_argument("--goal", type=str, help="Goal to decompose via GoalDecompositionWorkflow")
    parser.add_argument("--workflow", type=str, help="Specific workflow to trigger")
    parser.add_argument("--args", type=str, help="JSON array of arguments for workflow")
    parser.add_argument("--list", action="store_true", help="List available workflows")
    parser.add_argument("--status", action="store_true", help="Check Temporal status")
    parser.add_argument("--timeout", type=int, default=300, help="Workflow timeout in seconds")

    args = parser.parse_args()

    if args.list:
        result = await list_workflows()
        print(json.dumps(result, indent=2))

    elif args.status:
        result = await check_temporal_status()
        print(json.dumps(result, indent=2))

    elif args.goal:
        print(f"Triggering goal decomposition for: {args.goal}")
        result = await trigger_goal_decomposition(args.goal)
        print(json.dumps(result, indent=2))

    elif args.workflow:
        workflow_args = json.loads(args.args) if args.args else []
        print(f"Triggering workflow: {args.workflow}")
        result = await trigger_workflow(
            args.workflow,
            args=workflow_args,
            timeout_seconds=args.timeout
        )
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
