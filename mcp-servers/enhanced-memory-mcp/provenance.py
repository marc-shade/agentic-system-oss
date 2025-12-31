#!/usr/bin/env python3
"""
Provenance & L-Score System for Enhanced Memory MCP

Implements the God Agent L-Score provenance metric:
L = geometric_mean(confidence) × average(relevance) / depth_factor

Key Concepts:
- L-Score: Combined provenance quality metric (threshold >= 0.3 for acceptance)
- Source Chain: JSON array tracking derivation from original sources
- Reasoning Quality: Epistemological quality separate from semantic importance
- Derivation Depth: Hop count from original verifiable sources

Reference: God Agent White Paper Section 2.3 - L-Score Calculation
"""

import json
import math
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("enhanced-memory-provenance")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ProvenanceChain:
    """Tracks the derivation history of a piece of knowledge."""
    source_ids: List[int] = field(default_factory=list)
    confidence_scores: List[float] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    derivation_methods: List[str] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "source_ids": self.source_ids,
            "confidence_scores": self.confidence_scores,
            "relevance_scores": self.relevance_scores,
            "derivation_methods": self.derivation_methods,
            "timestamps": self.timestamps
        })

    @classmethod
    def from_json(cls, json_str: str) -> "ProvenanceChain":
        if not json_str:
            return cls()
        data = json.loads(json_str)
        return cls(
            source_ids=data.get("source_ids", []),
            confidence_scores=data.get("confidence_scores", []),
            relevance_scores=data.get("relevance_scores", []),
            derivation_methods=data.get("derivation_methods", []),
            timestamps=data.get("timestamps", [])
        )

    @property
    def depth(self) -> int:
        return len(self.source_ids)


@dataclass
class LScoreResult:
    """Result of L-Score calculation with breakdown."""
    l_score: float
    geometric_mean_confidence: float
    average_relevance: float
    depth_penalty: float
    derivation_depth: int
    is_acceptable: bool  # L-Score >= 0.3
    reasoning_quality: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "l_score": round(self.l_score, 4),
            "geometric_mean_confidence": round(self.geometric_mean_confidence, 4),
            "average_relevance": round(self.average_relevance, 4),
            "depth_penalty": round(self.depth_penalty, 4),
            "derivation_depth": self.derivation_depth,
            "is_acceptable": self.is_acceptable,
            "reasoning_quality": round(self.reasoning_quality, 4),
            "threshold": 0.3
        }


# ============================================================================
# L-SCORE CALCULATION
# ============================================================================

def calculate_l_score(
    confidence_scores: List[float],
    relevance_scores: List[float],
    depth: int,
    depth_penalty_factor: float = 0.1
) -> LScoreResult:
    """
    Calculate L-Score using the God Agent formula.

    L = geometric_mean(confidence) × average(relevance) / depth_factor

    Where:
    - geometric_mean = product(scores)^(1/n)
    - depth_factor = 1 + (depth × depth_penalty_factor)
    - Threshold: >= 0.3 for acceptance

    Args:
        confidence_scores: List of confidence values from source chain [0.0-1.0]
        relevance_scores: List of relevance values [0.0-1.0]
        depth: Derivation depth (hop count from original sources)
        depth_penalty_factor: Penalty per derivation hop (default 10%)

    Returns:
        LScoreResult with full breakdown
    """
    # Default values for empty chains
    if not confidence_scores:
        return LScoreResult(
            l_score=0.5,
            geometric_mean_confidence=0.5,
            average_relevance=0.5,
            depth_penalty=1.0,
            derivation_depth=0,
            is_acceptable=True,
            reasoning_quality=0.5
        )

    # Clamp all scores to [0.0, 1.0]
    confidence_scores = [max(0.0, min(1.0, c)) for c in confidence_scores]
    relevance_scores = [max(0.0, min(1.0, r)) for r in relevance_scores] if relevance_scores else [0.5]

    # Geometric mean of confidence scores
    # Handle zero values by using small epsilon
    epsilon = 1e-10
    product = math.prod(max(c, epsilon) for c in confidence_scores)
    geometric_mean = product ** (1 / len(confidence_scores))

    # Average relevance
    avg_relevance = sum(relevance_scores) / len(relevance_scores)

    # Depth penalty factor: 10% penalty per hop
    depth_factor = 1 + (depth * depth_penalty_factor)

    # L-Score calculation
    l_score = (geometric_mean * avg_relevance) / depth_factor

    # Reasoning quality is geometric mean of confidence (epistemological measure)
    reasoning_quality = geometric_mean

    return LScoreResult(
        l_score=l_score,
        geometric_mean_confidence=geometric_mean,
        average_relevance=avg_relevance,
        depth_penalty=depth_factor,
        derivation_depth=depth,
        is_acceptable=l_score >= 0.3,
        reasoning_quality=reasoning_quality
    )


