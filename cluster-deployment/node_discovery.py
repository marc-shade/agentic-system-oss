#!/usr/bin/env python3
"""
Node Discovery and Inventory System

Enables nodes to discover what code, configs, capabilities, and data
exist on other nodes in the cluster. This forms the foundation for
autonomous self-improvement and synchronization.

Features:
- Inventory all installed packages, scripts, configs
- Discover MCP servers and their capabilities
- Map installed services and daemons
- Track versions and git commits
- Identify capability gaps between nodes
- Generate upgrade recommendations

Usage:
    # Discover local node inventory
    python3 node_discovery.py --local

    # Discover remote node inventory
    python3 node_discovery.py --node macbook-air

    # Compare all nodes and find gaps
    python3 node_discovery.py --compare

    # Generate upgrade plan
    python3 node_discovery.py --upgrade-plan
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import hashlib

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from distributed_task_router import CLUSTER_NODES


@dataclass
class NodeInventory:
    """Complete inventory of a node's capabilities"""
    node_id: str
    hostname: str
    os_type: str
    architecture: str

    # System info
    python_version: str
    git_commit: Optional[str]

    # Installed packages
    pip_packages: Dict[str, str]  # package_name -> version
    system_packages: Dict[str, str]  # For apt/dnf/brew packages

    # Code inventory
    scripts: Dict[str, str]  # path -> checksum
    mcp_servers: Dict[str, Dict]  # server_name -> {path, version, capabilities}
    intelligent_agents: Dict[str, str]  # agent_name -> path
    workflows: Dict[str, str]  # workflow_name -> path

    # Configuration
    configs: Dict[str, str]  # config_path -> checksum
    env_vars: Dict[str, str]  # Important env vars

    # Services
    systemd_services: List[str]  # Running services
    docker_containers: List[str]  # Running containers
    listening_ports: Dict[int, str]  # port -> service

    # Databases
    databases: Dict[str, int]  # db_path -> record_count

    # Capabilities
    capabilities: List[str]  # docker, podman, temporal, etc.

    # Timestamp
    discovered_at: float


