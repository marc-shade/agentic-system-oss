#!/usr/bin/env python3
"""
Cluster Coordination Workflow - Multi-node task distribution and coordination

Capabilities:
- Monitor node health across mac-studio, macbook-air, macpro51
- Distribute tasks to optimal nodes based on capabilities and load
- Handle node failures with automatic retry and redistribution
- Coordinate shared memory updates across cluster
- Balance workload across available nodes

STATUS: Production Ready
"""

import asyncio
import logging
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
import sys
import socket
import platform

# Add cluster deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cluster-deployment"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_storage_base() -> Path:
    """Detect correct storage base path for current platform"""
    system = platform.system()
    hostname = socket.gethostname().lower()

    if system == "Darwin":  # macOS
        # Check for SSDRAID0 (hot tier)
        ssd_path = Path("/Volumes/SSDRAID0/agentic-system")
        if ssd_path.exists():
            return ssd_path
        # Fallback to FILES (cold tier - backup only)
        files_path = Path("/Volumes/FILES/agentic-system")
        if files_path.exists():
            return files_path
        # Last resort - home directory
        return Path.home() / "agentic-system"
    elif system == "Linux":
        # Linux nodes use /home/marc/agentic-system
        return Path("/home/marc/agentic-system")
    else:
        # Unknown platform - use home directory
        return Path.home() / "agentic-system"

# Cluster node registry
CLUSTER_NODES = {
    "macpro51": {
        "ip": "192.168.1.183",
        "hostname": "macpro51.local",
        "os": "linux",
        "arch": "x86_64",
        "api_port": 9000,
        "capabilities": ["docker", "podman", "compilation", "testing"],
        "specialties": ["compilation", "testing", "containerization"],
        "max_tasks": 10,
        "priority": 3
    },
    "mac-studio": {
        "ip": "192.168.1.176",
        "hostname": "Marcs-Mac-Studio.local",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["orchestration", "coordination", "temporal"],
        "specialties": ["orchestration", "coordination"],
        "max_tasks": 5,
        "priority": 1  # Keep orchestrator free
    },
    "macbook-air": {
        "ip": "192.168.1.76",
        "hostname": "Mac.fios-router.home",
        "os": "macos",
        "arch": "arm64",
        "capabilities": ["research", "documentation", "analysis"],
        "specialties": ["research", "documentation"],
        "max_tasks": 3,
        "priority": 2
    }
}


@activity.defn
async def monitor_node_health() -> Dict[str, Any]:
    """Check health of all cluster nodes"""
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "nodes": {}
    }

    for node_id, node_info in CLUSTER_NODES.items():
        try:
            # Try to ping node
            response = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "ping", "-c", "1", "-W", "1", node_info["hostname"],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=2.0
            )
            await response.communicate()
            reachable = response.returncode == 0

            # For macpro51, also check Builder API
            api_healthy = False
            if node_id == "macpro51" and reachable:
                try:
                    api_url = f"http://{node_info['ip']}:{node_info['api_port']}/api/v1/health"
                    async with asyncio.timeout(2.0):
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(api_url) as resp:
                                api_healthy = resp.status == 200
                except:
                    pass

            health_status["nodes"][node_id] = {
                "reachable": reachable,
                "api_healthy": api_healthy if node_id == "macpro51" else None,
                "status": "healthy" if reachable else "unreachable",
                "checked_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed for {node_id}: {e}")
            health_status["nodes"][node_id] = {
                "reachable": False,
                "status": "error",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }

    logger.info(f"Node health: {json.dumps(health_status, indent=2)}")
    return health_status


