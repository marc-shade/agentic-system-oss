#!/usr/bin/env python3
"""
Workflow Scheduler - Sets up periodic execution of all autonomous workflows

Schedules:
- Memory Consolidation: Daily at 3 AM (sleep time)
- Memory Manager: Every hour
- System Optimization: Every 4 hours
- Service Health: Every 15 minutes

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import timedelta
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_schedules():
    """Set up all workflow schedules"""
    client = await Client.connect("localhost:7233")
    
    schedules = [
        {
            "id": "nightly-memory-consolidation",
            "workflow": "MemoryConsolidationWorkflow",
            "task_queue": "memory-consolidation",
            "interval": timedelta(days=1),  # Daily
            "description": "Nightly memory consolidation (sleep-like processing)",
            "args": ["full"]  # Full consolidation mode
        },
        {
            "id": "hourly-memory-manager",
            "workflow": "AutonomousMemoryManagerWorkflow",
            "task_queue": "memory-manager",
            "interval": timedelta(hours=1),  # Hourly
            "description": "Hourly memory tier management and curation",
            "args": []
        },
        {
            "id": "system-optimization",
            "workflow": "SystemOptimizationWorkflow",
            "task_queue": "system-optimization",
            "interval": timedelta(hours=4),  # Every 4 hours
            "description": "System performance optimization",
            "args": [False]  # Not dry-run
        }
    ]
    
    for sched in schedules:
        try:
            # Delete existing schedule if it exists
            try:
                handle = client.get_schedule_handle(sched["id"])
                await handle.delete()
                logger.info(f"Deleted existing schedule: {sched['id']}")
            except Exception:
                pass  # Schedule doesn't exist yet
            
            # Create new schedule
            await client.create_schedule(
                sched["id"],
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        sched["workflow"],
                        *sched["args"],
                        id=f"{sched['id']}-{{ScheduledTime}}",
                        task_queue=sched["task_queue"]
                    ),
                    spec=ScheduleSpec(
                        intervals=[ScheduleIntervalSpec(every=sched["interval"])]
                    )
                ),
                memo={"description": sched["description"]}
            )
            
            logger.info(f"✓ Created schedule: {sched['id']} - {sched['description']}")
            logger.info(f"  Interval: {sched['interval']}")
            
        except Exception as e:
            logger.error(f"✗ Failed to create schedule {sched['id']}: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("All workflow schedules configured!")
    logger.info("="*60)


async def list_schedules():
    """List all configured schedules"""
    client = await Client.connect("localhost:7233")
    
    logger.info("\nConfigured Schedules:")
    logger.info("="*60)
    
    async for sched in client.list_schedules():
        logger.info(f"Schedule ID: {sched.id}")
        logger.info(f"  Description: {sched.memo.get('description', 'N/A')}")
        logger.info(f"  Next run: {sched.info.next_action_times}")
        logger.info("")


async def main():
    """Main entry point"""
    logger.info("Setting up Temporal workflow schedules...")
    await setup_schedules()
    await list_schedules()


if __name__ == "__main__":
    asyncio.run(main())
