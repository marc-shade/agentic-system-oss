#!/usr/bin/env python3
"""
Cluster Multi-AI Guardian - Demonstrates all three AI providers working together

Uses:
- Claude: Orchestration and complex reasoning
- Codex: Code quality and security audits
- Gemini: Performance analysis and fast inference

All agents query the same comprehensive cluster state for coordinated decisions.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdk_agents.claude_agent import ClaudeAgent, AgentPurpose as ClaudePurpose
from sdk_agents.codex_agent import CodexAgent, AgentPurpose as CodexPurpose
from sdk_agents.gemini_cli_agent import GeminiCLIAgent, AgentPurpose as GeminiPurpose


class ClusterMultiAIGuardian:
    """
    Multi-AI cluster guardian that coordinates three AI providers

    Architecture:
    - Claude (orchestrator): Makes high-level decisions, coordinates other agents
    - Codex (security): Audits code, checks for vulnerabilities
    - Gemini (performance): Analyzes topology, identifies bottlenecks

    All query the same comprehensive cluster state database.
    """

    def __init__(self):
        print("🚀 Initializing Multi-AI Cluster Guardian...")
        print()

        # Initialize Claude agent (orchestrator)
        try:
            self.claude = ClaudeAgent(
                purpose=ClaudePurpose(
                    name="Cluster Orchestrator",
                    description="Coordinates cluster operations and makes high-level decisions",
                    primary_goal="Maintain cluster health and optimize performance",
                    decision_criteria=[
                        "Security vulnerabilities must be addressed immediately",
                        "Performance bottlenecks should be identified and resolved",
                        "Service distribution should be balanced",
                        "All nodes should be healthy and communicating"
                    ],
                    tools_needed=["cluster_state", "codex", "gemini"]
                ),
                tools=[],
                use_cluster_state=True
            )
            print("✅ Claude orchestrator initialized")
        except Exception as e:
            print(f"❌ Claude initialization failed: {e}")
            self.claude = None

        # Initialize Codex agent (security)
        try:
            self.codex = CodexAgent(
                purpose=CodexPurpose.CODE_QUALITY,
                tools=[],
                use_cluster_state=True
            )
            print("✅ Codex security auditor initialized")
        except Exception as e:
            print(f"⚠️  Codex initialization failed: {e}")
            self.codex = None

        # Initialize Gemini agent (performance)
        try:
            self.gemini = GeminiCLIAgent(
                purpose=GeminiPurpose.PERFORMANCE_TUNING,
                tools=[],
                use_cluster_state=True
            )
            print("✅ Gemini performance analyzer initialized")
        except Exception as e:
            print(f"⚠️  Gemini initialization failed: {e}")
            self.gemini = None

        print()

    async def run_cluster_analysis(self):
        """
        Run complete cluster analysis with all three AI providers

        Workflow:
        1. Claude gets cluster state and decides what to analyze
        2. Codex audits packages for security issues
        3. Gemini analyzes performance and topology
        4. Claude orchestrates fixes based on both analyses
        """
        print("=" * 60)
        print("CLUSTER MULTI-AI ANALYSIS")
        print("=" * 60)
        print()

        # Step 1: Claude orchestrates
        if self.claude:
            print("🧠 Claude: Getting cluster state and deciding priorities...")
            cluster_state = self.claude.get_cluster_state()

            if "error" not in cluster_state:
                total_nodes = len(cluster_state.get("nodes", {}))
                total_services = sum(
                    len(node.get("services", []))
                    for node in cluster_state.get("nodes", {}).values()
                )

                print(f"   📊 Cluster overview:")
                print(f"      - Nodes: {total_nodes}")
                print(f"      - Services: {total_services}")
                print()

                # Claude decides what needs analysis
                task = "Analyze cluster for security vulnerabilities and performance bottlenecks"
                orchestration = await self.claude.orchestrate_cluster_task(task)

                print(f"   🎯 Claude's orchestration plan:")
                print(f"      {orchestration.get('plan', 'N/A')[:200]}...")
                print()

        # Step 2: Codex security audit
        if self.codex:
            print("🔒 Codex: Running security audit across all nodes...")
            # Query all installed packages
            all_packages = self.codex.query_software()

            if all_packages:
                print(f"   📦 Auditing {len(all_packages)} packages...")

                # Group by node
                by_node = {}
                for pkg in all_packages:
                    node = pkg.get("node_id", "unknown")
                    if node not in by_node:
                        by_node[node] = []
                    by_node[node].append(pkg)

                # Show summary
                for node_id, packages in by_node.items():
                    print(f"      {node_id}: {len(packages)} packages")

                print()
                print("   ℹ️  (Full security audit would use Codex API to analyze each package)")
                print()

        # Step 3: Gemini performance analysis
        if self.gemini:
            print("⚡ Gemini: Analyzing cluster performance...")

            # Get network topology
            topology = self.gemini.get_network_topology()

            if topology.get("interfaces"):
                total_interfaces = sum(
                    len(ifaces) for ifaces in topology["interfaces"].values()
                )
                print(f"   🌐 Network topology:")
                print(f"      - Network interfaces: {total_interfaces}")

                # Show service distribution
                if "listening_ports" in topology:
                    for node_id, ports in topology["listening_ports"].items():
                        print(f"      - {node_id}: {len(ports)} listening ports")

                print()
                print("   ℹ️  (Full performance analysis would use Gemini CLI to identify bottlenecks)")
                print()

        # Step 4: Claude coordinates next actions
        if self.claude:
            print("🎯 Claude: Coordinating next actions based on analysis...")
            print()
            print("   Recommendations:")
            print("   - All agents have visibility into complete cluster state")
            print("   - Codex can audit packages across all nodes")
            print("   - Gemini can analyze network topology")
            print("   - Claude orchestrates based on their findings")
            print()

        print("=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

    def show_cluster_state_access(self):
        """Demonstrate that all three agents query the same cluster state"""
        print()
        print("=" * 60)
        print("CLUSTER STATE ACCESS DEMONSTRATION")
        print("=" * 60)
        print()

        # Query services from all three agents
        if self.claude:
            print("🧠 Claude querying services...")
            claude_services = self.claude.query_services(service_name="qdrant")
            print(f"   Found {len(claude_services)} qdrant instances")

        if self.codex:
            print("🔒 Codex querying services...")
            codex_services = self.codex.query_services(service_name="qdrant")
            print(f"   Found {len(codex_services)} qdrant instances")

        if self.gemini:
            print("⚡ Gemini querying services...")
            gemini_services = self.gemini.query_services(service_name="qdrant")
            print(f"   Found {len(gemini_services)} qdrant instances")

        print()
        print("✅ All three agents query the same comprehensive cluster state!")
        print()


async def main():
    """Example usage of Multi-AI Cluster Guardian"""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         CLUSTER MULTI-AI GUARDIAN DEMONSTRATION            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("This demonstrates three AI providers working together:")
    print("  • Claude (Anthropic) - Orchestration & complex reasoning")
    print("  • Codex (OpenAI) - Code quality & security audits")
    print("  • Gemini (Google) - Performance analysis & fast inference")
    print()
    print("All agents query the SAME comprehensive cluster state database.")
    print()

    # Initialize multi-AI guardian
    guardian = ClusterMultiAIGuardian()

    # Demonstrate cluster state access
    guardian.show_cluster_state_access()

    # Run full cluster analysis
    await guardian.run_cluster_analysis()

    print()
    print("Next steps:")
    print("  1. Deploy this as a background service on orchestrator node")
    print("  2. Each AI provider runs analysis on their specialty")
    print("  3. Claude coordinates actions based on findings")
    print("  4. All decisions logged for learning and improvement")
    print()


if __name__ == "__main__":
    asyncio.run(main())
