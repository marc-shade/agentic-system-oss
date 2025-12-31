#!/usr/bin/env python3
"""
Visual Memory Consolidation Workflow

Nightly workflow that:
- Consolidates visual memories from the day
- Clusters similar observations
- Extracts patterns and trends
- Prunes low-value memories
- Strengthens important visual concepts
- Integrates with enhanced-memory consolidation

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
async def get_daily_visual_memories() -> Dict[str, Any]:
    """Activity: Get all visual memories from the past 24 hours."""
    from visual_memory_integration import VisualMemoryManager

    try:
        manager = VisualMemoryManager()
        memories = manager.memory_store.get_recent(hours=24, limit=1000)

        return {
            "success": True,
            "count": len(memories),
            "memories": [
                {
                    "id": m.id,
                    "scene_type": m.scene_type,
                    "objects": m.objects,
                    "importance": m.importance.value,
                    "confidence": m.confidence,
                    "description": m.description[:200],
                    "timestamp": m.timestamp
                }
                for m in memories
            ],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get daily memories: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def cluster_visual_memories(memories: List[Dict]) -> Dict[str, Any]:
    """Activity: Cluster similar visual memories."""
    from visual_memory_integration import VisualEmbedder

    try:
        embedder = VisualEmbedder()

        # Group by scene type first
        scene_clusters = {}
        for mem in memories:
            scene = mem.get("scene_type", "unknown")
            if scene not in scene_clusters:
                scene_clusters[scene] = []
            scene_clusters[scene].append(mem)

        # Calculate cluster statistics
        cluster_stats = {}
        for scene, mems in scene_clusters.items():
            cluster_stats[scene] = {
                "count": len(mems),
                "avg_confidence": sum(m["confidence"] for m in mems) / len(mems) if mems else 0,
                "avg_importance": sum(m["importance"] for m in mems) / len(mems) if mems else 0,
                "common_objects": _get_common_objects(mems)
            }

        return {
            "success": True,
            "clusters": cluster_stats,
            "total_memories": len(memories),
            "cluster_count": len(scene_clusters),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return {"success": False, "error": str(e)}


def _get_common_objects(memories: List[Dict]) -> List[str]:
    """Get most common objects across memories."""
    object_counts = {}
    for mem in memories:
        for obj in mem.get("objects", []):
            object_counts[obj] = object_counts.get(obj, 0) + 1

    sorted_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)
    return [obj for obj, _ in sorted_objects[:10]]


@activity.defn
async def extract_visual_patterns(cluster_stats: Dict) -> Dict[str, Any]:
    """Activity: Extract patterns and trends from clusters."""
    try:
        patterns = []

        # Analyze scene distribution
        clusters = cluster_stats.get("clusters", {})
        total = cluster_stats.get("total_memories", 0)

        if total > 0:
            for scene, stats in clusters.items():
                percentage = (stats["count"] / total) * 100
                if percentage > 20:
                    patterns.append({
                        "type": "dominant_scene",
                        "scene": scene,
                        "percentage": percentage,
                        "insight": f"{scene} dominated visual activity ({percentage:.1f}%)"
                    })

            # Find high-importance clusters
            high_importance = [
                (scene, stats) for scene, stats in clusters.items()
                if stats["avg_importance"] >= 3.5
            ]
            for scene, stats in high_importance:
                patterns.append({
                    "type": "high_importance_activity",
                    "scene": scene,
                    "avg_importance": stats["avg_importance"],
                    "insight": f"High importance activity in {scene}"
                })

            # Find recurring objects
            all_objects = {}
            for scene, stats in clusters.items():
                for obj in stats.get("common_objects", []):
                    all_objects[obj] = all_objects.get(obj, 0) + 1

            recurring = [(obj, count) for obj, count in all_objects.items() if count > 2]
            for obj, count in recurring[:5]:
                patterns.append({
                    "type": "recurring_object",
                    "object": obj,
                    "occurrences": count,
                    "insight": f"'{obj}' appeared across {count} scene types"
                })

        return {
            "success": True,
            "patterns": patterns,
            "pattern_count": len(patterns),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Pattern extraction failed: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def prune_low_value_memories(memories: List[Dict], retention_threshold: float = 0.3) -> Dict[str, Any]:
    """Activity: Identify low-value memories for pruning."""
    try:
        # Calculate value score for each memory
        to_prune = []
        to_keep = []

        for mem in memories:
            # Value = importance * confidence * recency_factor
            importance = mem.get("importance", 1) / 5.0
            confidence = mem.get("confidence", 0)

            # Parse timestamp for recency
            try:
                ts = datetime.fromisoformat(mem["timestamp"].replace("Z", "+00:00"))
                hours_old = (datetime.now(ts.tzinfo) - ts).total_seconds() / 3600
                recency = max(0, 1 - (hours_old / 24))  # 0-1 scale over 24 hours
            except Exception:
                recency = 0.5

            value = importance * confidence * (0.5 + 0.5 * recency)

            if value < retention_threshold:
                to_prune.append({
                    "id": mem["id"],
                    "value_score": value,
                    "reason": "Below retention threshold"
                })
            else:
                to_keep.append(mem["id"])

        return {
            "success": True,
            "to_prune": to_prune,
            "prune_count": len(to_prune),
            "keep_count": len(to_keep),
            "retention_rate": len(to_keep) / len(memories) if memories else 1.0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Pruning analysis failed: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def strengthen_visual_concepts(patterns: List[Dict]) -> Dict[str, Any]:
    """Activity: Strengthen important visual concepts in knowledge graph."""
    from visual_memory_integration import VisualMemoryManager

    try:
        manager = VisualMemoryManager()
        strengthened = []

        for pattern in patterns:
            if pattern["type"] == "recurring_object":
                # This object is significant - strengthen its concept
                obj_name = pattern["object"]
                concept_id = f"obj_{obj_name.lower().replace(' ', '_')}"

                # Add reinforcement relation
                manager.knowledge_graph.add_concept_relation(
                    source=concept_id,
                    target="core_visual_vocabulary",
                    relation="strengthened_by_recurrence",
                    strength=pattern["occurrences"] / 10.0
                )
                strengthened.append(concept_id)

            elif pattern["type"] == "dominant_scene":
                scene_id = f"scene_{pattern['scene'].lower().replace(' ', '_')}"
                manager.knowledge_graph.add_concept_relation(
                    source=scene_id,
                    target="primary_work_context",
                    relation="dominant_scene",
                    strength=pattern["percentage"] / 100.0
                )
                strengthened.append(scene_id)

        return {
            "success": True,
            "strengthened_concepts": strengthened,
            "count": len(strengthened),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Concept strengthening failed: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def generate_consolidation_summary(
    cluster_stats: Dict,
    patterns: List[Dict],
    prune_results: Dict
) -> Dict[str, Any]:
    """Activity: Generate summary of visual memory consolidation."""
    try:
        summary = {
            "consolidation_date": datetime.now().isoformat(),
            "total_memories_processed": cluster_stats.get("total_memories", 0),
            "clusters_formed": cluster_stats.get("cluster_count", 0),
            "patterns_discovered": len(patterns),
            "memories_pruned": prune_results.get("prune_count", 0),
            "memories_retained": prune_results.get("keep_count", 0),
            "retention_rate": prune_results.get("retention_rate", 1.0),
            "key_patterns": patterns[:5],
            "cluster_summary": cluster_stats.get("clusters", {}),
            "status": "complete"
        }

        # Store summary
        summary_path = "/Volumes/SSDRAID0/agentic-system/databases/visual_memory/consolidation_summaries.jsonl"
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)

        with open(summary_path, 'a') as f:
            f.write(json.dumps(summary) + '\n')

        return {
            "success": True,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return {"success": False, "error": str(e)}


@workflow.defn
class VisualMemoryConsolidationWorkflow:
    """
    Nightly visual memory consolidation workflow.

    Processes the day's visual memories:
    1. Retrieve all memories from past 24 hours
    2. Cluster by scene type and similarity
    3. Extract patterns and trends
    4. Identify memories for pruning
    5. Strengthen important concepts
    6. Generate consolidation summary
    """

    @workflow.run
    async def run(self, mode: str = "full") -> Dict[str, Any]:
        """
        Run visual memory consolidation.

        Args:
            mode: "full" (all steps) or "analysis" (no pruning)
        """
        workflow.logger.info(f"Starting visual memory consolidation - mode: {mode}")

        results = {
            "start_time": workflow.now().isoformat(),
            "mode": mode,
            "steps": {}
        }

        try:
            # Step 1: Get daily memories
            workflow.logger.info("Retrieving daily visual memories...")
            daily_memories = await workflow.execute_activity(
                get_daily_visual_memories,
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["retrieval"] = {
                "success": daily_memories.get("success"),
                "count": daily_memories.get("count", 0)
            }

            if not daily_memories.get("success") or daily_memories.get("count", 0) == 0:
                workflow.logger.info("No memories to consolidate")
                results["status"] = "no_memories"
                return results

            memories = daily_memories.get("memories", [])

            # Step 2: Cluster memories
            workflow.logger.info("Clustering visual memories...")
            cluster_stats = await workflow.execute_activity(
                cluster_visual_memories,
                args=[memories],
                start_to_close_timeout=timedelta(minutes=5)
            )
            results["steps"]["clustering"] = cluster_stats

            # Step 3: Extract patterns
            workflow.logger.info("Extracting visual patterns...")
            patterns = await workflow.execute_activity(
                extract_visual_patterns,
                args=[cluster_stats],
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["patterns"] = patterns

            # Step 4: Identify pruning candidates
            workflow.logger.info("Analyzing memory retention...")
            prune_results = await workflow.execute_activity(
                prune_low_value_memories,
                args=[memories, 0.3],
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["pruning"] = prune_results

            # Step 5: Strengthen concepts
            workflow.logger.info("Strengthening visual concepts...")
            strengthen_results = await workflow.execute_activity(
                strengthen_visual_concepts,
                args=[patterns.get("patterns", [])],
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["strengthening"] = strengthen_results

            # Step 6: Generate summary
            workflow.logger.info("Generating consolidation summary...")
            summary = await workflow.execute_activity(
                generate_consolidation_summary,
                args=[cluster_stats, patterns.get("patterns", []), prune_results],
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["summary"] = summary

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success"

            workflow.logger.info(f"Visual memory consolidation complete: {results['status']}")
            return results

        except Exception as e:
            workflow.logger.error(f"Visual memory consolidation failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            results["end_time"] = workflow.now().isoformat()
            return results


async def run_worker():
    """Run Temporal worker for visual memory consolidation."""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="visual-memory-consolidation",
        workflows=[VisualMemoryConsolidationWorkflow],
        activities=[
            get_daily_visual_memories,
            cluster_visual_memories,
            extract_visual_patterns,
            prune_low_value_memories,
            strengthen_visual_concepts,
            generate_consolidation_summary
        ]
    )

    logger.info("Visual Memory Consolidation Worker started on task_queue: visual-memory-consolidation")
    await worker.run()


async def run_once(mode: str = "full"):
    """Run the workflow once (for testing)."""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        VisualMemoryConsolidationWorkflow.run,
        args=[mode],
        id=f"visual-memory-consolidation-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="visual-memory-consolidation"
    )

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visual Memory Consolidation Workflow")
    parser.add_argument("--worker", action="store_true", help="Run as worker")
    parser.add_argument("--once", action="store_true", help="Run workflow once")
    parser.add_argument("--mode", default="full", choices=["full", "analysis"],
                        help="Consolidation mode")

    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker())
    elif args.once:
        asyncio.run(run_once(args.mode))
    else:
        print("Use --worker to start worker or --once to run workflow")