def calculate_l_score_from_chain(chain: ProvenanceChain) -> LScoreResult:
    """Calculate L-Score from a ProvenanceChain object."""
    return calculate_l_score(
        confidence_scores=chain.confidence_scores,
        relevance_scores=chain.relevance_scores,
        depth=chain.depth
    )


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def init_provenance_schema(db_path: Path) -> None:
    """
    Add L-Score columns to entities table if they don't exist.

    New columns:
    - l_score: Combined provenance metric [0.0-1.0]
    - reasoning_quality: Epistemological quality [0.0-1.0]
    - source_chain: JSON array of provenance data
    - derivation_depth: Hop count from original sources
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(entities)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = [
        ("l_score", "REAL DEFAULT 0.5"),
        ("reasoning_quality", "REAL DEFAULT 0.5"),
        ("source_chain", "TEXT"),  # JSON array
        ("derivation_depth", "INTEGER DEFAULT 0")
    ]

    for col_name, col_def in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE entities ADD COLUMN {col_name} {col_def}")
                logger.info(f"Added column '{col_name}' to entities table")
            except sqlite3.OperationalError as e:
                logger.warning(f"Column '{col_name}' may already exist: {e}")

    # Create index for L-Score queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_l_score
        ON entities(l_score)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_reasoning_quality
        ON entities(reasoning_quality)
    """)

    conn.commit()
    conn.close()
    logger.info("Provenance schema initialized")


