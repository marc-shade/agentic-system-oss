"""
Routing Learning MCP Tools - Phase 4 Holographic Memory

Exposes routing learning capabilities as MCP tools:
- Record routing outcomes for learning
- Get learned routing bias
- Get tier performance statistics
- Integrate with procedural evolution
- View learning statistics
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("routing-learning-tools")


def register_routing_learning_tools(app):
    """Register routing learning MCP tools."""

    from agi.routing_learning import (
        get_routing_learner,
        record_routing_outcome,
        get_learned_routing_bias
    )

    learner = get_routing_learner()

    @app.tool()
    async def record_model_routing_outcome(
        task_type: str,
        model_tier: str,
        success_score: float,
        model_name: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        context_key: Optional[str] = None,
        activated_count: Optional[int] = None,
        emotional_valence: Optional[float] = None,
        emotional_arousal: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Record a model routing outcome for learning.

        Phase 4 Holographic Memory: Memory learns from model performance.

        Args:
            task_type: Category of task (code_review, debugging, architecture, etc.)
            model_tier: Tier used (simple, balanced, complex, local)
            success_score: 0.0 to 1.0 success score
            model_name: Specific model used (optional)
            execution_time_ms: Execution time in milliseconds
            context_key: Optional context identifier
            activated_count: Number of activated entities
            emotional_valence: Emotional valence from activation field
            emotional_arousal: Emotional arousal from activation field

        Returns:
            Confirmation with outcome_id
        """
        try:
            outcome_id = learner.record_outcome(
                task_type=task_type,
                model_tier=model_tier,
                success_score=success_score,
                model_name=model_name or "",
                execution_time_ms=execution_time_ms or 0,
                context_key=context_key or "",
                activated_count=activated_count or 0,
                emotional_valence=emotional_valence or 0.0,
                emotional_arousal=emotional_arousal or 0.0
            )

            return {
                "success": True,
                "outcome_id": outcome_id,
                "task_type": task_type,
                "model_tier": model_tier,
                "success_score": success_score
            }
        except Exception as e:
            logger.error(f"Error recording routing outcome: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_routing_bias_for_task(
        task_type: str,
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get learned routing bias for a task type.

        Returns model tier preferences learned from historical outcomes.

        Args:
            task_type: Type of task
            context_key: Optional context filter

        Returns:
            Bias values for each tier (positive = prefer, negative = avoid)
        """
        try:
            bias = learner.get_learned_bias(task_type, context_key)
            sample_count = bias.pop("_sample_count", 0)

            # Get recommended tier
            recommended, confidence = learner.get_recommended_tier(task_type, context_key)

            return {
                "success": True,
                "task_type": task_type,
                "bias": bias,
                "sample_count": sample_count,
                "recommended_tier": recommended,
                "recommendation_confidence": confidence,
                "has_reliable_data": sample_count >= 3
            }
        except Exception as e:
            logger.error(f"Error getting routing bias: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_tier_performance_stats(
        task_type: str,
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for each model tier.

        Shows success rates, execution times, and fitness scores
        for each tier on the specified task type.

        Args:
            task_type: Type of task
            context_key: Optional context filter

        Returns:
            Performance statistics per tier
        """
        try:
            performances = learner.get_tier_performance(task_type, context_key)

            tier_data = []
            for perf in performances:
                tier_data.append({
                    "tier": perf.tier,
                    "total_executions": perf.total_executions,
                    "avg_success": round(perf.avg_success, 3),
                    "avg_execution_time_ms": round(perf.avg_execution_time_ms, 1),
                    "fitness_score": round(perf.fitness_score(), 3),
                    "confidence": round(perf.confidence, 3)
                })

            return {
                "success": True,
                "task_type": task_type,
                "tiers": tier_data
            }
        except Exception as e:
            logger.error(f"Error getting tier performance: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def integrate_procedural_with_routing(
        skill_name: str,
        variant_tag: str,
        success_score: float,
        model_tier: str,
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Integrate procedural evolution outcome with routing learning.

        Links Phase 3 (Procedural Evolution) with Phase 4 (Routing Learning).
        When a skill variant succeeds/fails, we learn about the model tier used.

        Args:
            skill_name: Name of the skill
            variant_tag: Variant tag
            success_score: 0.0 to 1.0 success score
            model_tier: Which model tier was used
            context_key: Optional context

        Returns:
            Confirmation
        """
        try:
            learner.integrate_procedural_outcome(
                skill_name=skill_name,
                variant_tag=variant_tag,
                success_score=success_score,
                model_tier=model_tier,
                context_key=context_key
            )

            return {
                "success": True,
                "skill_name": skill_name,
                "variant_tag": variant_tag,
                "model_tier": model_tier,
                "success_score": success_score,
                "integrated": True
            }
        except Exception as e:
            logger.error(f"Error integrating procedural outcome: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_routing_learning_stats() -> Dict[str, Any]:
        """
        Get overall routing learning statistics.

        Shows:
        - Total outcomes recorded
        - Performance by tier
        - Task types with learned patterns
        - Reliability of learned biases

        Returns:
            Comprehensive statistics
        """
        try:
            stats = learner.get_stats()

            return {
                "success": True,
                **stats
            }
        except Exception as e:
            logger.error(f"Error getting routing stats: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_recent_routing_outcomes(
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get recent routing outcomes for analysis.

        Args:
            limit: Maximum number of outcomes to return

        Returns:
            List of recent routing outcomes
        """
        try:
            outcomes = learner.get_recent_outcomes(limit)

            return {
                "success": True,
                "count": len(outcomes),
                "outcomes": [o.to_dict() for o in outcomes]
            }
        except Exception as e:
            logger.error(f"Error getting recent outcomes: {e}")
            return {"success": False, "error": str(e)}

    @app.tool()
    async def get_recommended_model_tier(
        task_type: str,
        context_key: Optional[str] = None,
        emotional_arousal: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get recommended model tier based on learned patterns.

        Combines historical success patterns with emotional context
        to recommend the best model tier.

        Args:
            task_type: Type of task
            context_key: Optional context
            emotional_arousal: Current arousal level (0.0-1.0)

        Returns:
            Recommended tier with confidence
        """
        try:
            tier, confidence = learner.get_recommended_tier(
                task_type=task_type,
                context_key=context_key,
                emotional_arousal=emotional_arousal
            )

            # Get bias details
            bias = learner.get_learned_bias(task_type, context_key)
            sample_count = bias.pop("_sample_count", 0)

            return {
                "success": True,
                "recommended_tier": tier,
                "confidence": round(confidence, 3),
                "sample_count": sample_count,
                "bias_breakdown": {k: round(v, 3) for k, v in bias.items()},
                "reasoning": _get_recommendation_reasoning(tier, confidence, sample_count, emotional_arousal)
            }
        except Exception as e:
            logger.error(f"Error getting recommendation: {e}")
            return {"success": False, "error": str(e)}

    def _get_recommendation_reasoning(
        tier: str,
        confidence: float,
        sample_count: int,
        arousal: float
    ) -> str:
        """Generate human-readable reasoning for recommendation."""
        if sample_count < 3:
            return f"Recommending '{tier}' as default (insufficient historical data: {sample_count} samples)"

        if confidence > 0.7:
            return f"Strong recommendation for '{tier}' based on {sample_count} historical outcomes (confidence: {confidence:.0%})"
        elif confidence > 0.5:
            return f"Moderate recommendation for '{tier}' based on {sample_count} outcomes (confidence: {confidence:.0%})"
        else:
            reason = f"Tentative recommendation for '{tier}' ({sample_count} samples, {confidence:.0%} confidence)"
            if arousal > 0.7:
                reason += "; high arousal suggests more thorough reasoning may help"
            return reason

    @app.tool()
    async def integrate_reasoning_bank_with_routing(
        task_id: str,
        query: str,
        verdict: str,
        model_tier: str,
        domain: str = "general",
        memories_created: int = 0,
        execution_time_ms: int = 0
    ) -> Dict[str, Any]:
        """
        Integrate ReasoningBank learning outcome with routing learning.

        Links ReasoningBank (what strategies work) with Routing Learning
        (which model tiers work). When ReasoningBank distills memories,
        this also records which model tier performed well.

        Args:
            task_id: Task identifier from ReasoningBank
            query: Original task query
            verdict: Task verdict (success, failure, partial)
            model_tier: Which model tier was used (simple, balanced, complex, local)
            domain: ReasoningBank domain (maps to task type)
            memories_created: Number of memories distilled
            execution_time_ms: Task execution time

        Returns:
            Confirmation with task type inference
        """
        try:
            learner.integrate_reasoning_bank_outcome(
                task_id=task_id,
                query=query,
                verdict=verdict,
                model_tier=model_tier,
                domain=domain,
                memories_created=memories_created,
                execution_time_ms=execution_time_ms
            )

            # Get the inferred task type
            if domain != "general":
                task_type = domain
            else:
                task_type = learner._infer_task_type_from_query(query)

            return {
                "success": True,
                "task_id": task_id,
                "verdict": verdict,
                "model_tier": model_tier,
                "inferred_task_type": task_type,
                "memories_created": memories_created,
                "integrated": True
            }
        except Exception as e:
            logger.error(f"Error integrating ReasoningBank outcome: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Registered routing learning MCP tools (Phase 4)")
    return learner
