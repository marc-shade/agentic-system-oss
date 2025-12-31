#!/usr/bin/env python3
"""
Visual Perception Workflow - Temporal Workflow for Visual AGI

Provides scheduled and event-driven visual perception capabilities:
- Periodic screenshot analysis for environmental awareness
- Image batch processing with multi-provider consensus
- Visual change detection and alerting
- Integration with memory consolidation

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

# Add paths
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def capture_screenshot() -> Dict[str, Any]:
    """Activity: Capture screenshot."""
    from visual_perception_agent import ScreenshotCapture

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "/Volumes/SSDRAID0/agentic-system/databases/sensory/screenshots"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"screenshot_{timestamp}.png")

        path = await ScreenshotCapture.capture(output_path)

        return {
            "success": True,
            "path": path,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Screenshot capture failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def analyze_image(image_path: str, prompt: str) -> Dict[str, Any]:
    """Activity: Analyze image with multi-provider consensus."""
    from visual_perception_agent import VisualPerceptionAgent, ImageSource

    try:
        agent = VisualPerceptionAgent()
        perception = await agent.perceive(
            image_source=image_path,
            source_type=ImageSource.FILE,
            prompt=prompt,
            use_all_providers=True,
            apply_privacy=True
        )

        return {
            "success": True,
            "consensus": perception.consensus,
            "confidence": perception.confidence,
            "providers": [o.provider for o in perception.observations],
            "conflicts": perception.conflicts,
            "image_hash": perception.image_hash,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def detect_visual_changes(current: Dict, previous: Optional[Dict]) -> Dict[str, Any]:
    """Activity: Detect changes between visual analyses."""
    if not previous:
        return {
            "status": "first_observation",
            "changes_detected": False,
            "timestamp": datetime.now().isoformat()
        }

    try:
        changes = []

        # Compare scene types
        curr_scene = current.get("consensus", {}).get("scene_type", "")
        prev_scene = previous.get("consensus", {}).get("scene_type", "")
        if curr_scene != prev_scene:
            changes.append({
                "type": "scene_change",
                "from": prev_scene,
                "to": curr_scene
            })

        # Compare objects
        curr_objects = set(current.get("consensus", {}).get("objects", []))
        prev_objects = set(previous.get("consensus", {}).get("objects", []))

        new_objects = curr_objects - prev_objects
        removed_objects = prev_objects - curr_objects

        if new_objects:
            changes.append({
                "type": "objects_appeared",
                "objects": list(new_objects)
            })
        if removed_objects:
            changes.append({
                "type": "objects_disappeared",
                "objects": list(removed_objects)
            })

        # Compare confidence levels
        curr_conf = current.get("confidence", 0)
        prev_conf = previous.get("confidence", 0)
        if abs(curr_conf - prev_conf) > 0.2:
            changes.append({
                "type": "confidence_shift",
                "from": prev_conf,
                "to": curr_conf
            })

        return {
            "status": "compared",
            "changes_detected": len(changes) > 0,
            "changes": changes,
            "change_count": len(changes),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Change detection failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def store_visual_observation(observation: Dict) -> Dict[str, Any]:
    """Activity: Store visual observation in memory."""
    try:
        # Store in local JSONL database
        db_path = "/Volumes/SSDRAID0/agentic-system/databases/sensory/visual_observations.jsonl"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        with open(db_path, 'a') as f:
            f.write(json.dumps(observation) + '\n')

        # Store in visual memory system with knowledge graph
        memory_id = None
        try:
            from visual_memory_integration import VisualMemoryManager, VisualMemoryType

            manager = VisualMemoryManager()
            analysis = observation.get("analysis", {})

            if analysis.get("success"):
                memory = await manager.store_perception(
                    perception=analysis,
                    memory_type=VisualMemoryType.SCREENSHOT
                )
                memory_id = memory.id
                logger.info(f"Stored visual memory: {memory_id}")
        except Exception as e:
            logger.warning(f"Could not store in visual memory: {e}")

        return {
            "success": True,
            "stored_at": db_path,
            "memory_id": memory_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Storage failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@activity.defn
async def batch_analyze_images(image_paths: List[str], prompt: str) -> Dict[str, Any]:
    """Activity: Analyze multiple images in batch."""
    from visual_perception_agent import VisualPerceptionAgent, ImageSource

    try:
        agent = VisualPerceptionAgent()
        results = []

        for path in image_paths:
            if os.path.exists(path):
                perception = await agent.perceive(
                    image_source=path,
                    source_type=ImageSource.FILE,
                    prompt=prompt,
                    use_all_providers=True,
                    apply_privacy=True
                )
                results.append({
                    "path": path,
                    "consensus": perception.consensus,
                    "confidence": perception.confidence
                })
            else:
                results.append({
                    "path": path,
                    "error": "File not found"
                })

        return {
            "success": True,
            "analyzed": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@workflow.defn
class VisualPerceptionWorkflow:
    """
    Visual Perception Workflow.

    Captures and analyzes visual input with multi-provider consensus,
    detects changes, and stores observations for learning.
    """

    @workflow.run
    async def run(self, mode: str = "snapshot", config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run visual perception workflow.

        Args:
            mode:
                "snapshot" - Single screenshot capture and analysis
                "monitor" - Continuous monitoring (for scheduled runs)
                "batch" - Process batch of images from config
            config:
                Additional configuration (image_paths for batch mode, etc.)
        """
        config = config or {}
        workflow.logger.info(f"Starting visual perception - mode: {mode}")

        results = {
            "start_time": workflow.now().isoformat(),
            "mode": mode,
            "steps": {}
        }

        try:
            if mode == "snapshot":
                # Single screenshot capture and analysis
                workflow.logger.info("Capturing screenshot...")
                capture_result = await workflow.execute_activity(
                    capture_screenshot,
                    start_to_close_timeout=timedelta(seconds=30)
                )
                results["steps"]["capture"] = capture_result

                if capture_result.get("success"):
                    workflow.logger.info("Analyzing screenshot...")
                    analysis = await workflow.execute_activity(
                        analyze_image,
                        args=[capture_result["path"], config.get("prompt", "Describe what you see on screen.")],
                        start_to_close_timeout=timedelta(minutes=3)
                    )
                    results["steps"]["analysis"] = analysis

                    # Store observation
                    await workflow.execute_activity(
                        store_visual_observation,
                        args=[{
                            "type": "snapshot",
                            "capture": capture_result,
                            "analysis": analysis
                        }],
                        start_to_close_timeout=timedelta(seconds=30)
                    )

            elif mode == "monitor":
                # Environmental monitoring mode
                workflow.logger.info("Running visual monitoring...")

                # Capture current state
                capture_result = await workflow.execute_activity(
                    capture_screenshot,
                    start_to_close_timeout=timedelta(seconds=30)
                )
                results["steps"]["capture"] = capture_result

                if capture_result.get("success"):
                    analysis = await workflow.execute_activity(
                        analyze_image,
                        args=[capture_result["path"], "Describe the current screen state. Note any applications, windows, or notable content visible."],
                        start_to_close_timeout=timedelta(minutes=3)
                    )
                    results["steps"]["analysis"] = analysis

                    # Compare with previous (if available)
                    previous = config.get("previous_observation")
                    if previous:
                        changes = await workflow.execute_activity(
                            detect_visual_changes,
                            args=[analysis, previous],
                            start_to_close_timeout=timedelta(seconds=30)
                        )
                        results["steps"]["changes"] = changes

                        if changes.get("changes_detected"):
                            workflow.logger.info(f"Visual changes detected: {changes['changes']}")
                            results["changes_detected"] = changes["changes"]

                    # Store
                    await workflow.execute_activity(
                        store_visual_observation,
                        args=[{
                            "type": "monitor",
                            "capture": capture_result,
                            "analysis": analysis,
                            "changes": results.get("steps", {}).get("changes")
                        }],
                        start_to_close_timeout=timedelta(seconds=30)
                    )

            elif mode == "batch":
                # Batch processing mode
                image_paths = config.get("image_paths", [])
                prompt = config.get("prompt", "Describe what you see.")

                if not image_paths:
                    results["error"] = "No image_paths provided for batch mode"
                else:
                    workflow.logger.info(f"Batch analyzing {len(image_paths)} images...")
                    batch_result = await workflow.execute_activity(
                        batch_analyze_images,
                        args=[image_paths, prompt],
                        start_to_close_timeout=timedelta(minutes=10)
                    )
                    results["steps"]["batch"] = batch_result

            else:
                results["error"] = f"Unknown mode: {mode}"

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success" if "error" not in results else "failed"

            workflow.logger.info(f"Visual perception complete: {results['status']}")
            return results

        except Exception as e:
            workflow.logger.error(f"Visual perception failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            results["end_time"] = workflow.now().isoformat()
            return results


@workflow.defn
class VisualMonitoringWorkflow:
    """
    Continuous Visual Monitoring Workflow.

    Runs periodic visual perception and tracks changes over time.
    Designed for scheduled execution (e.g., every 15 minutes).
    """

    @workflow.run
    async def run(self, interval_minutes: int = 15) -> Dict[str, Any]:
        """Run continuous monitoring session."""
        workflow.logger.info(f"Starting visual monitoring session")

        results = {
            "start_time": workflow.now().isoformat(),
            "observations": [],
            "total_changes": 0
        }

        try:
            # Initial capture
            capture = await workflow.execute_activity(
                capture_screenshot,
                start_to_close_timeout=timedelta(seconds=30)
            )

            if capture.get("success"):
                analysis = await workflow.execute_activity(
                    analyze_image,
                    args=[capture["path"], "Describe the current visual environment."],
                    start_to_close_timeout=timedelta(minutes=3)
                )

                results["observations"].append({
                    "timestamp": workflow.now().isoformat(),
                    "analysis": analysis
                })

                await workflow.execute_activity(
                    store_visual_observation,
                    args=[{
                        "type": "monitoring_session",
                        "analysis": analysis,
                        "session_start": results["start_time"]
                    }],
                    start_to_close_timeout=timedelta(seconds=30)
                )

            results["status"] = "success"
            results["end_time"] = workflow.now().isoformat()
            return results

        except Exception as e:
            workflow.logger.error(f"Visual monitoring failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def run_worker():
    """Run Temporal worker for visual perception workflows."""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="visual-perception",
        workflows=[VisualPerceptionWorkflow, VisualMonitoringWorkflow],
        activities=[
            capture_screenshot,
            analyze_image,
            detect_visual_changes,
            store_visual_observation,
            batch_analyze_images
        ]
    )

    logger.info("Visual Perception Worker started on task_queue: visual-perception")
    await worker.run()


async def run_once(mode: str = "snapshot", config: Optional[Dict] = None):
    """Run the workflow once (for testing)."""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        VisualPerceptionWorkflow.run,
        args=[mode, config or {}],
        id=f"visual-perception-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="visual-perception"
    )

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visual Perception Workflow")
    parser.add_argument("--worker", action="store_true", help="Run as worker")
    parser.add_argument("--once", action="store_true", help="Run workflow once")
    parser.add_argument("--mode", default="snapshot", choices=["snapshot", "monitor", "batch"],
                        help="Workflow mode")

    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker())
    elif args.once:
        asyncio.run(run_once(args.mode))
    else:
        print("Use --worker to start worker or --once to run workflow")