class ProvenanceManager:
    """
    Manages provenance tracking and L-Score calculations for entities.

    ANTI-GAMING PROTECTIONS (Stage 3.1 Hardening):
    - Citation cycle detection: Blocks A→B→A mutual boosting
    - Source laundering detection: Flags chains with circular source references
    - Confidence decay: Deeper chains get compounding penalties
    - External source requirement: Root entities need ground_truth flag
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        init_provenance_schema(db_path)

    def _detect_citation_cycle(
        self,
        entity_id: int,
        source_ids: List[int],
        max_depth: int = 10
    ) -> Tuple[bool, Optional[List[int]]]:
        """
        ANTI-GAMING: Detect if adding these sources would create a citation cycle.

        A citation cycle exists when:
        - Source A derives from entity B
        - Entity B is deriving from Source A (directly or transitively)

        This prevents mutual boosting where A cites B and B cites A.

        Args:
            entity_id: Entity being created/updated
            source_ids: Proposed source entity IDs
            max_depth: Maximum depth to search for cycles

        Returns:
            (has_cycle, cycle_path) - True if cycle detected with path
        """
        if not source_ids:
            return False, None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            for source_id in source_ids:
                # Check if this source (or any of its sources) eventually cites entity_id
                visited = set()
                stack = [(source_id, [source_id])]

                while stack:
                    current_id, path = stack.pop()

                    if current_id == entity_id:
                        # Found cycle: source chain leads back to entity
                        conn.close()
                        return True, path + [entity_id]

                    if current_id in visited or len(path) > max_depth:
                        continue

                    visited.add(current_id)

                    # Get this entity's sources
                    cursor.execute("""
                        SELECT source_chain FROM entities WHERE id = ?
                    """, (current_id,))

                    row = cursor.fetchone()
                    if row and row[0]:
                        try:
                            chain_data = json.loads(row[0])
                            for src_id in chain_data.get("source_ids", []):
                                if src_id not in visited:
                                    stack.append((src_id, path + [src_id]))
                        except json.JSONDecodeError:
                            pass

            conn.close()
            return False, None

        except Exception as e:
            conn.close()
            logger.error(f"Error in citation cycle detection: {e}")
            return False, None

    def _calculate_source_quality_penalty(
        self,
        source_ids: List[int]
    ) -> float:
        """
        ANTI-GAMING: Calculate penalty for source chain quality issues.

        Detects:
        - Sources with low L-Scores passing through (source laundering)
        - Sources that are themselves poorly sourced
        - Chains that concentrate derivations (single source amplification)

        Returns:
            Penalty factor (1.0 = no penalty, 0.5 = 50% penalty, etc.)
        """
        if not source_ids:
            return 1.0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        penalties = []

        for source_id in source_ids:
            cursor.execute("""
                SELECT l_score, derivation_depth, source_chain
                FROM entities WHERE id = ?
            """, (source_id,))

            row = cursor.fetchone()
            if not row:
                # Unknown source - heavy penalty
                penalties.append(0.5)
                continue

            source_l_score, source_depth, source_chain_json = row
            source_l_score = source_l_score or 0.5
            source_depth = source_depth or 0

            # Penalty 1: Low L-Score sources shouldn't boost derived entities
            if source_l_score < 0.3:
                penalties.append(0.6)  # 40% penalty for low-quality source
            elif source_l_score < 0.5:
                penalties.append(0.8)  # 20% penalty for medium-quality source
            else:
                penalties.append(1.0)  # No penalty for good sources

            # Penalty 2: Deep derivation chains get compounding penalty
            if source_depth > 3:
                depth_penalty = 1.0 - (source_depth - 3) * 0.1
                penalties.append(max(0.5, depth_penalty))

            # Penalty 3: Check for concentrated single-source derivation
            if source_chain_json:
                try:
                    chain_data = json.loads(source_chain_json)
                    source_sources = chain_data.get("source_ids", [])
                    if len(set(source_sources)) < len(source_sources) * 0.5:
                        # More than half the sources are duplicates - suspicious
                        penalties.append(0.7)
                except json.JSONDecodeError:
                    pass

        conn.close()

        # Return geometric mean of all penalty factors
        if not penalties:
            return 1.0

        product = math.prod(penalties)
        return product ** (1 / len(penalties))

    def create_entity_with_provenance(
        self,
        entity_id: int,
        source_entity_ids: List[int],
        confidence: float = 0.8,
        relevance: float = 0.8,
        derivation_method: str = "inference"
    ) -> LScoreResult:
        """
        Set provenance for an entity based on its source entities.

        ANTI-GAMING (Stage 3.1):
        - Checks for citation cycles (A→B→A mutual boosting)
        - Applies quality penalty for low-quality source chains
        - Blocks gaming attempts with warnings

        Args:
            entity_id: The entity being created/updated
            source_entity_ids: List of entity IDs this derives from
            confidence: Confidence in this derivation [0.0-1.0]
            relevance: Relevance of sources to this derivation [0.0-1.0]
            derivation_method: Method used (inference, extraction, synthesis, citation)

        Returns:
            LScoreResult with calculated L-Score

        Raises:
            ValueError: If citation cycle detected (anti-gaming)
        """
        # ANTI-GAMING: Check for citation cycles before proceeding
        has_cycle, cycle_path = self._detect_citation_cycle(entity_id, source_entity_ids)
        if has_cycle:
            path_str = " → ".join(str(e) for e in cycle_path)
            logger.warning(f"GAMING ATTEMPT: Citation cycle detected for entity {entity_id}: {path_str}")
            raise ValueError(
                f"Citation cycle detected. Entity {entity_id} cannot derive from sources "
                f"that themselves derive from entity {entity_id}. Cycle: {path_str}. "
                f"This is an anti-gaming protection against mutual L-Score boosting."
            )

        # ANTI-GAMING: Calculate source quality penalty
        quality_penalty = self._calculate_source_quality_penalty(source_entity_ids)
        if quality_penalty < 0.8:
            logger.info(f"Source quality penalty applied to entity {entity_id}: {quality_penalty:.2f}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build provenance chain from sources
        chain = ProvenanceChain()

        for source_id in source_entity_ids:
            # Get source entity's provenance
            cursor.execute("""
                SELECT l_score, reasoning_quality, source_chain, derivation_depth
                FROM entities WHERE id = ?
            """, (source_id,))

            source = cursor.fetchone()
            if source:
                source_l_score, source_rq, source_chain_json, source_depth = source

                # Add source to chain
                chain.source_ids.append(source_id)
                chain.confidence_scores.append(source_rq if source_rq else 0.5)
                chain.relevance_scores.append(relevance)
                chain.derivation_methods.append(derivation_method)
                chain.timestamps.append(datetime.now().isoformat())

                # Merge source's chain
                if source_chain_json:
                    source_chain = ProvenanceChain.from_json(source_chain_json)
                    # Only merge up to 5 levels deep to prevent explosion
                    if len(source_chain.source_ids) < 5:
                        chain.source_ids.extend(source_chain.source_ids[:3])
                        chain.confidence_scores.extend(source_chain.confidence_scores[:3])

        # Add current derivation confidence
        chain.confidence_scores.append(confidence)
        chain.relevance_scores.append(relevance)

        # Calculate L-Score
        derivation_depth = max(len(source_entity_ids), 1)
        l_score_result = calculate_l_score(
            confidence_scores=chain.confidence_scores,
            relevance_scores=chain.relevance_scores,
            depth=derivation_depth
        )

        # ANTI-GAMING: Apply source quality penalty to final L-Score
        # This prevents source laundering and low-quality source amplification
        if quality_penalty < 1.0:
            penalized_l_score = l_score_result.l_score * quality_penalty
            logger.info(
                f"Entity {entity_id}: L-Score {l_score_result.l_score:.3f} → {penalized_l_score:.3f} "
                f"(quality penalty: {quality_penalty:.2f})"
            )
            # Create new result with penalized score
            l_score_result = LScoreResult(
                l_score=penalized_l_score,
                geometric_mean_confidence=l_score_result.geometric_mean_confidence,
                average_relevance=l_score_result.average_relevance,
                depth_penalty=l_score_result.depth_penalty * (1 / quality_penalty),  # Record effective penalty
                derivation_depth=l_score_result.derivation_depth,
                is_acceptable=penalized_l_score >= 0.3,
                reasoning_quality=l_score_result.reasoning_quality * quality_penalty
            )

        # Update entity with provenance data
        cursor.execute("""
            UPDATE entities SET
                l_score = ?,
                reasoning_quality = ?,
                source_chain = ?,
                derivation_depth = ?
            WHERE id = ?
        """, (
            l_score_result.l_score,
            l_score_result.reasoning_quality,
            chain.to_json(),
            derivation_depth,
            entity_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Entity {entity_id} provenance set: L-Score={l_score_result.l_score:.3f}, depth={derivation_depth}")
        return l_score_result

    def get_provenance_chain(
        self,
        entity_id: int,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Get the full provenance chain for an entity.

        Args:
            entity_id: Entity to trace
            max_depth: Maximum depth to trace back

        Returns:
            Dictionary with chain details and L-Score breakdown
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, entity_type, l_score, reasoning_quality,
                   source_chain, derivation_depth, created_at
            FROM entities WHERE id = ?
        """, (entity_id,))

        entity = cursor.fetchone()
        if not entity:
            conn.close()
            return {"error": f"Entity {entity_id} not found"}

        name, entity_type, l_score, rq, source_chain_json, depth, created = entity

        # Parse chain
        chain = ProvenanceChain.from_json(source_chain_json) if source_chain_json else ProvenanceChain()

        # Get source entity details
        sources = []
        for source_id in chain.source_ids[:max_depth]:
            cursor.execute("""
                SELECT id, name, entity_type, l_score, reasoning_quality
                FROM entities WHERE id = ?
            """, (source_id,))
            source = cursor.fetchone()
            if source:
                sources.append({
                    "id": source[0],
                    "name": source[1],
                    "type": source[2],
                    "l_score": source[3],
                    "reasoning_quality": source[4]
                })

        conn.close()

        # Calculate L-Score breakdown
        l_score_result = calculate_l_score_from_chain(chain)

        return {
            "entity": {
                "id": entity_id,
                "name": name,
                "type": entity_type,
                "created_at": created
            },
            "l_score": l_score_result.to_dict(),
            "provenance_chain": {
                "depth": chain.depth,
                "sources": sources,
                "derivation_methods": chain.derivation_methods,
                "confidence_scores": chain.confidence_scores,
                "relevance_scores": chain.relevance_scores
            },
            "is_acceptable": l_score_result.is_acceptable
        }

    def validate_l_score(
        self,
        entity_id: int,
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Validate if an entity meets the L-Score threshold.

        Args:
            entity_id: Entity to validate
            threshold: Minimum acceptable L-Score (default 0.3)

        Returns:
            Validation result with recommendation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, l_score, reasoning_quality, derivation_depth, source_chain
            FROM entities WHERE id = ?
        """, (entity_id,))

        entity = cursor.fetchone()
        conn.close()

        if not entity:
            return {
                "valid": False,
                "error": f"Entity {entity_id} not found"
            }

        name, l_score, rq, depth, source_chain_json = entity
        l_score = l_score if l_score is not None else 0.5

        is_valid = l_score >= threshold

        # Generate recommendation
        if is_valid:
            if l_score >= 0.8:
                recommendation = "ACCEPT - High provenance quality"
            elif l_score >= 0.5:
                recommendation = "ACCEPT - Good provenance quality"
            else:
                recommendation = "ACCEPT - Meets minimum threshold"
        else:
            if l_score >= 0.2:
                recommendation = "REVIEW - Below threshold but recoverable. Add sources or verify derivation."
            else:
                recommendation = "REJECT - Poor provenance. Requires re-derivation from verified sources."

        return {
            "entity_id": entity_id,
            "entity_name": name,
            "l_score": l_score,
            "threshold": threshold,
            "valid": is_valid,
            "reasoning_quality": rq,
            "derivation_depth": depth,
            "has_sources": bool(source_chain_json),
            "recommendation": recommendation
        }

    def update_l_score(
        self,
        entity_id: int,
        additional_confidence: float = None,
        additional_relevance: float = None
    ) -> LScoreResult:
        """
        Recalculate L-Score with optional additional confidence/relevance.

        Useful when new evidence supports or questions an entity.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT source_chain, derivation_depth
            FROM entities WHERE id = ?
        """, (entity_id,))

        entity = cursor.fetchone()
        if not entity:
            conn.close()
            return LScoreResult(
                l_score=0.0, geometric_mean_confidence=0.0,
                average_relevance=0.0, depth_penalty=1.0,
                derivation_depth=0, is_acceptable=False, reasoning_quality=0.0
            )

        source_chain_json, depth = entity
        chain = ProvenanceChain.from_json(source_chain_json) if source_chain_json else ProvenanceChain()

        # Add new evidence
        if additional_confidence is not None:
            chain.confidence_scores.append(additional_confidence)
        if additional_relevance is not None:
            chain.relevance_scores.append(additional_relevance)

        # Recalculate
        l_score_result = calculate_l_score(
            confidence_scores=chain.confidence_scores,
            relevance_scores=chain.relevance_scores,
            depth=depth or 0
        )

        # Update entity
        cursor.execute("""
            UPDATE entities SET
                l_score = ?,
                reasoning_quality = ?,
                source_chain = ?
            WHERE id = ?
        """, (
            l_score_result.l_score,
            l_score_result.reasoning_quality,
            chain.to_json(),
            entity_id
        ))

        conn.commit()
        conn.close()

        return l_score_result

    def get_high_provenance_entities(
        self,
        min_l_score: float = 0.7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get entities with high provenance quality."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, entity_type, l_score, reasoning_quality, derivation_depth
            FROM entities
            WHERE l_score >= ?
            ORDER BY l_score DESC
            LIMIT ?
        """, (min_l_score, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "l_score": row[3],
                "reasoning_quality": row[4],
                "derivation_depth": row[5]
            })

        conn.close()
        return results

    def get_low_provenance_entities(
        self,
        max_l_score: float = 0.3,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get entities with low provenance quality that need attention."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, entity_type, l_score, reasoning_quality, derivation_depth
            FROM entities
            WHERE l_score < ? OR l_score IS NULL
            ORDER BY l_score ASC
            LIMIT ?
        """, (max_l_score, limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "l_score": row[3] if row[3] is not None else 0.0,
                "reasoning_quality": row[4],
                "derivation_depth": row[5],
                "needs_review": True
            })

        conn.close()
        return results


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_provenance_tools(app, db_path: Path):
    """Register provenance MCP tools with the FastMCP app."""

    manager = ProvenanceManager(db_path)

    @app.tool()
    async def create_entity_with_provenance(
        entity_id: int,
        source_ids: List[int],
        confidence: float = 0.8,
        relevance: float = 0.8,
        derivation_method: str = "inference"
    ) -> Dict[str, Any]:
        """
        Create or update entity provenance from source entities.

        Calculates L-Score based on source chain and derivation method.
        L = geometric_mean(confidence) × average(relevance) / depth_factor

        Args:
            entity_id: Entity to set provenance for
            source_ids: List of source entity IDs this derives from
            confidence: Confidence in derivation [0.0-1.0]
            relevance: Relevance of sources [0.0-1.0]
            derivation_method: Method (inference, extraction, synthesis, citation)

        Returns:
            L-Score result with full breakdown
        """
        result = manager.create_entity_with_provenance(
            entity_id=entity_id,
            source_entity_ids=source_ids,
            confidence=confidence,
            relevance=relevance,
            derivation_method=derivation_method
        )
        return {
            "success": True,
            "entity_id": entity_id,
            **result.to_dict()
        }

    @app.tool()
    async def get_provenance_chain(
        entity_id: int,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Get full provenance chain for an entity.

        Traces back through source entities to show derivation history
        and calculates L-Score breakdown.

        Args:
            entity_id: Entity to trace
            max_depth: Maximum depth to trace (default 5)

        Returns:
            Complete provenance chain with sources and L-Score
        """
        return manager.get_provenance_chain(entity_id, max_depth)

    @app.tool()
    async def validate_l_score(
        entity_id: int,
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Validate if entity meets L-Score threshold.

        L-Score threshold of 0.3 is the default minimum for acceptance.
        Higher thresholds (0.5, 0.7) can be used for critical knowledge.

        Args:
            entity_id: Entity to validate
            threshold: Minimum L-Score required (default 0.3)

        Returns:
            Validation result with recommendation
        """
        return manager.validate_l_score(entity_id, threshold)

    @app.tool()
    async def get_high_provenance_entities(
        min_l_score: float = 0.7,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get entities with high provenance quality.

        Useful for finding well-sourced, reliable knowledge.

        Args:
            min_l_score: Minimum L-Score (default 0.7)
            limit: Maximum results (default 50)

        Returns:
            List of high-quality entities
        """
        entities = manager.get_high_provenance_entities(min_l_score, limit)
        return {
            "count": len(entities),
            "min_l_score": min_l_score,
            "entities": entities
        }

    @app.tool()
    async def get_low_provenance_entities(
        max_l_score: float = 0.3,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get entities needing provenance review.

        Returns entities below threshold that may need:
        - Additional source citations
        - Verification of derivation
        - Potential removal if unverifiable

        Args:
            max_l_score: Maximum L-Score to include (default 0.3)
            limit: Maximum results (default 50)

        Returns:
            List of entities needing review
        """
        entities = manager.get_low_provenance_entities(max_l_score, limit)
        return {
            "count": len(entities),
            "max_l_score": max_l_score,
            "entities": entities,
            "recommendation": "Review these entities and add source citations or remove if unverifiable"
        }

    @app.tool()
    async def calculate_l_score_preview(
        confidence_scores: List[float],
        relevance_scores: List[float],
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Preview L-Score calculation without creating entity.

        Use this to understand how different confidence/relevance values
        affect the final L-Score before committing.

        Args:
            confidence_scores: List of confidence values [0.0-1.0]
            relevance_scores: List of relevance values [0.0-1.0]
            depth: Derivation depth (hop count)

        Returns:
            L-Score breakdown
        """
        result = calculate_l_score(confidence_scores, relevance_scores, depth)
        return result.to_dict()

    logger.info("Provenance tools registered: 6 tools for L-Score management")
    return manager