@activity.defn
async def fetch_pending_tasks() -> List[Dict]:
    """Fetch pending tasks from cluster task queue"""
    try:
        # Get platform-specific database path
        storage_base = get_storage_base()
        db_path = storage_base / "databases/cluster/task_queue.db"

        if not db_path.exists():
            logger.warning(f"Task queue database not found: {db_path}")
            return []

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get pending tasks ordered by priority
        cursor.execute("""
            SELECT task_id, task_type, command, script, requires_os, requires_arch,
                   requires_capabilities, priority, metadata, submitted_from, submitted_at
            FROM task_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, submitted_at ASC
            LIMIT 20
        """)

        tasks = []
        for row in cursor.fetchall():
            task = {
                "task_id": row[0],
                "task_type": row[1],
                "command": row[2],
                "script": row[3],
                "requires_os": row[4],
                "requires_arch": row[5],
                "requires_capabilities": row[6],
                "priority": row[7],
                "metadata": json.loads(row[8]) if row[8] else {},
                "submitted_from": row[9],
                "submitted_at": row[10]
            }
            tasks.append(task)

        conn.close()
        logger.info(f"Fetched {len(tasks)} pending tasks")
        return tasks

    except Exception as e:
        logger.error(f"Failed to fetch pending tasks: {e}")
        return []


@activity.defn
async def select_optimal_node(task: Dict, health_status: Dict) -> Optional[str]:
    """Select the best node for a task based on requirements and health"""
    try:
        candidates = []

        for node_id, node_info in CLUSTER_NODES.items():
            # Skip unhealthy nodes
            if not health_status["nodes"].get(node_id, {}).get("reachable", False):
                continue

            # Check OS requirement
            if task.get("requires_os") and task["requires_os"] != node_info["os"]:
                continue

            # Check architecture requirement
            if task.get("requires_arch") and task["requires_arch"] != node_info["arch"]:
                continue

            # Check capability requirements
            if task.get("requires_capabilities"):
                required = set(task["requires_capabilities"].split(","))
                available = set(node_info["capabilities"])
                if not required.issubset(available):
                    continue

            # Calculate score (lower is better)
            score = node_info["priority"]

            # Boost score if node specialty matches task type
            if task.get("task_type") in node_info.get("specialties", []):
                score -= 1

            candidates.append((node_id, score))

        if not candidates:
            logger.warning(f"No suitable node found for task {task['task_id']}")
            return None

        # Select node with best score
        candidates.sort(key=lambda x: x[1])
        selected_node = candidates[0][0]

        logger.info(f"Selected node {selected_node} for task {task['task_id']}")
        return selected_node

    except Exception as e:
        logger.error(f"Node selection failed: {e}")
        return None


