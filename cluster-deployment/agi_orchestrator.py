#!/usr/bin/env python3
"""
AGI Orchestrator - Coordinates autonomous multi-node intelligence

Enables:
- Autonomous research-to-implementation pipelines
- Distributed problem-solving via node conversations
- Self-improvement coordination
- Knowledge synthesis across nodes
- Collective decision-making
"""
import os
import platform

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import subprocess
import sys


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        macos_primary = Path("/Volumes/SSDRAID0/agentic-system")
        macos_fallback = Path("/Volumes/FILES/agentic-system")
        if macos_primary.exists():
            return macos_primary
        elif macos_fallback.exists():
            return macos_fallback
    elif system == "Linux":
        linux_primary = Path("/home/marc/agentic-system")
        linux_fallback = Path("/mnt/agentic-system")
        if linux_primary.exists():
            return linux_primary
        elif linux_fallback.exists():
            return linux_fallback
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


class AGIOrchestrator:
    """
    Coordinates AGI-level capabilities across the cluster.

    Responsibilities:
    - Autonomous goal decomposition
    - Multi-node task coordination via chat
    - Research paper integration
    - Self-improvement cycles
    - Collective learning coordination
    """

    def __init__(self, storage_base: str = str(_STORAGE_BASE)):
        self.storage_base = Path(storage_base)
        self.chat_db = self.storage_base / "databases/cluster/node_chat.db"
        self.memory_db = self.storage_base / "databases/mcp/enhanced_memories.db"

        # Node capabilities mapping
        self.node_capabilities = {
            "macpro51": {
                "specialties": ["compilation", "testing", "containerization", "performance", "rust", "c++"],
                "persona": "Builder",
                "style": "pragmatic and direct"
            },
            "mac-studio": {
                "specialties": ["coordination", "planning", "resource-allocation", "monitoring"],
                "persona": "Phoenix (Orchestrator)",
                "style": "strategic and comprehensive"
            },
            "macbook-air-m3": {
                "specialties": ["research", "documentation", "analysis", "knowledge-synthesis"],
                "persona": "Researcher",
                "style": "analytical and thorough"
            }
        }

    def decompose_goal(self, goal: str, node_id: str) -> Dict:
        """
        Decompose a complex goal into coordinated multi-node tasks.

        Uses distributed reasoning to break down goal optimally.

        Args:
            goal: High-level objective
            node_id: Which node is initiating

        Returns:
            Decomposition with node assignments
        """
        # Analyze goal to determine required capabilities
        required_capabilities = self._analyze_goal_requirements(goal)

        # Match capabilities to nodes
        node_assignments = self._assign_to_optimal_nodes(required_capabilities)

        # Create coordination plan
        plan = {
            "goal": goal,
            "initiated_by": node_id,
            "timestamp": datetime.now().isoformat(),
            "tasks": node_assignments,
            "coordination_strategy": "parallel" if len(node_assignments) > 1 else "sequential"
        }

        return plan

    def _analyze_goal_requirements(self, goal: str) -> List[str]:
        """Analyze what capabilities are needed for this goal."""
        goal_lower = goal.lower()

        capabilities = []

        # Research needed?
        if any(word in goal_lower for word in ["research", "investigate", "find", "discover", "learn about"]):
            capabilities.append("research")

        # Implementation needed?
        if any(word in goal_lower for word in ["implement", "build", "create", "develop", "code"]):
            capabilities.append("compilation")
            capabilities.append("testing")

        # Performance work?
        if any(word in goal_lower for word in ["optimize", "faster", "performance", "benchmark"]):
            capabilities.append("performance")

        # Documentation?
        if any(word in goal_lower for word in ["document", "explain", "describe", "catalog"]):
            capabilities.append("documentation")

        # Planning/coordination?
        if any(word in goal_lower for word in ["plan", "coordinate", "organize", "manage"]):
            capabilities.append("planning")

        return capabilities if capabilities else ["general"]

    def _assign_to_optimal_nodes(self, capabilities: List[str]) -> List[Dict]:
        """Assign capabilities to best-fit nodes."""
        assignments = []

        for capability in capabilities:
            # Find node with this capability
            best_node = None
            for node_id, node_info in self.node_capabilities.items():
                if capability in node_info["specialties"]:
                    best_node = node_id
                    break

            if best_node:
                assignments.append({
                    "node": best_node,
                    "capability": capability,
                    "persona": self.node_capabilities[best_node]["persona"]
                })
            else:
                # Default to orchestrator for general tasks
                assignments.append({
                    "node": "mac-studio",
                    "capability": capability,
                    "persona": "Orchestrator"
                })

        return assignments

    def coordinate_research_implementation(self, research_topic: str) -> Dict:
        """
        Autonomous research-to-implementation pipeline.

        1. Researcher searches papers
        2. Researcher summarizes findings
        3. Orchestrator evaluates applicability
        4. Builder implements if approved
        5. Results stored in cluster memory

        Args:
            research_topic: What to research

        Returns:
            Pipeline status and results
        """
        pipeline = {
            "topic": research_topic,
            "initiated": datetime.now().isoformat(),
            "stages": []
        }

        # Stage 1: Research (Researcher node)
        pipeline["stages"].append({
            "stage": "research",
            "node": "macbook-air-m3",
            "action": "search_papers_and_extract_insights",
            "status": "pending"
        })

        # Stage 2: Evaluation (Orchestrator node)
        pipeline["stages"].append({
            "stage": "evaluation",
            "node": "mac-studio",
            "action": "assess_applicability_to_system",
            "status": "pending"
        })

        # Stage 3: Implementation (Builder node)
        pipeline["stages"].append({
            "stage": "implementation",
            "node": "macpro51",
            "action": "implement_and_test",
            "status": "pending"
        })

        # Stage 4: Consolidation (All nodes)
        pipeline["stages"].append({
            "stage": "consolidation",
            "node": "all",
            "action": "store_knowledge_in_cluster_memory",
            "status": "pending"
        })

        return pipeline

    def initiate_self_improvement_cycle(self, target_metric: str) -> Dict:
        """
        Coordinate a self-improvement cycle across nodes.

        1. Baseline measurement (Builder)
        2. Weakness identification (Orchestrator)
        3. Solution research (Researcher)
        4. Implementation (Builder)
        5. Validation (All)
        6. Consolidation (All)

        Args:
            target_metric: What to improve (e.g., "memory_consolidation_speed")

        Returns:
            Improvement cycle plan
        """
        cycle = {
            "metric": target_metric,
            "cycle_number": self._get_next_cycle_number(),
            "initiated": datetime.now().isoformat(),
            "phases": []
        }

        # Phase 1: Baseline
        cycle["phases"].append({
            "phase": "baseline",
            "node": "macpro51",
            "action": f"benchmark_current_{target_metric}",
            "expected_output": "performance metrics"
        })

        # Phase 2: Analysis
        cycle["phases"].append({
            "phase": "analysis",
            "node": "mac-studio",
            "action": "identify_bottlenecks_and_weaknesses",
            "expected_output": "weakness list"
        })

        # Phase 3: Research
        cycle["phases"].append({
            "phase": "research",
            "node": "macbook-air-m3",
            "action": "search_optimization_techniques",
            "expected_output": "solution proposals"
        })

        # Phase 4: Implementation
        cycle["phases"].append({
            "phase": "implementation",
            "node": "macpro51",
            "action": "apply_optimizations",
            "expected_output": "modified system"
        })

        # Phase 5: Validation
        cycle["phases"].append({
            "phase": "validation",
            "node": "macpro51",
            "action": "measure_improvement",
            "expected_output": "new metrics"
        })

        # Phase 6: Consolidation
        cycle["phases"].append({
            "phase": "consolidation",
            "node": "all",
            "action": "store_learnings_and_update_procedures",
            "expected_output": "updated knowledge base"
        })

        return cycle

    def _get_next_cycle_number(self) -> int:
        """Get next self-improvement cycle number."""
        # Check memory DB for previous cycles
        try:
            conn = sqlite3.connect(self.memory_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM entities
                WHERE name LIKE 'improvement_cycle_%'
            """)
            count = cursor.fetchone()[0]
            conn.close()
            return count + 1
        except:
            return 1

    def send_coordination_message(self, from_node: str, to_node: str,
                                  message: str, context: Dict = None) -> Dict:
        """
        Send a coordination message via node chat.

        Args:
            from_node: Sending node ID
            to_node: Receiving node ID
            message: Message content
            context: Optional context dict

        Returns:
            Delivery status
        """
        # Use node_chat_client
        sys.path.insert(0, str(self.storage_base / "cluster-deployment"))
        from node_chat_client import NodeChatClient

        client = NodeChatClient(from_node, str(self.storage_base))
        result = client.send_message(to_node, message)

        return result

    def get_collective_decision(self, decision_point: str,
                               involved_nodes: List[str]) -> Dict:
        """
        Get collective decision from multiple nodes via conversation.

        Sends question to all nodes, collects responses, synthesizes decision.

        Args:
            decision_point: What to decide
            involved_nodes: Which nodes to consult

        Returns:
            Decision with reasoning
        """
        decision = {
            "question": decision_point,
            "consulted_nodes": involved_nodes,
            "responses": [],
            "synthesis": None,
            "timestamp": datetime.now().isoformat()
        }

        # In full implementation, this would:
        # 1. Send question to each node via chat
        # 2. Wait for responses (with timeout)
        # 3. Synthesize responses into collective decision
        # 4. Return decision with attribution

        return decision

    def monitor_autonomous_activities(self) -> Dict:
        """
        Monitor what nodes are doing autonomously.

        Returns:
            Current autonomous activities across cluster
        """
        activities = {
            "timestamp": datetime.now().isoformat(),
            "active_conversations": self._get_active_conversations(),
            "ongoing_tasks": self._get_ongoing_tasks(),
            "recent_decisions": self._get_recent_decisions()
        }

        return activities

    def _get_active_conversations(self) -> List[Dict]:
        """Get currently active node conversations."""
        try:
            conn = sqlite3.connect(self.chat_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT conversation_id, participants, context,
                       COUNT(*) as message_count,
                       MAX(timestamp) as last_activity
                FROM conversations c
                JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.active = 1
                  AND m.timestamp > datetime('now', '-1 hour')
                GROUP BY c.conversation_id
            """)

            conversations = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return conversations
        except:
            return []

    def _get_ongoing_tasks(self) -> List[Dict]:
        """Get tasks currently being executed."""
        # In full implementation, would query task execution system
        return []

    def _get_recent_decisions(self) -> List[Dict]:
        """Get recent collective decisions."""
        # In full implementation, would query decision log
        return []

    def get_system_health(self) -> Dict:
        """
        Get overall AGI system health.

        Returns:
            Health metrics across all subsystems
        """
        health = {
            "timestamp": datetime.now().isoformat(),
            "nodes": {},
            "communication": {},
            "memory": {},
            "learning": {}
        }

        # Node health
        for node_id in self.node_capabilities.keys():
            health["nodes"][node_id] = {
                "status": "unknown",  # Would check actual node status
                "last_active": None,
                "message_count": self._count_node_messages(node_id)
            }

        # Communication health
        health["communication"]["total_messages"] = self._count_total_messages()
        health["communication"]["active_conversations"] = len(self._get_active_conversations())

        return health

    def _count_node_messages(self, node_id: str) -> int:
        """Count messages from a specific node."""
        try:
            conn = sqlite3.connect(self.chat_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages WHERE from_node = ?", (node_id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def _count_total_messages(self) -> int:
        """Count total cluster messages."""
        try:
            conn = sqlite3.connect(self.chat_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0


def main():
    """CLI entry point."""
    import sys

    orchestrator = AGIOrchestrator()

    if len(sys.argv) < 2:
        print("Usage: agi_orchestrator.py <command> [args]")
        print("\nCommands:")
        print("  decompose <goal> <node_id>")
        print("  research <topic>")
        print("  improve <metric>")
        print("  health")
        print("  monitor")
        sys.exit(1)

    command = sys.argv[1]

    if command == "decompose":
        goal = sys.argv[2]
        node_id = sys.argv[3] if len(sys.argv) > 3 else "mac-studio"
        result = orchestrator.decompose_goal(goal, node_id)
        print(json.dumps(result, indent=2))

    elif command == "research":
        topic = sys.argv[2]
        result = orchestrator.coordinate_research_implementation(topic)
        print(json.dumps(result, indent=2))

    elif command == "improve":
        metric = sys.argv[2]
        result = orchestrator.initiate_self_improvement_cycle(metric)
        print(json.dumps(result, indent=2))

    elif command == "health":
        result = orchestrator.get_system_health()
        print(json.dumps(result, indent=2))

    elif command == "monitor":
        result = orchestrator.monitor_autonomous_activities()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
