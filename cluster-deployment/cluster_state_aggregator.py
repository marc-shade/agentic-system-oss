#!/usr/bin/env python3
"""
Cluster State Aggregator - Unified View Across All Nodes

Queries all nodes' comprehensive_state.db databases and aggregates
into a single unified cluster view.

This enables:
- Multi-AI agents to see the complete cluster (all nodes)
- Cross-node service discovery
- Cluster-wide software inventory
- Complete network topology

Architecture:
- Each node maintains its own local comprehensive_state.db
- Aggregator queries all nodes via SSH
- Results merged into unified cluster state
- Used by Claude, Codex, Gemini agents for cluster-wide decisions

Usage:
    from cluster_state_aggregator import ClusterStateAggregator

    aggregator = ClusterStateAggregator()
    complete_cluster = aggregator.get_unified_cluster_state()

    # Now you have ALL nodes' state in one dict
    print(f"Total nodes: {len(complete_cluster['nodes'])}")
"""

import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClusterStateAggregator:
    """Aggregates comprehensive cluster state from all nodes"""

    def __init__(self):
        """Initialize aggregator with known nodes"""
        # Known nodes and their IPs
        self.known_nodes = {
            "macpro51": {
                "ip": "192.168.1.183",  # Updated from 192.168.1.154 (DHCP changed)
                "user": "marc",
                "db_path": "/mnt/agentic-system/databases/cluster/comprehensive_state.db"
            },
            "mac-studio": {
                "ip": "192.168.1.157",
                "user": "marc",
                "db_path": "~/agentic-system/databases/cluster/comprehensive_state.db"
            },
            "macbook-air": {
                "ip": "192.168.1.76",
                "user": "marc",
                "db_path": "~/agentic-system/databases/cluster/comprehensive_state.db"
            },
            "completeu-server": {
                "ip": "192.168.1.186",
                "user": "marc",
                "db_path": "~/agentic-system/databases/cluster/comprehensive_state.db"
            }
        }

    def _query_remote_node(self, node_id: str, node_info: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Query a remote node's comprehensive_state.db via SSH

        Args:
            node_id: Node identifier
            node_info: Dict with 'ip', 'user', 'db_path'

        Returns:
            Dict with node's complete state, or None if unreachable
        """
        try:
            # SQL query to get complete node state (schema-tolerant)
            # Try with memory_total_gb first, fall back to older schema
            query = """
            SELECT
                n.node_id,
                n.role,
                n.hostname,
                n.os_type,
                n.architecture,
                n.cpu_count,
                n.python_version
            FROM nodes n
            WHERE n.node_id = (SELECT node_id FROM nodes LIMIT 1);
            """

            # Execute remote query via SSH
            cmd = [
                "ssh",
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                f"{node_info['user']}@{node_info['ip']}",
                f"sqlite3 {node_info['db_path']} \"{query}\""
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                logger.warning(f"Failed to query {node_id}: {result.stderr}")
                return None

            # Parse result (pipe-separated values)
            if not result.stdout.strip():
                logger.warning(f"No data returned from {node_id}")
                return None

            values = result.stdout.strip().split('|')
            if len(values) < 7:
                logger.warning(f"Incomplete data from {node_id}: got {len(values)} values")
                return None

            node_data = {
                "node_id": values[0],
                "role": values[1],
                "hostname": values[2],
                "os_type": values[3],
                "architecture": values[4],
                "cpu_count": int(values[5]) if values[5] else 0,
                "python_version": values[6],
                "memory_total_gb": 0.0  # Not available in older schemas
            }

            # Get services count
            services_query = f"SELECT COUNT(*) FROM service_endpoints WHERE node_id = '{node_data['node_id']}';"
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 f"{node_info['user']}@{node_info['ip']}",
                 f"sqlite3 {node_info['db_path']} \"{services_query}\""],
                capture_output=True, text=True, timeout=10
            )
            node_data["services_count"] = int(result.stdout.strip()) if result.returncode == 0 else 0

            # Get software count
            software_query = f"SELECT COUNT(*) FROM installed_software WHERE node_id = '{node_data['node_id']}';"
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 f"{node_info['user']}@{node_info['ip']}",
                 f"sqlite3 {node_info['db_path']} \"{software_query}\""],
                capture_output=True, text=True, timeout=10
            )
            node_data["software_count"] = int(result.stdout.strip()) if result.returncode == 0 else 0

            # Get network interfaces count
            interfaces_query = f"SELECT COUNT(*) FROM network_interfaces WHERE node_id = '{node_data['node_id']}';"
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 f"{node_info['user']}@{node_info['ip']}",
                 f"sqlite3 {node_info['db_path']} \"{interfaces_query}\""],
                capture_output=True, text=True, timeout=10
            )
            node_data["interfaces_count"] = int(result.stdout.strip()) if result.returncode == 0 else 0

            logger.info(f"✓ Retrieved state from {node_id}")
            return node_data

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout querying {node_id}")
            return None
        except Exception as e:
            logger.warning(f"Error querying {node_id}: {e}")
            return None

    def _query_local_node(self) -> Optional[Dict[str, Any]]:
        """
        Query local comprehensive_state.db directly

        Returns:
            Dict with local node's complete state
        """
        try:
            # Try multiple possible database locations
            db_paths = [
                Path("/mnt/agentic-system/databases/cluster/comprehensive_state.db"),
                Path.home() / "agentic-system/databases/cluster/comprehensive_state.db",
                Path("/home/marc/agentic-system/databases/cluster/comprehensive_state.db")
            ]

            db_path = None
            for path in db_paths:
                if path.exists():
                    db_path = path
                    break

            if not db_path:
                logger.warning("Local comprehensive_state.db not found")
                return None

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get node info
                node_row = conn.execute("SELECT * FROM nodes LIMIT 1").fetchone()
                if not node_row:
                    return None

                node_data = dict(node_row)

                # Get counts
                node_id = node_data['node_id']
                services_count = conn.execute(
                    "SELECT COUNT(*) FROM service_endpoints WHERE node_id = ?", (node_id,)
                ).fetchone()[0]

                software_count = conn.execute(
                    "SELECT COUNT(*) FROM installed_software WHERE node_id = ?", (node_id,)
                ).fetchone()[0]

                interfaces_count = conn.execute(
                    "SELECT COUNT(*) FROM network_interfaces WHERE node_id = ?", (node_id,)
                ).fetchone()[0]

                node_data["services_count"] = services_count
                node_data["software_count"] = software_count
                node_data["interfaces_count"] = interfaces_count

                logger.info(f"✓ Retrieved local state for {node_id}")
                return node_data

        except Exception as e:
            logger.warning(f"Error querying local node: {e}")
            return None

    def get_unified_cluster_state(self) -> Dict[str, Any]:
        """
        Get unified cluster state from all nodes

        Returns:
            Dict with complete cluster state:
            {
                "nodes": {
                    "node_id": {node_data},
                    ...
                },
                "summary": {
                    "total_nodes": int,
                    "total_services": int,
                    "total_packages": int,
                    "reachable_nodes": int,
                    "unreachable_nodes": int
                }
            }
        """
        unified_state = {
            "nodes": {},
            "summary": {
                "total_nodes": 0,
                "total_services": 0,
                "total_packages": 0,
                "total_interfaces": 0,
                "reachable_nodes": 0,
                "unreachable_nodes": 0
            }
        }

        logger.info("🔍 Aggregating cluster state from all nodes...")

        # Query local node first
        local_state = self._query_local_node()
        if local_state:
            node_id = local_state['node_id']
            unified_state["nodes"][node_id] = local_state
            unified_state["summary"]["total_nodes"] += 1
            unified_state["summary"]["total_services"] += local_state.get("services_count", 0)
            unified_state["summary"]["total_packages"] += local_state.get("software_count", 0)
            unified_state["summary"]["total_interfaces"] += local_state.get("interfaces_count", 0)
            unified_state["summary"]["reachable_nodes"] += 1

        # Query all remote nodes
        for node_id, node_info in self.known_nodes.items():
            # Skip if already got local
            if local_state and node_id == local_state.get('node_id'):
                continue

            node_state = self._query_remote_node(node_id, node_info)

            if node_state:
                unified_state["nodes"][node_state['node_id']] = node_state
                unified_state["summary"]["total_nodes"] += 1
                unified_state["summary"]["total_services"] += node_state.get("services_count", 0)
                unified_state["summary"]["total_packages"] += node_state.get("software_count", 0)
                unified_state["summary"]["total_interfaces"] += node_state.get("interfaces_count", 0)
                unified_state["summary"]["reachable_nodes"] += 1
            else:
                unified_state["summary"]["unreachable_nodes"] += 1

        logger.info(f"✅ Aggregated state from {unified_state['summary']['reachable_nodes']} nodes")
        logger.info(f"   Total services: {unified_state['summary']['total_services']}")
        logger.info(f"   Total packages: {unified_state['summary']['total_packages']}")

        return unified_state

    def query_services_across_cluster(self, service_name: Optional[str] = None, port: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query services across all nodes

        Args:
            service_name: Filter by service name (optional)
            port: Filter by port (optional)

        Returns:
            List of services matching criteria
        """
        services = []

        for node_id, node_info in self.known_nodes.items():
            try:
                # Build query
                query = "SELECT * FROM service_endpoints WHERE 1=1"
                if service_name:
                    query += f" AND service_name LIKE '%{service_name}%'"
                if port:
                    query += f" AND port = {port}"
                query += ";"

                # Execute remote query
                cmd = [
                    "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                    f"{node_info['user']}@{node_info['ip']}",
                    f"sqlite3 -json {node_info['db_path']} \"{query}\""
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and result.stdout.strip():
                    node_services = json.loads(result.stdout)
                    services.extend(node_services)

            except Exception as e:
                logger.warning(f"Error querying services from {node_id}: {e}")
                continue

        return services


def main():
    """Demo: Aggregate cluster state"""
    print()
    print("=" * 60)
    print("CLUSTER STATE AGGREGATOR DEMONSTRATION")
    print("=" * 60)
    print()

    aggregator = ClusterStateAggregator()

    # Get unified cluster state
    cluster_state = aggregator.get_unified_cluster_state()

    print()
    print("📊 Unified Cluster State:")
    print(f"   Nodes: {cluster_state['summary']['total_nodes']} "
          f"({cluster_state['summary']['reachable_nodes']} reachable, "
          f"{cluster_state['summary']['unreachable_nodes']} unreachable)")
    print(f"   Total services: {cluster_state['summary']['total_services']}")
    print(f"   Total packages: {cluster_state['summary']['total_packages']}")
    print(f"   Total interfaces: {cluster_state['summary']['total_interfaces']}")
    print()

    print("Nodes in cluster:")
    for node_id, node_data in sorted(cluster_state['nodes'].items()):
        print(f"  • {node_id} ({node_data.get('role', 'unknown')})")
        print(f"    - OS: {node_data.get('os_type')} {node_data.get('architecture')}")
        print(f"    - Services: {node_data.get('services_count', 0)}")
        print(f"    - Packages: {node_data.get('software_count', 0)}")
        print(f"    - Interfaces: {node_data.get('interfaces_count', 0)}")
    print()

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
