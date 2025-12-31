"""
MCP Tool Registration for ModelRouter.

Provides tools for:
- router_chat: Send chat completion
- router_select_provider: Get provider selection without calling
- router_metrics: Get routing metrics
- router_status: Get router status
- router_set_mode: Change routing mode
- router_add_rule: Add routing rule
- router_get_uncertainty: Get uncertainty stats
- router_estimate_uncertainty: Estimate uncertainty for prediction
- router_get_memory_state: Get memory-influenced routing state
- router_enable_memory_routing: Enable memory routing mode
"""

from typing import Any, Dict, List, Optional

from .config import RoutingConfig, RoutingRule
from .models import ChatParams, ChatResponse, Message, RoutingMode, Tool
from .router import ModelRouter


# Global default router instance
_default_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get or create default router instance."""
    global _default_router
    if _default_router is None:
        _default_router = ModelRouter()
    return _default_router


async def chat(
    model: str,
    messages: List[Dict[str, str]],
    **kwargs
) -> ChatResponse:
    """
    Quick chat completion using default router.

    Example:
        response = await chat(
            "claude-3.5-sonnet",
            [{"role": "user", "content": "Hello!"}]
        )
    """
    router = get_router()
    params = ChatParams(
        model=model,
        messages=[Message(role=m["role"], content=m["content"]) for m in messages],
        **kwargs
    )
    return await router.chat(params)


def register_model_router_tools(app, router: Optional[ModelRouter] = None):
    """
    Register ModelRouter tools with FastMCP app.

    Tools:
    - router_chat: Send chat completion
    - router_select_provider: Get provider selection without calling
    - router_metrics: Get routing metrics
    - router_status: Get router status
    - router_set_mode: Change routing mode
    - router_add_rule: Add routing rule
    - router_get_uncertainty: Get uncertainty stats
    - router_estimate_uncertainty: Estimate uncertainty for prediction
    - router_get_memory_state: Get memory-influenced routing state
    - router_enable_memory_routing: Enable memory routing mode
    """

    if router is None:
        router = ModelRouter()

    @app.tool()
    async def router_chat(
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send chat completion through ModelRouter.

        Intelligently routes to appropriate provider based on routing mode.

        Args:
            model: Model ID (e.g., "claude-3.5-sonnet", "gpt-4o")
            messages: List of message dicts with role and content
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            provider: Force specific provider (anthropic, openai, ollama)
            agent_type: Agent type for rule-based routing

        Returns:
            Response with content, usage, metadata
        """
        params = ChatParams(
            model=model,
            messages=[Message(role=m["role"], content=m["content"]) for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider
        )

        response = await router.chat(params, agent_type=agent_type)

        return {
            "id": response.id,
            "model": response.model,
            "content": [{"type": b.type, "text": b.text} for b in response.content if b.type == "text"],
            "stop_reason": response.stop_reason.value if response.stop_reason else None,
            "usage": {
                "input_tokens": response.usage.input_tokens if response.usage else 0,
                "output_tokens": response.usage.output_tokens if response.usage else 0
            },
            "metadata": {
                "provider": response.metadata.provider if response.metadata else "unknown",
                "cost": response.metadata.cost if response.metadata else 0.0,
                "latency": response.metadata.latency if response.metadata else 0.0
            }
        }

    @app.tool()
    async def router_select_provider(
        model: str,
        agent_type: Optional[str] = None,
        requires_tools: bool = False
    ) -> Dict[str, Any]:
        """
        Preview which provider would be selected for a request.

        Args:
            model: Model ID to route
            agent_type: Optional agent type for rule-based routing
            requires_tools: Whether request needs tool support

        Returns:
            Provider selection details
        """
        params = ChatParams(
            model=model,
            messages=[],
            tools=[Tool(name="dummy", description="", input_schema={"type": "object", "properties": {}})] if requires_tools else None
        )

        provider = await router._select_provider(params, agent_type)

        return {
            "selected_provider": provider.type.value,
            "provider_name": provider.name,
            "supports_streaming": provider.supports_streaming,
            "supports_tools": provider.supports_tools,
            "supports_mcp": provider.supports_mcp,
            "routing_mode": router.config.routing.mode.value if router.config.routing else "manual"
        }

    @app.tool()
    async def router_metrics() -> Dict[str, Any]:
        """
        Get routing metrics.

        Returns comprehensive metrics including per-provider breakdown.
        """
        m = router.get_metrics()

        return {
            "total_requests": m.total_requests,
            "total_cost": round(m.total_cost, 6),
            "total_tokens": {
                "input": m.total_tokens.input_tokens,
                "output": m.total_tokens.output_tokens
            },
            "provider_breakdown": {
                name: {
                    "requests": pm.requests,
                    "cost": round(pm.cost, 6),
                    "avg_latency_ms": round(pm.avg_latency * 1000, 2),
                    "errors": pm.errors
                }
                for name, pm in m.provider_breakdown.items()
            },
            "agent_breakdown": m.agent_breakdown
        }

    @app.tool()
    async def router_status() -> Dict[str, Any]:
        """Get router status and configuration."""
        return {
            "version": router.config.version,
            "routing_mode": router.config.routing.mode.value if router.config.routing else "manual",
            "default_provider": router.config.default_provider.value,
            "fallback_chain": [p.value for p in router.config.fallback_chain],
            "available_providers": [p.value for p in router.providers.keys()],
            "rules_count": len(router.config.routing.rules) if router.config.routing else 0,
            "monitoring_enabled": router.config.monitoring.enabled if router.config.monitoring else False
        }

    @app.tool()
    async def router_set_mode(mode: str) -> Dict[str, Any]:
        """
        Change routing mode.

        Args:
            mode: One of:
                - "manual": Direct provider selection
                - "rule-based": Match agent types to providers
                - "cost-optimized": Prefer cheaper providers
                - "performance-optimized": Prefer faster providers
                - "memory-influenced": Use holographic memory activation field
                  (Phase 2: Memory automatically influences model selection)
        """
        try:
            new_mode = RoutingMode(mode)
        except ValueError:
            return {"error": f"Invalid mode. Must be one of: {[m.value for m in RoutingMode]}"}

        if router.config.routing is None:
            router.config.routing = RoutingConfig()

        router.config.routing.mode = new_mode

        return {"success": True, "new_mode": new_mode.value}

    @app.tool()
    async def router_add_rule(
        provider: str,
        model: str,
        agent_types: Optional[List[str]] = None,
        requires_tools: Optional[bool] = None,
        local_only: bool = False,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a routing rule.

        Args:
            provider: Target provider (anthropic, openai, ollama)
            model: Model to use
            agent_types: List of agent types this rule applies to
            requires_tools: Whether request must require tools
            local_only: Whether to force local inference
            reason: Description of rule
        """
        condition = {}
        if agent_types:
            condition["agent_type"] = agent_types
        if requires_tools is not None:
            condition["requires_tools"] = requires_tools
        if local_only:
            condition["local_only"] = True

        rule = RoutingRule(
            condition=condition,
            action={"provider": provider, "model": model},
            reason=reason
        )

        if router.config.routing is None:
            router.config.routing = RoutingConfig()

        router.config.routing.rules.append(rule)
        router.config.routing.mode = RoutingMode.RULE_BASED

        return {"success": True, "rules_count": len(router.config.routing.rules)}

    @app.tool()
    async def router_get_uncertainty() -> Dict[str, Any]:
        """
        Get uncertainty estimation statistics for routing decisions.

        Returns statistics from conformal prediction-based uncertainty estimation:
        - calibration_quantile: Configured confidence level (default 0.9 = 90%)
        - calibration_threshold: Current calibration threshold from non-conformity scores
        - total_predictions_tracked: Number of routing decisions tracked
        - recent_accuracy: Accuracy of recent routing predictions
        - average_uncertainty: Mean uncertainty across recent predictions
        - is_calibrated: Whether the estimator has been calibrated
        - calibration_samples: Number of samples used for calibration

        Ported from ruvector/tiny-dancer-core uncertainty.rs
        """
        stats = router.get_uncertainty_stats()
        return {
            "success": True,
            "uncertainty_stats": stats,
            "description": "Conformal prediction-based uncertainty estimation for routing decisions"
        }

    @app.tool()
    async def router_estimate_uncertainty(prediction: float) -> Dict[str, Any]:
        """
        Estimate uncertainty for a routing prediction score.

        Args:
            prediction: Routing confidence score [0.0-1.0]
                       0.5 = maximum uncertainty (at decision boundary)
                       0.0 or 1.0 = minimum uncertainty (confident decision)

        Returns:
            raw_uncertainty: Boundary distance uncertainty
            calibrated_uncertainty: Adjusted by calibration threshold (if available)
        """
        if prediction < 0.0 or prediction > 1.0:
            return {"error": "prediction must be between 0.0 and 1.0"}

        result = router.get_routing_uncertainty(prediction)
        return {
            "success": True,
            "prediction": prediction,
            "raw_uncertainty": round(result["raw_uncertainty"], 4),
            "calibrated_uncertainty": round(result["calibrated_uncertainty"], 4)
        }

    @app.tool()
    async def router_get_memory_state() -> Dict[str, Any]:
        """
        Get current memory-influenced routing state from activation field.

        Returns the holographic memory activation state that influences
        routing decisions when mode is "memory-influenced".

        Returns:
            routing_bias: Dict with simple/balanced/complex/local weights
            confidence_modifier: Memory familiarity scaling (>1 = familiar)
            primed_concepts: Subconsciously activated concepts
            emotional_context: Valence/arousal/dominance from memory
            recommendation: Suggested routing tier
        """
        try:
            from agi.activation_field import get_activation_field

            field = get_activation_field()
            state = field.current_state

            if state:
                return {
                    "success": True,
                    "has_state": True,
                    "routing_bias": state.routing_bias,
                    "confidence_modifier": round(state.confidence_modifier, 3),
                    "primed_concepts": list(state.primed_concepts),
                    "emotional_context": state.emotional_context,
                    "recommendation": field.get_routing_recommendation(),
                    "should_elaborate": field.should_elaborate()
                }
            else:
                return {
                    "success": True,
                    "has_state": False,
                    "message": "No activation field computed yet. Use router_chat or compute_activation_field first."
                }

        except ImportError:
            return {
                "success": False,
                "error": "Activation field module not available"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def router_enable_memory_routing() -> Dict[str, Any]:
        """
        Enable memory-influenced routing mode.

        This activates Phase 2 holographic memory routing, where the
        activation field automatically influences model selection based on:
        - Query familiarity (confidence modifier)
        - Emotional context from activated memories
        - Primed concepts and associations
        - Routing bias (simple/balanced/complex/local)

        Returns:
            Confirmation of mode change
        """
        if router.config.routing is None:
            router.config.routing = RoutingConfig()

        router.config.routing.mode = RoutingMode.MEMORY_INFLUENCED

        return {
            "success": True,
            "mode": "memory-influenced",
            "message": "Memory-influenced routing enabled. Activation field will now influence model selection."
        }

    return router
