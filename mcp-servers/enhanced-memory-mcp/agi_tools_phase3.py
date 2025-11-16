"""
AGI Memory Tools Phase 3 - MCP Server Integration

Exposes Phase 3 AGI capabilities (emotional tagging & associative networks) via MCP tools.
"""

import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

from agi import EmotionalMemory, AssociativeNetwork, AttentionMechanism, ForgettingCurve

logger = logging.getLogger("agi-tools-phase3")


def register_agi_phase3_tools(app: FastMCP, db_path: str):
    """Register AGI Phase 3 memory tools with FastMCP app"""

    # ============================================================================
    # EMOTIONAL MEMORY TOOLS
    # ============================================================================

    @app.tool()
    def tag_entity_emotion(
        entity_id: int,
        valence: float = 0.0,
        arousal: float = 0.0,
        dominance: float = 0.5,
        primary_emotion: Optional[str] = None,
        emotion_intensity: float = 0.5,
        salience_score: float = 0.5,
        context_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tag an entity with emotional metadata

        Args:
            entity_id: Entity to tag
            valence: -1.0 (negative) to +1.0 (positive)
            arousal: 0.0 (calm) to 1.0 (excited)
            dominance: 0.0 (controlled) to 1.0 (in control)
            primary_emotion: joy, sadness, anger, fear, surprise, disgust
            emotion_intensity: 0.0 to 1.0
            salience_score: 0.0 (unimportant) to 1.0 (critical)
            context_type: success, failure, neutral, surprising

        Returns:
            Tag confirmation with tag_id

        Use this to add emotional context to memories for better recall.
        """
        emotional = EmotionalMemory()
        tag_id = emotional.tag_entity(
            entity_id, valence, arousal, dominance,
            primary_emotion, emotion_intensity,
            salience_score, context_type
        )

        return {
            "status": "success",
            "tag_id": tag_id,
            "entity_id": entity_id,
            "valence": valence,
            "arousal": arousal,
            "salience_score": salience_score
        }

    @app.tool()
    def search_by_emotion(
        emotion_filter: Dict[str, Any],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search memories by emotional criteria

        Args:
            emotion_filter: {
                "valence_min": -1.0,
                "valence_max": 1.0,
                "arousal_min": 0.0,
                "arousal_max": 1.0,
                "primary_emotion": "joy",
                "min_salience": 0.5
            }
            limit: Maximum results

        Returns:
            List of matching entities with emotional tags

        Use this to find memories by emotional state (e.g., positive high-energy memories).
        """
        emotional = EmotionalMemory()
        return emotional.search_by_emotion(emotion_filter, limit)

    @app.tool()
    def update_salience(
        entity_id: int,
        salience_delta: float,
        reason: str
    ) -> Dict[str, str]:
        """
        Update importance/salience score for an entity

        Args:
            entity_id: Entity to update
            salience_delta: Change in salience (-1.0 to +1.0)
            reason: Why salience changed

        Returns:
            Confirmation

        Use this when memory becomes more/less important.
        """
        emotional = EmotionalMemory()
        emotional.update_salience(entity_id, salience_delta, reason)

        return {
            "status": "success",
            "entity_id": str(entity_id),
            "salience_delta": salience_delta,
            "reason": reason
        }

    @app.tool()
    def get_high_salience_memories(
        threshold: float = 0.7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get memories with high importance/salience

        Args:
            threshold: Minimum salience score (0.7 = high)
            limit: Maximum results

        Returns:
            List of important memories

        Use this to retrieve the most important memories.
        """
        emotional = EmotionalMemory()
        return emotional.get_high_salience_memories(threshold, limit)

    @app.tool()
    def get_emotional_clusters() -> List[Dict[str, Any]]:
        """
        Get emotional memory clusters grouped by emotion

        Returns:
            List of clusters with emotion type and statistics

        Use this to understand emotional distribution of memories.
        """
        emotional = EmotionalMemory()
        return emotional.get_emotional_clusters()

    @app.tool()
    def decay_memory_strength(
        entity_id: int,
        time_elapsed_hours: float
    ) -> Dict[str, Any]:
        """
        Apply forgetting curve decay to memory strength

        Uses Ebbinghaus forgetting curve: strength = e^(-kt)

        Args:
            entity_id: Entity to decay
            time_elapsed_hours: Hours since last access

        Returns:
            New strength value

        Use this to simulate natural forgetting over time.
        """
        emotional = EmotionalMemory()
        new_strength = emotional.decay_memory_strength(entity_id, time_elapsed_hours)

        return {
            "status": "success",
            "entity_id": entity_id,
            "time_elapsed_hours": time_elapsed_hours,
            "new_strength": new_strength
        }

    @app.tool()
    def boost_memory_strength(
        entity_id: int,
        boost_amount: float = 0.2
    ) -> Dict[str, str]:
        """
        Boost memory strength (spacing effect on retrieval)

        Args:
            entity_id: Entity to boost
            boost_amount: Strength increase (0.0-1.0)

        Returns:
            Confirmation

        Use this when memory is retrieved to implement spacing effect.
        """
        emotional = EmotionalMemory()
        emotional.boost_memory_strength(entity_id, boost_amount)

        return {
            "status": "success",
            "entity_id": str(entity_id),
            "boost_amount": boost_amount
        }

    # ============================================================================
    # ASSOCIATIVE NETWORK TOOLS
    # ============================================================================

    @app.tool()
    def create_association(
        entity_a_id: int,
        entity_b_id: int,
        association_type: str = "semantic",
        association_strength: float = 0.5,
        bidirectional: bool = True,
        context_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create associative link between two entities

        Args:
            entity_a_id: First entity
            entity_b_id: Second entity
            association_type: semantic, temporal, causal, emotional, spatial
            association_strength: 0.0 to 1.0
            bidirectional: Can activate in both directions?
            context_conditions: Optional context requirements

        Returns:
            Association details

        Use this to link related memories for associative recall.
        """
        network = AssociativeNetwork()
        association_id = network.create_association(
            entity_a_id, entity_b_id,
            association_type, association_strength,
            bidirectional, context_conditions
        )

        return {
            "status": "success",
            "association_id": association_id,
            "entity_a_id": entity_a_id,
            "entity_b_id": entity_b_id,
            "association_type": association_type,
            "strength": association_strength
        }

    @app.tool()
    def get_associations(
        entity_id: int,
        min_strength: float = 0.0,
        association_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all associations for an entity

        Args:
            entity_id: Entity to get associations for
            min_strength: Minimum association strength
            association_type: Optional type filter

        Returns:
            List of associations

        Use this to see what memories are linked to a given memory.
        """
        network = AssociativeNetwork()
        return network.get_associations(entity_id, min_strength, association_type)

    @app.tool()
    def spread_activation(
        source_entity_id: int,
        initial_activation: float = 1.0,
        max_hops: int = 3,
        activation_threshold: float = 0.3,
        context_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Spread activation from source entity through associative network

        Implements spreading activation like neural networks.

        Args:
            source_entity_id: Starting entity
            initial_activation: Starting activation level (0.0-1.0)
            max_hops: Maximum distance to spread
            activation_threshold: Minimum activation to continue spreading
            context_id: Optional context for context-dependent associations

        Returns:
            List of activated entities with activation levels

        Use this for associative recall - one memory triggers related memories.
        """
        network = AssociativeNetwork()
        return network.spread_activation(
            source_entity_id, initial_activation,
            max_hops, activation_threshold, context_id
        )

    @app.tool()
    def reinforce_association(
        entity_a_id: int,
        entity_b_id: int,
        reinforcement: float = 0.1
    ) -> Dict[str, str]:
        """
        Reinforce an association (e.g., when co-activated)

        Args:
            entity_a_id: First entity
            entity_b_id: Second entity
            reinforcement: Strength increase (0.0-1.0)

        Returns:
            Confirmation

        Use this when two memories are activated together to strengthen their link.
        """
        network = AssociativeNetwork()
        network.reinforce_association(entity_a_id, entity_b_id, reinforcement)

        return {
            "status": "success",
            "entity_a_id": str(entity_a_id),
            "entity_b_id": str(entity_b_id),
            "reinforcement": reinforcement
        }

    @app.tool()
    def get_strong_associations(
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get strong associations across entire network

        Args:
            threshold: Minimum strength (0.7 = strong)
            limit: Maximum results

        Returns:
            List of strong associations

        Use this to see the most reliable associative links.
        """
        network = AssociativeNetwork()
        return network.get_strong_associations(threshold, limit)

    # ============================================================================
    # ATTENTION MECHANISM TOOLS
    # ============================================================================

    @app.tool()
    def set_attention(
        entity_id: int,
        relevance_score: float,
        context_id: Optional[int] = None,
        recency_weight: float = 0.3,
        frequency_weight: float = 0.3,
        emotional_weight: float = 0.4
    ) -> Dict[str, str]:
        """
        Set attention weights for selective retrieval

        Args:
            entity_id: Entity to attend to
            relevance_score: Current relevance (0.0-1.0)
            context_id: Optional context (None = global)
            recency_weight: Weight for recent access
            frequency_weight: Weight for frequent access
            emotional_weight: Weight for emotional salience

        Returns:
            Confirmation

        Use this to focus on currently relevant memories.
        """
        attention = AttentionMechanism()
        attention.set_attention(
            entity_id, relevance_score, context_id,
            recency_weight, frequency_weight, emotional_weight
        )

        return {
            "status": "success",
            "entity_id": str(entity_id),
            "relevance_score": relevance_score
        }

    @app.tool()
    def get_attended_memories(
        threshold: float = 0.3,
        context_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get currently attended memories

        Args:
            threshold: Minimum attention level
            context_id: Optional context filter
            limit: Maximum results

        Returns:
            List of attended memories

        Use this to retrieve memories that are currently in focus.
        """
        attention = AttentionMechanism()
        return attention.get_attended_memories(threshold, context_id, limit)

    # ============================================================================
    # FORGETTING CURVE TOOLS
    # ============================================================================

    @app.tool()
    def get_memories_needing_review(
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get memories that need review (spaced repetition)

        Args:
            limit: Maximum results

        Returns:
            List of memories needing review

        Use this to implement spaced repetition for important memories.
        """
        forgetting = ForgettingCurve()
        return forgetting.get_memories_needing_review(limit)

    logger.info("✅ AGI Memory Phase 3 tools registered (Emotional Tagging & Associative Networks)")
