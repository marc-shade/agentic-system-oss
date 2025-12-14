#!/usr/bin/env python3
"""
Cluster-Aware AGI Orchestrator
==============================

Extends the base AGIOrchestrator to integrate with the unified cluster brain,
enabling cross-node AGI coordination and learning.

Enhancements:
- Shares meta-learning insights with all nodes
- Syncs skill evolution to cluster brain
- Routes tasks to optimal nodes based on capabilities
- Shares significant outcomes cluster-wide
- Tracks AGI goals at cluster level
"""

import asyncio
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(_STORAGE_BASE / "mcp-servers" / "enhanced-memory-mcp"))

# Import base orchestrator and cluster bridge
from agi_orchestrator import AGIOrchestrator
from agi_cluster_bridge import get_agi_cluster_bridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClusterAwareAGIOrchestrator(AGIOrchestrator):
    """
    AGI Orchestrator with cluster brain integration.

    This extends the base orchestrator to:
    - Share learnings across all cluster nodes
    - Route tasks to optimal nodes
    - Track skills at cluster level
    - Coordinate goals across the cluster
    """

    def __init__(self, share_to_cluster: bool = True):
        """
        Initialize cluster-aware orchestrator.

        Args:
            share_to_cluster: Whether to share learnings to cluster brain
        """
        super().__init__()

        self.share_to_cluster = share_to_cluster
        self.bridge = get_agi_cluster_bridge()
        self.node_id = self.bridge.node_id

        logger.info(f"Cluster-Aware AGI Orchestrator initialized on {self.node_id}")

    async def execute_goal(
        self,
        goal_description: str,
        context: Optional[Dict] = None,
        record_learning: bool = True,
        propose_improvements: bool = True,
        cluster_goal_id: int = None
    ) -> Dict[str, Any]:
        """
        Execute AGI workflow with cluster brain integration.

        Args:
            goal_description: Natural language goal
            context: Optional context
            record_learning: Record to meta-learning
            propose_improvements: Analyze for improvements
            cluster_goal_id: Optional cluster brain goal to update

        Returns:
            Complete execution result with cluster sync status
        """
        start_time = datetime.now()

        # Execute base workflow
        result = await super().execute_goal(
            goal_description,
            context,
            record_learning,
            propose_improvements
        )

        # Add cluster integration phases
        if self.share_to_cluster:
            cluster_status = await self._sync_to_cluster(
                result,
                goal_description,
                context,
                cluster_goal_id
            )
            result["cluster_sync"] = cluster_status

        return result

    async def _sync_to_cluster(
        self,
        result: Dict,
        goal_description: str,
        context: Optional[Dict],
        cluster_goal_id: int = None
    ) -> Dict[str, Any]:
        """
        Sync execution results to cluster brain.

        Args:
            result: Execution result from base workflow
            goal_description: The goal that was executed
            context: Execution context
            cluster_goal_id: Optional goal ID to update

        Returns:
            Cluster sync status
        """
        sync_status = {
            "synced": True,
            "meta_learning_shared": False,
            "skills_shared": False,
            "goal_updated": False,
            "outcome_shared": False
        }

        try:
            # 1. Share meta-learning patterns
            if result.get("phases", {}).get("meta_learning", {}).get("patterns_detected", 0) > 0:
                patterns = self.meta_learning.detect_patterns(lookback_days=1)
                for pattern in patterns[:3]:  # Share top 3 patterns
                    self.bridge.share_meta_learning_insight(
                        domain=pattern.get("domain", "general"),
                        best_strategy=pattern.get("strategy", "unknown"),
                        success_rate=pattern.get("success_rate", 0.5),
                        sample_size=pattern.get("sample_size", 1)
                    )
                sync_status["meta_learning_shared"] = True
                logger.info(f"Shared {len(patterns[:3])} meta-learning patterns to cluster")

            # 2. Sync skill improvements
            skill_phase = result.get("phases", {}).get("skill_evolution", {})
            if skill_phase.get("skills_tracked", 0) > 0:
                # Get skill summary and share
                skill_name = context.get("task_type", "general") if context else "general"
                success_rate = 1.0 if result.get("success") else 0.5

                self.bridge.sync_skill_to_cluster(
                    skill_name=skill_name,
                    proficiency=success_rate,
                    source_task=goal_description[:100]
                )
                sync_status["skills_shared"] = True
                logger.info(f"Synced skill {skill_name} to cluster")

            # 3. Update cluster goal if provided
            if cluster_goal_id:
                progress = 1.0 if result.get("success") else 0.5
                self.bridge.update_goal_progress(
                    goal_id=cluster_goal_id,
                    progress=progress,
                    status="completed" if result.get("success") else "active"
                )
                sync_status["goal_updated"] = True
                logger.info(f"Updated cluster goal {cluster_goal_id} to {progress:.0%}")

            # 4. Share significant outcome
            if result.get("success") or result.get("phases", {}).get("darwin_godel", {}).get("improvement_opportunities", 0) > 0:
                self.bridge.share_significant_episode(
                    episode_summary=f"Executed: {goal_description[:80]}",
                    outcome="success" if result.get("success") else "partial",
                    significance_score=0.8 if result.get("success") else 0.6,
                    lessons_learned=[
                        f"Duration: {result.get('total_duration_seconds', 0):.1f}s",
                        f"Tasks: {result.get('phases', {}).get('goal_decomposition', {}).get('total_tasks', 0)}",
                        f"Patterns: {result.get('phases', {}).get('meta_learning', {}).get('patterns_detected', 0)}"
                    ]
                )
                sync_status["outcome_shared"] = True
                logger.info("Shared significant episode to cluster")

            # 5. Record self-improvement if Darwin Gödel found opportunities
            darwin_phase = result.get("phases", {}).get("darwin_godel", {})
            if darwin_phase.get("improvement_opportunities", 0) > 0:
                opportunities = darwin_phase.get("opportunities", [])
                for opp in opportunities[:2]:  # Share top 2
                    self.bridge.record_self_improvement(
                        improvement_type=opp.get("type", "efficiency"),
                        description=opp.get("description", "Unknown improvement"),
                        metrics_before=opp.get("metrics_before", {"baseline": 1.0}),
                        metrics_after=opp.get("metrics_after", {"baseline": 1.1}),
                        technique_used=opp.get("technique", "analysis")
                    )
                logger.info(f"Recorded {len(opportunities[:2])} self-improvement opportunities")

        except Exception as e:
            logger.error(f"Error syncing to cluster: {e}")
            sync_status["synced"] = False
            sync_status["error"] = str(e)

        return sync_status

    async def execute_cluster_goal(
        self,
        cluster_goal_id: int,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a goal from the cluster brain.

        Fetches the goal details and executes it, automatically
        updating progress in the cluster brain.

        Args:
            cluster_goal_id: Goal ID from cluster brain
            context: Additional context

        Returns:
            Execution result
        """
        # Get goal from cluster brain
        goals = self.bridge.brain.get_active_goals()
        goal = next((g for g in goals if g["id"] == cluster_goal_id), None)

        if not goal:
            return {"success": False, "error": f"Goal {cluster_goal_id} not found"}

        logger.info(f"Executing cluster goal: {goal['goal']}")

        # Execute with goal description
        result = await self.execute_goal(
            goal_description=f"{goal['goal']}. {goal.get('description', '')}",
            context=context,
            record_learning=True,
            propose_improvements=True,
            cluster_goal_id=cluster_goal_id
        )

        return result

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current cluster brain status."""
        return self.bridge.brain.get_brain_summary()

    def get_cluster_learnings(self, category: str = None) -> List[Dict]:
        """Get learnings from cluster brain."""
        return self.bridge.brain.get_learnings(category=category)

    def route_task_to_cluster(self, task_type: str, description: str) -> Dict[str, Any]:
        """Route a task to the optimal cluster node."""
        return self.bridge.route_agi_task(task_type, description)


async def demo_cluster_agi():
    """Demo the cluster-aware AGI orchestrator."""
    print("=" * 60)
    print("CLUSTER-AWARE AGI ORCHESTRATOR DEMO")
    print("=" * 60)

    orchestrator = ClusterAwareAGIOrchestrator()

    # Show cluster status
    status = orchestrator.get_cluster_status()
    print(f"\nNode: {status['this_node']['id']}")
    print(f"Role: {status['this_node']['role']}")
    print(f"Cluster Knowledge: {status['shared_knowledge']} entries")
    print(f"Cluster Goals: {status['active_goals']} active")
    print(f"Cluster Learnings: {status['shared_learnings']} shared")

    # Execute a simple goal
    print("\n--- Executing Goal ---")
    result = await orchestrator.execute_goal(
        goal_description="Analyze cluster brain integration effectiveness",
        context={"task_type": "analysis", "domain": "systems"},
        record_learning=True,
        propose_improvements=True
    )

    print(f"\nExecution Result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Duration: {result.get('total_duration_seconds', 0):.2f}s")
    print(f"  Cluster Sync: {result.get('cluster_sync', {}).get('synced')}")

    # Show cluster learnings
    learnings = orchestrator.get_cluster_learnings()
    print(f"\n--- Cluster Learnings ({len(learnings)}) ---")
    for learning in learnings[:3]:
        text = learning.get("learning", "")[:60] + "..."
        print(f"  • {text}")

    return result


if __name__ == "__main__":
    asyncio.run(demo_cluster_agi())
