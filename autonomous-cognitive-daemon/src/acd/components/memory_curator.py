"""Memory Curator - Consolidates and optimizes the memory system."""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import math

from ..utils.config import get_path, get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


class MemoryCurator:
    """
    Curates and consolidates the memory system.

    Responsibilities:
    - Run memory consolidation (pattern extraction, causal discovery)
    - Apply forgetting curve decay to old memories
    - Optimize tier distribution (75/15/10 rule)
    - Compress old low-importance memories
    - Detect and resolve memory conflicts
    """

    def __init__(self, config: dict):
        """Initialize Memory Curator.

        Args:
            config: Daemon configuration
        """
        self.config = config
        self.memory_db_path = get_path("memory_db", config)

        # Configuration
        self.decay_constant = get_config_value(
            "components.memory_curator.decay_constant", 0.1, config
        )
        self.compression_age_hours = get_config_value(
            "components.memory_curator.compression_age_hours", 168, config  # 7 days
        )
        self.min_importance_for_keep = get_config_value(
            "components.memory_curator.min_importance", 0.2, config
        )

        # 75/15/10 rule targets
        self.tier_targets = {
            "reasoning": 0.75,  # Code, math, science, logic
            "visual": 0.15,    # Images, spatial, visual concepts
            "general": 0.10,   # Everything else
        }

        logger.info(
            "memory_curator_initialized",
            memory_db=str(self.memory_db_path),
            decay_constant=self.decay_constant,
        )

    async def consolidate(self) -> Dict[str, Any]:
        """Run full memory consolidation cycle.

        Returns:
            Consolidation report
        """
        logger.info("starting_memory_consolidation")

        report = {
            "consolidated_at": datetime.now().isoformat(),
            "stages": {},
            "errors": [],
        }

        try:
            # Stage 1: Pattern extraction (episodic -> semantic)
            pattern_result = await self._extract_patterns()
            report["stages"]["pattern_extraction"] = pattern_result

            # Stage 2: Causal discovery
            causal_result = await self._discover_causal_links()
            report["stages"]["causal_discovery"] = causal_result

            # Stage 3: Forgetting curve decay
            decay_result = await self._apply_forgetting_decay()
            report["stages"]["forgetting_decay"] = decay_result

            # Stage 4: Tier optimization
            tier_result = await self._optimize_tiers()
            report["stages"]["tier_optimization"] = tier_result

            # Stage 5: Compression
            compression_result = await self._compress_old_memories()
            report["stages"]["compression"] = compression_result

            # Stage 6: Conflict detection
            conflict_result = await self._detect_conflicts()
            report["stages"]["conflict_detection"] = conflict_result

            logger.info(
                "memory_consolidation_complete",
                stages=len(report["stages"]),
                errors=len(report["errors"]),
            )

        except Exception as e:
            logger.error("memory_consolidation_failed", error=str(e))
            report["errors"].append(str(e))

        return report

    async def _extract_patterns(self) -> Dict[str, Any]:
        """Extract patterns from episodic memories into semantic memory.

        Returns:
            Pattern extraction results
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            db.row_factory = aiosqlite.Row

            # Find frequently occurring patterns in episodic memory
            # Look for event types that occur multiple times
            cursor = await db.execute(
                """
                SELECT event_type, COUNT(*) as frequency,
                       AVG(significance_score) as avg_significance
                FROM episodic_memory
                WHERE created_at > datetime('now', '-24 hours')
                GROUP BY event_type
                HAVING frequency >= 3
                """
            )

            patterns = []
            rows = await cursor.fetchall()

            for row in rows:
                event_type = row["event_type"]
                frequency = row["frequency"]
                significance = row["avg_significance"] or 0.5

                # Check if this pattern is already in semantic memory
                existing = await db.execute(
                    """
                    SELECT concept_id FROM semantic_memory
                    WHERE concept_name = ?
                    """,
                    (f"pattern:{event_type}",),
                )

                if not await existing.fetchone():
                    # Promote to semantic memory
                    await db.execute(
                        """
                        INSERT INTO semantic_memory
                        (concept_name, concept_type, definition, confidence_score, created_at)
                        VALUES (?, 'pattern', ?, ?, datetime('now'))
                        """,
                        (
                            f"pattern:{event_type}",
                            f"Recurring pattern: {event_type} (observed {frequency} times)",
                            min(0.9, significance * 1.2),
                        ),
                    )
                    patterns.append({
                        "event_type": event_type,
                        "frequency": frequency,
                        "promoted": True,
                    })

            await db.commit()

            logger.debug("patterns_extracted", count=len(patterns))
            return {
                "patterns_found": len(rows) if rows else 0,
                "patterns_promoted": len(patterns),
            }

    async def _discover_causal_links(self) -> Dict[str, Any]:
        """Discover causal relationships from action outcomes.

        NOTE: This is currently a stub as the causal_links table schema
        doesn't match the expected format. The actual table uses entity IDs
        rather than text descriptions. This will be improved in a future version.

        Returns:
            Causal discovery results
        """
        try:
            async with aiosqlite.connect(self.memory_db_path) as db:
                db.row_factory = aiosqlite.Row

                # Look for action sequences that lead to outcomes
                cursor = await db.execute(
                    """
                    SELECT action_type, actual_result, AVG(success_score) as avg_success,
                           COUNT(*) as count
                    FROM action_outcomes
                    WHERE executed_at > datetime('now', '-7 days')
                    GROUP BY action_type, actual_result
                    HAVING count >= 2
                    ORDER BY avg_success DESC
                    """
                )

                rows = await cursor.fetchall()

                # Log patterns found but skip causal link creation for now
                # due to schema mismatch (actual table uses entity IDs, not descriptions)
                logger.debug(
                    "causal_patterns_found",
                    patterns=len(rows) if rows else 0,
                    note="causal_link_creation_skipped_schema_mismatch",
                )

                return {
                    "patterns_analyzed": len(rows) if rows else 0,
                    "links_created": 0,
                    "note": "causal_links_disabled_pending_schema_alignment",
                }

        except Exception as e:
            logger.warning("causal_discovery_error", error=str(e))
            return {
                "patterns_analyzed": 0,
                "links_created": 0,
                "error": str(e),
            }

    async def _apply_forgetting_decay(self) -> Dict[str, Any]:
        """Apply Ebbinghaus forgetting curve to memory strengths.

        Returns:
            Decay application results
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            # Get memories that haven't been accessed recently
            # Note: entities table uses 'id' and 'salience_score' (not entity_id/importance)
            cursor = await db.execute(
                """
                SELECT id, salience_score, last_accessed
                FROM entities
                WHERE last_accessed < datetime('now', '-24 hours')
                  AND salience_score > 0.1
                """
            )

            updated = 0
            rows = await cursor.fetchall()

            for row in rows:
                entity_id = row[0]
                current_salience = row[1] or 0.5
                last_accessed = row[2]

                if last_accessed:
                    # Calculate hours since last access
                    last_dt = datetime.fromisoformat(last_accessed)
                    hours_elapsed = (datetime.now() - last_dt).total_seconds() / 3600

                    # Apply forgetting curve: S = e^(-kt)
                    decay_factor = math.exp(-self.decay_constant * hours_elapsed / 24)
                    new_salience = current_salience * decay_factor

                    # Don't decay below minimum if originally important
                    if current_salience > 0.5:
                        new_salience = max(self.min_importance_for_keep, new_salience)

                    if new_salience != current_salience:
                        await db.execute(
                            """
                            UPDATE entities
                            SET salience_score = ?
                            WHERE id = ?
                            """,
                            (new_salience, entity_id),
                        )
                        updated += 1

            await db.commit()

            logger.debug("forgetting_decay_applied", updated=updated)
            return {
                "memories_evaluated": len(rows) if rows else 0,
                "memories_decayed": updated,
            }

    async def _optimize_tiers(self) -> Dict[str, Any]:
        """Optimize memory tier distribution per 75/15/10 rule.

        Returns:
            Tier optimization results
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get current distribution by entity type
            cursor = await db.execute(
                """
                SELECT entity_type, COUNT(*) as count
                FROM entities
                GROUP BY entity_type
                """
            )

            distribution = {row["entity_type"]: row["count"] for row in await cursor.fetchall()}
            total = sum(distribution.values()) or 1

            # Classify current distribution
            reasoning_types = {"code", "algorithm", "math", "logic", "science", "pattern"}
            visual_types = {"image", "visual", "spatial", "diagram"}

            current = {
                "reasoning": sum(distribution.get(t, 0) for t in reasoning_types) / total,
                "visual": sum(distribution.get(t, 0) for t in visual_types) / total,
                "general": 0,
            }
            current["general"] = 1.0 - current["reasoning"] - current["visual"]

            # Calculate deviations from target
            deviations = {
                tier: abs(current.get(tier, 0) - target)
                for tier, target in self.tier_targets.items()
            }

            logger.debug(
                "tier_distribution",
                current=current,
                targets=self.tier_targets,
                deviations=deviations,
            )

            return {
                "current_distribution": current,
                "target_distribution": self.tier_targets,
                "total_entities": total,
                "recommendation": self._tier_recommendation(current),
            }

    def _tier_recommendation(self, current: Dict[str, float]) -> str:
        """Generate recommendation for tier optimization."""
        if current.get("reasoning", 0) < 0.65:
            return "Focus learning on reasoning-centric content (code, math, logic)"
        elif current.get("visual", 0) > 0.25:
            return "Consider consolidating visual memories"
        else:
            return "Distribution is within acceptable range"

    async def _compress_old_memories(self) -> Dict[str, Any]:
        """Compress old, low-importance memories.

        Note: Observations are stored in a separate 'observations' table,
        linked to entities via entity_id foreign key.

        Returns:
            Compression results
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            threshold_time = datetime.now() - timedelta(hours=self.compression_age_hours)

            # Find old, low-importance entities with uncompressed observations
            cursor = await db.execute(
                """
                SELECT e.id, e.name, o.id as obs_id, o.content
                FROM entities e
                JOIN observations o ON o.entity_id = e.id
                WHERE e.created_at < ?
                  AND e.salience_score < ?
                  AND o.compressed IS NULL
                  AND LENGTH(o.content) > 500
                """,
                (threshold_time.isoformat(), self.min_importance_for_keep),
            )

            compressed = 0
            rows = await cursor.fetchall()

            for row in rows:
                obs_id = row[2]
                content = row[3]

                if content and len(content) > 500:
                    # Truncate content as simple compression
                    compressed_content = content[:200] + "... [compressed]"

                    await db.execute(
                        """
                        UPDATE observations
                        SET content = ?, compressed = ?
                        WHERE id = ?
                        """,
                        (compressed_content, content.encode('utf-8'), obs_id),
                    )
                    compressed += 1

            await db.commit()

            logger.debug("memories_compressed", count=compressed)
            return {
                "candidates_found": len(rows) if rows else 0,
                "memories_compressed": compressed,
            }

    async def _detect_conflicts(self) -> Dict[str, Any]:
        """Detect conflicting memories.

        Returns:
            Conflict detection results
        """
        async with aiosqlite.connect(self.memory_db_path) as db:
            db.row_factory = aiosqlite.Row

            # Find entities with similar names but different types (potential conflicts)
            # Note: entities table uses 'id' not 'entity_id'
            cursor = await db.execute(
                """
                SELECT e1.id as id1, e2.id as id2,
                       e1.name as name1, e2.name as name2
                FROM entities e1
                JOIN entities e2 ON e1.name = e2.name AND e1.id < e2.id
                WHERE e1.entity_type = e2.entity_type
                """
            )

            conflicts = []
            for row in await cursor.fetchall():
                conflicts.append({
                    "entity_1": row["id1"],
                    "entity_2": row["id2"],
                    "name": row["name1"],
                })

            logger.debug("conflicts_detected", count=len(conflicts))
            return {
                "conflicts_found": len(conflicts),
                "conflicts": conflicts[:10],  # Limit to first 10
            }

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics.

        Returns:
            Memory statistics
        """
        try:
            async with aiosqlite.connect(self.memory_db_path) as db:
                db.row_factory = aiosqlite.Row

                stats = {}

                # Entity counts
                cursor = await db.execute("SELECT COUNT(*) as count FROM entities")
                row = await cursor.fetchone()
                stats["total_entities"] = row["count"] if row else 0

                # Episodic memory count
                cursor = await db.execute("SELECT COUNT(*) as count FROM episodic_memory")
                row = await cursor.fetchone()
                stats["episodic_memories"] = row["count"] if row else 0

                # Semantic memory count
                cursor = await db.execute("SELECT COUNT(*) as count FROM semantic_memory")
                row = await cursor.fetchone()
                stats["semantic_concepts"] = row["count"] if row else 0

                # Action outcomes
                cursor = await db.execute("SELECT COUNT(*) as count FROM action_outcomes")
                row = await cursor.fetchone()
                stats["action_outcomes"] = row["count"] if row else 0

                return stats

        except Exception as e:
            logger.error("memory_stats_failed", error=str(e))
            return {"error": str(e)}
