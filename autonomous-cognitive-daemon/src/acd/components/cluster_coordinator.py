"""Cluster Coordinator - Monitors and coordinates the agentic cluster."""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..utils.config import get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class ClusterCoordinator:
    """
    Coordinates the multi-node agentic cluster.

    Responsibilities:
    - Monitor health of all cluster nodes
    - Track resource availability (CPU, memory, GPU)
    - Route tasks to optimal nodes
    - Detect and report node failures
    - Sync cluster brain state
    """

    def __init__(self, config: dict):
        """Initialize Cluster Coordinator.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Get cluster configuration
        cluster_config = config.get("cluster", {})
        self.nodes = cluster_config.get("nodes", self._default_nodes())
        self.health_timeout = cluster_config.get("health_timeout_seconds", 10)

        # Track node status
        self._node_status: Dict[str, Dict[str, Any]] = {}
        self._last_health_check: Optional[datetime] = None

        logger.info(
            "cluster_coordinator_initialized",
            nodes=list(self.nodes.keys()),
        )

    def _default_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Return default cluster node configuration."""
        return {
            "mac-studio": {
                "host": "192.168.1.79",
                "role": "orchestrator",
                "capabilities": ["coordination", "research", "inference"],
            },
            "macpro51": {
                "host": "192.168.1.87",
                "role": "builder",
                "capabilities": ["computation", "docker", "compilation"],
            },
            "macbook-air": {
                "host": "192.168.1.55",
                "role": "researcher",
                "capabilities": ["research", "analysis"],
            },
            "completeu-server": {
                "host": "192.168.1.186",
                "role": "inference",
                "capabilities": ["gpu", "inference", "ollama"],
            },
        }

    async def check_health(self) -> Dict[str, Any]:
        """Check health of all cluster nodes.

        Returns:
            Health check report
        """
        logger.info("checking_cluster_health")

        report = {
            "checked_at": datetime.now().isoformat(),
            "nodes": {},
            "healthy_count": 0,
            "unhealthy_count": 0,
            "warnings": [],
        }

        # Check each node in parallel
        tasks = [
            self._check_node_health(node_id, node_config)
            for node_id, node_config in self.nodes.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for (node_id, _), result in zip(self.nodes.items(), results):
            if isinstance(result, Exception):
                report["nodes"][node_id] = {
                    "status": "error",
                    "error": str(result),
                }
                report["unhealthy_count"] += 1
            else:
                report["nodes"][node_id] = result
                if result.get("status") == "healthy":
                    report["healthy_count"] += 1
                else:
                    report["unhealthy_count"] += 1

                # Check for warnings
                if result.get("cpu_percent", 0) > 80:
                    report["warnings"].append(f"{node_id}: High CPU usage ({result['cpu_percent']}%)")
                if result.get("memory_percent", 0) > 85:
                    report["warnings"].append(f"{node_id}: High memory usage ({result['memory_percent']}%)")

        # Update internal state
        self._node_status = report["nodes"]
        self._last_health_check = datetime.now()

        logger.info(
            "cluster_health_checked",
            healthy=report["healthy_count"],
            unhealthy=report["unhealthy_count"],
            warnings=len(report["warnings"]),
        )

        return report

    async def _check_node_health(
        self, node_id: str, node_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check health of a single node.

        Args:
            node_id: Node identifier
            node_config: Node configuration

        Returns:
            Node health status
        """
        host = node_config.get("host", "localhost")

        try:
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                # Try hardware-broadcast API if available
                try:
                    response = await client.get(f"http://{host}:8888/api/all")
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "status": "healthy",
                            "host": host,
                            "role": node_config.get("role"),
                            "cpu_percent": data.get("cpu", {}).get("percent", 0),
                            "memory_percent": data.get("memory", {}).get("percent", 0),
                            "load_average": data.get("cpu", {}).get("load_avg", [0, 0, 0])[0],
                            "checked_at": datetime.now().isoformat(),
                        }
                except Exception:
                    pass

                # Fallback: simple connectivity check
                # Try SSH port
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(host, 22),
                        timeout=5.0,
                    )
                    writer.close()
                    await writer.wait_closed()
                    return {
                        "status": "reachable",
                        "host": host,
                        "role": node_config.get("role"),
                        "note": "SSH reachable but no metrics API",
                        "checked_at": datetime.now().isoformat(),
                    }
                except Exception:
                    pass

                return {
                    "status": "unreachable",
                    "host": host,
                    "role": node_config.get("role"),
                    "checked_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.warning("node_health_check_failed", node_id=node_id, error=str(e))
            return {
                "status": "error",
                "host": host,
                "error": str(e),
            }

    async def get_optimal_node(
        self, task_type: str, requirements: Optional[List[str]] = None
    ) -> Optional[str]:
        """Get the optimal node for a task.

        Args:
            task_type: Type of task (build, test, inference, research)
            requirements: Required capabilities

        Returns:
            Node ID or None if no suitable node
        """
        requirements = requirements or []

        # Ensure we have recent health data
        if not self._node_status or not self._last_health_check:
            await self.check_health()

        best_node = None
        best_score = -1

        for node_id, node_config in self.nodes.items():
            status = self._node_status.get(node_id, {})

            # Skip unhealthy nodes
            if status.get("status") not in ("healthy", "reachable"):
                continue

            # Check capability requirements
            capabilities = node_config.get("capabilities", [])
            if requirements and not all(req in capabilities for req in requirements):
                continue

            # Score based on task type affinity and current load
            score = self._score_node_for_task(
                node_id, node_config, status, task_type
            )

            if score > best_score:
                best_score = score
                best_node = node_id

        logger.debug(
            "optimal_node_selected",
            task_type=task_type,
            selected=best_node,
            score=best_score,
        )

        return best_node

    def _score_node_for_task(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        status: Dict[str, Any],
        task_type: str,
    ) -> float:
        """Score a node for a specific task type.

        Args:
            node_id: Node identifier
            node_config: Node configuration
            status: Current node status
            task_type: Type of task

        Returns:
            Score (higher is better)
        """
        score = 50.0  # Base score

        role = node_config.get("role", "")
        capabilities = node_config.get("capabilities", [])

        # Role affinity bonuses
        role_affinity = {
            "build": {"builder": 30, "inference": 10},
            "test": {"builder": 20, "orchestrator": 15},
            "inference": {"inference": 40, "builder": 5},
            "research": {"researcher": 30, "orchestrator": 20},
            "coordination": {"orchestrator": 40},
        }

        if task_type in role_affinity:
            score += role_affinity[task_type].get(role, 0)

        # Capability bonuses
        if "gpu" in capabilities and task_type in ("inference", "training"):
            score += 30
        if "docker" in capabilities and task_type == "build":
            score += 15

        # Load penalty
        cpu_percent = status.get("cpu_percent", 50)
        memory_percent = status.get("memory_percent", 50)
        load_penalty = (cpu_percent + memory_percent) / 4  # Max 50 penalty
        score -= load_penalty

        return max(0, score)

    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Get a summary of cluster status.

        Returns:
            Cluster summary
        """
        # Ensure we have recent data
        if not self._node_status:
            await self.check_health()

        healthy = sum(
            1 for s in self._node_status.values()
            if s.get("status") in ("healthy", "reachable")
        )

        total_cpu = sum(
            s.get("cpu_percent", 0) for s in self._node_status.values()
        )
        total_mem = sum(
            s.get("memory_percent", 0) for s in self._node_status.values()
        )
        node_count = len(self._node_status) or 1

        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": healthy,
            "average_cpu_percent": total_cpu / node_count,
            "average_memory_percent": total_mem / node_count,
            "last_check": self._last_health_check.isoformat() if self._last_health_check else None,
            "nodes": {
                node_id: {
                    "role": self.nodes.get(node_id, {}).get("role"),
                    "status": status.get("status"),
                    "cpu": status.get("cpu_percent"),
                    "memory": status.get("memory_percent"),
                }
                for node_id, status in self._node_status.items()
            },
        }

    async def broadcast_to_cluster(
        self, message: str, message_type: str = "notification"
    ) -> Dict[str, Any]:
        """Broadcast a message to all cluster nodes.

        Args:
            message: Message content
            message_type: Type of message

        Returns:
            Broadcast results
        """
        logger.info("broadcasting_to_cluster", message_type=message_type)

        results = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            for node_id, node_config in self.nodes.items():
                host = node_config.get("host")

                try:
                    # Try node-chat MCP endpoint if available
                    response = await client.post(
                        f"http://{host}:8765/broadcast",
                        json={"message": message, "type": message_type},
                    )
                    results[node_id] = {
                        "status": "sent",
                        "response_code": response.status_code,
                    }
                except Exception as e:
                    results[node_id] = {
                        "status": "failed",
                        "error": str(e),
                    }

        return {
            "broadcast_at": datetime.now().isoformat(),
            "message_type": message_type,
            "results": results,
        }
