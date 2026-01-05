"""
Context Compaction Module for Enhanced Memory MCP Server.

Implements Beads-inspired tiered compaction:
- Tier 0: Full content (default)
- Tier 1: Summarized after 30 days of inactivity
- Tier 2: Further compressed after 90 days

Pinned entities are protected from compaction.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from .config import DB_PATH, logger


# Compaction thresholds (in days)
TIER1_THRESHOLD_DAYS = 30
TIER2_THRESHOLD_DAYS = 90


def get_compaction_candidates(tier: int = 1, limit: int = 100) -> List[Dict]:
    """
    Get entities that are candidates for compaction.

    Tier 1 candidates: Not accessed in 30+ days, compaction_level=0, not pinned
    Tier 2 candidates: Not accessed in 90+ days, compaction_level=1, not pinned

    Args:
        tier: Target compaction tier (1 or 2)
        limit: Maximum candidates to return

    Returns:
        List of entity dicts that are compaction candidates
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if tier == 1:
        threshold_days = TIER1_THRESHOLD_DAYS
        current_level = 0
    elif tier == 2:
        threshold_days = TIER2_THRESHOLD_DAYS
        current_level = 1
    else:
        raise ValueError(f"Invalid tier: {tier}. Must be 1 or 2.")

    threshold_date = (datetime.now() - timedelta(days=threshold_days)).isoformat()

    cursor.execute('''
        SELECT id, name, entity_type, tier, compaction_level, pinned,
               created_at, last_accessed, access_count, original_size
        FROM entities
        WHERE compaction_level = ?
          AND COALESCE(pinned, 0) = 0
          AND last_accessed < ?
        ORDER BY last_accessed ASC
        LIMIT ?
    ''', (current_level, threshold_date, limit))

    candidates = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return candidates