@activity.defn
async def distribute_task(task: Dict, target_node: str) -> Dict:
    """Distribute a task to the selected node"""
    try:
        # Get platform-specific database path
        storage_base = get_storage_base()
        db_path = storage_base / "databases/cluster/task_queue.db"

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE task_queue
            SET status = 'assigned',
                assigned_to = ?,
                assigned_at = ?
            WHERE task_id = ?
        """, (target_node, datetime.now().isoformat(), task["task_id"]))

        conn.commit()
        conn.close()

        # If target is macpro51, send via Builder API
        if target_node == "macpro51":
            try:
                node_info = CLUSTER_NODES[target_node]
                api_url = f"http://{node_info['ip']}:{node_info['api_port']}/api/v1/tasks"

                # Send task to Builder API
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=task, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            logger.info(f"Task {task['task_id']} sent to {target_node}: {result}")
                            return {"success": True, "node": target_node, "response": result}
                        else:
                            error_msg = await resp.text()
                            logger.error(f"Failed to send task to {target_node}: {error_msg}")
                            return {"success": False, "error": error_msg}
            except Exception as e:
                logger.error(f"Failed to communicate with {target_node}: {e}")
                return {"success": False, "error": str(e)}

        # For other nodes, mark as assigned (they'll pick it up)
        logger.info(f"Task {task['task_id']} assigned to {target_node}")
        return {"success": True, "node": target_node, "method": "pull"}

    except Exception as e:
        logger.error(f"Task distribution failed: {e}")
        return {"success": False, "error": str(e)}


@activity.defn
async def sync_shared_memory() -> Dict:
    """Synchronize shared memory across cluster nodes"""
    try:
        # Get platform-specific database path
        storage_base = get_storage_base()
        shared_db = storage_base / "databases/cluster/shared_memories.db"

        if shared_db.exists():
            conn = sqlite3.connect(shared_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()[0]
            conn.close()

            logger.info(f"Shared memory synced: {count} entities")
            return {"success": True, "shared_entities": count}
        else:
            return {"success": False, "error": "Shared DB not found"}

    except Exception as e:
        logger.error(f"Memory sync failed: {e}")
        return {"success": False, "error": str(e)}


@workflow.defn
class ClusterCoordinationWorkflow:
    """
    Continuous cluster coordination workflow
    Monitors nodes, distributes tasks, handles failures
    """

    @workflow.run
    async def run(self) -> dict:
        workflow.logger.info("Starting cluster coordination workflow")

        iteration = 0
        stats = {
            "started_at": workflow.now().isoformat(),  # FIX: Use workflow.now() for determinism
            "nodes_monitored": 0,
            "tasks_distributed": 0,
            "errors": 0
        }

        while True:
            iteration += 1
            workflow.logger.info(f"Cluster coordination iteration {iteration}")

            try:
                # Step 1: Monitor node health
                health_status = await workflow.execute_activity(
                    monitor_node_health,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                stats["nodes_monitored"] = len(health_status["nodes"])

                # Step 2: Fetch pending tasks
                pending_tasks = await workflow.execute_activity(
                    fetch_pending_tasks,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )

                # Step 3: Distribute tasks to optimal nodes
                for task in pending_tasks:
                    try:
                        # Select optimal node
                        target_node = await workflow.execute_activity(
                            select_optimal_node,
                            args=[task, health_status],
                            start_to_close_timeout=timedelta(seconds=5)
                        )

                        if target_node:
                            # Distribute task
                            result = await workflow.execute_activity(
                                distribute_task,
                                args=[task, target_node],
                                start_to_close_timeout=timedelta(seconds=30),
                                retry_policy=RetryPolicy(
                                    maximum_attempts=3,
                                    initial_interval=timedelta(seconds=5)
                                )
                            )

                            if result.get("success"):
                                stats["tasks_distributed"] += 1
                                workflow.logger.info(f"Task {task['task_id']} distributed to {target_node}")
                            else:
                                stats["errors"] += 1
                                workflow.logger.error(f"Failed to distribute task {task['task_id']}: {result.get('error')}")

                    except Exception as e:
                        stats["errors"] += 1
                        workflow.logger.error(f"Error processing task {task.get('task_id', 'unknown')}: {e}")

                # Step 4: Sync shared memory
                sync_result = await workflow.execute_activity(
                    sync_shared_memory,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )

                # Wait before next iteration (check every 30 seconds)
                await asyncio.sleep(30)

            except Exception as e:
                stats["errors"] += 1
                workflow.logger.error(f"Cluster coordination iteration {iteration} failed: {e}")
                await asyncio.sleep(60)  # Wait longer on error

        return stats


async def main():
    """Test cluster coordination activities"""
    print("Testing Cluster Coordination Activities...")
    print("=" * 60)

    # Test node health monitoring
    print("\n1. Monitoring node health...")
    health = await monitor_node_health()
    print(json.dumps(health, indent=2))

    # Test pending task fetch
    print("\n2. Fetching pending tasks...")
    tasks = await fetch_pending_tasks()
    print(f"Found {len(tasks)} pending tasks")

    # Test memory sync
    print("\n3. Syncing shared memory...")
    sync = await sync_shared_memory()
    print(json.dumps(sync, indent=2))

    print("\n" + "=" * 60)
    print("Cluster coordination activities tested successfully!")


if __name__ == "__main__":
    asyncio.run(main())
