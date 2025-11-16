"""
AGI Memory Tools Phase 2 - MCP Server Integration

Exposes Phase 2 AGI capabilities (temporal reasoning & consolidation) via MCP tools.
"""

import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

from agi import TemporalReasoning, ConsolidationEngine

logger = logging.getLogger("agi-tools-phase2")


def register_agi_phase2_tools(app: FastMCP, db_path: str):
    """Register AGI Phase 2 memory tools with FastMCP app"""

    # ============================================================================
    # TEMPORAL REASONING TOOLS
    # ============================================================================

    @app.tool()
    def create_causal_link(
        cause_entity_id: int,
        effect_entity_id: int,
        relationship_type: str = "direct",
        strength: float = 0.5,
        typical_delay_seconds: Optional[int] = None,
        context_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a causal link between two entities

        Args:
            cause_entity_id: Entity that causes the effect
            effect_entity_id: Entity that is the effect
            relationship_type: "direct", "indirect", "contributory", "preventive"
            strength: 0.0 (weak) to 1.0 (strong)
            typical_delay_seconds: Average time between cause and effect
            context_conditions: Conditions under which this link holds

        Returns:
            link_id and status
        """
        temporal = TemporalReasoning()
        link_id = temporal.create_causal_link(
            cause_entity_id, effect_entity_id,
            relationship_type, strength,
            typical_delay_seconds, context_conditions
        )
        return {
            "status": "success",
            "link_id": link_id,
            "cause_id": cause_entity_id,
            "effect_id": effect_entity_id,
            "strength": strength
        }

    @app.tool()
    def get_causal_chain(
        entity_id: int,
        direction: str = "forward",
        depth: int = 5,
        min_strength: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Get causal chain from an entity

        Args:
            entity_id: Starting entity
            direction: "forward" (what this causes) or "backward" (what caused this)
            depth: How many levels deep to traverse
            min_strength: Minimum link strength to follow

        Returns:
            List of entities in causal chain with link metadata

        Use this to understand cascading effects or root causes.
        """
        temporal = TemporalReasoning()
        return temporal.get_causal_chain(entity_id, direction, depth, min_strength)

    @app.tool()
    def predict_outcome(
        action_entity_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict likely outcomes of an action based on causal history

        Args:
            action_entity_id: Entity representing the action to predict
            context: Optional current context conditions

        Returns:
            {
                "likely_outcomes": List[Dict] with probabilities,
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "similar_cases": int
            }

        Use this before taking actions to predict what will happen.
        """
        temporal = TemporalReasoning()
        return temporal.predict_outcome(action_entity_id, context)

    @app.tool()
    def detect_causal_pattern(
        entity_ids: List[int],
        time_window_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if a sequence of entities represents a causal pattern

        Args:
            entity_ids: Ordered list of entity IDs
            time_window_hours: Time window to look for patterns

        Returns:
            Pattern info if found, None otherwise

        Use this to identify recurring causal sequences.
        """
        temporal = TemporalReasoning()
        return temporal.detect_causal_pattern(entity_ids, time_window_hours)

    @app.tool()
    def create_temporal_chain(
        entity_ids: List[int],
        chain_type: str,
        chain_name: Optional[str] = None,
        description: Optional[str] = None,
        confidence: float = 0.5
    ) -> Dict[str, str]:
        """
        Create a temporal chain from a sequence of entities

        Args:
            entity_ids: Ordered list of entity IDs in the chain
            chain_type: "causal", "sequential", "conditional", "cyclic"
            chain_name: Optional name for the chain
            description: Optional description
            confidence: Confidence in this chain (0.0-1.0)

        Returns:
            chain_id and status

        Use this to capture known workflows or causal sequences.
        """
        temporal = TemporalReasoning()
        chain_id = temporal.create_temporal_chain(
            entity_ids, chain_type, chain_name, description, confidence
        )
        return {
            "status": "success",
            "chain_id": chain_id,
            "chain_type": chain_type,
            "entity_count": len(entity_ids)
        }

    @app.tool()
    def get_temporal_chain(chain_id: str) -> Optional[Dict[str, Any]]:
        """
        Get temporal chain details

        Args:
            chain_id: Chain ID to retrieve

        Returns:
            Complete chain information including all entities and metadata
        """
        temporal = TemporalReasoning()
        return temporal.get_temporal_chain(chain_id)

    # ============================================================================
    # CONSOLIDATION TOOLS
    # ============================================================================

    @app.tool()
    def run_pattern_extraction(
        time_window_hours: int = 24,
        min_pattern_frequency: int = 3
    ) -> Dict[str, Any]:
        """
        Extract patterns from recent episodic memories

        Promotes recurring patterns to semantic memory (like sleep consolidation).

        Args:
            time_window_hours: Hours of memory to analyze
            min_pattern_frequency: Minimum occurrences to be a pattern

        Returns:
            {
                "patterns_found": int,
                "patterns_promoted": int,
                "semantic_memories_created": int
            }

        Run this periodically to consolidate learnings.
        """
        consolidation = ConsolidationEngine()
        return consolidation.run_pattern_extraction(time_window_hours, min_pattern_frequency)

    @app.tool()
    def run_causal_discovery(
        time_window_hours: int = 24,
        min_confidence: float = 0.6
    ) -> Dict[str, Any]:
        """
        Discover causal relationships from recent action outcomes

        Automatically creates causal links based on what worked and what didn't.

        Args:
            time_window_hours: Hours of memory to analyze
            min_confidence: Minimum confidence for causal link

        Returns:
            {
                "chains_created": int,
                "links_created": int,
                "hypotheses_generated": int
            }

        Run this to learn cause-effect relationships automatically.
        """
        consolidation = ConsolidationEngine()
        return consolidation.run_causal_discovery(time_window_hours, min_confidence)

    @app.tool()
    def run_memory_compression(
        time_window_hours: int = 168  # 7 days
    ) -> Dict[str, Any]:
        """
        Compress old low-importance memories

        Frees up space while preserving important information.

        Args:
            time_window_hours: Only compress memories older than this

        Returns:
            {
                "memories_compressed": int,
                "space_saved_bytes": int
            }

        Run this weekly to maintain memory efficiency.
        """
        consolidation = ConsolidationEngine()
        return consolidation.run_memory_compression(time_window_hours)

    @app.tool()
    def run_full_consolidation(
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Run all consolidation processes (sleep-like consolidation)

        This is the main consolidation function that:
        1. Extracts patterns from episodic to semantic memory
        2. Discovers causal relationships
        3. Compresses old memories

        Args:
            time_window_hours: Hours of memory to consolidate

        Returns:
            Combined results from all consolidation processes

        Run this daily (e.g., at night) for best results.
        Mimics human sleep consolidation.
        """
        consolidation = ConsolidationEngine()
        return consolidation.run_full_consolidation(time_window_hours)

    @app.tool()
    def get_consolidation_stats() -> Dict[str, Any]:
        """
        Get consolidation statistics

        Returns:
            {
                "total_jobs": int,
                "by_status": Dict[str, int],
                "totals": Dict[str, int],
                "recent_jobs": List[Dict]
            }

        Use this to monitor consolidation effectiveness.
        """
        consolidation = ConsolidationEngine()
        return consolidation.get_consolidation_stats()

    logger.info("✅ AGI Memory Phase 2 tools registered (Temporal Reasoning & Consolidation)")
