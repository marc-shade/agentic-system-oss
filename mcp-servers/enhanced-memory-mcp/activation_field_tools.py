"""
Activation Field MCP Tools

Exposes the holographic memory activation field as MCP tools.
These tools allow the activation field to influence behavior
automatically without explicit retrieval calls.

The activation field is the bridge between:
- "Filing Cabinet" model (store → retrieve → inject → hope)
- "Holographic" model (memory automatically modulates behavior)
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("activation-field-tools")


def register_activation_field_tools(app):
    """
    Register activation field tools with the MCP server.

    Args:
        app: FastMCP application instance
    """
    from agi.activation_field import (
        ActivationField,
        get_activation_field,
        compute_activation_for_query,
        get_current_routing_bias,
        get_current_confidence_modifier
    )

    @app.tool()
    async def compute_activation_field(
        query: str,
        session_context: Optional[Dict[str, Any]] = None,
        force_recompute: bool = False
    ) -> Dict[str, Any]:
        """
        Compute activation field from query context.

        This is the MAIN holographic memory entry point. Call once at the
        start of an interaction, then the field automatically influences
        all downstream processing.

        The activation field provides:
        - routing_bias: Model selection influence (+/- for simple/balanced/complex)
        - confidence_modifier: Familiarity scaling (>1 = familiar, <1 = novel)
        - primed_concepts: Subconsciously activated concepts for priming
        - emotional_context: Valence/arousal/dominance from memory
        - active_entity_ids: Which memories are activated

        Args:
            query: Current user query or context
            session_context: Optional session metadata (task_type, etc.)
            force_recompute: Bypass cache and recompute

        Returns:
            Dict with activation state including biases and priming

        Example:
            compute_activation_field(
                query="How do I optimize database queries?",
                session_context={"task_type": "code_review"}
            )
        """
        try:
            field = get_activation_field()
            state = field.compute_from_context(
                query=query,
                session_context=session_context,
                force_recompute=force_recompute
            )

            return {
                "success": True,
                "activation_state": state.to_dict(),
                "recommendations": {
                    "routing": field.get_routing_recommendation(),
                    "should_elaborate": field.should_elaborate(),
                    "search_boost": field.get_primed_search_boost()
                }
            }

        except Exception as e:
            logger.error(f"Error computing activation field: {e}")
            return {
                "success": False,
                "error": str(e),
                "activation_state": None
            }

    @app.tool()
    async def get_activation_state() -> Dict[str, Any]:
        """
        Get current activation field state.

        Returns the most recently computed activation field without
        recomputing. Returns None if no field has been computed.

        Returns:
            Dict with current activation state or None
        """
        try:
            field = get_activation_field()
            state = field.current_state

            if state:
                return {
                    "success": True,
                    "has_state": True,
                    "activation_state": state.to_dict(),
                    "recommendations": {
                        "routing": field.get_routing_recommendation(),
                        "should_elaborate": field.should_elaborate()
                    }
                }
            else:
                return {
                    "success": True,
                    "has_state": False,
                    "activation_state": None,
                    "message": "No activation field computed yet"
                }

        except Exception as e:
            logger.error(f"Error getting activation state: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_routing_bias() -> Dict[str, Any]:
        """
        Get current routing bias for model selection.

        The routing bias indicates which model tier is most appropriate
        based on the activated memory context:
        - simple: Fast/simple queries (Haiku)
        - balanced: Standard queries (Sonnet)
        - complex: Complex reasoning (Opus)
        - local: Local inference preferred

        Returns:
            Dict with routing biases and recommendation
        """
        try:
            field = get_activation_field()
            bias = get_current_routing_bias()
            recommendation = field.get_routing_recommendation()

            return {
                "success": True,
                "routing_bias": bias,
                "recommendation": recommendation,
                "confidence_modifier": get_current_confidence_modifier()
            }

        except Exception as e:
            logger.error(f"Error getting routing bias: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_primed_concepts() -> Dict[str, Any]:
        """
        Get currently primed concepts from activation field.

        Primed concepts are subconsciously activated and influence
        behavior without explicit retrieval. Use these to:
        - Boost search results for related content
        - Prime generation with relevant context
        - Adjust response style based on domain

        Returns:
            Dict with primed concepts and search boost weights
        """
        try:
            field = get_activation_field()
            state = field.current_state

            if state:
                return {
                    "success": True,
                    "primed_concepts": list(state.primed_concepts),
                    "concept_count": len(state.primed_concepts),
                    "search_boost": field.get_primed_search_boost()
                }
            else:
                return {
                    "success": True,
                    "primed_concepts": [],
                    "concept_count": 0,
                    "message": "No activation field computed yet"
                }

        except Exception as e:
            logger.error(f"Error getting primed concepts: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_emotional_context() -> Dict[str, Any]:
        """
        Get emotional context from activation field.

        Returns the emotional modulation based on activated memories
        using Russell's circumplex model:
        - valence: -1 (negative) to +1 (positive)
        - arousal: 0 (calm) to 1 (excited)
        - dominance: 0 (controlled) to 1 (in control)

        Use this to:
        - Adjust response tone
        - Be more careful in high-arousal contexts
        - Show empathy in negative valence contexts

        Returns:
            Dict with emotional context values
        """
        try:
            field = get_activation_field()
            state = field.current_state

            if state:
                return {
                    "success": True,
                    "emotional_context": state.emotional_context,
                    "interpretation": _interpret_emotional_context(state.emotional_context)
                }
            else:
                return {
                    "success": True,
                    "emotional_context": {
                        "valence": 0.0,
                        "arousal": 0.5,
                        "dominance": 0.5
                    },
                    "interpretation": "neutral",
                    "message": "No activation field computed yet - using defaults"
                }

        except Exception as e:
            logger.error(f"Error getting emotional context: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def clear_activation_field() -> Dict[str, Any]:
        """
        Clear the current activation field.

        Use this when starting a completely new context that shouldn't
        be influenced by previous activation state.

        Returns:
            Confirmation of field cleared
        """
        try:
            field = get_activation_field()
            field.clear()

            return {
                "success": True,
                "message": "Activation field cleared"
            }

        except Exception as e:
            logger.error(f"Error clearing activation field: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_activation_field_stats() -> Dict[str, Any]:
        """
        Get statistics about activation field usage.

        Returns historical data about activation field computations
        for learning and optimization.

        Returns:
            Dict with usage statistics
        """
        try:
            import sqlite3
            from pathlib import Path

            db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check if log table exists
            cursor.execute('''
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='activation_field_log'
            ''')

            if not cursor.fetchone():
                conn.close()
                return {
                    "success": True,
                    "total_computations": 0,
                    "message": "No activation field history yet"
                }

            # Get stats
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    AVG(activated_count) as avg_activated,
                    AVG(primed_count) as avg_primed,
                    AVG(confidence_modifier) as avg_confidence,
                    AVG(computation_time_ms) as avg_time_ms,
                    MAX(computed_at) as last_computed
                FROM activation_field_log
            ''')

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "success": True,
                    "total_computations": row[0],
                    "avg_activated_entities": round(row[1] or 0, 1),
                    "avg_primed_concepts": round(row[2] or 0, 1),
                    "avg_confidence_modifier": round(row[3] or 1.0, 2),
                    "avg_computation_time_ms": round(row[4] or 0, 1),
                    "last_computed": row[5]
                }
            else:
                return {
                    "success": True,
                    "total_computations": 0
                }

        except Exception as e:
            logger.error(f"Error getting activation field stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("Registered 7 activation field tools")


def _interpret_emotional_context(context: Dict[str, float]) -> str:
    """Interpret emotional context into human-readable description."""
    valence = context.get("valence", 0.0)
    arousal = context.get("arousal", 0.5)

    if valence > 0.3 and arousal > 0.6:
        return "excited_positive"
    elif valence > 0.3 and arousal < 0.4:
        return "calm_positive"
    elif valence < -0.3 and arousal > 0.6:
        return "stressed_negative"
    elif valence < -0.3 and arousal < 0.4:
        return "sad_negative"
    elif arousal > 0.7:
        return "high_arousal"
    elif arousal < 0.3:
        return "low_arousal"
    else:
        return "neutral"
