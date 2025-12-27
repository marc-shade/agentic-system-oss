#!/usr/bin/env python3
"""
Librarian Consolidation Workflow - Structured memory synthesis

Uses the Librarian prompt pattern (from vlt-cli) to create structured
knowledge synthesis that REPLACES instead of appends:

- Status: Current consolidation state
- Context: Top patterns with success rates
- Concepts: Learned abstractions
- Pivot Log: Validated and flagged patterns
- Next Steps: Actionable recommendations

Runs periodically to maintain a clear, structured view of system learnings.

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import sys
import os

# Add MCP path for SleetimeAgent
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def run_librarian_consolidation(
    agent_id: str = "phoenix",
    time_window_hours: int = 24
) -> dict:
    """
    Run Librarian-style consolidation using SleetimeAgent.

    This creates a structured synthesis that replaces the learnings block
    with fresh, up-to-date content.
    """
    try:
        from sleeptime_agent import SleetimeAgent

        agent = SleetimeAgent(agent_id=agent_id)
        result = agent.run_consolidation_cycle(time_window_hours=time_window_hours)

        # Get the updated block content for logging
        block = agent.block_manager.get_block(agent_id, 'learnings')
        block_preview = block.value[:200] if block else "No block"

        logger.info(f"Librarian consolidation complete: {result}")
        logger.info(f"Block preview: {block_preview}...")

        return {
            "success": result.get("success", False),
            "memories_processed": result.get("memories_processed", 0),
            "patterns_found": result.get("patterns_found", 0),
            "concepts_created": result.get("concepts_created", 0),
            "learnings_updated": result.get("learnings_updated", False),
            "duration_seconds": result.get("duration_seconds", 0),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Librarian consolidation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def get_learnings_block(agent_id: str = "phoenix") -> dict:
    """Get the current learnings block content"""
    try:
        from letta_memory_blocks import MemoryBlockManager

        bm = MemoryBlockManager()
        block = bm.get_block(agent_id, 'learnings')

        if block:
            return {
                "success": True,
                "content": block.value,
                "chars_used": len(block.value),
                "chars_limit": block.limit
            }
        else:
            return {
                "success": False,
                "error": "Block not found"
            }

    except Exception as e:
        logger.error(f"Failed to get learnings block: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@activity.defn
async def notify_consolidation_complete(result: dict) -> dict:
    """Send notification about consolidation results (optional)"""
    try:
        # Could integrate with voice-mode or arduino-surface for notifications
        patterns = result.get("patterns_found", 0)
        memories = result.get("memories_processed", 0)

        message = f"Librarian consolidated {memories} memories into {patterns} patterns"
        logger.info(f"Notification: {message}")

        return {"notified": True, "message": message}

    except Exception as e:
        logger.error(f"Notification failed: {e}")
        return {"notified": False, "error": str(e)}


@workflow.defn
class LibrarianConsolidationWorkflow:
    """
    Periodic Librarian-style memory consolidation workflow.

    Uses structured synthesis (Status/Context/Concepts/Pivot/Next)
    to maintain clear, actionable knowledge state.
    """

    @workflow.run
    async def run(
        self,
        agent_id: str = "phoenix",
        time_window_hours: int = 24
    ) -> dict:
        """
        Run Librarian consolidation.

        Args:
            agent_id: Agent to consolidate for (default: phoenix)
            time_window_hours: How far back to look for memories
        """
        workflow.logger.info(
            f"Starting Librarian consolidation for {agent_id} "
            f"(last {time_window_hours}h)"
        )

        results = {
            "start_time": workflow.now().isoformat(),
            "agent_id": agent_id,
            "time_window_hours": time_window_hours,
            "steps": {}
        }

        try:
            # Step 1: Run Librarian consolidation
            workflow.logger.info("Running Librarian consolidation...")
            consolidation_result = await workflow.execute_activity(
                run_librarian_consolidation,
                args=[agent_id, time_window_hours],
                start_to_close_timeout=timedelta(minutes=5)
            )
            results["steps"]["consolidation"] = consolidation_result

            # Step 2: Get updated block content
            workflow.logger.info("Retrieving updated learnings block...")
            block_result = await workflow.execute_activity(
                get_learnings_block,
                args=[agent_id],
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["block_retrieval"] = {
                "success": block_result.get("success", False),
                "chars_used": block_result.get("chars_used", 0),
                "chars_limit": block_result.get("chars_limit", 3000)
            }

            # Step 3: Notify (optional)
            if consolidation_result.get("success"):
                workflow.logger.info("Sending completion notification...")
                notify_result = await workflow.execute_activity(
                    notify_consolidation_complete,
                    args=[consolidation_result],
                    start_to_close_timeout=timedelta(minutes=1)
                )
                results["steps"]["notification"] = notify_result

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success" if consolidation_result.get("success") else "failed"
            results["summary"] = {
                "memories": consolidation_result.get("memories_processed", 0),
                "patterns": consolidation_result.get("patterns_found", 0),
                "concepts": consolidation_result.get("concepts_created", 0)
            }

            workflow.logger.info(f"Librarian consolidation complete: {results['summary']}")
            return results

        except Exception as e:
            workflow.logger.error(f"Librarian consolidation workflow failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def run_worker():
    """Run worker for Librarian consolidation workflow"""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="librarian-consolidation",
        workflows=[LibrarianConsolidationWorkflow],
        activities=[
            run_librarian_consolidation,
            get_learnings_block,
            notify_consolidation_complete
        ]
    )

    logger.info("Librarian Consolidation Worker started on task_queue: librarian-consolidation")
    await worker.run()


async def run_once():
    """Run workflow once for testing"""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        LibrarianConsolidationWorkflow.run,
        args=["phoenix", 720],  # 30 days for testing
        id=f"librarian-consolidation-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="librarian-consolidation"
    )

    logger.info(f"Workflow result: {result}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run workflow once for testing")
    args = parser.parse_args()

    if args.test:
        asyncio.run(run_once())
    else:
        asyncio.run(run_worker())
