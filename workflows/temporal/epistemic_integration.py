#!/usr/bin/env python3
"""
Epistemic Flexibility Integration for Self-Improvement Workflows
================================================================

Connects Stanford Research epistemic flexibility framework with
recursive self-improvement cycles.

Integration Points:
1. Belief tracking during improvement cycles
2. Counterfactual testing for strategy validation
3. Cluster belief sharing for multi-node coordination
4. Flexibility monitoring to prevent narrative overfitting

STATUS: Production Ready
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import os

# Dynamic path detection
_current_file = os.path.abspath(__file__)
_workflows_dir = os.path.dirname(_current_file)
_base_dir = os.path.dirname(os.path.dirname(_workflows_dir))
_mcp_memory_dir = os.path.join(_base_dir, "mcp-servers", "enhanced-memory-mcp")
_agi_dir = os.path.join(_mcp_memory_dir, "agi")

sys.path.insert(0, _mcp_memory_dir)
sys.path.insert(0, _agi_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = Path.home() / ".claude" / "enhanced_memories" / "memory.db"


class EpistemicSelfImprovement:
    """
    Integrates epistemic flexibility into self-improvement cycles.

    Features:
    - Records beliefs about improvement strategies
    - Tests belief rigidity with counterfactuals
    - Shares learnings across cluster nodes
    - Monitors for narrative overfitting
    """

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id

    async def record_improvement_belief(
        self,
        belief_statement: str,
        probability: float,
        evidence: List[str],
        category: str = "strategy"
    ) -> int:
        """
        Record a belief about improvement strategy.

        Example beliefs:
        - "XGBoost is best for tabular data" (p=0.85)
        - "Larger batch sizes improve training" (p=0.6)
        - "Memory consolidation improves recall" (p=0.75)
        """
        try:
            from belief_tracking import BeliefTracker

            tracker = BeliefTracker(self.agent_id)

            # Convert evidence list to supporting_evidence format
            supporting_evidence = [
                {"description": e, "weight": 1.0, "source": "experiment"}
                for e in evidence
            ]

            belief_id = tracker.record_belief(
                belief_statement=belief_statement,
                probability=probability,
                belief_category=category,
                supporting_evidence=supporting_evidence
            )

            logger.info(f"Recorded improvement belief: {belief_statement[:50]}... (p={probability})")
            return belief_id

        except Exception as e:
            logger.error(f"Failed to record belief: {e}")
            return -1

    async def update_belief_from_experiment(
        self,
        belief_id: int,
        experiment_result: Dict[str, Any],
        new_evidence: str
    ) -> Dict[str, Any]:
        """
        Update belief probability based on experiment results.

        Uses Bayesian update: If experiment succeeded, increase probability.
        If failed, decrease probability.
        """
        try:
            from belief_tracking import BeliefTracker

            tracker = BeliefTracker(self.agent_id)

            success_score = experiment_result.get("success_score", 0.5)

            # Get current probability first
            beliefs = tracker.get_beliefs(limit=100)
            current_prob = 0.5
            for b in beliefs:
                if b.get("belief_id") == belief_id:
                    current_prob = b.get("probability", 0.5)
                    break

            # Calculate new probability based on experiment outcome
            # Strong success (+5% to +15%), weak success (+1% to +5%)
            # Failure (-5% to -15%)
            if success_score > 0.7:
                delta = 0.05 + (success_score - 0.7) * 0.33  # Up to +15%
            elif success_score > 0.5:
                delta = 0.01 + (success_score - 0.5) * 0.2  # Up to +5%
            else:
                delta = -0.05 - (0.5 - success_score) * 0.2  # Down to -15%

            new_probability = max(0.0, min(1.0, current_prob + delta))

            result = tracker.update_probability(
                belief_id=belief_id,
                new_probability=new_probability,
                revision_trigger="new_evidence",
                evidence_provided=new_evidence,
                reasoning=f"Experiment result: score={success_score:.2f}"
            )

            logger.info(f"Updated belief {belief_id} by {delta:+.2f} based on experiment")
            return result

        except Exception as e:
            logger.error(f"Failed to update belief: {e}")
            return {"error": str(e)}

    async def test_strategy_flexibility(
        self,
        strategy_belief_id: int,
        counterfactual_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test if agent can revise strategy beliefs with counterfactual evidence.

        Presents alternative evidence and measures belief revision.
        Low revision = potential narrative overfitting.
        """
        try:
            from counterfactual_testing import CounterfactualTester
            from belief_tracking import BeliefTracker

            tester = CounterfactualTester(self.agent_id)
            tracker = BeliefTracker(self.agent_id)

            # Get current belief
            beliefs = tracker.get_beliefs(limit=100)
            target_belief = None
            for b in beliefs:
                if b.get("belief_id") == strategy_belief_id:
                    target_belief = b
                    break

            if not target_belief:
                return {"error": "Belief not found"}

            # Create counterfactual scenario
            scenario_id = tester.create_scenario(
                scenario_name=f"Strategy test for belief {strategy_belief_id}",
                scenario_description="Testing flexibility of strategy belief",
                target_belief_id=strategy_belief_id,
                original_facts={
                    "belief": target_belief.get("belief_statement"),
                    "probability": target_belief.get("probability")
                },
                counterfactual_facts=counterfactual_evidence,
                expected_revision=0.3  # Expect ~30% revision with strong evidence
            )

            logger.info(f"Created counterfactual scenario {scenario_id} for belief {strategy_belief_id}")

            return {
                "scenario_id": scenario_id,
                "original_probability": target_belief.get("probability"),
                "counterfactual_evidence": counterfactual_evidence,
                "prompt": tester.generate_counterfactual_prompt(scenario_id)
            }

        except Exception as e:
            logger.error(f"Failed to create counterfactual test: {e}")
            return {"error": str(e)}

    async def get_flexibility_score(self) -> Dict[str, Any]:
        """
        Get agent's overall epistemic flexibility score.

        Monitors for narrative overfitting risk.
        Score < 0.4 = high risk, > 0.7 = healthy flexibility.
        """
        try:
            from counterfactual_testing import CounterfactualTester

            tester = CounterfactualTester(self.agent_id)
            return tester.get_epistemic_flexibility_score()

        except Exception as e:
            logger.error(f"Failed to get flexibility score: {e}")
            return {"error": str(e)}

    async def share_improvement_learning(
        self,
        learning: str,
        confidence: float,
        domain: str = "self_improvement"
    ) -> Dict[str, Any]:
        """
        Share improvement learning with cluster via shared belief blocks.

        Enables multi-node learning coordination.
        """
        try:
            from cluster_beliefs import ClusterBeliefManager

            manager = ClusterBeliefManager("agi_cluster")

            # Create belief block with learning as Dict[str, float]
            # The API expects {statement: probability}
            block_id = manager.create_belief_block(
                belief_domain="improvement_learnings",
                initial_beliefs={learning: confidence},
                description=f"Improvement learnings from {self.agent_id}"
            )

            logger.info(f"Shared learning: {learning[:50]}... (confidence={confidence})")

            return {
                "block_id": block_id,
                "learning": learning,
                "confidence": confidence,
                "shared_to": "agi_cluster"
            }

        except Exception as e:
            logger.error(f"Failed to share learning: {e}")
            return {"error": str(e)}

    async def get_cluster_learnings(
        self,
        domain: str = "improvement_learnings"
    ) -> Dict[str, Any]:
        """
        Get learnings shared by all cluster nodes.

        Aggregates knowledge from across the cluster.
        """
        try:
            from cluster_beliefs import get_cluster_belief_summary

            summary = get_cluster_belief_summary("agi_cluster")

            # Filter for improvement learnings
            blocks = summary.get("belief_blocks", [])
            improvement_blocks = [b for b in blocks if domain in b.get("belief_domain", "")]

            return {
                "cluster_learnings": improvement_blocks,
                "total_blocks": len(improvement_blocks),
                "active_nodes": summary.get("summary", {}).get("unique_contributors", 0)
            }

        except Exception as e:
            logger.error(f"Failed to get cluster learnings: {e}")
            return {"error": str(e)}

    async def run_flexibility_audit(self) -> Dict[str, Any]:
        """
        Run epistemic flexibility audit for this agent.

        Identifies:
        - Rigid beliefs needing attention
        - Areas of potential overfitting
        - Recommendations for flexibility improvement
        """
        try:
            from counterfactual_testing import run_flexibility_audit

            return run_flexibility_audit([self.agent_id])

        except Exception as e:
            logger.error(f"Failed to run flexibility audit: {e}")
            return {"error": str(e)}


