#!/usr/bin/env python3
"""
Morning Briefing Workflow - The Hyperthink Move 1 Implementation

Runs daily at 6 AM to prepare Marc's morning briefing.
Replaces log diving with a 30-second digestible summary.

The briefing includes:
- What happened overnight (3 bullet points max)
- One insight the system learned
- One proposal awaiting approval
- System health score

Output channels:
- Arduino LCD: Short status message
- Voice Mode: Spoken summary
- Enhanced Memory: Stored for later reference

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import json
import sys
import os

# Add paths for local imports
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp')

# NOTE: httpx imported inside activities due to Temporal sandbox restrictions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ARDUINO_MCP_URL = "http://localhost:8200"
VOICE_MODE_URL = "http://localhost:8201"  # If available via HTTP


@activity.defn
async def gather_overnight_activity(hours: int = 12) -> Dict[str, Any]:
    """Gather activity from the past N hours"""
    try:
        # Get memory system stats
        from server import (
            get_memory_status,
            get_episodes,
            get_consolidation_stats,
            get_high_salience_memories
        )

        memory_status = await get_memory_status()

        # Get recent high-significance episodes
        recent_episodes = await get_episodes(
            min_significance=0.6,
            limit=20
        )

        # Get consolidation stats
        consolidation_stats = await get_consolidation_stats()

        # Get high-salience memories (important recent learnings)
        high_salience = await get_high_salience_memories(threshold=0.7, limit=10)

        return {
            "memory_status": memory_status,
            "recent_episodes": recent_episodes,
            "consolidation_stats": consolidation_stats,
            "high_salience_memories": high_salience,
            "gathered_at": datetime.now().isoformat(),
            "hours_covered": hours
        }
    except Exception as e:
        logger.error(f"Failed to gather overnight activity: {e}")
        return {"error": str(e), "gathered_at": datetime.now().isoformat()}


@activity.defn
async def gather_workflow_completions(hours: int = 12) -> Dict[str, Any]:
    """Check what Temporal workflows completed overnight"""
    try:
        client = await Client.connect("localhost:7233")

        # Query for completed workflows in the time window
        cutoff = datetime.now() - timedelta(hours=hours)

        completions = []
        failures = []

        # List recent workflow executions
        async for workflow in client.list_workflows(
            query=f"CloseTime > '{cutoff.isoformat()}'"
        ):
            info = {
                "workflow_id": workflow.id,
                "type": workflow.workflow_type,
                "status": str(workflow.status),
                "close_time": workflow.close_time.isoformat() if workflow.close_time else None
            }
            if "COMPLETED" in str(workflow.status):
                completions.append(info)
            elif "FAILED" in str(workflow.status):
                failures.append(info)

        return {
            "completions": completions[:10],  # Top 10
            "failures": failures[:5],  # Top 5 failures
            "total_completed": len(completions),
            "total_failed": len(failures)
        }
    except Exception as e:
        logger.error(f"Failed to gather workflow completions: {e}")
        return {"error": str(e), "completions": [], "failures": []}


@activity.defn
async def gather_system_health() -> Dict[str, Any]:
    """Gather overall system health metrics"""
    try:
        import psutil

        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/Volumes/SSDRAID0')

        # Check key services
        services_up = []
        services_down = []

        service_checks = [
            ("Temporal", "localhost", 7233),
            ("Qdrant", "localhost", 6333),
            ("Prometheus", "localhost", 9700),
        ]

        for name, host, port in service_checks:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=2.0
                )
                writer.close()
                await writer.wait_closed()
                services_up.append(name)
            except:
                services_down.append(name)

        # Calculate health score (0-10)
        health_score = 10.0
        if cpu_percent > 80:
            health_score -= 1
        if memory.percent > 85:
            health_score -= 1
        if disk.percent > 90:
            health_score -= 1
        health_score -= len(services_down) * 0.5
        health_score = max(0, min(10, health_score))

        return {
            "health_score": round(health_score, 1),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "services_up": services_up,
            "services_down": services_down,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to gather system health: {e}")
        return {"error": str(e), "health_score": 0}


@activity.defn
async def synthesize_briefing(
    overnight_activity: Dict[str, Any],
    workflow_completions: Dict[str, Any],
    system_health: Dict[str, Any]
) -> Dict[str, Any]:
    """Synthesize all data into a human-readable briefing"""
    try:
        # Extract key metrics
        episodes = overnight_activity.get("recent_episodes", [])
        consolidation = overnight_activity.get("consolidation_stats", {})
        high_salience = overnight_activity.get("high_salience_memories", [])

        completed_workflows = workflow_completions.get("total_completed", 0)
        failed_workflows = workflow_completions.get("total_failed", 0)

        health_score = system_health.get("health_score", 0)
        services_down = system_health.get("services_down", [])

        # Build the 3 overnight bullets
        bullets = []

        if completed_workflows > 0:
            bullets.append(f"{completed_workflows} workflows completed successfully")

        patterns_found = consolidation.get("totals", {}).get("patterns_promoted", 0)
        if patterns_found > 0:
            bullets.append(f"{patterns_found} patterns discovered and promoted to semantic memory")

        if len(high_salience) > 0:
            bullets.append(f"{len(high_salience)} high-importance memories captured")

        if failed_workflows > 0:
            bullets.append(f"⚠️ {failed_workflows} workflow(s) failed - review recommended")

        # Limit to 3 bullets
        bullets = bullets[:3]
        if not bullets:
            bullets = ["Quiet night - system maintained steady state"]

        # Extract one insight (most recent high-salience memory)
        insight = None
        if high_salience and isinstance(high_salience, list) and len(high_salience) > 0:
            top_memory = high_salience[0]
            if isinstance(top_memory, dict):
                insight = top_memory.get("name", "New pattern detected in system behavior")

        # Generate a proposal (placeholder - will be enhanced with agency ladder)
        proposal = None
        if services_down:
            proposal = f"Restart {', '.join(services_down)} services"
        elif health_score < 7:
            proposal = "Run system optimization workflow"

        # Build briefing
        briefing = {
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "time": datetime.now().strftime("%I:%M %p"),
            "overnight_summary": bullets,
            "insight": insight or "System operating within normal parameters",
            "proposal": proposal,
            "health_score": health_score,
            "issues_count": failed_workflows + len(services_down),
            "raw_data": {
                "overnight_activity": overnight_activity,
                "workflow_completions": workflow_completions,
                "system_health": system_health
            }
        }

        return briefing
    except Exception as e:
        logger.error(f"Failed to synthesize briefing: {e}")
        return {
            "error": str(e),
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "overnight_summary": ["Error generating briefing"],
            "health_score": 0
        }


@activity.defn
async def display_on_arduino(briefing: Dict[str, Any]) -> Dict[str, Any]:
    """Display brief status on Arduino LCD"""
    import httpx  # Import inside activity for Temporal sandbox
    try:
        async with httpx.AsyncClient() as client:
            # Clear display
            await client.post(f"{ARDUINO_MCP_URL}/surface_display_clear")

            # Show health score and status
            health = briefing.get("health_score", 0)
            issues = briefing.get("issues_count", 0)

            if issues == 0:
                status_line = f"Health: {health}/10 OK"
            else:
                status_line = f"Health: {health}/10 !{issues}"

            # Line 1: Health status
            await client.post(f"{ARDUINO_MCP_URL}/surface_display", json={
                "row": 0,
                "col": 0,
                "text": status_line[:16]
            })

            # Line 2: Date/time
            time_str = datetime.now().strftime("%m/%d %I:%M%p")
            await client.post(f"{ARDUINO_MCP_URL}/surface_display", json={
                "row": 1,
                "col": 0,
                "text": time_str[:16]
            })

            # Set LED based on health
            if health >= 8:
                color = {"r": 0, "g": 255, "b": 100}  # Green
            elif health >= 5:
                color = {"r": 255, "g": 200, "b": 0}  # Yellow
            else:
                color = {"r": 255, "g": 50, "b": 0}  # Red

            await client.post(f"{ARDUINO_MCP_URL}/surface_led_set", json={
                "tier": 0,
                **color
            })

            # Success beep
            await client.post(f"{ARDUINO_MCP_URL}/surface_beep", json={
                "frequency_hz": 1000,
                "duration_ms": 100
            })

            return {"success": True, "displayed": status_line}
    except Exception as e:
        logger.warning(f"Arduino display failed (may not be connected): {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def speak_briefing(briefing: Dict[str, Any]) -> Dict[str, Any]:
    """Speak the briefing via voice mode"""
    import httpx  # Import inside activity for Temporal sandbox
    try:
        # Build spoken message
        health = briefing.get("health_score", 0)
        bullets = briefing.get("overnight_summary", [])
        insight = briefing.get("insight")
        proposal = briefing.get("proposal")

        # Construct speech
        speech_parts = [f"Good morning. System health is {health} out of 10."]

        if bullets:
            speech_parts.append("Overnight summary:")
            for bullet in bullets:
                speech_parts.append(bullet)

        if insight:
            speech_parts.append(f"Key insight: {insight}")

        if proposal:
            speech_parts.append(f"Proposal awaiting review: {proposal}")

        message = " ".join(speech_parts)

        # Use voice mode MCP via HTTP or direct import
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{VOICE_MODE_URL}/converse",
                    json={
                        "message": message,
                        "wait_for_response": False
                    }
                )
                return {"success": True, "spoken": message}
        except:
            # Voice mode may not be available via HTTP, log the message
            logger.info(f"Voice briefing (not spoken): {message}")
            return {"success": False, "message": message, "note": "Voice mode not available via HTTP"}

    except Exception as e:
        logger.error(f"Failed to speak briefing: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def store_briefing(briefing: Dict[str, Any]) -> Dict[str, Any]:
    """Store briefing in enhanced memory for future reference"""
    try:
        from server import create_entities, add_episode

        # Store as an episode
        episode_result = await add_episode(
            event_type="morning_briefing",
            episode_data={
                "date": briefing.get("date"),
                "summary": briefing.get("overnight_summary"),
                "insight": briefing.get("insight"),
                "proposal": briefing.get("proposal"),
                "health_score": briefing.get("health_score")
            },
            significance_score=0.7,
            tags=["briefing", "daily", "morning"]
        )

        # Also create a searchable entity
        entity_result = await create_entities([{
            "name": f"morning-briefing-{datetime.now().strftime('%Y-%m-%d')}",
            "entityType": "morning_briefing",
            "observations": [
                f"Health score: {briefing.get('health_score')}/10",
                f"Summary: {'; '.join(briefing.get('overnight_summary', []))}",
                f"Insight: {briefing.get('insight', 'None')}",
                f"Proposal: {briefing.get('proposal', 'None')}"
            ]
        }])

        return {
            "success": True,
            "episode_id": episode_result.get("episode_id"),
            "entity_id": entity_result.get("results", [{}])[0].get("id")
        }
    except Exception as e:
        logger.error(f"Failed to store briefing: {e}")
        return {"success": False, "error": str(e)}


@workflow.defn
class MorningBriefingWorkflow:
    """
    Daily morning briefing workflow.

    Gathers overnight activity, synthesizes into digestible format,
    and presents via multiple channels (Arduino, Voice, Memory).
    """

    @workflow.run
    async def run(self, hours_to_cover: int = 12) -> Dict[str, Any]:
        """Execute the morning briefing workflow"""

        workflow.logger.info(f"Starting morning briefing for past {hours_to_cover} hours")

        # Phase 1: Gather data in parallel
        overnight_activity, workflow_completions, system_health = await asyncio.gather(
            workflow.execute_activity(
                gather_overnight_activity,
                args=[hours_to_cover],
                start_to_close_timeout=timedelta(minutes=2)
            ),
            workflow.execute_activity(
                gather_workflow_completions,
                args=[hours_to_cover],
                start_to_close_timeout=timedelta(minutes=2)
            ),
            workflow.execute_activity(
                gather_system_health,
                start_to_close_timeout=timedelta(minutes=1)
            )
        )

        # Phase 2: Synthesize briefing
        briefing = await workflow.execute_activity(
            synthesize_briefing,
            args=[overnight_activity, workflow_completions, system_health],
            start_to_close_timeout=timedelta(minutes=1)
        )

        # Phase 3: Present via all channels (parallel)
        arduino_result, voice_result, storage_result = await asyncio.gather(
            workflow.execute_activity(
                display_on_arduino,
                args=[briefing],
                start_to_close_timeout=timedelta(seconds=30)
            ),
            workflow.execute_activity(
                speak_briefing,
                args=[briefing],
                start_to_close_timeout=timedelta(minutes=2)
            ),
            workflow.execute_activity(
                store_briefing,
                args=[briefing],
                start_to_close_timeout=timedelta(seconds=30)
            )
        )

        workflow.logger.info("Morning briefing completed")

        return {
            "briefing": briefing,
            "delivery": {
                "arduino": arduino_result,
                "voice": voice_result,
                "storage": storage_result
            },
            "completed_at": workflow.now().isoformat()
        }


async def run_worker():
    """Run the morning briefing worker"""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="morning-briefing",
        workflows=[MorningBriefingWorkflow],
        activities=[
            gather_overnight_activity,
            gather_workflow_completions,
            gather_system_health,
            synthesize_briefing,
            display_on_arduino,
            speak_briefing,
            store_briefing
        ]
    )

    logger.info("Morning Briefing Worker started on task queue: morning-briefing")
    await worker.run()


async def trigger_briefing_now():
    """Manually trigger a morning briefing (for testing)"""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        MorningBriefingWorkflow.run,
        args=[12],  # Last 12 hours
        id=f"morning-briefing-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="morning-briefing"
    )

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Morning Briefing Workflow")
    parser.add_argument("--worker", action="store_true", help="Run as worker")
    parser.add_argument("--trigger", action="store_true", help="Trigger briefing now")
    parser.add_argument("--hours", type=int, default=12, help="Hours to cover")

    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker())
    elif args.trigger:
        asyncio.run(trigger_briefing_now())
    else:
        parser.print_help()
