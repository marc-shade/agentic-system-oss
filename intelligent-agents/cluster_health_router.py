#!/usr/bin/env python3
"""
Cluster Health-Based Task Router
=================================

Integration layer between cluster health monitor and task execution.
Routes tasks to optimal nodes based on real-time health metrics.

Features:
- Health-aware task routing
- Automatic failover on node failure
- Load balancing across healthy nodes
- Capability-based node selection
- Task queue integration
- Performance optimization

Integrates with:
- cluster_health_monitor.py - Health data source
- cluster-execution-mcp - Task execution
- agent-runtime-mcp - Task queue
- node-chat-mcp - Node coordination
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from cluster_health_monitor import ClusterHealthMonitor, NodeStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('health-router')


@dataclass
class TaskRequirements:
    """Task execution requirements"""
    required_capabilities: List[str]
    estimated_cpu_percent: float = 10.0
    estimated_memory_gb: float = 1.0
    estimated_duration_seconds: int = 60
    priority: str = "medium"  # low, medium, high, critical
    can_retry: bool = True
    max_retries: int = 3


class ClusterHealthRouter:
    """
    Health-aware task router for distributed cluster execution.

    Routes tasks to optimal nodes based on:
    - Real-time health metrics
    - Node capabilities
    - Current load
    - Historical performance
    - SLA requirements
    """

    def __init__(self, health_monitor: ClusterHealthMonitor):
        """
        Initialize health router.

        Args:
            health_monitor: Cluster health monitor instance
        """
        self.health_monitor = health_monitor

        # Routing statistics
        self.routing_stats = {
            "total_routes": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "failover_routes": 0,
            "node_usage": {}
        }

        # Task history for performance tracking
        self.task_history = []
        self.task_history_file = Path("/mnt/agentic-system/databases/task_routing_history.json")

        logger.info("Cluster Health Router initialized")

    async def route_task(
        self,
        task_description: str,
        requirements: TaskRequirements,
        preferred_node: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route a task to the optimal node based on health and requirements.

        Args:
            task_description: Task description
            requirements: Task execution requirements
            preferred_node: Optional preferred node (will use if healthy)

        Returns:
            Routing decision with node selection and rationale
        """
        self.routing_stats["total_routes"] += 1

        routing_decision = {
            "task_description": task_description,
            "timestamp": datetime.now().isoformat(),
            "requirements": requirements.__dict__,
            "preferred_node": preferred_node,
            "selected_node": None,
            "routing_rationale": [],
            "success": False,
            "fallback_nodes": []
        }

        try:
            # 1. Check if preferred node is healthy and capable
            if preferred_node and self._is_node_suitable(preferred_node, requirements):
                health = self.health_monitor.get_node_health(preferred_node)
                if health and health.status in [NodeStatus.HEALTHY, NodeStatus.DEGRADED]:
                    routing_decision["selected_node"] = preferred_node
                    routing_decision["routing_rationale"].append(
                        f"Using preferred node {preferred_node} (health: {health.status.value})"
                    )
                    routing_decision["success"] = True
                    self.routing_stats["successful_routes"] += 1
                    await self._record_routing(routing_decision)
                    return routing_decision

            # 2. Find all eligible nodes
            eligible_nodes = self._find_eligible_nodes(requirements)

            if not eligible_nodes:
                routing_decision["routing_rationale"].append("No eligible nodes found")
                routing_decision["success"] = False
                self.routing_stats["failed_routes"] += 1
                await self._record_routing(routing_decision)
                return routing_decision

            # 3. Rank nodes by health score and availability
            ranked_nodes = self._rank_nodes(eligible_nodes, requirements)

            routing_decision["fallback_nodes"] = [node[0] for node in ranked_nodes[1:]]

            # 4. Select best node
            best_node, score = ranked_nodes[0]
            routing_decision["selected_node"] = best_node
            routing_decision["node_health_score"] = score
            routing_decision["success"] = True
            self.routing_stats["successful_routes"] += 1

            # 5. Build routing rationale
            health = self.health_monitor.get_node_health(best_node)
            routing_decision["routing_rationale"].extend([
                f"Selected {best_node} with health score {score:.2f}",
                f"Status: {health.status.value}",
                f"CPU: {health.cpu_percent:.1f}%, Memory: {health.memory_percent:.1f}%",
                f"Load: {health.load_avg_1m:.2f}, Available capacity: {health.max_task_capacity - health.current_task_count}",
                f"Fallback options: {len(routing_decision['fallback_nodes'])}"
            ])

            # 6. Update node usage stats
            if best_node not in self.routing_stats["node_usage"]:
                self.routing_stats["node_usage"][best_node] = 0
            self.routing_stats["node_usage"][best_node] += 1

            logger.info(
                f"Routed task to {best_node} (score: {score:.2f}, "
                f"status: {health.status.value})"
            )

        except Exception as e:
            logger.error(f"Error routing task: {e}", exc_info=True)
            routing_decision["routing_rationale"].append(f"Routing error: {e}")
            routing_decision["success"] = False
            self.routing_stats["failed_routes"] += 1

        await self._record_routing(routing_decision)
        return routing_decision

    def _is_node_suitable(self, node_id: str, requirements: TaskRequirements) -> bool:
        """
        Check if a node is suitable for task requirements.

        Args:
            node_id: Node identifier
            requirements: Task requirements

        Returns:
            True if node is suitable
        """
        health = self.health_monitor.get_node_health(node_id)

        if not health:
            return False

        # Check capabilities
        if requirements.required_capabilities:
            if not any(cap in health.capabilities for cap in requirements.required_capabilities):
                return False

        # Check capacity
        if health.current_task_count >= health.max_task_capacity:
            return False

        return True

    def _find_eligible_nodes(self, requirements: TaskRequirements) -> List[str]:
        """
        Find all eligible nodes for task requirements.

        Args:
            requirements: Task requirements

        Returns:
            List of eligible node IDs
        """
        eligible = []

        for node_id, health in self.health_monitor.node_health.items():
            # Must be at least degraded
            if health.status not in [NodeStatus.HEALTHY, NodeStatus.DEGRADED]:
                continue

            # Check capabilities
            if requirements.required_capabilities:
                if not any(cap in health.capabilities for cap in requirements.required_capabilities):
                    continue

            # Check capacity
            if health.current_task_count >= health.max_task_capacity:
                continue

            # Check resource availability
            available_cpu = 100 - health.cpu_percent
            available_memory_gb = (100 - health.memory_percent) / 100 * (
                health.max_task_capacity * 2  # Assume 2GB per task capacity
            )

            if available_cpu < requirements.estimated_cpu_percent:
                continue

            if available_memory_gb < requirements.estimated_memory_gb:
                continue

            eligible.append(node_id)

        return eligible

    def _rank_nodes(
        self,
        eligible_nodes: List[str],
        requirements: TaskRequirements
    ) -> List[tuple[str, float]]:
        """
        Rank eligible nodes by suitability score.

        Scoring factors:
        - Health score (40%)
        - Available capacity (30%)
        - Load average (20%)
        - Historical performance (10%)

        Args:
            eligible_nodes: List of eligible node IDs
            requirements: Task requirements

        Returns:
            List of (node_id, score) tuples, sorted by score descending
        """
        scores = []

        for node_id in eligible_nodes:
            health = self.health_monitor.get_node_health(node_id)

            # Health score (40%)
            health_component = health.health_score * 0.40

            # Available capacity (30%)
            capacity_ratio = (health.max_task_capacity - health.current_task_count) / health.max_task_capacity
            capacity_component = capacity_ratio * 0.30

            # Load average (20%)
            load_score = max(0.0, 1.0 - (health.load_avg_1m / 20.0))  # Normalize to 0-1
            load_component = load_score * 0.20

            # Historical performance (10%)
            # TODO: Track historical task performance per node
            history_component = 0.10

            # Total score
            total_score = health_component + capacity_component + load_component + history_component

            scores.append((node_id, total_score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores

    async def handle_task_failure(
        self,
        task_description: str,
        failed_node: str,
        requirements: TaskRequirements,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Handle task failure with automatic failover.

        Args:
            task_description: Task description
            failed_node: Node that failed
            requirements: Task requirements
            retry_count: Current retry attempt

        Returns:
            Failover routing decision
        """
        logger.warning(f"Task failed on {failed_node}, attempting failover (retry {retry_count})")

        self.routing_stats["failover_routes"] += 1

        # Route to different node
        failover_decision = await self.route_task(
            task_description=task_description,
            requirements=requirements,
            preferred_node=None  # Don't use failed node
        )

        failover_decision["is_failover"] = True
        failover_decision["failed_node"] = failed_node
        failover_decision["retry_count"] = retry_count

        return failover_decision

    async def _record_routing(self, routing_decision: Dict):
        """Record routing decision to history"""
        self.task_history.append(routing_decision)

        # Keep last 1000 entries
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]

        # Save periodically
        if len(self.task_history) % 100 == 0:
            await self._save_routing_history()

    async def _save_routing_history(self):
        """Save routing history to disk"""
        try:
            with open(self.task_history_file, 'w') as f:
                json.dump(self.task_history[-100:], f, indent=2)
            logger.debug(f"Routing history saved: {len(self.task_history)} entries")
        except Exception as e:
            logger.error(f"Failed to save routing history: {e}")

    def get_routing_statistics(self) -> Dict:
        """Get routing statistics"""
        success_rate = 0.0
        if self.routing_stats["total_routes"] > 0:
            success_rate = self.routing_stats["successful_routes"] / self.routing_stats["total_routes"]

        return {
            "total_routes": self.routing_stats["total_routes"],
            "successful_routes": self.routing_stats["successful_routes"],
            "failed_routes": self.routing_stats["failed_routes"],
            "failover_routes": self.routing_stats["failover_routes"],
            "success_rate": success_rate,
            "node_usage": self.routing_stats["node_usage"]
        }

    async def optimize_cluster_load(self):
        """
        Analyze current cluster load and suggest optimizations.

        Returns:
            Optimization recommendations
        """
        recommendations = []

        # Get cluster health
        cluster_health = self.health_monitor.get_cluster_health_summary()

        # Check for overloaded nodes
        for node_id, health in self.health_monitor.node_health.items():
            if health.status == NodeStatus.CRITICAL:
                recommendations.append({
                    "type": "critical_node",
                    "node": node_id,
                    "message": f"Node {node_id} is critical - consider task migration",
                    "action": "migrate_tasks",
                    "details": {
                        "cpu": health.cpu_percent,
                        "memory": health.memory_percent,
                        "load": health.load_avg_1m
                    }
                })

        # Check for underutilized nodes
        for node_id, health in self.health_monitor.node_health.items():
            if (health.status == NodeStatus.HEALTHY and
                health.cpu_percent < 20 and
                health.current_task_count < health.max_task_capacity * 0.3):

                recommendations.append({
                    "type": "underutilized_node",
                    "node": node_id,
                    "message": f"Node {node_id} is underutilized - can accept more tasks",
                    "action": "increase_load",
                    "details": {
                        "cpu": health.cpu_percent,
                        "current_tasks": health.current_task_count,
                        "capacity": health.max_task_capacity
                    }
                })

        # Check cluster SLA
        if not cluster_health["meeting_sla"]:
            recommendations.append({
                "type": "sla_breach",
                "message": f"Cluster availability {cluster_health['availability_percent']:.1f}% below SLA target",
                "action": "investigate_failures",
                "details": cluster_health
            })

        return {
            "timestamp": datetime.now().isoformat(),
            "cluster_health": cluster_health,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations)
        }


async def demo_health_routing():
    """Demo the health-based task router"""
    print("=" * 60)
    print("CLUSTER HEALTH-BASED TASK ROUTING DEMO")
    print("=" * 60)

    # Initialize health monitor
    monitor = ClusterHealthMonitor(heartbeat_interval=10)

    # Run one health check cycle
    await monitor.run_heartbeat_cycle()

    # Initialize router
    router = ClusterHealthRouter(monitor)

    # Example task requirements
    requirements = TaskRequirements(
        required_capabilities=["compilation", "testing"],
        estimated_cpu_percent=25.0,
        estimated_memory_gb=2.0,
        estimated_duration_seconds=120,
        priority="high"
    )

    # Route a task
    print("\n--- Routing Task ---")
    decision = await router.route_task(
        task_description="Build and test Rust project",
        requirements=requirements
    )

    print(f"\nSelected Node: {decision['selected_node']}")
    print(f"Success: {decision['success']}")
    print(f"\nRationale:")
    for line in decision['routing_rationale']:
        print(f"  • {line}")

    # Get optimization recommendations
    print("\n--- Cluster Optimization ---")
    optimizations = await router.optimize_cluster_load()

    print(f"Total Recommendations: {optimizations['total_recommendations']}")
    for rec in optimizations['recommendations']:
        print(f"\n  Type: {rec['type']}")
        print(f"  Message: {rec['message']}")
        print(f"  Action: {rec['action']}")

    # Show routing stats
    print("\n--- Routing Statistics ---")
    stats = router.get_routing_statistics()
    print(f"Total Routes: {stats['total_routes']}")
    print(f"Success Rate: {stats['success_rate']:.1%}")
    print(f"Failovers: {stats['failover_routes']}")


if __name__ == "__main__":
    asyncio.run(demo_health_routing())