async def integrate_with_improvement_cycle(
    cycle_id: int,
    cycle_type: str,
    agent_id: str = "default_agent"
) -> Dict[str, Any]:
    """
    Integrate epistemic tracking with an improvement cycle.

    Records beliefs at each phase:
    1. ASSESS: Record baseline beliefs
    2. RESEARCH: Track strategy beliefs
    3. IMPLEMENT: Record confidence in changes
    4. VALIDATE: Update beliefs with results
    5. CONSOLIDATE: Share learnings with cluster
    """
    integrator = EpistemicSelfImprovement(agent_id)

    # Record cycle start belief
    cycle_belief_id = await integrator.record_improvement_belief(
        belief_statement=f"Improvement cycle {cycle_id} ({cycle_type}) will succeed",
        probability=0.5,  # Start neutral
        evidence=[f"Starting {cycle_type} cycle", f"Cycle ID: {cycle_id}"],
        category="meta"
    )

    logger.info(f"Epistemic integration started for cycle {cycle_id}")

    return {
        "cycle_id": cycle_id,
        "cycle_belief_id": cycle_belief_id,
        "integration_status": "active",
        "flexibility_score": (await integrator.get_flexibility_score()).get("composite_flexibility_score", 0.5)
    }


async def test_integration():
    """Test epistemic integration with self-improvement."""
    print("\n" + "=" * 60)
    print("Epistemic Integration Test")
    print("=" * 60)

    integrator = EpistemicSelfImprovement("test_agent")

    # Test 1: Record belief
    print("\n[1/5] Recording improvement belief...")
    belief_id = await integrator.record_improvement_belief(
        belief_statement="Memory consolidation improves retention",
        probability=0.75,
        evidence=["Stanford research", "Empirical testing"],
        category="strategy"
    )
    print(f"  Created belief ID: {belief_id}")

    # Test 2: Update belief
    print("\n[2/5] Updating belief from experiment...")
    update = await integrator.update_belief_from_experiment(
        belief_id=belief_id,
        experiment_result={"success_score": 0.85, "metric": "recall"},
        new_evidence="Experiment showed 15% improvement in recall"
    )
    print(f"  Update result: {update}")

    # Test 3: Get flexibility score
    print("\n[3/5] Getting flexibility score...")
    score = await integrator.get_flexibility_score()
    print(f"  Flexibility: {score.get('composite_flexibility_score', 0):.2f}")
    print(f"  Interpretation: {score.get('interpretation', 'Unknown')}")

    # Test 4: Share learning
    print("\n[4/5] Sharing learning with cluster...")
    share = await integrator.share_improvement_learning(
        learning="Memory consolidation with 24h window is optimal",
        confidence=0.8
    )
    print(f"  Share result: block_id={share.get('block_id')}")

    # Test 5: Run flexibility audit
    print("\n[5/5] Running flexibility audit...")
    audit = await integrator.run_flexibility_audit()
    print(f"  Agents audited: {audit.get('agents_audited', 0)}")
    print(f"  Cluster health: {audit.get('cluster_health', 'Unknown')}")

    print("\n" + "=" * 60)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_integration())
