#!/usr/bin/env python3
"""
SysAdmin Worker - Runs Watchdog and Auto-Recovery workflows

This worker runs persistently in the background, managing:
- Service health monitoring (every 60 seconds)
- Auto-recovery with exponential backoff
- Arduino LED status updates
- Development mode detection

Start: python sysadmin_worker.py
Stop: Ctrl+C or signal the workflows

STATUS: Production Ready
"""

import asyncio
import logging
import sys
import signal
from datetime import timedelta

from temporalio.client import Client
from temporalio.worker import Worker

# Add workflows path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/workflows/temporal')

from sysadmin_watchdog_workflow import (
    SysAdminWatchdogWorkflow,
    watchdog_activities
)

from sysadmin_auto_recovery_workflow import (
    SysAdminAutoRecoveryWorkflow,
    recovery_activities
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("sysadmin-worker")

TEMPORAL_ADDRESS = "localhost:7233"
TASK_QUEUE = "sysadmin-queue"

# Workflow IDs (fixed for singleton behavior)
WATCHDOG_WORKFLOW_ID = "sysadmin-watchdog-persistent"
RECOVERY_WORKFLOW_ID = "sysadmin-recovery-persistent"


async def start_persistent_workflows(client: Client):
    """Start or resume the persistent workflows"""

    # Start Watchdog (if not already running)
    try:
        handle = client.get_workflow_handle(WATCHDOG_WORKFLOW_ID)
        # Check if it's running
        desc = await handle.describe()
        if desc.status.name == "RUNNING":
            logger.info("Watchdog workflow already running")
        else:
            raise Exception("Not running")
    except Exception:
        # Start new watchdog
        logger.info("Starting watchdog workflow...")
        await client.start_workflow(
            SysAdminWatchdogWorkflow.run,
            args=[60],  # Check every 60 seconds
            id=WATCHDOG_WORKFLOW_ID,
            task_queue=TASK_QUEUE,
        )
        logger.info("Watchdog workflow started")

    # Start Auto-Recovery (if not already running)
    try:
        handle = client.get_workflow_handle(RECOVERY_WORKFLOW_ID)
        desc = await handle.describe()
        if desc.status.name == "RUNNING":
            logger.info("Auto-recovery workflow already running")
        else:
            raise Exception("Not running")
    except Exception:
        logger.info("Starting auto-recovery workflow...")
        await client.start_workflow(
            SysAdminAutoRecoveryWorkflow.run,
            args=[15],  # Poll every 15 seconds
            id=RECOVERY_WORKFLOW_ID,
            task_queue=TASK_QUEUE,
        )
        logger.info("Auto-recovery workflow started")


async def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("SysAdmin Worker Starting")
    logger.info("=" * 50)

    # Connect to Temporal
    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info(f"Connected to Temporal at {TEMPORAL_ADDRESS}")

    # Combine all activities
    all_activities = watchdog_activities + recovery_activities

    # Create worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SysAdminWatchdogWorkflow, SysAdminAutoRecoveryWorkflow],
        activities=all_activities,
    )

    # Start persistent workflows
    await start_persistent_workflows(client)

    # Handle shutdown gracefully
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Run worker
    logger.info(f"Worker listening on queue: {TASK_QUEUE}")
    logger.info("Monitoring services in background...")
    logger.info("-" * 50)

    async with worker:
        await shutdown_event.wait()

    logger.info("SysAdmin Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
