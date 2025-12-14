#!/usr/bin/env python3
"""
Cluster Shared Memory Blocks

Sets up shared memory blocks for cluster coordination between cluster nodes.
Node configuration is loaded from environment or config files.

Shared blocks enable real-time coordination without polling or message-passing.
"""

import os
import json
import logging
from letta_memory_blocks import MemoryBlockManager
from pathlib import Path

logger = logging.getLogger(__name__)

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


def _load_cluster_nodes() -> list:
    """Load cluster node IDs from configuration."""
    env_nodes = os.environ.get("CLUSTER_NODE_IDS")
    if env_nodes:
        try:
            return json.loads(env_nodes)
        except json.JSONDecodeError:
            pass
    config_path = Path.home() / ".claude" / "cluster-nodes.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
                return list(data.keys()) if isinstance(data, dict) else data
        except (json.JSONDecodeError, IOError):
            pass
    return ["builder", "orchestrator", "researcher"]


def _get_node_description(node_id: str) -> str:
    """Get human-readable description for a node."""
    descriptions = {
        "builder": "Linux builder node for compilation, testing, containers",
        "orchestrator": "Orchestrator node for coordination, monitoring, routing",
        "researcher": "Researcher node for analysis, documentation, research"
    }
    return descriptions.get(node_id, f"{node_id} cluster node")


def setup_cluster_shared_blocks() -> dict:
    """
    Set up shared memory blocks for cluster coordination.

    Creates:
    1. cluster_context - Active goals and coordination state
    2. cluster_status - Node health and availability
    3. cluster_learnings - Collective insights across nodes

    Returns:
        Setup results with block IDs
    """
    manager = MemoryBlockManager(DB_PATH)

    results = {
        "blocks_created": [],
        "attachments_created": []
    }

    # Load cluster nodes dynamically
    cluster_nodes = _load_cluster_nodes()

    # Build cluster configuration description
    node_descriptions = "\n".join([f"- {node_id}: {_get_node_description(node_id)}" for node_id in cluster_nodes])

    # Block 1: cluster_context (coordination state)
    context_result = manager.create_shared_block(
        label="cluster_context",
        description="Cluster-wide coordination state and active goals",
        initial_value=f"""Cluster Configuration:
{node_descriptions}

Active Goals:
- Integrate Letta memory blocks across cluster
- Implement sleeptime agent consolidation
- Enable multi-agent shared memory coordination

Status: Phase 3 in progress
Last Update: System initialization
""",
        limit=5000
    )

    if context_result["success"]:
        results["blocks_created"].append({
            "label": "cluster_context",
            "block_id": context_result["shared_block_id"]
        })
    else:
        # Block already exists, get its ID
        existing_block = manager.get_shared_block("cluster_context")
        if existing_block:
            results["blocks_created"].append({
                "label": "cluster_context",
                "block_id": existing_block["shared_block_id"]
            })

    # Build initial status string
    status_lines = "\n".join([f"- {node_id}: Online (initialized)" for node_id in cluster_nodes])

    # Block 2: cluster_status (health monitoring)
    status_result = manager.create_shared_block(
        label="cluster_status",
        description="Node health, availability, and resource status",
        initial_value=f"""Node Status:
{status_lines}

Cluster Health: All nodes operational
Network: SSH mesh configured
Services: Operational

Last Health Check: System initialization
""",
        limit=5000
    )

    if status_result["success"]:
        results["blocks_created"].append({
            "label": "cluster_status",
            "block_id": status_result["shared_block_id"]
        })
    else:
        # Block already exists, get its ID
        existing_block = manager.get_shared_block("cluster_status")
        if existing_block:
            results["blocks_created"].append({
                "label": "cluster_status",
                "block_id": existing_block["shared_block_id"]
            })

    # Block 3: cluster_learnings (collective insights)
    learnings_result = manager.create_shared_block(
        label="cluster_learnings",
        description="Collective insights and learnings across all cluster nodes",
        initial_value="",
        limit=8000  # Larger for collective learnings
    )

    if learnings_result["success"]:
        results["blocks_created"].append({
            "label": "cluster_learnings",
            "block_id": learnings_result["shared_block_id"]
        })
    else:
        # Block already exists, get its ID
        existing_block = manager.get_shared_block("cluster_learnings")
        if existing_block:
            results["blocks_created"].append({
                "label": "cluster_learnings",
                "block_id": existing_block["shared_block_id"]
            })

    # Attach blocks to all node agents
    for node_id in cluster_nodes:
        agent_id = f"{node_id}_agent"

        for block_info in results["blocks_created"]:
            attach_result = manager.attach_shared_block(
                agent_id=agent_id,
                shared_block_id=block_info["block_id"]
            )

            if attach_result["success"]:
                results["attachments_created"].append({
                    "agent_id": agent_id,
                    "block_label": block_info["label"],
                    "block_id": block_info["block_id"]
                })

    results["success"] = True
    results["total_blocks"] = len(results["blocks_created"])
    results["total_attachments"] = len(results["attachments_created"])

    logger.info(f"✅ Cluster shared blocks setup complete:")
    logger.info(f"   - {results['total_blocks']} shared blocks created")
    logger.info(f"   - {results['total_attachments']} attachments created")

    return results


def update_cluster_context(
    update: str,
    updated_by: str = None
) -> dict:
    """
    Update cluster context with new information.

    Args:
        update: Context update message
        updated_by: Node making the update

    Returns:
        Update result
    """
    import socket
    if updated_by is None:
        updated_by = os.environ.get("NODE_ID", socket.gethostname())

    manager = MemoryBlockManager(DB_PATH)
    block = manager.get_shared_block("cluster_context")

    if not block:
        return {
            "success": False,
            "error": "cluster_context block not found - run setup first"
        }

    # Append update with timestamp and attribution
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    update_text = f"\n\n[{timestamp}] {updated_by}:\n{update}"

    current_value = block["value"]
    new_value = current_value + update_text

    return manager.update_shared_block("cluster_context", new_value)


def get_cluster_overview() -> dict:
    """Get overview of all cluster shared blocks"""
    manager = MemoryBlockManager(DB_PATH)

    overview = {
        "cluster_context": manager.get_shared_block("cluster_context"),
        "cluster_status": manager.get_shared_block("cluster_status"),
        "cluster_learnings": manager.get_shared_block("cluster_learnings")
    }

    return {
        "success": True,
        "blocks": overview
    }


# Convenience function for testing
def test_cluster_shared_blocks():
    """Test cluster shared blocks setup"""
    print("Setting up cluster shared blocks...")

    # Setup
    result = setup_cluster_shared_blocks()
    print(f"\nSetup Results:")
    print(json.dumps(result, indent=2))

    # Update cluster context
    print("\nUpdating cluster context...")
    update_result = update_cluster_context(
        "Phase 3 complete - shared blocks operational across all nodes"
    )
    print(json.dumps(update_result, indent=2))

    # Get overview
    print("\nCluster Overview:")
    overview = get_cluster_overview()
    for block_label, block_data in overview["blocks"].items():
        if block_data:
            print(f"\n{block_label}:")
            print(f"  Chars: {block_data['chars_current']}/{block_data['chars_limit']}")
            print(f"  Value (first 200 chars): {block_data['value'][:200]}...")

    print("\n✓ Cluster shared blocks test complete!")


if __name__ == "__main__":
    test_cluster_shared_blocks()
