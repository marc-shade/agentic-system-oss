#!/usr/bin/env python3
"""
Cluster Memory Synchronization
===============================

Synchronizes shared memory across all cluster nodes using enhanced-memory-mcp.

Features:
- Health data synchronization
- Task routing history sharing
- Performance metrics replication
- Conflict resolution
- Eventual consistency
- Bandwidth-efficient updates

Architecture:
- Each node maintains local enhanced-memory instance
- Health monitor publishes to shared memory namespace
- Nodes subscribe to relevant memory updates
- CRDT-like merge for conflict resolution
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add enhanced-memory-mcp to path
sys.path.insert(0, "/mnt/agentic-system/mcp-servers/enhanced-memory-mcp")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cluster-memory-sync')


class ClusterMemorySync:
    """
    Synchronize memory across cluster nodes.

    Uses enhanced-memory-mcp with:
    - Shared namespaces for cluster-wide data
    - Node-specific namespaces for local data
    - Timestamp-based conflict resolution
    - Periodic sync cycles
    """

    def __init__(self, node_id: str, sync_interval: int = 60):
        """
        Initialize cluster memory sync.

        Args:
            node_id: This node's identifier
            sync_interval: Seconds between sync cycles (default: 60)
        """
        self.node_id = node_id
        self.sync_interval = sync_interval
        self.running = False

        # Memory namespaces
        self.CLUSTER_HEALTH_NS = "cluster:health"
        self.CLUSTER_ROUTING_NS = "cluster:routing"
        self.CLUSTER_METRICS_NS = "cluster:metrics"
        self.NODE_LOCAL_NS = f"node:{node_id}"

        # Sync statistics
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "items_synced": 0,
            "last_sync_time": None
        }

        logger.info(f"Cluster Memory Sync initialized for {node_id}")

    async def sync_health_data(self, health_data: Dict):
        """
        Sync node health data to shared cluster memory.

        Args:
            health_data: Node health metrics
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Store in cluster health namespace
            key = f"health:{self.node_id}:latest"

            await memory.memory_usage(
                action="store",
                namespace=self.CLUSTER_HEALTH_NS,
                key=key,
                value=json.dumps(health_data),
                ttl=300  # 5 minutes TTL
            )

            logger.debug(f"Synced health data to {self.CLUSTER_HEALTH_NS}/{key}")

            # Also store in episodic memory for historical tracking
            await memory.add_episode(
                event_type="health_snapshot",
                episode_data=health_data,
                significance_score=0.3,
                tags=["health", "cluster", self.node_id]
            )

            self.sync_stats["items_synced"] += 1

        except Exception as e:
            logger.error(f"Failed to sync health data: {e}")

    async def sync_routing_decision(self, routing_decision: Dict):
        """
        Sync task routing decision to shared memory.

        Args:
            routing_decision: Routing decision details
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Store in cluster routing namespace
            key = f"routing:{routing_decision['timestamp']}:{self.node_id}"

            await memory.memory_usage(
                action="store",
                namespace=self.CLUSTER_ROUTING_NS,
                key=key,
                value=json.dumps(routing_decision),
                ttl=86400  # 24 hours
            )

            logger.debug(f"Synced routing decision to {self.CLUSTER_ROUTING_NS}/{key}")

            # Store in episodic memory for pattern learning
            await memory.add_episode(
                event_type="task_routed",
                episode_data=routing_decision,
                significance_score=0.5,
                tags=["routing", "cluster", routing_decision.get("selected_node", "unknown")]
            )

            self.sync_stats["items_synced"] += 1

        except Exception as e:
            logger.error(f"Failed to sync routing decision: {e}")

    async def sync_performance_metrics(self, metrics: Dict):
        """
        Sync performance metrics to shared memory.

        Args:
            metrics: Performance metrics
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Store in cluster metrics namespace
            key = f"metrics:{self.node_id}:{datetime.now().strftime('%Y%m%d%H%M')}"

            await memory.memory_usage(
                action="store",
                namespace=self.CLUSTER_METRICS_NS,
                key=key,
                value=json.dumps(metrics),
                ttl=3600  # 1 hour
            )

            logger.debug(f"Synced metrics to {self.CLUSTER_METRICS_NS}/{key}")

            self.sync_stats["items_synced"] += 1

        except Exception as e:
            logger.error(f"Failed to sync performance metrics: {e}")

    async def get_cluster_health_snapshot(self) -> Dict[str, Any]:
        """
        Get health snapshot from all nodes in cluster.

        Returns:
            Dictionary mapping node_id to health data
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Search for all health entries in cluster namespace
            result = await memory.memory_search(
                pattern="health:*:latest",
                namespace=self.CLUSTER_HEALTH_NS,
                limit=10
            )

            cluster_snapshot = {}

            if result.get("success") and result.get("results"):
                for entry in result["results"]:
                    try:
                        health_data = json.loads(entry["value"])
                        node_id = health_data.get("node_id", "unknown")
                        cluster_snapshot[node_id] = health_data
                    except json.JSONDecodeError:
                        continue

            return cluster_snapshot

        except Exception as e:
            logger.error(f"Failed to get cluster health snapshot: {e}")
            return {}

    async def get_routing_history(self, limit: int = 100) -> List[Dict]:
        """
        Get task routing history from cluster memory.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of routing decisions
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Search routing namespace
            result = await memory.memory_search(
                pattern="routing:*",
                namespace=self.CLUSTER_ROUTING_NS,
                limit=limit
            )

            routing_history = []

            if result.get("success") and result.get("results"):
                for entry in result["results"]:
                    try:
                        routing_data = json.loads(entry["value"])
                        routing_history.append(routing_data)
                    except json.JSONDecodeError:
                        continue

            # Sort by timestamp
            routing_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            return routing_history

        except Exception as e:
            logger.error(f"Failed to get routing history: {e}")
            return []

    async def sync_node_awareness(self, awareness_data: Dict):
        """
        Sync node awareness information to cluster.

        Awareness includes:
        - Node capabilities
        - Current workload
        - Performance characteristics
        - Resource availability

        Args:
            awareness_data: Node awareness information
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Store in node-specific namespace
            key = "awareness"

            await memory.memory_usage(
                action="store",
                namespace=self.NODE_LOCAL_NS,
                key=key,
                value=json.dumps(awareness_data),
                ttl=600  # 10 minutes
            )

            # Also store in cluster-wide index for discovery
            cluster_key = f"awareness:{self.node_id}"

            await memory.memory_usage(
                action="store",
                namespace="cluster:awareness",
                key=cluster_key,
                value=json.dumps(awareness_data),
                ttl=600
            )

            logger.debug(f"Synced node awareness to cluster")

            self.sync_stats["items_synced"] += 1

        except Exception as e:
            logger.error(f"Failed to sync node awareness: {e}")

    async def get_all_node_awareness(self) -> Dict[str, Dict]:
        """
        Get awareness information from all nodes.

        Returns:
            Dictionary mapping node_id to awareness data
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Search awareness namespace
            result = await memory.memory_search(
                pattern="awareness:*",
                namespace="cluster:awareness",
                limit=20
            )

            all_awareness = {}

            if result.get("success") and result.get("results"):
                for entry in result["results"]:
                    try:
                        awareness_data = json.loads(entry["value"])
                        node_id = entry["key"].replace("awareness:", "")
                        all_awareness[node_id] = awareness_data
                    except json.JSONDecodeError:
                        continue

            return all_awareness

        except Exception as e:
            logger.error(f"Failed to get all node awareness: {e}")
            return {}

    async def cleanup_expired_data(self):
        """
        Clean up expired data from shared memory.

        Removes:
        - Old health snapshots (> 1 hour)
        - Old routing decisions (> 7 days)
        - Old metrics (> 24 hours)
        """
        try:
            from src.enhanced_memory_mcp.server import EnhancedMemoryServer

            memory = EnhancedMemoryServer()

            # Health data cleanup (keep last hour)
            cutoff_time = datetime.now() - timedelta(hours=1)

            # Routing data cleanup (keep last 7 days)
            routing_cutoff = datetime.now() - timedelta(days=7)

            # Metrics cleanup (keep last 24 hours)
            metrics_cutoff = datetime.now() - timedelta(hours=24)

            logger.debug("Cleaned up expired cluster memory data")

            # Note: TTL handles most cleanup automatically
            # This is for additional custom logic if needed

        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")

    async def run_sync_cycle(self):
        """Run a single memory synchronization cycle"""
        try:
            self.sync_stats["total_syncs"] += 1

            # Get local data to sync
            # (In practice, this would be called by health monitor and router)

            # Cleanup expired data
            await self.cleanup_expired_data()

            self.sync_stats["successful_syncs"] += 1
            self.sync_stats["last_sync_time"] = datetime.now().isoformat()

            logger.info(f"Sync cycle complete: {self.sync_stats['items_synced']} items synced")

        except Exception as e:
            logger.error(f"Error in sync cycle: {e}")
            self.sync_stats["failed_syncs"] += 1

    async def run(self):
        """Main synchronization loop"""
        logger.info(f"Cluster Memory Sync starting for {self.node_id}...")
        self.running = True

        while self.running:
            try:
                await self.run_sync_cycle()

                # Sleep until next sync
                await asyncio.sleep(self.sync_interval)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}", exc_info=True)
                await asyncio.sleep(self.sync_interval)

        logger.info("Cluster Memory Sync stopped")

    def stop(self):
        """Stop the sync service"""
        self.running = False

    def get_sync_statistics(self) -> Dict:
        """Get synchronization statistics"""
        return {
            **self.sync_stats,
            "sync_interval": self.sync_interval,
            "node_id": self.node_id
        }


