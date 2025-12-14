#!/usr/bin/env python3
"""
Quick Demo: MAKER Integration with Swarm System

Demonstrates key features of the MAKER-enhanced coordinator.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from multi_agent_coordinator_maker import MultiAgentCoordinatorMAKER
from maker_swarm_integration import MAKERSwarmBridge


async def demo():
    """Quick demonstration of MAKER integration"""

    print("🚀 MAKER Integration Demo")
    print("=" * 70)
    print()

    # Demo 1: Check if voting should be used
    print("📋 Demo 1: Automatic Voting Detection")
    print("-" * 70)

    bridge = MAKERSwarmBridge()

    security_task = await bridge.should_use_voting(
        task_type="security",
        task_description="Review authentication for SQL injection",
        criticality="high"
    )
    print(f"Security task (high criticality) → Voting: {security_task}")

    general_task = await bridge.should_use_voting(
        task_type="general",
        task_description="Format code with prettier",
        criticality="normal"
    )
    print(f"General task (normal criticality) → Voting: {general_task}")

    # Demo 2: Coordinator with MAKER
    print("\n\n📋 Demo 2: MAKER-Enhanced Coordinator")
    print("-" * 70)

    coordinator = MultiAgentCoordinatorMAKER(enable_maker_voting=True)

    print(f"Coordinator initialized")
    print(f"  - MAKER voting: enabled")
    print(f"  - Cluster offload: {coordinator.enable_cluster_offload}")
    print(f"  - Total agents: {len(coordinator.agents)}")

    # Demo 3: Show available cluster agents
    print("\n\n📋 Demo 3: Cluster Agents Available")
    print("-" * 70)

    cluster_agents = [name for name in coordinator.agents.keys() if name.startswith("cluster:")]
    if cluster_agents:
        print(f"Found {len(cluster_agents)} cluster agents:")
        for agent in cluster_agents:
            print(f"  - {agent}")
    else:
        print("No cluster agents registered (cluster may be unavailable)")

    # Demo 4: Statistics (empty initially)
    print("\n\n📋 Demo 4: MAKER Statistics")
    print("-" * 70)

    stats = coordinator.get_maker_statistics()
    print(json.dumps(stats, indent=2))

    # Demo 5: Task routing explanation
    print("\n\n📋 Demo 5: Task Routing Rules")
    print("-" * 70)

    task_examples = [
        ("security", "Audit OAuth2 implementation", "Always votes"),
        ("architecture", "Design microservices architecture", "Always votes"),
        ("code_generation", "Write hello world function", "No voting"),
        ("testing", "Test authentication flow", "Votes (critical)"),
        ("general", "Format code with prettier", "No voting"),
    ]

    print("Task Type".ljust(20) + "Description".ljust(40) + "Voting")
    print("-" * 70)
    for task_type, description, voting in task_examples:
        print(f"{task_type:20} {description[:38]:40} {voting}")

    # Summary
    print("\n\n✅ Demo Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Use MultiAgentCoordinatorMAKER() for production tasks")
    print("  2. Security tasks will automatically use MAKER voting")
    print("  3. Monitor via coordinator.get_maker_statistics()")
    print("  4. Test with: python3 tests/test_maker_swarm_integration.py")
    print("\nDocumentation:")
    print("  - docs/MAKER_SWARM_INTEGRATION.md")
    print("  - docs/MAKER_INTEGRATION_COMPLETE.md")


if __name__ == "__main__":
    asyncio.run(demo())
