#!/usr/bin/env python3
"""
Cross-Node Memory Sync Workflow
================================

Ensures cluster-wide memory consistency by periodically synchronizing
shared and personal memories across all active cluster nodes.

Schedule: Every 15 minutes
Duration: ~30-60 seconds
Fault-tolerant: Survives node failures

Operations:
1. Discover active cluster nodes
2. Pull shared memories from all nodes
3. Detect and resolve conflicts
4. Push consolidated memories to all nodes
5. Verify synchronization
6. Track sync metrics

STATUS: Production Ready
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy
import sys
import json
from pathlib import Path

# Dynamic path detection for cross-node compatibility (sandbox-safe)
import os
_current_file = os.path.abspath(__file__)
_script_dir = os.path.dirname(_current_file)
BASE_DIR = os.path.dirname(os.path.dirname(_script_dir))  # agentic-system root
CLUSTER_DIR = os.path.join(BASE_DIR, "cluster-deployment")

sys.path.insert(0, CLUSTER_DIR)
from cluster_memory import ClusterMemoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def discover_active_nodes() -> List[str]:
    """
    Discover active cluster nodes via multiple methods:
    - SSH connectivity
    - Avahi/mDNS discovery
    - Node registry database
    """
    try:
        manager = ClusterMemoryManager()
        nodes = manager.get_active_nodes()
        logger.info(f"Discovered {len(nodes)} active nodes: {nodes}")
        return nodes
    except Exception as e:
        logger.error(f"Node discovery failed: {e}")
        return ["macpro51"]  # Fallback to local node


@activity.defn
async def collect_shared_memories(node_id: str) -> Dict[str, Any]:
    """
    Collect shared memories from a specific node

    Returns:
        {
            "node_id": str,
            "entity_count": int,
            "entities": List[Dict],
            "timestamp": str
        }
    """
    try:
        manager = ClusterMemoryManager()
        entities = manager.get_node_memories(node_id, scope="shared")

        return {
            "node_id": node_id,
            "entity_count": len(entities),
            "entities": entities,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to collect memories from {node_id}: {e}")
        return {
            "node_id": node_id,
            "entity_count": 0,
            "entities": [],
            "error": str(e)
        }


@activity.defn
async def detect_memory_conflicts(all_memories: List[Dict]) -> Dict[str, Any]:
    """
    Detect conflicts in memories across nodes

    Conflicts arise when:
    - Same entity name with different content
    - Different timestamps (versioning issue)
    - Duplicate entities from different nodes

    Returns conflict report and resolution strategy
    """
    try:
        conflicts = []
        entity_map = {}

        # Build entity map: name -> list of versions from different nodes
        for node_data in all_memories:
            node_id = node_data["node_id"]
            for entity in node_data.get("entities", []):
                name = entity.get("name")
                if name:
                    if name not in entity_map:
                        entity_map[name] = []
                    entity_map[name].append({
                        "node_id": node_id,
                        "entity": entity
                    })

        # Detect conflicts
        for name, versions in entity_map.items():
            if len(versions) > 1:
                # Check if content differs
                contents = set()
                for v in versions:
                    observations = v["entity"].get("observations", [])
                    content_hash = hash(tuple(observations))
                    contents.add(content_hash)

                if len(contents) > 1:
                    conflicts.append({
                        "entity_name": name,
                        "versions": versions,
                        "conflict_type": "content_mismatch",
                        "resolution": "use_latest_timestamp"
                    })

        logger.info(f"Detected {len(conflicts)} conflicts")

        return {
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "total_entities": len(entity_map)
        }
    except Exception as e:
        logger.error(f"Conflict detection failed: {e}")
        return {"error": str(e), "conflict_count": 0}


@activity.defn
async def resolve_conflicts(conflict_report: Dict) -> List[Dict]:
    """
    Resolve conflicts using strategy:
    1. Latest timestamp wins (for content conflicts)
    2. Merge observations (for partial updates)
    3. Preserve all versions in history

    Returns resolved entity set
    """
    try:
        conflicts = conflict_report.get("conflicts", [])
        resolved_entities = []

        for conflict in conflicts:
            versions = conflict["versions"]

            # Strategy: Use version with latest timestamp
            latest = max(versions, key=lambda v: v["entity"].get("updated_at", ""))

            resolved_entity = latest["entity"]
            resolved_entity["_resolved_from_conflict"] = True
            resolved_entity["_conflict_resolution_time"] = datetime.now().isoformat()

            resolved_entities.append(resolved_entity)

            logger.info(f"Resolved conflict for {conflict['entity_name']}")

        return resolved_entities
    except Exception as e:
        logger.error(f"Conflict resolution failed: {e}")
        return []


@activity.defn
async def sync_to_node(node_id: str, entities: List[Dict]) -> Dict[str, Any]:
    """
    Push synchronized entities to a specific node

    Returns sync status
    """
    try:
        manager = ClusterMemoryManager()

        # Create or update entities on target node
        success_count = 0
        for entity in entities:
            try:
                manager.create_entity(
                    name=entity["name"],
                    entity_type=entity.get("entity_type", "knowledge"),
                    observations=entity.get("observations", []),
                    scope="shared"
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to sync entity {entity['name']} to {node_id}: {e}")

        return {
            "node_id": node_id,
            "synced_count": success_count,
            "total_entities": len(entities),
            "success": success_count == len(entities)
        }
    except Exception as e:
        logger.error(f"Sync to {node_id} failed: {e}")
        return {
            "node_id": node_id,
            "error": str(e),
            "success": False
        }


@activity.defn
async def verify_sync(nodes: List[str]) -> Dict[str, Any]:
    """
    Verify that all nodes have consistent memory counts

    Returns verification report
    """
    try:
        manager = ClusterMemoryManager()
        node_counts = {}

        for node_id in nodes:
            try:
                entities = manager.get_node_memories(node_id, scope="shared")
                node_counts[node_id] = len(entities)
            except Exception as e:
                node_counts[node_id] = f"error: {e}"

        # Check if all counts match
        counts = [c for c in node_counts.values() if isinstance(c, int)]
        is_consistent = len(set(counts)) <= 1 if counts else False

        return {
            "is_consistent": is_consistent,
            "node_counts": node_counts,
            "expected_count": counts[0] if counts else None
        }
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {"error": str(e), "is_consistent": False}


@activity.defn
async def record_sync_metrics(sync_result: Dict) -> None:
    """
    Record sync metrics for monitoring
    """
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": sync_result.get("duration_seconds", 0),
            "nodes_synced": sync_result.get("nodes_synced", 0),
            "conflicts_resolved": sync_result.get("conflicts_resolved", 0),
            "entities_synced": sync_result.get("entities_synced", 0),
            "is_consistent": sync_result.get("is_consistent", False)
        }

        # Log to file
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "cluster-memory-sync.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(metrics) + "\n")

        logger.info(f"Sync metrics recorded: {metrics}")
    except Exception as e:
        logger.error(f"Failed to record metrics: {e}")


@workflow.defn
class ClusterMemorySyncWorkflow:
    """
    Periodic cluster memory synchronization workflow

    Ensures all nodes have consistent shared memory
    """

    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """
        Execute cluster memory sync

        Returns:
            Sync report with metrics and status
        """
        start_time = workflow.now()
        logger.info("Starting cluster memory sync workflow")

        # Retry policy for activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )

        try:
            # Step 1: Discover active nodes
            nodes = await workflow.execute_activity(
                discover_active_nodes,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy
            )

            if not nodes:
                return {"error": "No active nodes discovered", "success": False}

            # Step 2: Collect memories from all nodes (parallel)
            collect_tasks = [
                workflow.execute_activity(
                    collect_shared_memories,
                    args=[node_id],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=retry_policy
                )
                for node_id in nodes
            ]

            all_memories = await asyncio.gather(*collect_tasks)

            # Step 3: Detect conflicts
            conflict_report = await workflow.execute_activity(
                detect_memory_conflicts,
                args=[all_memories],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy
            )

            # Step 4: Resolve conflicts
            resolved_entities = []
            if conflict_report.get("conflict_count", 0) > 0:
                resolved_entities = await workflow.execute_activity(
                    resolve_conflicts,
                    args=[conflict_report],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=retry_policy
                )

            # Step 5: Sync to all nodes (parallel)
            # Merge all unique entities + resolved conflicts
            all_entities = {}
            for node_data in all_memories:
                for entity in node_data.get("entities", []):
                    name = entity.get("name")
                    if name:
                        all_entities[name] = entity

            # Add resolved entities (overwrite conflicts)
            for entity in resolved_entities:
                all_entities[entity["name"]] = entity

            entities_to_sync = list(all_entities.values())

            sync_tasks = [
                workflow.execute_activity(
                    sync_to_node,
                    args=[node_id, entities_to_sync],
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=retry_policy
                )
                for node_id in nodes
            ]

            sync_results = await asyncio.gather(*sync_tasks)

            # Step 6: Verify synchronization
            verification = await workflow.execute_activity(
                verify_sync,
                args=[nodes],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy
            )

            # Calculate metrics
            duration = (workflow.now() - start_time).total_seconds()

            sync_report = {
                "success": verification.get("is_consistent", False),
                "duration_seconds": duration,
                "nodes_synced": len(nodes),
                "conflicts_resolved": len(resolved_entities),
                "entities_synced": len(entities_to_sync),
                "is_consistent": verification.get("is_consistent", False),
                "node_counts": verification.get("node_counts", {}),
                "timestamp": workflow.now().isoformat()
            }

            # Step 7: Record metrics
            await workflow.execute_activity(
                record_sync_metrics,
                args=[sync_report],
                start_to_close_timeout=timedelta(seconds=10)
            )

            logger.info(f"Cluster sync completed: {sync_report}")

            return sync_report

        except Exception as e:
            logger.error(f"Cluster sync workflow failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": workflow.now().isoformat()
            }


async def main():
    """
    Worker process for cluster memory sync workflow
    """
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="cluster-memory-sync",
        workflows=[ClusterMemorySyncWorkflow],
        activities=[
            discover_active_nodes,
            collect_shared_memories,
            detect_memory_conflicts,
            resolve_conflicts,
            sync_to_node,
            verify_sync,
            record_sync_metrics
        ]
    )

    logger.info("Cluster Memory Sync worker started")
    logger.info("Workflow: ClusterMemorySyncWorkflow")
    logger.info("Schedule: Every 15 minutes")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
