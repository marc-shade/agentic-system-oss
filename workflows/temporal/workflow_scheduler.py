#!/usr/bin/env python3
"""
Workflow Scheduler - Sets up periodic execution of all autonomous workflows

Schedules:
- Morning Briefing: Daily at 6 AM (Hyperthink Move 1)
- Memory Consolidation: Daily at 3 AM (sleep time)
- Memory Manager: Every hour
- System Optimization: Every 4 hours
- Model Discovery: Daily (track LLM model versions)
- Visual Monitoring: Every 30 minutes
- Visual Consolidation: Daily (nightly)
- Cross-Modal Integration: Every 2 hours
- Librarian Consolidation: Every 6 hours (structured synthesis)

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
            "id": "morning-briefing",
            "workflow": "MorningBriefingWorkflow",
            "task_queue": "morning-briefing",
            "interval": timedelta(days=1),  # Daily at 6 AM
            "description": "Daily morning briefing - replaces log diving (Hyperthink Move 1)",
            "args": [12]  # Cover last 12 hours
        },
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
        },
        {
            "id": "daily-model-discovery",
            "workflow": "ModelDiscoveryWorkflow",
            "task_queue": "model-discovery",
            "interval": timedelta(days=1),  # Daily
            "description": "Discover current LLM model versions from CLI providers",
            "args": ["quick"]  # Quick mode (just CLI versions, no token usage)
        },
        {
            "id": "visual-monitoring",
            "workflow": "VisualMonitoringWorkflow",
            "task_queue": "visual-perception",
            "interval": timedelta(minutes=30),  # Every 30 minutes
            "description": "Periodic visual environment monitoring with multi-provider analysis",
            "args": [30]  # 30 minute interval
        },
        {
            "id": "nightly-visual-consolidation",
            "workflow": "VisualMemoryConsolidationWorkflow",
            "task_queue": "visual-memory-consolidation",
            "interval": timedelta(days=1),  # Daily (runs at night)
            "description": "Nightly visual memory consolidation, pattern extraction, and learning",
            "args": ["full"]  # Full consolidation mode
        },
        {
            "id": "cross-modal-integration",
            "workflow": "CrossModalIntegrationWorkflow",
            "task_queue": "cross-modal",
            "interval": timedelta(hours=2),  # Every 2 hours
            "description": "Cross-modal correlation discovery, pattern extraction, and unified context building",
            "args": ["full"]  # Full mode (hours passed separately in workflow)
        },
        {
            "id": "librarian-consolidation",
            "workflow": "LibrarianConsolidationWorkflow",
            "task_queue": "librarian-consolidation",
            "interval": timedelta(hours=6),  # Every 6 hours
            "description": "Librarian-style memory consolidation (structured synthesis replacing learnings block)",
            "args": []  # Uses defaults: agent_id="phoenix", time_window_hours=24
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

    # Get schedule handles directly by ID (more reliable)
    schedule_ids = [
        "morning-briefing",
        "nightly-memory-consolidation",
        "hourly-memory-manager",
        "system-optimization",
        "daily-model-discovery",
        "visual-monitoring",
        "nightly-visual-consolidation",
        "cross-modal-integration",
        "librarian-consolidation"
    ]

    for sched_id in schedule_ids:
        try:
            handle = client.get_schedule_handle(sched_id)
            desc = await handle.describe()
            logger.info(f"Schedule ID: {sched_id}")
            if desc.info and desc.info.next_action_times:
                logger.info(f"  Next run: {desc.info.next_action_times[0]}")
            logger.info("")
        except Exception as e:
            logger.info(f"Schedule ID: {sched_id} - Not found or error: {e}")


async def main():
    """Main entry point"""
    logger.info("Setting up Temporal workflow schedules...")
    await setup_schedules()
    await list_schedules()


if __name__ == "__main__":
    asyncio.run(main())
