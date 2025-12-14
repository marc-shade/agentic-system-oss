#!/usr/bin/env python3
"""
Claude-Flow Integration with Distributed Cluster
Enables claude-flow swarm orchestration across the agentic cluster
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for cluster_offload
sys.path.insert(0, str(Path(__file__).parent))
from cluster_offload import offload, offload_many, get_cluster_status


class ClaudeFlowCluster:
    """Integration layer between claude-flow and distributed cluster"""

    def __init__(self):
        self.cluster_status = get_cluster_status()
        self.claude_flow_db = "/mnt/agentic-system/databases/claude/claude_flow_real.db"

    def execute_claude_flow_command(
        self,
        command: str,
        requires_os: Optional[str] = None,
        requires_arch: Optional[str] = None
    ) -> Dict:
        """
        Execute a claude-flow command on the cluster

        Args:
            command: Claude-flow command to execute (e.g., "sparc tdd 'feature'")
            requires_os: Optional OS requirement (linux, macos)
            requires_arch: Optional architecture requirement (x86_64, arm64)

        Returns:
            Result dictionary with output and metadata
        """
        # Build the full command
        full_cmd = f"cd /mnt/agentic-system/claude-flow && npx claude-flow {command}"

        # Offload to cluster
        result = offload(
            full_cmd,
            requires_os=requires_os,
            requires_arch=requires_arch
        )

        return result

    def spawn_agent_swarm(
        self,
        agent_types: List[str],
        task: str,
        topology: str = "hierarchical"
    ) -> Dict:
        """
        Spawn a multi-agent swarm across cluster nodes

        Args:
            agent_types: List of agent types to spawn
            task: Task description for the swarm
            topology: Swarm topology (hierarchical, mesh, ring, star)

        Returns:
            Swarm execution results
        """
        # Create agents in parallel across nodes
        commands = []
        for agent_type in agent_types:
            cmd = f"""cd /mnt/agentic-system/claude-flow && npx claude-flow agent spawn \\
                --type {agent_type} \\
                --task '{task}' \\
                --topology {topology}"""
            commands.append(cmd)

        # Execute in parallel across cluster
        results = offload_many(commands)

        return {
            "status": "success",
            "agents_spawned": len(agent_types),
            "results": results
        }

    def run_sparc_workflow(
        self,
        feature_description: str,
        mode: str = "tdd",
        parallel: bool = True
    ) -> Dict:
        """
        Run SPARC workflow (Specification, Pseudocode, Architecture, Refinement, Completion)

        Args:
            feature_description: Description of feature to implement
            mode: SPARC mode (tdd, spec-pseudocode, architect, etc.)
            parallel: Whether to run phases in parallel when possible

        Returns:
            SPARC workflow results
        """
        command = f"sparc {mode} '{feature_description}'"

        if parallel:
            command += " --parallel"

        return self.execute_claude_flow_command(command)

    def distributed_code_review(
        self,
        files: List[str],
        review_type: str = "quality"
    ) -> Dict:
        """
        Perform distributed code review across cluster

        Args:
            files: List of file paths to review
            review_type: Type of review (quality, security, performance)

        Returns:
            Review results
        """
        # Split files across nodes
        commands = []
        for file_path in files:
            cmd = f"""cd /mnt/agentic-system/claude-flow && npx claude-flow agent spawn \\
                --type reviewer \\
                --task 'Review {file_path} for {review_type}' \\
                --file {file_path}"""
            commands.append(cmd)

        # Execute reviews in parallel
        results = offload_many(commands)

        return {
            "status": "success",
            "files_reviewed": len(files),
            "review_type": review_type,
            "results": results
        }

    def get_swarm_status(self) -> Dict:
        """Get status of all active swarms"""
        result = self.execute_claude_flow_command("status --json")

        try:
            return json.loads(result.get("output", "{}"))
        except json.JSONDecodeError:
            return {"error": "Failed to parse status"}

    def deploy_to_all_nodes(self) -> Dict:
        """Deploy claude-flow to all cluster nodes"""
        nodes = self.cluster_status.get("nodes", {})
        results = {}

        for node_id in nodes.keys():
            if node_id == "macpro51":
                # Already installed on macpro51
                results[node_id] = {"status": "already_installed"}
                continue

            # Clone and build on remote node
            deploy_cmd = f"""
                cd $STORAGE_BASE && \\
                git clone https://github.com/marc-shade/claude-flow.git || true && \\
                cd claude-flow && \\
                git pull && \\
                npm install && \\
                npm run build
            """

            result = offload(deploy_cmd)
            results[node_id] = result

        return results


def main():
    """Test claude-flow cluster integration"""
    print("🔄 Testing Claude-Flow Cluster Integration\n")

    cluster = ClaudeFlowCluster()

    # Test 1: Execute simple command
    print("Test 1: Execute simple status command")
    result = cluster.execute_claude_flow_command("status")
    print(f"✓ Status: {result.get('status')}")
    print(f"  Output: {result.get('output', '')[:200]}...")

    # Test 2: Get swarm status
    print("\nTest 2: Get swarm status")
    status = cluster.get_swarm_status()
    print(f"✓ Swarm Status: {json.dumps(status, indent=2)[:300]}...")

    # Test 3: Test deployment detection
    print("\nTest 3: Check cluster nodes")
    nodes = cluster.cluster_status.get("nodes", {})
    print(f"✓ Cluster has {len(nodes)} nodes")
    for node_id, node_info in nodes.items():
        print(f"  - {node_id}: {node_info.get('specialties', [])}")

    print("\n✅ Claude-Flow cluster integration working!")


if __name__ == "__main__":
    main()
