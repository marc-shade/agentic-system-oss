#!/usr/bin/env python3
"""
Autonomous Self-Improvement Agent

Runs continuously on each node to:
1. Observe other nodes and discover their capabilities
2. Compare self to cluster peers
3. Identify gaps and improvement opportunities
4. Autonomously upgrade and evolve
5. Share improvements with other nodes

This creates a distributed self-improving system where nodes
collectively evolve toward an optimal configuration.

Features:
- Periodic discovery of peer nodes
- Gap analysis and improvement planning
- Autonomous code/config synchronization
- Continuous learning and adaptation
- Distributed collective intelligence

Usage:
    # Run as daemon (recommended)
    python3 autonomous_self_improvement_agent.py --daemon

    # Run one improvement cycle
    python3 autonomous_self_improvement_agent.py --once

    # Check what would be improved (dry-run)
    python3 autonomous_self_improvement_agent.py --dry-run
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import signal

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from node_discovery import NodeDiscovery, NodeInventory
from distributed_task_router import CLUSTER_NODES


@dataclass
class ImprovementAction:
    """An action to improve the node"""
    action_type: str  # install_package, sync_code, update_config, install_service
    target: str  # What to improve
    source_node: Optional[str]  # Where to get it from
    command: str  # Shell command to execute
    priority: int  # 1-10, higher is more important
    estimated_impact: str  # Description of expected benefit


class AutonomousSelfImprovementAgent:
    """
    Agent that continuously improves its node by observing cluster peers
    """

    def __init__(
        self,
        cycle_interval: int = 3600,  # 1 hour
        enable_auto_improve: bool = True,
        storage_base: Optional[Path] = None
    ):
        self.cycle_interval = cycle_interval
        self.enable_auto_improve = enable_auto_improve

        self.discovery = NodeDiscovery(storage_base)
        self.node_id = self.discovery.node_id
        self.storage_base = self.discovery.storage_base

        self.running = False
        self.improvements_applied = 0
        self.last_cycle_time = 0
        self.improvement_history = []

    def discover_cluster_state(self) -> Dict[str, NodeInventory]:
        """
        Discover current state of all nodes in cluster

        Returns dict of node_id -> NodeInventory
        """
        print(f"\n{'='*60}")
        print("Discovering Cluster State")
        print(f"{'='*60}")

        inventories = {}

        # Discover local node
        print(f"\n🔍 Discovering local node ({self.node_id})...")
        inventories[self.node_id] = self.discovery.discover_local_inventory()

        # Discover remote nodes
        for node_id in CLUSTER_NODES.keys():
            if node_id != self.node_id:
                print(f"\n🔍 Discovering remote node ({node_id})...")
                try:
                    inv = self.discovery.discover_remote_inventory(node_id)
                    if inv:
                        inventories[node_id] = inv
                        print(f"  ✓ {node_id} discovered successfully")
                    else:
                        print(f"  ✗ {node_id} discovery failed")
                except Exception as e:
                    print(f"  ✗ {node_id} error: {e}")

        print(f"\n✓ Discovered {len(inventories)} nodes")
        return inventories

    def analyze_gaps(self, inventories: Dict[str, NodeInventory]) -> List[ImprovementAction]:
        """
        Analyze gaps between this node and peers

        Returns list of recommended improvements
        """
        print(f"\n{'='*60}")
        print("Analyzing Gaps and Opportunities")
        print(f"{'='*60}")

        improvements = []
        local_inv = inventories[self.node_id]

        # Find nodes with more capabilities
        all_mcp_servers = set()
        all_packages = set()
        all_agents = set()
        all_workflows = set()

        for node_id, inv in inventories.items():
            all_mcp_servers.update(inv.mcp_servers.keys())
            all_packages.update(inv.pip_packages.keys())
            all_agents.update(inv.intelligent_agents.keys())
            all_workflows.update(inv.workflows.keys())

        # Missing MCP servers
        missing_mcp = all_mcp_servers - set(local_inv.mcp_servers.keys())
        for server in missing_mcp:
            # Find which node has it
            source_node = None
            for node_id, inv in inventories.items():
                if server in inv.mcp_servers:
                    source_node = node_id
                    break

            if source_node:
                source_ip = CLUSTER_NODES[source_node]['ip']
                improvements.append(ImprovementAction(
                    action_type="install_mcp_server",
                    target=server,
                    source_node=source_node,
                    command=f"scp -r marc@{source_ip}:~/agentic-system/mcp-servers/{server} {self.storage_base}/mcp-servers/",
                    priority=8,
                    estimated_impact=f"Gain {server} capabilities from {source_node}"
                ))

        # Missing Python packages
        missing_packages = all_packages - set(local_inv.pip_packages.keys())
        # Filter to important packages only
        important_packages = {
            'anthropic', 'openai', 'psutil', 'temporal-sdk', 'anthropic-mcp',
            'qdrant-client', 'redis', 'prometheus-client'
        }
        for package in missing_packages & important_packages:
            improvements.append(ImprovementAction(
                action_type="install_package",
                target=package,
                source_node=None,
                command=f"pip3 install {package}",
                priority=6,
                estimated_impact=f"Install {package} for enhanced functionality"
            ))

        # Missing intelligent agents
        missing_agents = all_agents - set(local_inv.intelligent_agents.keys())
        for agent in missing_agents:
            # Find source
            source_node = None
            agent_path = None
            for node_id, inv in inventories.items():
                if agent in inv.intelligent_agents:
                    source_node = node_id
                    agent_path = inv.intelligent_agents[agent]
                    break

            if source_node and agent_path:
                source_ip = CLUSTER_NODES[source_node]['ip']
                improvements.append(ImprovementAction(
                    action_type="sync_agent",
                    target=agent,
                    source_node=source_node,
                    command=f"scp marc@{source_ip}:~/agentic-system/{agent_path} {self.storage_base}/{agent_path}",
                    priority=7,
                    estimated_impact=f"Gain {agent} agent from {source_node}"
                ))

        # Missing workflows
        missing_workflows = all_workflows - set(local_inv.workflows.keys())
        for workflow in missing_workflows:
            # Find source
            source_node = None
            workflow_path = None
            for node_id, inv in inventories.items():
                if workflow in inv.workflows:
                    source_node = node_id
                    workflow_path = inv.workflows[workflow]
                    break

            if source_node and workflow_path:
                source_ip = CLUSTER_NODES[source_node]['ip']
                improvements.append(ImprovementAction(
                    action_type="sync_workflow",
                    target=workflow,
                    source_node=source_node,
                    command=f"scp marc@{source_ip}:~/agentic-system/{workflow_path} {self.storage_base}/{workflow_path}",
                    priority=5,
                    estimated_impact=f"Gain {workflow} workflow from {source_node}"
                ))

        # Check for outdated git commits
        git_commits = {node_id: inv.git_commit for node_id, inv in inventories.items() if inv.git_commit}
        if len(set(git_commits.values())) > 1:
            # We might be behind
            most_common_commit = max(set(git_commits.values()), key=list(git_commits.values()).count)
            if local_inv.git_commit != most_common_commit:
                improvements.append(ImprovementAction(
                    action_type="update_git",
                    target="agentic-system",
                    source_node=None,
                    command=f"cd {self.storage_base} && git pull",
                    priority=9,
                    estimated_impact="Update to latest cluster codebase"
                ))

        # Sort by priority
        improvements.sort(key=lambda x: x.priority, reverse=True)

        print(f"\n✓ Found {len(improvements)} improvement opportunities")
        return improvements

    def apply_improvements(self, improvements: List[ImprovementAction], dry_run: bool = False) -> int:
        """
        Apply improvements to this node

        Returns number of improvements successfully applied
        """
        print(f"\n{'='*60}")
        if dry_run:
            print("Improvement Plan (DRY RUN)")
        else:
            print("Applying Improvements")
        print(f"{'='*60}")

        applied = 0

        for i, improvement in enumerate(improvements, 1):
            print(f"\n[{i}/{len(improvements)}] {improvement.action_type}: {improvement.target}")
            print(f"  Priority: {improvement.priority}/10")
            print(f"  Impact: {improvement.estimated_impact}")
            print(f"  Command: {improvement.command}")

            if dry_run:
                print("  Status: WOULD APPLY (dry-run)")
                continue

            if not self.enable_auto_improve:
                print("  Status: SKIPPED (auto-improve disabled)")
                continue

            # Execute improvement
            try:
                print("  Executing...")
                result = subprocess.run(
                    improvement.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    print(f"  ✓ SUCCESS")
                    applied += 1
                    self.improvement_history.append({
                        "timestamp": time.time(),
                        "action": improvement.action_type,
                        "target": improvement.target,
                        "success": True
                    })
                else:
                    print(f"  ✗ FAILED: {result.stderr[:100]}")
                    self.improvement_history.append({
                        "timestamp": time.time(),
                        "action": improvement.action_type,
                        "target": improvement.target,
                        "success": False,
                        "error": result.stderr
                    })

            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                self.improvement_history.append({
                    "timestamp": time.time(),
                    "action": improvement.action_type,
                    "target": improvement.target,
                    "success": False,
                    "error": str(e)
                })

        print(f"\n{'='*60}")
        print(f"Applied {applied}/{len(improvements)} improvements")
        print(f"{'='*60}\n")

        self.improvements_applied += applied
        return applied

    def run_improvement_cycle(self, dry_run: bool = False) -> Dict:
        """
        Run one complete improvement cycle

        Returns summary of cycle results
        """
        cycle_start = time.time()

        print(f"\n{'#'*60}")
        print(f"# Autonomous Self-Improvement Cycle - {self.node_id}")
        print(f"# {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'#'*60}")

        # Step 1: Discover cluster state
        inventories = self.discover_cluster_state()

        # Step 2: Analyze gaps
        improvements = self.analyze_gaps(inventories)

        # Step 3: Apply improvements
        applied = self.apply_improvements(improvements, dry_run=dry_run)

        cycle_duration = time.time() - cycle_start

        summary = {
            "node": self.node_id,
            "timestamp": time.time(),
            "duration_seconds": cycle_duration,
            "nodes_discovered": len(inventories),
            "improvements_found": len(improvements),
            "improvements_applied": applied,
            "dry_run": dry_run
        }

        print(f"\n{'#'*60}")
        print(f"# Cycle Complete")
        print(f"# Duration: {cycle_duration:.1f}s")
        print(f"# Nodes discovered: {len(inventories)}")
        print(f"# Improvements found: {len(improvements)}")
        print(f"# Improvements applied: {applied}")
        print(f"{'#'*60}\n")

        self.last_cycle_time = time.time()
        return summary

    def run_continuous(self):
        """
        Run continuous self-improvement loop

        Discovers cluster state and improves every cycle_interval seconds
        """
        print(f"Autonomous Self-Improvement Agent started for {self.node_id}")
        print(f"Improvement cycle interval: {self.cycle_interval} seconds ({self.cycle_interval/3600:.1f} hours)")
        print(f"Auto-improve: {'ENABLED' if self.enable_auto_improve else 'DISABLED'}")
        print(f"\nPress Ctrl+C to stop\n")

        self.running = True

        try:
            while self.running:
                # Run improvement cycle
                self.run_improvement_cycle(dry_run=False)

                # Wait for next cycle
                print(f"Next cycle in {self.cycle_interval} seconds...")
                print(f"Total improvements applied: {self.improvements_applied}")
                print()

                time.sleep(self.cycle_interval)

        except KeyboardInterrupt:
            print("\n\nStopping autonomous self-improvement agent...")
            self.running = False

    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            "node": self.node_id,
            "running": self.running,
            "improvements_applied_total": self.improvements_applied,
            "last_cycle": self.last_cycle_time,
            "cycle_interval": self.cycle_interval,
            "auto_improve_enabled": self.enable_auto_improve,
            "recent_history": self.improvement_history[-10:]
        }


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Self-Improvement Agent")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as daemon")
    parser.add_argument("--once", action="store_true", help="Run one improvement cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be improved (no changes)")
    parser.add_argument("--interval", type=int, default=3600, help="Cycle interval in seconds")
    parser.add_argument("--disable-auto-improve", action="store_true", help="Disable automatic improvements")
    parser.add_argument("--stats", action="store_true", help="Show agent statistics")

    args = parser.parse_args()

    agent = AutonomousSelfImprovementAgent(
        cycle_interval=args.interval,
        enable_auto_improve=not args.disable_auto_improve
    )

    if args.stats:
        stats = agent.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.once:
        # Run one cycle
        agent.run_improvement_cycle(dry_run=args.dry_run)
    elif args.daemon:
        # Run continuously
        agent.run_continuous()
    else:
        # Default: run one cycle
        agent.run_improvement_cycle(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