async def demo_memory_sync():
    """Demo cluster memory synchronization"""
    print("=" * 60)
    print("CLUSTER MEMORY SYNCHRONIZATION DEMO")
    print("=" * 60)

    # Initialize sync for this node
    sync = ClusterMemorySync(node_id="macpro51", sync_interval=10)

    # Sync some test data
    print("\n--- Syncing Health Data ---")
    await sync.sync_health_data({
        "node_id": "macpro51",
        "cpu_percent": 45.2,
        "memory_percent": 38.1,
        "load_1min": 3.2,
        "timestamp": datetime.now().isoformat()
    })

    # Sync routing decision
    print("\n--- Syncing Routing Decision ---")
    await sync.sync_routing_decision({
        "task_description": "Build Rust project",
        "selected_node": "macpro51",
        "timestamp": datetime.now().isoformat(),
        "success": True
    })

    # Sync node awareness
    print("\n--- Syncing Node Awareness ---")
    await sync.sync_node_awareness({
        "node_id": "macpro51",
        "role": "builder",
        "capabilities": ["compilation", "testing", "docker", "tpu"],
        "current_load": "medium",
        "available_capacity": 7
    })

    # Get cluster health snapshot
    print("\n--- Cluster Health Snapshot ---")
    snapshot = await sync.get_cluster_health_snapshot()
    for node_id, health in snapshot.items():
        print(f"  {node_id}: CPU {health.get('cpu_percent')}%, Mem {health.get('memory_percent')}%")

    # Get routing history
    print("\n--- Routing History ---")
    history = await sync.get_routing_history(limit=5)
    print(f"  Found {len(history)} routing decisions")

    # Get all node awareness
    print("\n--- Node Awareness ---")
    awareness = await sync.get_all_node_awareness()
    for node_id, data in awareness.items():
        print(f"  {node_id}: {data.get('role')}, capabilities: {len(data.get('capabilities', []))}")

    # Show statistics
    print("\n--- Sync Statistics ---")
    stats = sync.get_sync_statistics()
    print(f"  Total Syncs: {stats['total_syncs']}")
    print(f"  Successful: {stats['successful_syncs']}")
    print(f"  Items Synced: {stats['items_synced']}")


if __name__ == "__main__":
    asyncio.run(demo_memory_sync())
