#!/usr/bin/env python3
"""
Import existing GAIA results into AVIR cluster format.

Converts GAIA benchmark output to AVIR cluster format and broadcasts to other nodes.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))

from gaia_avir_cluster import (
    GAIAAVIRClusterVerifier,
    GAIATaskResult,
    NodeGAIAResults,
    CLUSTER_NODES
)
from avir_node_messenger import AVIRNodeMessenger

logger = logging.getLogger(__name__)


def convert_gaia_results(gaia_file: Path, node_id: str) -> NodeGAIAResults:
    """
    Convert standard GAIA results JSON to AVIR cluster format.
    """
    with open(gaia_file) as f:
        data = json.load(f)

    task_results = []
    for r in data.get("results", []):
        task_results.append(GAIATaskResult(
            task_id=r["task_id"],
            question=r["question"][:300],  # Truncate for storage
            expected_answer=r["expected_answer"],
            node_answer=r["agent_answer"],
            is_correct=r["is_correct"],
            confidence=0.85 if r["is_correct"] else 0.4,  # Estimate confidence
            execution_time_seconds=r.get("execution_time_seconds", 0),
            tools_used=r.get("tools_used", []),
            node_id=node_id,
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
        ))

    return NodeGAIAResults(
        node_id=node_id,
        node_role=CLUSTER_NODES.get(node_id, {}).get("role", "unknown"),
        level=data.get("level", 1),
        total_tasks=data.get("total_tasks", len(task_results)),
        correct=data.get("correct", sum(1 for r in task_results if r.is_correct)),
        accuracy=data.get("accuracy", 0) / 100 if data.get("accuracy", 0) > 1 else data.get("accuracy", 0),
        results=task_results,
        timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat())
    )


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Import GAIA results to AVIR cluster")
    parser.add_argument("gaia_file", type=Path, help="Path to GAIA results JSON file")
    parser.add_argument("--node-id", type=str, help="Override node ID (default: auto-detect)")
    parser.add_argument("--broadcast", action="store_true", help="Broadcast to other nodes")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if not args.gaia_file.exists():
        logger.error(f"File not found: {args.gaia_file}")
        sys.exit(1)

    # Initialize verifier to detect node
    verifier = GAIAAVIRClusterVerifier()
    node_id = args.node_id or verifier.current_node

    logger.info(f"Importing results from {args.gaia_file} for node {node_id}")

    # Convert results
    node_results = convert_gaia_results(args.gaia_file, node_id)

    # Display summary
    print(f"\nImported GAIA Results for {node_id}")
    print("-" * 50)
    print(f"Level: {node_results.level}")
    print(f"Total Tasks: {node_results.total_tasks}")
    print(f"Correct: {node_results.correct}")
    print(f"Accuracy: {node_results.accuracy:.1%}")
    print(f"Role: {node_results.node_role}")

    # Save to cluster format
    await verifier.broadcast_results(node_results)
    print(f"\nSaved to cluster format at {verifier.results_dir}")

    # Broadcast if requested
    if args.broadcast:
        messenger = AVIRNodeMessenger()
        success = await messenger.send_gaia_results(node_results.to_dict())
        if success:
            print("Broadcast to other nodes: SUCCESS")
        else:
            print("Broadcast to other nodes: FAILED (files saved for manual sync)")

    # Show verification status
    print("\n--- Cluster Verification Status ---")
    await verifier.collect_node_results()
    for nid, results in verifier.node_results.items():
        print(f"  {nid}: {results.accuracy:.1%} ({results.correct}/{results.total_tasks})")

    if len(verifier.node_results) >= 2:
        print("\nReady for cross-verification! Run:")
        print("  python gaia_avir_cluster.py verify")
    else:
        print(f"\nNeed results from {2 - len(verifier.node_results)} more node(s) for cross-verification")


if __name__ == "__main__":
    asyncio.run(main())
