#!/usr/bin/env python3
"""
Start Continuous Workflows
Starts the long-running 24/7 autonomous workflows

Workflows:
- Cluster Coordination: Multi-node task distribution
- Task Queue Processor: Persistent task execution
- Arduino Status Rotation: Physical monitoring display

STATUS: Production Ready
"""

import asyncio
import logging
from temporalio.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start_workflows():
    """Start all continuous workflows"""
    client = await Client.connect("localhost:7233")

    workflows = [
        {
            "id": "cluster-coordination-001",
            "workflow": "ClusterCoordinationWorkflow",
            "task_queue": "cluster-coordination",
            "description": "Multi-node cluster coordination and task distribution"
        },
        {
            "id": "task-queue-processor-001",
            "workflow": "TaskQueueProcessorWorkflow",
            "task_queue": "task-queue-processor",
            "description": "Persistent task queue processing from Agent Runtime"
        },
        {
            "id": "arduino-status-rotation-001",
            "workflow": "ArduinoStatusRotationWorkflow",
            "task_queue": "arduino-status-rotation",
            "description": "Physical monitoring display on Arduino LCD"
        }
    ]

    logger.info("="*60)
    logger.info("Starting continuous 24/7 workflows...")
    logger.info("="*60)

    for wf in workflows:
        try:
            # Check if workflow is already running
            try:
                handle = client.get_workflow_handle(wf["id"])
                result = await handle.describe()

                if result.status.name == "RUNNING":
                    logger.info(f"✓ Already running: {wf['id']}")
                    logger.info(f"  Description: {wf['description']}")
                    continue
            except Exception:
                pass  # Workflow doesn't exist, will create it

            # Start new workflow execution
            await client.start_workflow(
                wf["workflow"],
                id=wf["id"],
                task_queue=wf["task_queue"]
            )

            logger.info(f"✓ Started: {wf['id']}")
            logger.info(f"  Description: {wf['description']}")
            logger.info(f"  Task Queue: {wf['task_queue']}")

        except Exception as e:
            logger.error(f"✗ Failed to start {wf['id']}: {e}")

    logger.info("\n" + "="*60)
    logger.info("Continuous workflows started!")
    logger.info("="*60)
    logger.info("\nThese workflows will run 24/7 until manually stopped.")
    logger.info("Monitor via Temporal UI: http://localhost:8233")


async def stop_workflows():
    """Stop all continuous workflows"""
    client = await Client.connect("localhost:7233")

    workflow_ids = [
        "cluster-coordination-001",
        "task-queue-processor-001",
        "arduino-status-rotation-001"
    ]

    logger.info("="*60)
    logger.info("Stopping continuous workflows...")
    logger.info("="*60)

    for wf_id in workflow_ids:
        try:
            handle = client.get_workflow_handle(wf_id)
            await handle.cancel()
            logger.info(f"✓ Stopped: {wf_id}")
        except Exception as e:
            logger.error(f"✗ Failed to stop {wf_id}: {e}")

    logger.info("\n" + "="*60)
    logger.info("Workflows stopped!")
    logger.info("="*60)


async def status_workflows():
    """Check status of all continuous workflows"""
    client = await Client.connect("localhost:7233")

    workflow_ids = [
        "cluster-coordination-001",
        "task-queue-processor-001",
        "arduino-status-rotation-001"
    ]

    logger.info("="*60)
    logger.info("Continuous Workflow Status")
    logger.info("="*60)

    for wf_id in workflow_ids:
        try:
            handle = client.get_workflow_handle(wf_id)
            result = await handle.describe()

            logger.info(f"\n{wf_id}:")
            logger.info(f"  Status: {result.status.name}")
            logger.info(f"  Type: {result.workflow_type}")
            logger.info(f"  Start Time: {result.start_time}")
            logger.info(f"  Task Queue: {result.task_queue}")

        except Exception as e:
            logger.info(f"\n{wf_id}: NOT RUNNING")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "start":
            asyncio.run(start_workflows())
        elif command == "stop":
            asyncio.run(stop_workflows())
        elif command == "status":
            asyncio.run(status_workflows())
        else:
            print(f"Unknown command: {command}")
            print("Usage: python3 start_continuous_workflows.py [start|stop|status]")
    else:
        # Default: start workflows
        asyncio.run(start_workflows())
