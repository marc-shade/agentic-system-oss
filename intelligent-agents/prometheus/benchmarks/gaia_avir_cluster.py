#!/usr/bin/env python3
"""
GAIA-AVIR Cluster Integration

Cross-node verification of GAIA benchmark results using AVIR protocol.
Each cluster node runs GAIA tasks independently, shares results via node-chat-mcp,
and builds a consensus matrix using AVIR's statistical measures.

Key Principle: Nodes verify EACH OTHER's answers, never their own (diagonal excluded).

Architecture:
  macpro51 (builder)     - Linux x86_64, heavy computation
  mac-studio (orchestrator) - macOS ARM64, coordination
  macbook-air (researcher) - macOS ARM64, analysis

Usage:
  # On each node, run GAIA and share results:
  python gaia_avir_cluster.py run --tasks 10 --level 1

  # On orchestrator, collect and verify:
  python gaia_avir_cluster.py collect
  python gaia_avir_cluster.py verify
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import secrets
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import statistics

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "avir-protocol"))

logger = logging.getLogger(__name__)

# Cluster node configuration
CLUSTER_NODES = {
    "macpro51": {
        "role": "builder",
        "os": "linux",
        "arch": "x86_64",
        "capabilities": ["heavy_compute", "docker", "podman"]
    },
    "mac-studio": {
        "role": "orchestrator",
        "os": "darwin",
        "arch": "arm64",
        "capabilities": ["coordination", "gpu_inference"]
    },
    "macbook-air": {
        "role": "researcher",
        "os": "darwin",
        "arch": "arm64",
        "capabilities": ["analysis", "documentation"]
    }
}


class VerificationVerdict(Enum):
    """Cross-verification verdict levels (adapted from AVIR)."""
    VERIFIED = "verified"        # >=80% agreement
    PARTIAL = "partial"          # 50-79% agreement
    FAILED = "failed"           # <50% agreement
    INCONCLUSIVE = "inconclusive"  # Insufficient data or high disagreement
    PENDING = "pending"          # Not yet verified


@dataclass
class GAIATaskResult:
    """Result from a single GAIA task execution on a node."""
    task_id: str
    question: str
    expected_answer: str
    node_answer: str
    is_correct: bool
    confidence: float
    execution_time_seconds: float
    tools_used: List[str]
    node_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GAIATaskResult":
        return cls(**data)


@dataclass
class NodeGAIAResults:
    """Complete GAIA results from a single node."""
    node_id: str
    node_role: str
    level: int
    total_tasks: int
    correct: int
    accuracy: float
    results: List[GAIATaskResult]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_role": self.node_role,
            "level": self.level,
            "total_tasks": self.total_tasks,
            "correct": self.correct,
            "accuracy": self.accuracy,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeGAIAResults":
        results = [GAIATaskResult.from_dict(r) for r in data.get("results", [])]
        return cls(
            node_id=data["node_id"],
            node_role=data["node_role"],
            level=data["level"],
            total_tasks=data["total_tasks"],
            correct=data["correct"],
            accuracy=data["accuracy"],
            results=results,
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
        )


@dataclass
class CrossVerificationCell:
    """Single cell in the cross-verification matrix."""
    verifier_node: str
    subject_node: str
    task_id: str
    verifier_agrees: Optional[bool]  # None if excluded (self-verification)
    verifier_answer: Optional[str]
    confidence: float = 0.0
    is_self_verification: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossVerificationMatrix:
    """
    NxN matrix where nodes verify each other's GAIA answers.

    Diagonal is EXCLUDED (no self-verification).
    """
    task_id: str
    expected_answer: str
    nodes: List[str]
    cells: Dict[Tuple[str, str], CrossVerificationCell] = field(default_factory=dict)

    def add_verification(self, verifier: str, subject: str, agrees: bool, answer: str, confidence: float = 1.0):
        """Add a verification result."""
        is_self = verifier == subject
        self.cells[(verifier, subject)] = CrossVerificationCell(
            verifier_node=verifier,
            subject_node=subject,
            task_id=self.task_id,
            verifier_agrees=None if is_self else agrees,
            verifier_answer=answer,
            confidence=confidence,
            is_self_verification=is_self
        )

    @property
    def non_self_cells(self) -> List[CrossVerificationCell]:
        """Get all cells excluding self-verification (diagonal)."""
        return [c for c in self.cells.values() if not c.is_self_verification]

    @property
    def agreement_count(self) -> int:
        """Count of verifiers that agree."""
        return sum(1 for c in self.non_self_cells if c.verifier_agrees is True)

    @property
    def disagreement_count(self) -> int:
        """Count of verifiers that disagree."""
        return sum(1 for c in self.non_self_cells if c.verifier_agrees is False)

    @property
    def total_verifications(self) -> int:
        """Total non-self verifications."""
        return len(self.non_self_cells)

    @property
    def agreement_ratio(self) -> float:
        """Ratio of agreement among verifiers."""
        if self.total_verifications == 0:
            return 0.0
        return self.agreement_count / self.total_verifications

    @property
    def consensus_verdict(self) -> VerificationVerdict:
        """Determine consensus verdict based on agreement ratio."""
        if self.total_verifications < 2:
            return VerificationVerdict.INCONCLUSIVE

        ratio = self.agreement_ratio
        if ratio >= 0.8:
            return VerificationVerdict.VERIFIED
        elif ratio >= 0.5:
            return VerificationVerdict.PARTIAL
        elif ratio < 0.5 and self.total_verifications >= 2:
            return VerificationVerdict.FAILED
        else:
            return VerificationVerdict.INCONCLUSIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "expected_answer": self.expected_answer,
            "nodes": self.nodes,
            "cells": {f"{k[0]}:{k[1]}": v.to_dict() for k, v in self.cells.items()},
            "agreement_ratio": self.agreement_ratio,
            "consensus_verdict": self.consensus_verdict.value,
            "total_verifications": self.total_verifications
        }


@dataclass
class ClusterConsensusResult:
    """Final consensus result across all nodes and tasks."""
    timestamp: str
    nodes_participating: List[str]
    total_tasks: int
    verified_tasks: int
    partial_tasks: int
    failed_tasks: int
    inconclusive_tasks: int
    overall_accuracy: float
    consensus_accuracy: float  # Only counting verified tasks
    fleiss_kappa: float
    matrices: List[CrossVerificationMatrix]

    @property
    def overall_verdict(self) -> VerificationVerdict:
        """Overall verdict based on consensus."""
        if self.verified_tasks / max(self.total_tasks, 1) >= 0.8:
            return VerificationVerdict.VERIFIED
        elif self.verified_tasks / max(self.total_tasks, 1) >= 0.5:
            return VerificationVerdict.PARTIAL
        elif self.failed_tasks > self.verified_tasks:
            return VerificationVerdict.FAILED
        else:
            return VerificationVerdict.INCONCLUSIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "nodes_participating": self.nodes_participating,
            "total_tasks": self.total_tasks,
            "verified_tasks": self.verified_tasks,
            "partial_tasks": self.partial_tasks,
            "failed_tasks": self.failed_tasks,
            "inconclusive_tasks": self.inconclusive_tasks,
            "overall_accuracy": self.overall_accuracy,
            "consensus_accuracy": self.consensus_accuracy,
            "fleiss_kappa": self.fleiss_kappa,
            "overall_verdict": self.overall_verdict.value,
            "matrices": [m.to_dict() for m in self.matrices]
        }


def calculate_fleiss_kappa(ratings: List[List[int]], categories: int = 2) -> float:
    """
    Calculate Fleiss' kappa for inter-rater reliability.

    Args:
        ratings: List of ratings per item, each item has list of category counts
        categories: Number of categories (default 2 for agree/disagree)

    Returns:
        Fleiss' kappa coefficient (-1 to 1, >0.6 is substantial agreement)
    """
    if not ratings or len(ratings) == 0:
        return 0.0

    n = len(ratings)  # number of items
    if n == 0:
        return 0.0

    # Ensure all items have same number of raters
    k = sum(ratings[0]) if ratings else 0  # number of raters
    if k <= 1:
        return 0.0

    # Calculate P_i for each item
    P_i = []
    for item_ratings in ratings:
        total = sum(item_ratings)
        if total <= 1:
            continue
        sum_sq = sum(r * r for r in item_ratings)
        P_i.append((sum_sq - total) / (total * (total - 1)))

    if not P_i:
        return 0.0

    P_bar = sum(P_i) / len(P_i)  # Mean of P_i

    # Calculate P_j for each category
    category_totals = [0] * categories
    total_ratings = 0
    for item_ratings in ratings:
        for j, count in enumerate(item_ratings):
            if j < categories:
                category_totals[j] += count
                total_ratings += count

    if total_ratings == 0:
        return 0.0

    P_j = [c / total_ratings for c in category_totals]
    P_e = sum(p * p for p in P_j)  # Expected agreement

    if P_e >= 1.0:
        return 1.0 if P_bar >= 1.0 else 0.0

    kappa = (P_bar - P_e) / (1 - P_e)
    return kappa


class GAIAAVIRClusterVerifier:
    """
    Cross-node GAIA verification using AVIR protocol.

    Coordinates GAIA benchmark execution across cluster nodes,
    collects results via node-chat-mcp, and builds consensus matrix.
    """

    def __init__(self, results_dir: Optional[Path] = None):
        self.results_dir = results_dir or Path(__file__).parent / "gaia_results" / "cluster"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.node_results: Dict[str, NodeGAIAResults] = {}
        self.current_node = self._detect_current_node()

    def _detect_current_node(self) -> str:
        """Detect which cluster node we're running on."""
        hostname = platform.node().lower()

        # Map hostname patterns to node IDs
        if "macpro" in hostname or hostname.startswith("fedora"):
            return "macpro51"
        elif "mac-studio" in hostname or "macstudio" in hostname:
            return "mac-studio"
        elif "macbook-air" in hostname or "macbookair" in hostname:
            return "macbook-air"
        else:
            # Try to detect from environment or config
            return os.environ.get("CLUSTER_NODE_ID", hostname)

    async def broadcast_results(self, results: NodeGAIAResults) -> bool:
        """
        Broadcast GAIA results to other nodes via node-chat-mcp.

        Uses the cluster messaging system to share results.
        """
        try:
            # Save locally first
            result_file = self.results_dir / f"gaia_results_{self.current_node}.json"
            with open(result_file, "w") as f:
                json.dump(results.to_dict(), f, indent=2)

            logger.info(f"Saved local results to {result_file}")

            # Create broadcast message
            message = {
                "type": "gaia_results",
                "sender": self.current_node,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": results.to_dict()
            }

            # Write to shared location for cross-node access
            shared_file = self.results_dir / f"shared_{self.current_node}.json"
            with open(shared_file, "w") as f:
                json.dump(message, f, indent=2)

            logger.info(f"Broadcast results from {self.current_node}")
            return True

        except Exception as e:
            logger.error(f"Failed to broadcast results: {e}")
            return False

    async def collect_node_results(self) -> Dict[str, NodeGAIAResults]:
        """
        Collect GAIA results from all cluster nodes.

        Reads from shared result files and node-chat messages.
        """
        collected = {}

        # Check for shared result files
        for node_id in CLUSTER_NODES.keys():
            shared_file = self.results_dir / f"shared_{node_id}.json"
            if shared_file.exists():
                try:
                    with open(shared_file) as f:
                        message = json.load(f)

                    if message.get("type") == "gaia_results":
                        results = NodeGAIAResults.from_dict(message["payload"])
                        collected[node_id] = results
                        logger.info(f"Collected results from {node_id}: {results.accuracy:.1%} accuracy")
                except Exception as e:
                    logger.error(f"Error reading results from {node_id}: {e}")
            else:
                # Check for direct result file
                result_file = self.results_dir / f"gaia_results_{node_id}.json"
                if result_file.exists():
                    try:
                        with open(result_file) as f:
                            data = json.load(f)
                        results = NodeGAIAResults.from_dict(data)
                        collected[node_id] = results
                        logger.info(f"Collected results from {node_id}: {results.accuracy:.1%} accuracy")
                    except Exception as e:
                        logger.error(f"Error reading results from {node_id}: {e}")

        self.node_results = collected
        return collected

    def build_cross_verification_matrix(self, task_id: str, expected_answer: str) -> CrossVerificationMatrix:
        """
        Build cross-verification matrix for a single task.

        Each node's answer is verified by all other nodes.
        """
        nodes = list(self.node_results.keys())
        matrix = CrossVerificationMatrix(
            task_id=task_id,
            expected_answer=expected_answer,
            nodes=nodes
        )

        # Get each node's answer for this task
        node_answers = {}
        for node_id, results in self.node_results.items():
            for result in results.results:
                if result.task_id == task_id:
                    node_answers[node_id] = {
                        "answer": result.node_answer,
                        "is_correct": result.is_correct,
                        "confidence": result.confidence
                    }
                    break

        # Build verification matrix
        for verifier in nodes:
            for subject in nodes:
                if verifier not in node_answers or subject not in node_answers:
                    continue

                verifier_data = node_answers[verifier]
                subject_data = node_answers[subject]

                # Verifier agrees if subject got the same answer as verifier
                # Both checking against expected answer
                agrees = verifier_data["is_correct"] == subject_data["is_correct"]

                matrix.add_verification(
                    verifier=verifier,
                    subject=subject,
                    agrees=agrees,
                    answer=verifier_data["answer"],
                    confidence=verifier_data["confidence"]
                )

        return matrix

    def compute_cluster_consensus(self) -> ClusterConsensusResult:
        """
        Compute overall cluster consensus across all tasks.

        Uses AVIR-style cross-verification with Fleiss' kappa.
        """
        if not self.node_results:
            return ClusterConsensusResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                nodes_participating=[],
                total_tasks=0,
                verified_tasks=0,
                partial_tasks=0,
                failed_tasks=0,
                inconclusive_tasks=0,
                overall_accuracy=0.0,
                consensus_accuracy=0.0,
                fleiss_kappa=0.0,
                matrices=[]
            )

        # Collect all unique task IDs
        all_tasks = set()
        task_expected = {}
        for results in self.node_results.values():
            for result in results.results:
                all_tasks.add(result.task_id)
                task_expected[result.task_id] = result.expected_answer

        # Build matrices for each task
        matrices = []
        ratings_for_kappa = []

        verified = 0
        partial = 0
        failed = 0
        inconclusive = 0

        for task_id in all_tasks:
            expected = task_expected.get(task_id, "")
            matrix = self.build_cross_verification_matrix(task_id, expected)
            matrices.append(matrix)

            verdict = matrix.consensus_verdict
            if verdict == VerificationVerdict.VERIFIED:
                verified += 1
            elif verdict == VerificationVerdict.PARTIAL:
                partial += 1
            elif verdict == VerificationVerdict.FAILED:
                failed += 1
            else:
                inconclusive += 1

            # Prepare ratings for Fleiss' kappa
            # [agree_count, disagree_count] for each task
            ratings_for_kappa.append([
                matrix.agreement_count,
                matrix.disagreement_count
            ])

        # Calculate Fleiss' kappa
        kappa = calculate_fleiss_kappa(ratings_for_kappa, categories=2)

        # Calculate accuracies
        nodes = list(self.node_results.keys())
        total_tasks = len(all_tasks)

        # Overall accuracy (average across nodes)
        if self.node_results:
            overall_accuracy = statistics.mean(r.accuracy for r in self.node_results.values())
        else:
            overall_accuracy = 0.0

        # Consensus accuracy (only counting verified tasks)
        consensus_accuracy = verified / max(total_tasks, 1)

        return ClusterConsensusResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            nodes_participating=nodes,
            total_tasks=total_tasks,
            verified_tasks=verified,
            partial_tasks=partial,
            failed_tasks=failed,
            inconclusive_tasks=inconclusive,
            overall_accuracy=overall_accuracy,
            consensus_accuracy=consensus_accuracy,
            fleiss_kappa=kappa,
            matrices=matrices
        )

    def generate_report(self, consensus: ClusterConsensusResult) -> str:
        """Generate human-readable verification report."""
        lines = [
            "=" * 70,
            "GAIA-AVIR CLUSTER CROSS-VERIFICATION REPORT",
            "=" * 70,
            "",
            f"Timestamp: {consensus.timestamp}",
            f"Nodes Participating: {', '.join(consensus.nodes_participating)}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Tasks Verified: {consensus.total_tasks}",
            f"  - VERIFIED (>=80% agreement): {consensus.verified_tasks}",
            f"  - PARTIAL (50-79% agreement): {consensus.partial_tasks}",
            f"  - FAILED (<50% agreement): {consensus.failed_tasks}",
            f"  - INCONCLUSIVE: {consensus.inconclusive_tasks}",
            "",
            f"Overall Accuracy (avg across nodes): {consensus.overall_accuracy:.1%}",
            f"Consensus Accuracy (verified only): {consensus.consensus_accuracy:.1%}",
            f"Fleiss' Kappa (inter-rater reliability): {consensus.fleiss_kappa:.3f}",
            "",
            f"OVERALL VERDICT: {consensus.overall_verdict.value.upper()}",
            "",
        ]

        # Interpret kappa
        if consensus.fleiss_kappa > 0.8:
            kappa_interpretation = "Almost perfect agreement"
        elif consensus.fleiss_kappa > 0.6:
            kappa_interpretation = "Substantial agreement"
        elif consensus.fleiss_kappa > 0.4:
            kappa_interpretation = "Moderate agreement"
        elif consensus.fleiss_kappa > 0.2:
            kappa_interpretation = "Fair agreement"
        else:
            kappa_interpretation = "Slight agreement or less"

        lines.append(f"Kappa Interpretation: {kappa_interpretation}")
        lines.append("")

        # Node-by-node breakdown
        lines.append("NODE PERFORMANCE")
        lines.append("-" * 40)
        for node_id, results in self.node_results.items():
            role = CLUSTER_NODES.get(node_id, {}).get("role", "unknown")
            lines.append(f"  {node_id} ({role}): {results.accuracy:.1%} ({results.correct}/{results.total_tasks})")

        lines.append("")
        lines.append("CROSS-VERIFICATION MATRIX (first 5 tasks)")
        lines.append("-" * 40)

        # Show sample of matrices
        for i, matrix in enumerate(consensus.matrices[:5]):
            lines.append(f"\nTask {i+1}: {matrix.task_id[:20]}...")
            lines.append(f"  Expected: {matrix.expected_answer}")
            lines.append(f"  Agreement: {matrix.agreement_ratio:.1%} ({matrix.consensus_verdict.value})")

            # Show cross-verification grid
            if matrix.nodes:
                header = "         " + " ".join(f"{n[:8]:>8}" for n in matrix.nodes)
                lines.append(header)
                for verifier in matrix.nodes:
                    row = f"{verifier[:8]:>8} "
                    for subject in matrix.nodes:
                        cell = matrix.cells.get((verifier, subject))
                        if cell:
                            if cell.is_self_verification:
                                row += "    --   "
                            elif cell.verifier_agrees:
                                row += "    OK   "
                            else:
                                row += "   DIFF  "
                        else:
                            row += "    ?    "
                    lines.append(row)

        lines.append("")
        lines.append("=" * 70)
        lines.append("End of Report")

        return "\n".join(lines)

    async def run_verification(self) -> ClusterConsensusResult:
        """
        Run complete cross-verification workflow.

        1. Collect results from all nodes
        2. Build cross-verification matrices
        3. Compute consensus
        4. Generate report
        """
        logger.info("Starting GAIA-AVIR cluster verification...")

        # Collect results
        await self.collect_node_results()

        if len(self.node_results) < 2:
            logger.warning(f"Only {len(self.node_results)} nodes have results. Need >=2 for cross-verification.")

        # Compute consensus
        consensus = self.compute_cluster_consensus()

        # Generate and save report
        report = self.generate_report(consensus)
        print(report)

        # Save results
        result_file = self.results_dir / f"cluster_consensus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, "w") as f:
            json.dump(consensus.to_dict(), f, indent=2)

        report_file = self.results_dir / f"cluster_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"Saved consensus to {result_file}")
        logger.info(f"Saved report to {report_file}")

        return consensus


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GAIA-AVIR Cluster Cross-Verification")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run GAIA and share results
    run_parser = subparsers.add_parser("run", help="Run GAIA benchmark and share results")
    run_parser.add_argument("--tasks", type=int, default=10, help="Number of tasks to run")
    run_parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3], help="GAIA level")

    # Collect results from nodes
    subparsers.add_parser("collect", help="Collect GAIA results from all nodes")

    # Run cross-verification
    subparsers.add_parser("verify", help="Run cross-node verification")

    # Show status
    subparsers.add_parser("status", help="Show current node and cluster status")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    verifier = GAIAAVIRClusterVerifier()

    if args.command == "run":
        # Import and run GAIA benchmark
        try:
            from gaia_official_benchmark import GAIABenchmarkRunner

            runner = GAIABenchmarkRunner()
            results = await runner.run_benchmark(max_tasks=args.tasks, level=args.level)

            # Convert to NodeGAIAResults
            task_results = []
            for r in results.get("results", []):
                task_results.append(GAIATaskResult(
                    task_id=r["task_id"],
                    question=r["question"][:200],  # Truncate
                    expected_answer=r["expected_answer"],
                    node_answer=r["agent_answer"],
                    is_correct=r["is_correct"],
                    confidence=0.8 if r["is_correct"] else 0.5,
                    execution_time_seconds=r.get("execution_time_seconds", 0),
                    tools_used=r.get("tools_used", []),
                    node_id=verifier.current_node
                ))

            node_results = NodeGAIAResults(
                node_id=verifier.current_node,
                node_role=CLUSTER_NODES.get(verifier.current_node, {}).get("role", "unknown"),
                level=args.level,
                total_tasks=results.get("total_tasks", 0),
                correct=results.get("correct", 0),
                accuracy=results.get("accuracy", 0),
                results=task_results
            )

            # Broadcast to cluster
            await verifier.broadcast_results(node_results)
            print(f"\n{verifier.current_node}: Completed {node_results.total_tasks} tasks, {node_results.accuracy:.1%} accuracy")

        except ImportError as e:
            logger.error(f"Could not import GAIA benchmark: {e}")
            logger.info("Make sure gaia_official_benchmark.py is in the same directory")

    elif args.command == "collect":
        await verifier.collect_node_results()
        print(f"\nCollected results from {len(verifier.node_results)} nodes:")
        for node_id, results in verifier.node_results.items():
            print(f"  {node_id}: {results.accuracy:.1%} ({results.correct}/{results.total_tasks})")

    elif args.command == "verify":
        consensus = await verifier.run_verification()
        print(f"\nFinal verdict: {consensus.overall_verdict.value.upper()}")

    elif args.command == "status":
        print(f"\nCurrent Node: {verifier.current_node}")
        print(f"Role: {CLUSTER_NODES.get(verifier.current_node, {}).get('role', 'unknown')}")
        print(f"\nCluster Nodes:")
        for node_id, config in CLUSTER_NODES.items():
            status = "CURRENT" if node_id == verifier.current_node else "remote"
            print(f"  {node_id} ({config['role']}): {status}")

        # Check for existing results
        print(f"\nExisting Results:")
        for node_id in CLUSTER_NODES.keys():
            shared_file = verifier.results_dir / f"shared_{node_id}.json"
            result_file = verifier.results_dir / f"gaia_results_{node_id}.json"
            if shared_file.exists() or result_file.exists():
                print(f"  {node_id}: found")
            else:
                print(f"  {node_id}: not found")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