class NodeDiscovery:
    """
    Discovers and inventories node capabilities for self-improvement
    """

    def __init__(self, storage_base: Optional[Path] = None):
        if storage_base is None:
            # Auto-detect storage base
            if os.path.exists("/Volumes/SSDRAID0/agentic-system"):
                storage_base = Path("/Volumes/SSDRAID0/agentic-system")
            elif os.path.exists("/home/marc/agentic-system"):
                storage_base = Path("/home/marc/agentic-system")
            else:
                storage_base = Path.home() / "agentic-system"

        self.storage_base = storage_base
        self.node_id = self._detect_node_id()

    def _detect_node_id(self) -> str:
        """Detect current node ID"""
        try:
            hostname = subprocess.run(
                ["hostname"],
                capture_output=True,
                text=True
            ).stdout.strip()

            # Map hostnames to node IDs
            hostname_map = {
                "macpro51": "macpro51",
                "Mac-Studio.local": "mac-studio",
                "MacBook-Air.local": "macbook-air"
            }

            for h, nid in hostname_map.items():
                if h in hostname:
                    return nid

            return hostname
        except:
            return "unknown"

    def _get_file_checksum(self, filepath: Path) -> str:
        """Calculate MD5 checksum of a file"""
        try:
            md5 = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except:
            return "error"

    def _run_command(self, cmd: List[str], node_ip: Optional[str] = None) -> str:
        """Run command locally or via SSH"""
        if node_ip:
            # Remote execution via SSH
            ssh_cmd = ["ssh", "-o", "ConnectTimeout=5", f"marc@{node_ip}"] + [" ".join(cmd)]
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
        else:
            # Local execution
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

        return result.stdout.strip() if result.returncode == 0 else ""

    def discover_local_inventory(self) -> NodeInventory:
        """Create complete inventory of local node"""
        import time

        print(f"Discovering inventory for {self.node_id}...")

        # Basic system info
        hostname = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
        os_type = subprocess.run(["uname", "-s"], capture_output=True, text=True).stdout.strip().lower()
        arch = subprocess.run(["uname", "-m"], capture_output=True, text=True).stdout.strip()
        python_version = subprocess.run(["python3", "--version"], capture_output=True, text=True).stdout.strip()

        # Git commit
        try:
            git_commit = subprocess.run(
                ["git", "-C", str(self.storage_base), "rev-parse", "HEAD"],
                capture_output=True,
                text=True
            ).stdout.strip()
        except:
            git_commit = None

        # Python packages
        print("  Scanning pip packages...")
        pip_packages = {}
        try:
            pip_list = subprocess.run(
                ["pip3", "list", "--format=json"],
                capture_output=True,
                text=True
            ).stdout
            for pkg in json.loads(pip_list):
                pip_packages[pkg['name']] = pkg['version']
        except:
            pass

        # Scripts inventory
        print("  Scanning scripts...")
        scripts = {}
        if (self.storage_base / "scripts").exists():
            for script in (self.storage_base / "scripts").rglob("*.sh"):
                scripts[str(script.relative_to(self.storage_base))] = self._get_file_checksum(script)
            for script in (self.storage_base / "scripts").rglob("*.py"):
                scripts[str(script.relative_to(self.storage_base))] = self._get_file_checksum(script)

        # MCP servers
        print("  Scanning MCP servers...")
        mcp_servers = {}
        if (self.storage_base / "mcp-servers").exists():
            for server_dir in (self.storage_base / "mcp-servers").iterdir():
                if server_dir.is_dir():
                    server_info = {
                        "path": str(server_dir.relative_to(self.storage_base)),
                        "exists": True
                    }

                    # Check for server.py
                    if (server_dir / "server.py").exists():
                        server_info["checksum"] = self._get_file_checksum(server_dir / "server.py")

                    mcp_servers[server_dir.name] = server_info

        # Intelligent agents
        print("  Scanning intelligent agents...")
        intelligent_agents = {}
        if (self.storage_base / "intelligent-agents").exists():
            for agent in (self.storage_base / "intelligent-agents").rglob("*.py"):
                if agent.name != "__init__.py":
                    intelligent_agents[agent.stem] = str(agent.relative_to(self.storage_base))

        # Workflows
        print("  Scanning workflows...")
        workflows = {}
        if (self.storage_base / "workflows").exists():
            for wf in (self.storage_base / "workflows").rglob("*.py"):
                workflows[wf.stem] = str(wf.relative_to(self.storage_base))

        # Configs
        print("  Scanning configurations...")
        configs = {}
        config_files = [
            Path.home() / ".claude.json",
            Path.home() / ".claude" / "node-config.json",
            self.storage_base / "monitoring" / "prometheus" / "prometheus.yml"
        ]
        for cf in config_files:
            if cf.exists():
                configs[str(cf)] = self._get_file_checksum(cf)

        # Running services (Linux only)
        systemd_services = []
        if os_type == "linux":
            try:
                result = subprocess.run(
                    ["systemctl", "--user", "list-units", "--type=service", "--state=running", "--no-pager"],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if 'agentic' in line.lower() or 'builder' in line.lower():
                        systemd_services.append(line.split()[0])
            except:
                pass

        # Docker/Podman containers
        print("  Scanning containers...")
        docker_containers = []
        try:
            result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
            docker_containers = result.stdout.strip().split('\n') if result.stdout else []
        except:
            try:
                result = subprocess.run(["podman", "ps", "--format", "{{.Names}}"], capture_output=True, text=True)
                docker_containers = result.stdout.strip().split('\n') if result.stdout else []
            except:
                pass

        # Listening ports
        print("  Scanning listening ports...")
        listening_ports = {}
        try:
            if os_type == "linux":
                result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
            else:
                result = subprocess.run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True)

            # Parse output to get ports (simplified)
            for line in result.stdout.split('\n'):
                if ':' in line:
                    # Extract port numbers (simplified parsing)
                    pass  # TODO: Implement proper port parsing
        except:
            pass

        # Databases
        print("  Scanning databases...")
        databases = {}
        if (self.storage_base / "databases").exists():
            for db in (self.storage_base / "databases").rglob("*.db"):
                try:
                    import sqlite3
                    conn = sqlite3.connect(db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    count = 0
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                        count += cursor.fetchone()[0]
                    databases[str(db.relative_to(self.storage_base))] = count
                    conn.close()
                except:
                    databases[str(db.relative_to(self.storage_base))] = 0

        # Capabilities
        capabilities = []
        if os_type == "linux":
            capabilities.append("linux")
        elif os_type == "darwin":
            capabilities.append("macos")

        if arch == "x86_64":
            capabilities.append("x86_64")
        elif "arm" in arch or "aarch64" in arch:
            capabilities.append("arm64")

        # Check for Docker/Podman
        if subprocess.run(["which", "docker"], capture_output=True).returncode == 0:
            capabilities.append("docker")
        if subprocess.run(["which", "podman"], capture_output=True).returncode == 0:
            capabilities.append("podman")

        # Check for Temporal
        if (self.storage_base / "databases" / "temporal").exists():
            capabilities.append("temporal")

        print("✓ Discovery complete")

        return NodeInventory(
            node_id=self.node_id,
            hostname=hostname,
            os_type=os_type,
            architecture=arch,
            python_version=python_version,
            git_commit=git_commit,
            pip_packages=pip_packages,
            system_packages={},  # TODO
            scripts=scripts,
            mcp_servers=mcp_servers,
            intelligent_agents=intelligent_agents,
            workflows=workflows,
            configs=configs,
            env_vars={},  # TODO
            systemd_services=systemd_services,
            docker_containers=docker_containers,
            listening_ports=listening_ports,
            databases=databases,
            capabilities=capabilities,
            discovered_at=time.time()
        )

    def discover_remote_inventory(self, node_id: str) -> Optional[NodeInventory]:
        """Discover inventory of a remote node via SSH"""
        if node_id not in CLUSTER_NODES:
            print(f"Unknown node: {node_id}")
            return None

        node_info = CLUSTER_NODES[node_id]
        ip = node_info['ip']

        print(f"Discovering remote inventory for {node_id} ({ip})...")

        # Copy this script to remote node
        try:
            subprocess.run(
                ["scp", __file__, f"marc@{ip}:/tmp/node_discovery.py"],
                check=True,
                timeout=10
            )

            # Run discovery on remote node
            result = subprocess.run(
                ["ssh", f"marc@{ip}", "python3", "/tmp/node_discovery.py", "--local", "--json"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                inventory_data = json.loads(result.stdout)
                return NodeInventory(**inventory_data)
            else:
                print(f"Failed to discover {node_id}: {result.stderr}")
                return None

        except Exception as e:
            print(f"Error discovering {node_id}: {e}")
            return None

    def compare_nodes(self, inventories: List[NodeInventory]) -> Dict:
        """Compare multiple node inventories and identify gaps"""
        print("\nComparing node inventories...")

        comparison = {
            "nodes": [inv.node_id for inv in inventories],
            "gaps": {},
            "differences": {},
            "recommendations": []
        }

        # Compare MCP servers
        all_mcp_servers = set()
        for inv in inventories:
            all_mcp_servers.update(inv.mcp_servers.keys())

        for server in all_mcp_servers:
            nodes_with = [inv.node_id for inv in inventories if server in inv.mcp_servers]
            nodes_without = [inv.node_id for inv in inventories if server not in inv.mcp_servers]

            if nodes_without:
                comparison["gaps"][f"mcp_server_{server}"] = {
                    "type": "mcp_server",
                    "name": server,
                    "present_on": nodes_with,
                    "missing_on": nodes_without
                }

        # Compare Python packages
        all_packages = set()
        for inv in inventories:
            all_packages.update(inv.pip_packages.keys())

        for package in all_packages:
            versions = {}
            for inv in inventories:
                if package in inv.pip_packages:
                    versions[inv.node_id] = inv.pip_packages[package]

            if len(set(versions.values())) > 1:
                comparison["differences"][f"package_{package}"] = {
                    "type": "package_version",
                    "name": package,
                    "versions": versions
                }

        # Compare git commits
        git_commits = {inv.node_id: inv.git_commit for inv in inventories if inv.git_commit}
        if len(set(git_commits.values())) > 1:
            comparison["differences"]["git_commits"] = {
                "type": "git_commit",
                "commits": git_commits
            }

        # Generate recommendations
        for gap_name, gap_info in comparison["gaps"].items():
            if gap_info["type"] == "mcp_server":
                for node in gap_info["missing_on"]:
                    comparison["recommendations"].append({
                        "node": node,
                        "action": "install_mcp_server",
                        "target": gap_info["name"],
                        "source_nodes": gap_info["present_on"]
                    })

        return comparison

    def generate_upgrade_plan(self, comparison: Dict) -> List[Dict]:
        """Generate step-by-step upgrade plan to sync all nodes"""
        plan = []

        for rec in comparison["recommendations"]:
            plan.append({
                "step": len(plan) + 1,
                "node": rec["node"],
                "action": rec["action"],
                "details": rec,
                "command": self._generate_upgrade_command(rec)
            })

        return plan

    def _generate_upgrade_command(self, recommendation: Dict) -> str:
        """Generate shell command to execute upgrade"""
        if recommendation["action"] == "install_mcp_server":
            source_node = recommendation["source_nodes"][0]
            source_ip = CLUSTER_NODES[source_node]["ip"]
            target_node = recommendation["node"]
            server_name = recommendation["target"]

            return f"scp -r marc@{source_ip}:~/agentic-system/mcp-servers/{server_name} ~/agentic-system/mcp-servers/"

        return "# TODO: Generate command"


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Node Discovery and Inventory System")
    parser.add_argument("--local", action="store_true", help="Discover local node inventory")
    parser.add_argument("--node", type=str, help="Discover remote node inventory")
    parser.add_argument("--compare", action="store_true", help="Compare all nodes")
    parser.add_argument("--upgrade-plan", action="store_true", help="Generate upgrade plan")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    discovery = NodeDiscovery()

    if args.local:
        inventory = discovery.discover_local_inventory()
        if args.json:
            print(json.dumps(asdict(inventory), indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Node Inventory: {inventory.node_id}")
            print(f"{'='*60}")
            print(f"Hostname: {inventory.hostname}")
            print(f"OS: {inventory.os_type} ({inventory.architecture})")
            print(f"Python: {inventory.python_version}")
            print(f"Git Commit: {inventory.git_commit[:8] if inventory.git_commit else 'N/A'}")
            print(f"\nPython Packages: {len(inventory.pip_packages)}")
            print(f"MCP Servers: {len(inventory.mcp_servers)}")
            print(f"Intelligent Agents: {len(inventory.intelligent_agents)}")
            print(f"Workflows: {len(inventory.workflows)}")
            print(f"Databases: {len(inventory.databases)}")
            print(f"Capabilities: {', '.join(inventory.capabilities)}")
            print(f"{'='*60}\n")

    elif args.node:
        inventory = discovery.discover_remote_inventory(args.node)
        if inventory and args.json:
            print(json.dumps(asdict(inventory), indent=2))

    elif args.compare:
        print("Discovering all cluster nodes...")
        inventories = []

        # Local node
        inventories.append(discovery.discover_local_inventory())

        # Remote nodes
        for node_id in CLUSTER_NODES.keys():
            if node_id != discovery.node_id:
                inv = discovery.discover_remote_inventory(node_id)
                if inv:
                    inventories.append(inv)

        comparison = discovery.compare_nodes(inventories)

        if args.json:
            print(json.dumps(comparison, indent=2))
        else:
            print(f"\n{'='*60}")
            print("Cluster Comparison")
            print(f"{'='*60}")
            print(f"Nodes: {', '.join(comparison['nodes'])}")
            print(f"\nGaps Found: {len(comparison['gaps'])}")
            for gap_name, gap_info in comparison['gaps'].items():
                print(f"  - {gap_info['name']} missing on: {', '.join(gap_info['missing_on'])}")
            print(f"\nDifferences Found: {len(comparison['differences'])}")
            for diff_name, diff_info in comparison['differences'].items():
                print(f"  - {diff_info['name']}: {diff_info.get('versions', diff_info.get('commits', {}))}")
            print(f"\nRecommendations: {len(comparison['recommendations'])}")
            for rec in comparison['recommendations']:
                print(f"  - {rec['node']}: {rec['action']} {rec['target']}")
            print(f"{'='*60}\n")

    elif args.upgrade_plan:
        print("Generating upgrade plan...")
        inventories = []

        # Discover all nodes
        inventories.append(discovery.discover_local_inventory())
        for node_id in CLUSTER_NODES.keys():
            if node_id != discovery.node_id:
                inv = discovery.discover_remote_inventory(node_id)
                if inv:
                    inventories.append(inv)

        comparison = discovery.compare_nodes(inventories)
        plan = discovery.generate_upgrade_plan(comparison)

        if args.json:
            print(json.dumps(plan, indent=2))
        else:
            print(f"\n{'='*60}")
            print("Upgrade Plan")
            print(f"{'='*60}")
            for step in plan:
                print(f"\nStep {step['step']}: {step['node']}")
                print(f"  Action: {step['action']}")
                print(f"  Command: {step['command']}")
            print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