def get_entity_observations(entity_id: int) -> List[str]:
    """Get all observations for an entity."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT content FROM observations
        WHERE entity_id = ?
        ORDER BY created_at ASC
    ''', (entity_id,))

    observations = [row[0] for row in cursor.fetchall()]
    conn.close()

    return observations


def summarize_observations(observations: List[str], entity_name: str, tier: int) -> str:
    """
    Create a summary of observations for compaction.

    Tier 1: Preserve key points, reduce verbosity
    Tier 2: Extract only essential facts

    This is a simple extractive summarization. For better quality,
    integrate with an LLM summarization endpoint.
    """
    if not observations:
        return f"[Compacted] Entity '{entity_name}' - no observations"

    if tier == 1:
        # Tier 1: Keep first and last observations, plus key points
        if len(observations) <= 3:
            summary_parts = observations
        else:
            summary_parts = [
                observations[0],  # First observation (often most important)
                f"[{len(observations) - 2} intermediate observations compacted]",
                observations[-1]  # Most recent observation
            ]
        return " | ".join(summary_parts)

    elif tier == 2:
        # Tier 2: Aggressive compression - extract essence
        # Count total characters and create brief summary
        total_chars = sum(len(o) for o in observations)
        first_obs = observations[0][:200] + "..." if len(observations[0]) > 200 else observations[0]

        return f"[T2 Compacted] {entity_name}: {first_obs} ({len(observations)} obs, {total_chars} chars originally)"

    return f"[Unknown tier] {entity_name}"


def compact_entity(entity_id: int, tier: int) -> Dict:
    """
    Compact a single entity to the specified tier.

    Args:
        entity_id: ID of entity to compact
        tier: Target compaction tier (1 or 2)

    Returns:
        Dict with compaction results
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get entity info
    cursor.execute('SELECT * FROM entities WHERE id = ?', (entity_id,))
    entity = cursor.fetchone()

    if not entity:
        conn.close()
        return {"success": False, "error": f"Entity {entity_id} not found"}

    entity = dict(entity)

    # Check if pinned
    if entity.get('pinned', 0):
        conn.close()
        return {"success": False, "error": f"Entity {entity_id} is pinned"}

    # Check current compaction level
    current_level = entity.get('compaction_level', 0)
    if current_level >= tier:
        conn.close()
        return {"success": False, "error": f"Entity already at tier {current_level}"}

    # Get observations and create summary
    observations = get_entity_observations(entity_id)
    summary = summarize_observations(observations, entity['name'], tier)

    # Calculate size reduction
    original_size = entity.get('original_size', 0) or sum(len(o) for o in observations)
    compacted_size = len(summary)

    # Update entity with compaction
    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE entities
        SET compaction_level = ?,
            compacted_at = ?,
            compacted_summary = ?
        WHERE id = ?
    ''', (tier, now, summary, entity_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "entity_id": entity_id,
        "entity_name": entity['name'],
        "previous_tier": current_level,
        "new_tier": tier,
        "original_size": original_size,
        "compacted_size": compacted_size,
        "reduction_ratio": f"{(1 - compacted_size/max(original_size, 1)) * 100:.1f}%",
        "summary_preview": summary[:200] + "..." if len(summary) > 200 else summary
    }


def run_compaction_cycle(dry_run: bool = True) -> Dict:
    """
    Run a full compaction cycle across all eligible entities.

    Args:
        dry_run: If True, only report what would be compacted

    Returns:
        Dict with compaction cycle results
    """
    results = {
        "tier1_candidates": [],
        "tier2_candidates": [],
        "tier1_compacted": [],
        "tier2_compacted": [],
        "errors": [],
        "dry_run": dry_run
    }

    # Get Tier 1 candidates
    tier1_candidates = get_compaction_candidates(tier=1)
    results["tier1_candidates"] = [
        {"id": c["id"], "name": c["name"], "last_accessed": c["last_accessed"]}
        for c in tier1_candidates
    ]

    # Get Tier 2 candidates
    tier2_candidates = get_compaction_candidates(tier=2)
    results["tier2_candidates"] = [
        {"id": c["id"], "name": c["name"], "last_accessed": c["last_accessed"]}
        for c in tier2_candidates
    ]

    if not dry_run:
        # Compact Tier 1
        for candidate in tier1_candidates:
            result = compact_entity(candidate["id"], tier=1)
            if result["success"]:
                results["tier1_compacted"].append(result)
            else:
                results["errors"].append(result)

        # Compact Tier 2
        for candidate in tier2_candidates:
            result = compact_entity(candidate["id"], tier=2)
            if result["success"]:
                results["tier2_compacted"].append(result)
            else:
                results["errors"].append(result)

    results["summary"] = {
        "tier1_eligible": len(tier1_candidates),
        "tier2_eligible": len(tier2_candidates),
        "tier1_processed": len(results["tier1_compacted"]),
        "tier2_processed": len(results["tier2_compacted"]),
        "errors": len(results["errors"])
    }

    return results


def pin_entity(entity_id: int, pinned: bool = True) -> Dict:
    """
    Pin or unpin an entity to protect it from compaction.

    Args:
        entity_id: ID of entity to pin/unpin
        pinned: True to pin, False to unpin

    Returns:
        Dict with operation result
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT name FROM entities WHERE id = ?', (entity_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": f"Entity {entity_id} not found"}

    entity_name = row[0]

    cursor.execute('''
        UPDATE entities SET pinned = ? WHERE id = ?
    ''', (1 if pinned else 0, entity_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "pinned": pinned,
        "message": f"Entity '{entity_name}' {'pinned (protected from compaction)' if pinned else 'unpinned'}"
    }


def get_compaction_stats() -> Dict:
    """
    Get statistics about compaction state across all entities.

    Returns:
        Dict with compaction statistics
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Count by compaction level
    cursor.execute('''
        SELECT
            COALESCE(compaction_level, 0) as level,
            COUNT(*) as count,
            SUM(COALESCE(original_size, 0)) as total_original_size,
            SUM(COALESCE(compressed_size, 0)) as total_compressed_size
        FROM entities
        GROUP BY COALESCE(compaction_level, 0)
    ''')

    levels = {}
    for row in cursor.fetchall():
        levels[f"tier_{row[0]}"] = {
            "count": row[1],
            "total_original_size": row[2] or 0,
            "total_compressed_size": row[3] or 0
        }

    # Count pinned entities
    cursor.execute('SELECT COUNT(*) FROM entities WHERE COALESCE(pinned, 0) = 1')
    pinned_count = cursor.fetchone()[0]

    # Get candidates for next compaction
    tier1_candidates = len(get_compaction_candidates(tier=1))
    tier2_candidates = len(get_compaction_candidates(tier=2))

    conn.close()

    return {
        "by_tier": levels,
        "pinned_count": pinned_count,
        "tier1_candidates": tier1_candidates,
        "tier2_candidates": tier2_candidates,
        "thresholds": {
            "tier1_days": TIER1_THRESHOLD_DAYS,
            "tier2_days": TIER2_THRESHOLD_DAYS
        }
    }


def restore_entity(entity_id: int) -> Dict:
    """
    Restore a compacted entity by clearing compaction (requires re-creation of observations).

    Note: This resets compaction_level but doesn't restore original observations.
    The compacted_summary is preserved for reference.

    Args:
        entity_id: ID of entity to restore

    Returns:
        Dict with restoration result
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT name, compaction_level, compacted_summary FROM entities WHERE id = ?', (entity_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {"success": False, "error": f"Entity {entity_id} not found"}

    entity = dict(row)

    if entity['compaction_level'] == 0:
        conn.close()
        return {"success": False, "error": f"Entity is not compacted (level 0)"}

    # Reset compaction level but keep summary for reference
    cursor.execute('''
        UPDATE entities
        SET compaction_level = 0,
            last_accessed = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), entity_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "entity_id": entity_id,
        "entity_name": entity['name'],
        "previous_level": entity['compaction_level'],
        "new_level": 0,
        "note": "Entity restored to tier 0. Original observations preserved if not deleted.",
        "compacted_summary_preserved": entity['compacted_summary'] is not None
    }
