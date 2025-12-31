#!/usr/bin/env python3
"""
Cross-Modal Integration Workflow - Temporal Workflow for Unified AGI Memory

Provides scheduled cross-modal memory processing:
- Correlation discovery between modalities
- Cross-modal pattern extraction
- Unified context building
- Memory coherence maintenance

STATUS: Production Ready
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def discover_correlations(hours: int = 6) -> Dict[str, Any]:
    """Activity: Discover cross-modal correlations in recent memories."""
    from cross_modal_integration import CrossModalMemoryManager

    try:
        manager = CrossModalMemoryManager()

        # Get recent memories from each modality
        code_memories = manager.code_tracker.get_recent(hours=hours, limit=200)
        text_memories = manager.text_tracker.get_recent(hours=hours, limit=200)

        visual_memories = []
        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            visual_memories = vis_manager.memory_store.get_recent(hours=hours, limit=200)
        except ImportError:
            pass

        correlations_found = 0

        # Find temporal correlations between code and visual
        for code_mem in code_memories:
            try:
                code_time = datetime.fromisoformat(code_mem.timestamp.replace("Z", "+00:00"))

                for vis_mem in visual_memories:
                    try:
                        vis_time = datetime.fromisoformat(vis_mem.timestamp.replace("Z", "+00:00"))
                        delta = abs((code_time - vis_time).total_seconds())

                        # Within 5 minutes = correlation
                        if delta <= 300:
                            manager._store_correlation({
                                "memory_id_1": code_mem.id,
                                "modality_1": "code",
                                "memory_id_2": vis_mem.id,
                                "modality_2": "visual",
                                "time_delta_seconds": delta,
                                "correlation_strength": 1.0 - (delta / 300),
                                "context_type": "temporal"
                            })
                            correlations_found += 1
                    except Exception:
                        continue
            except Exception:
                continue

        # Find correlations between text and code
        for text_mem in text_memories:
            try:
                text_time = datetime.fromisoformat(text_mem.timestamp.replace("Z", "+00:00"))

                for code_mem in code_memories:
                    try:
                        code_time = datetime.fromisoformat(code_mem.timestamp.replace("Z", "+00:00"))
                        delta = abs((text_time - code_time).total_seconds())

                        if delta <= 300:
                            manager._store_correlation({
                                "memory_id_1": text_mem.id,
                                "modality_1": "text",
                                "memory_id_2": code_mem.id,
                                "modality_2": "code",
                                "time_delta_seconds": delta,
                                "correlation_strength": 1.0 - (delta / 300),
                                "context_type": "temporal"
                            })
                            correlations_found += 1
                    except Exception:
                        continue
            except Exception:
                continue

        return {
            "success": True,
            "hours_analyzed": hours,
            "memories_analyzed": {
                "code": len(code_memories),
                "text": len(text_memories),
                "visual": len(visual_memories)
            },
            "correlations_found": correlations_found,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Correlation discovery failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def extract_cross_modal_patterns(hours: int = 24) -> Dict[str, Any]:
    """Activity: Extract patterns that span modalities."""
    from cross_modal_integration import CrossModalMemoryManager

    try:
        manager = CrossModalMemoryManager()
        patterns = []

        # Get memories
        code_memories = manager.code_tracker.get_recent(hours=hours, limit=500)
        text_memories = manager.text_tracker.get_recent(hours=hours, limit=500)

        # Pattern: Code changes followed by text notes
        code_followed_by_text = 0
        for code_mem in code_memories:
            code_time = datetime.fromisoformat(code_mem.timestamp.replace("Z", "+00:00"))

            for text_mem in text_memories:
                text_time = datetime.fromisoformat(text_mem.timestamp.replace("Z", "+00:00"))

                # Text came after code within 10 minutes
                delta = (text_time - code_time).total_seconds()
                if 0 < delta < 600:
                    code_followed_by_text += 1

        if code_followed_by_text > 5:
            patterns.append({
                "type": "workflow_pattern",
                "name": "code_then_document",
                "occurrences": code_followed_by_text,
                "insight": "User often documents after coding"
            })

        # Pattern: Concentrated coding periods
        if code_memories:
            coding_hours = {}
            for mem in code_memories:
                try:
                    hour = datetime.fromisoformat(mem.timestamp.replace("Z", "+00:00")).hour
                    coding_hours[hour] = coding_hours.get(hour, 0) + 1
                except Exception:
                    continue

            if coding_hours:
                peak_hour = max(coding_hours, key=coding_hours.get)
                if coding_hours[peak_hour] > 10:
                    patterns.append({
                        "type": "temporal_pattern",
                        "name": "peak_coding_hour",
                        "hour": peak_hour,
                        "activity_count": coding_hours[peak_hour],
                        "insight": f"Most coding activity around {peak_hour}:00"
                    })

        # Pattern: File focus areas
        file_counts = {}
        for mem in code_memories:
            file_path = mem.content.get("file_path", "")
            if file_path:
                # Get directory
                parts = file_path.split("/")
                if len(parts) > 2:
                    area = "/".join(parts[-3:-1])
                    file_counts[area] = file_counts.get(area, 0) + 1

        focus_areas = [(area, count) for area, count in file_counts.items() if count > 5]
        focus_areas.sort(key=lambda x: x[1], reverse=True)

        for area, count in focus_areas[:3]:
            patterns.append({
                "type": "focus_pattern",
                "name": "active_area",
                "area": area,
                "change_count": count,
                "insight": f"High activity in {area}"
            })

        return {
            "success": True,
            "hours_analyzed": hours,
            "patterns_discovered": len(patterns),
            "patterns": patterns,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Pattern extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def build_unified_context(hours: int = 6) -> Dict[str, Any]:
    """Activity: Build unified context across modalities."""
    from cross_modal_integration import CrossModalMemoryManager

    try:
        manager = CrossModalMemoryManager()
        summary = manager.get_unified_summary(hours)

        # Build context narrative
        context = {
            "time_range_hours": hours,
            "activity_summary": summary,
            "context_narrative": []
        }

        # Get recent code activity
        code_memories = manager.code_tracker.get_recent(hours=hours, limit=10)
        if code_memories:
            files_modified = list(set(
                m.content.get("file_path", "unknown") for m in code_memories
            ))
            context["context_narrative"].append({
                "modality": "code",
                "summary": f"Modified {len(files_modified)} files",
                "details": files_modified[:5]
            })

        # Get recent text activity
        text_memories = manager.text_tracker.get_recent(hours=hours, limit=10)
        if text_memories:
            text_types = {}
            for m in text_memories:
                t = m.content.get("text_type", "note")
                text_types[t] = text_types.get(t, 0) + 1

            context["context_narrative"].append({
                "modality": "text",
                "summary": f"Created {len(text_memories)} text memories",
                "details": text_types
            })

        # Get visual summary
        try:
            from visual_memory_integration import VisualMemoryManager
            vis_manager = VisualMemoryManager()
            visual_memories = vis_manager.memory_store.get_recent(hours=hours, limit=10)

            if visual_memories:
                scene_types = {}
                for vm in visual_memories:
                    st = vm.scene_type
                    scene_types[st] = scene_types.get(st, 0) + 1

                context["context_narrative"].append({
                    "modality": "visual",
                    "summary": f"Captured {len(visual_memories)} visual observations",
                    "details": scene_types
                })
        except ImportError:
            pass

        return {
            "success": True,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Context building failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def maintain_memory_coherence() -> Dict[str, Any]:
    """Activity: Maintain coherence across memory modalities."""
    from cross_modal_integration import CrossModalMemoryManager

    try:
        manager = CrossModalMemoryManager()

        # Check for orphaned correlations (references to deleted memories)
        import sqlite3

        db_path = os.path.join(manager.storage_path, "cross_modal_index.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get correlation count before cleanup
        cursor.execute('SELECT COUNT(*) FROM temporal_correlations')
        before_count = cursor.fetchone()[0]

        # Clean up old correlations (older than 7 days)
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute('DELETE FROM temporal_correlations WHERE created_at < ?', (cutoff,))
        deleted = cursor.rowcount

        conn.commit()

        # Get correlation count after cleanup
        cursor.execute('SELECT COUNT(*) FROM temporal_correlations')
        after_count = cursor.fetchone()[0]

        conn.close()

        return {
            "success": True,
            "correlations_before": before_count,
            "correlations_after": after_count,
            "correlations_cleaned": deleted,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Coherence maintenance failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def store_cross_modal_summary(summary: Dict) -> Dict[str, Any]:
    """Activity: Store cross-modal processing summary."""
    try:
        summary_path = "/Volumes/SSDRAID0/agentic-system/databases/cross_modal/processing_summaries.jsonl"
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)

        with open(summary_path, 'a') as f:
            f.write(json.dumps(summary) + '\n')

        return {
            "success": True,
            "stored_at": summary_path,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Summary storage failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def sync_to_enhanced_memory(hours: int = 6) -> Dict[str, Any]:
    """Activity: Sync cross-modal memories to enhanced-memory-mcp."""
    from cross_modal_enhanced_memory_bridge import EnhancedMemoryBridge

    try:
        bridge = EnhancedMemoryBridge()
        results = await bridge.full_sync(hours)

        return {
            "success": True,
            "synced": {
                "visual": results.get("visual", 0),
                "text": results.get("text", 0),
                "code": results.get("code", 0),
                "correlations": results.get("correlations", 0)
            },
            "errors": results.get("errors", 0),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Enhanced-memory sync failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@workflow.defn
class CrossModalIntegrationWorkflow:
    """
    Cross-Modal Integration Workflow.

    Processes memories across modalities to build unified AGI context:
    1. Discover temporal correlations between modalities
    2. Extract cross-modal patterns
    3. Build unified context
    4. Maintain memory coherence
    5. Store processing summary
    """

    @workflow.run
    async def run(self, mode: str = "full", hours: int = 6) -> Dict[str, Any]:
        """
        Run cross-modal integration.

        Args:
            mode: "full" (all steps) or "quick" (correlations only)
            hours: Time range to process
        """
        workflow.logger.info(f"Starting cross-modal integration - mode: {mode}, hours: {hours}")

        results = {
            "start_time": workflow.now().isoformat(),
            "mode": mode,
            "hours": hours,
            "steps": {}
        }

        try:
            # Step 1: Discover correlations
            workflow.logger.info("Discovering cross-modal correlations...")
            correlations = await workflow.execute_activity(
                discover_correlations,
                args=[hours],
                start_to_close_timeout=timedelta(minutes=5)
            )
            results["steps"]["correlations"] = correlations

            if mode == "full":
                # Step 2: Extract patterns
                workflow.logger.info("Extracting cross-modal patterns...")
                patterns = await workflow.execute_activity(
                    extract_cross_modal_patterns,
                    args=[hours],
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["patterns"] = patterns

                # Step 3: Build unified context
                workflow.logger.info("Building unified context...")
                context = await workflow.execute_activity(
                    build_unified_context,
                    args=[hours],
                    start_to_close_timeout=timedelta(minutes=3)
                )
                results["steps"]["context"] = context

                # Step 4: Maintain coherence
                workflow.logger.info("Maintaining memory coherence...")
                coherence = await workflow.execute_activity(
                    maintain_memory_coherence,
                    start_to_close_timeout=timedelta(minutes=2)
                )
                results["steps"]["coherence"] = coherence

                # Step 5: Sync to enhanced-memory
                workflow.logger.info("Syncing to enhanced-memory...")
                sync_result = await workflow.execute_activity(
                    sync_to_enhanced_memory,
                    args=[hours],
                    start_to_close_timeout=timedelta(minutes=5)
                )
                results["steps"]["enhanced_memory_sync"] = sync_result

            # Step 6: Store summary
            workflow.logger.info("Storing processing summary...")
            await workflow.execute_activity(
                store_cross_modal_summary,
                args=[results],
                start_to_close_timeout=timedelta(seconds=30)
            )

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success"

            workflow.logger.info(f"Cross-modal integration complete: {results['status']}")
            return results

        except Exception as e:
            workflow.logger.error(f"Cross-modal integration failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            results["end_time"] = workflow.now().isoformat()
            return results


@workflow.defn
class CrossModalContextWorkflow:
    """
    On-demand cross-modal context retrieval workflow.

    Called when the AGI needs comprehensive context about a topic or time period.
    """

    @workflow.run
    async def run(self, query: str = "", timestamp: str = "", window_minutes: int = 10) -> Dict[str, Any]:
        """
        Get cross-modal context.

        Args:
            query: Search query (if searching by content)
            timestamp: ISO timestamp (if searching by time)
            window_minutes: Time window for temporal context
        """
        workflow.logger.info(f"Getting cross-modal context - query: {query}, timestamp: {timestamp}")

        results = {
            "start_time": workflow.now().isoformat(),
            "query": query,
            "timestamp": timestamp
        }

        try:
            # Build context
            context = await workflow.execute_activity(
                build_unified_context,
                args=[1],  # Last hour for immediate context
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["context"] = context

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success"
            return results

        except Exception as e:
            workflow.logger.error(f"Context retrieval failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def run_worker():
    """Run Temporal worker for cross-modal workflows."""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="cross-modal",
        workflows=[CrossModalIntegrationWorkflow, CrossModalContextWorkflow],
        activities=[
            discover_correlations,
            extract_cross_modal_patterns,
            build_unified_context,
            maintain_memory_coherence,
            store_cross_modal_summary,
            sync_to_enhanced_memory
        ]
    )

    logger.info("Cross-Modal Worker started on task_queue: cross-modal")
    await worker.run()


async def run_once(mode: str = "full", hours: int = 6):
    """Run the workflow once (for testing)."""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        CrossModalIntegrationWorkflow.run,
        args=[mode, hours],
        id=f"cross-modal-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="cross-modal"
    )

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-Modal Integration Workflow")
    parser.add_argument("--worker", action="store_true", help="Run as worker")
    parser.add_argument("--once", action="store_true", help="Run workflow once")
    parser.add_argument("--mode", default="full", choices=["full", "quick"],
                        help="Workflow mode")
    parser.add_argument("--hours", type=int, default=6, help="Hours to process")

    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker())
    elif args.once:
        asyncio.run(run_once(args.mode, args.hours))
    else:
        print("Use --worker to start worker or --once to run workflow")
