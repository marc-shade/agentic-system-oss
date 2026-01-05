"""
MCP Tools for Context Compaction (Beads-inspired).

Provides tools for:
- Viewing compaction candidates
- Running compaction cycles
- Pinning/unpinning entities
- Getting compaction stats
- Restoring compacted entities
"""

import json
from typing import Any
from ..compaction import (
    get_compaction_candidates,
    compact_entity,
    run_compaction_cycle,
    pin_entity,
    get_compaction_stats,
    restore_entity,
    TIER1_THRESHOLD_DAYS,
    TIER2_THRESHOLD_DAYS,
)
from ..config import logger


def register_compaction_tools(app: Any) -> None:
    """Register all compaction-related MCP tools."""

    @app.tool()
    async def memory_compaction_candidates(tier: int = 1, limit: int = 20) -> str:
        """
        Get entities that are candidates for compaction.

        Tier 1: Entities not accessed in 30+ days (compaction_level=0)
        Tier 2: Entities not accessed in 90+ days (compaction_level=1)

        Pinned entities are excluded.

        Args:
            tier: Target compaction tier (1 or 2)
            limit: Maximum candidates to return
        """
        try:
            candidates = get_compaction_candidates(tier=tier, limit=limit)
            return json.dumps({
                "tier": tier,
                "threshold_days": TIER1_THRESHOLD_DAYS if tier == 1 else TIER2_THRESHOLD_DAYS,
                "count": len(candidates),
                "candidates": candidates
            }, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error getting compaction candidates: {e}")
            return json.dumps({"error": str(e)})

    @app.tool()
    async def memory_compact_entity(entity_id: int, tier: int = 1) -> str:
        """
        Compact a single entity to the specified tier.

        Creates a summary of the entity's observations and marks it as compacted.
        Pinned entities cannot be compacted.

        Args:
            entity_id: ID of entity to compact
            tier: Target compaction tier (1 or 2)
        """
        try:
            result = compact_entity(entity_id=entity_id, tier=tier)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error compacting entity {entity_id}: {e}")
            return json.dumps({"error": str(e)})

    @app.tool()
    async def memory_run_compaction(dry_run: bool = True) -> str:
        """
        Run a full compaction cycle across all eligible entities.

        Identifies and optionally compacts:
        - Tier 1: Entities not accessed in 30+ days
        - Tier 2: Entities at Tier 1 not accessed in 90+ days

        Args:
            dry_run: If True (default), only report what would be compacted without making changes
        """
        try:
            result = run_compaction_cycle(dry_run=dry_run)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error running compaction cycle: {e}")
            return json.dumps({"error": str(e)})

    @app.tool()
    async def memory_pin_entity(entity_id: int, pinned: bool = True) -> str:
        """
        Pin or unpin an entity to protect it from compaction.

        Pinned entities are never automatically compacted, regardless of age.
        Use this for important/frequently referenced entities.

        Args:
            entity_id: ID of entity to pin/unpin
            pinned: True to pin (protect), False to unpin
        """
        try:
            result = pin_entity(entity_id=entity_id, pinned=pinned)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error pinning entity {entity_id}: {e}")
            return json.dumps({"error": str(e)})

    @app.tool()
    async def memory_compaction_stats() -> str:
        """
        Get statistics about compaction state across all entities.

        Returns:
        - Count of entities by compaction tier
        - Count of pinned entities
        - Number of candidates for next compaction cycle
        - Compaction thresholds
        """
        try:
            stats = get_compaction_stats()
            return json.dumps(stats, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error getting compaction stats: {e}")
            return json.dumps({"error": str(e)})

    @app.tool()
    async def memory_restore_entity(entity_id: int) -> str:
        """
        Restore a compacted entity to tier 0 (full).

        Resets compaction_level to 0 and updates last_accessed.
        The compacted_summary is preserved for reference.
        Original observations are retained if not deleted.

        Args:
            entity_id: ID of entity to restore
        """
        try:
            result = restore_entity(entity_id=entity_id)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error restoring entity {entity_id}: {e}")
            return json.dumps({"error": str(e)})

    logger.info("Registered context compaction tools (Beads-inspired)")
