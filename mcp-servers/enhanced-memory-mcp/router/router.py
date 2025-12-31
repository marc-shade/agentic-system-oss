"""
ModelRouter - Multi-provider LLM routing system.

Provides intelligent routing across multiple LLM providers with:
- Manual provider selection
- Rule-based routing (by agent type, complexity, privacy)
- Cost-optimized routing (prefer cheaper providers)
- Performance-optimized routing (prefer faster providers)
- Memory-influenced routing (Phase 2: Holographic memory)
- Fallback chains for reliability
- Metrics tracking per provider and agent type
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

from .config import (
    CacheConfig,
    MonitoringConfig,
    ProviderConfig,
    RouterConfig,
    RoutingConfig,
    RoutingRule,
)
from .models import (
    ChatParams,
    ChatResponse,
    ProviderType,
    RoutingMode,
    StreamChunk,
    UsageStats,
)
from .providers import (
    AnthropicProvider,
    ExoProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
)
from .uncertainty import UncertaintyEstimator
from .utils import get_model_pricing, map_model_id

logger = logging.getLogger("model_router")


@dataclass
class ProviderMetrics:
    """Metrics for a single provider."""
    requests: int = 0
    cost: float = 0.0
    avg_latency: float = 0.0
    errors: int = 0
    total_latency: float = 0.0  # For calculating average


@dataclass
class RouterMetrics:
    """Overall router metrics."""
    total_requests: int = 0
    total_cost: float = 0.0
    total_tokens: UsageStats = field(default_factory=UsageStats)
    provider_breakdown: Dict[str, ProviderMetrics] = field(default_factory=dict)
    agent_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class ModelRouter:
    """
    Multi-provider LLM router with intelligent routing strategies.

    Ported from ruvnet/agentic-flow TypeScript implementation.

    Features:
    - Manual provider selection
    - Rule-based routing (by agent type, complexity, privacy)
    - Cost-optimized routing (prefer cheaper providers)
    - Performance-optimized routing (prefer faster providers)
    - Fallback chains for reliability
    - Metrics tracking per provider and agent type
    """

    def __init__(self, config: Optional[RouterConfig] = None, config_path: Optional[str] = None):
        """
        Initialize router with config or config file path.

        Args:
            config: RouterConfig object
            config_path: Path to JSON config file
        """
        if config:
            self.config = config
        elif config_path:
            self.config = self._load_config(config_path)
        else:
            self.config = self._load_from_env()

        self.providers: Dict[ProviderType, LLMProvider] = {}
        self.metrics = RouterMetrics()
        self.uncertainty_estimator = UncertaintyEstimator()
        self._init_providers()

    def _load_config(self, path: str) -> RouterConfig:
        """Load config from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        providers = {}
        for name, pconfig in data.get("providers", {}).items():
            providers[name] = ProviderConfig(**pconfig)

        routing = None
        if "routing" in data:
            rules = [RoutingRule(**r) for r in data["routing"].get("rules", [])]
            routing = RoutingConfig(
                mode=RoutingMode(data["routing"].get("mode", "manual")),
                rules=rules,
                cost_optimization=data["routing"].get("costOptimization"),
                performance=data["routing"].get("performance")
            )

        return RouterConfig(
            version=data.get("version", "1.0.0"),
            default_provider=ProviderType(data.get("defaultProvider", "anthropic")),
            fallback_chain=[ProviderType(p) for p in data.get("fallbackChain", [])],
            providers=providers,
            routing=routing,
            monitoring=MonitoringConfig(**data.get("monitoring", {})) if "monitoring" in data else None,
            cache=CacheConfig(**data.get("cache", {})) if "cache" in data else None
        )

    def _load_from_env(self) -> RouterConfig:
        """Load config from environment variables."""
        providers = {}

        if os.getenv("ANTHROPIC_API_KEY"):
            providers["anthropic"] = ProviderConfig(api_key=os.getenv("ANTHROPIC_API_KEY"))
        if os.getenv("OPENAI_API_KEY"):
            providers["openai"] = ProviderConfig(api_key=os.getenv("OPENAI_API_KEY"))
        if os.getenv("OLLAMA_HOST") or True:
            providers["ollama"] = ProviderConfig(base_url=os.getenv("OLLAMA_HOST"))

        default = ProviderType.ANTHROPIC
        if "anthropic" not in providers and "openai" in providers:
            default = ProviderType.OPENAI
        elif "anthropic" not in providers and "openai" not in providers:
            default = ProviderType.OLLAMA

        fallback = []
        for p in [ProviderType.ANTHROPIC, ProviderType.OPENAI, ProviderType.OLLAMA]:
            if p.value in providers and p != default:
                fallback.append(p)

        return RouterConfig(
            default_provider=default,
            fallback_chain=fallback,
            providers=providers,
            routing=RoutingConfig(mode=RoutingMode.MANUAL),
            monitoring=MonitoringConfig(enabled=True)
        )

    def _init_providers(self):
        """Initialize configured providers."""
        provider_classes = {
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
            "exo": ExoProvider,
        }

        for name, config in self.config.providers.items():
            if name in provider_classes:
                try:
                    self.providers[ProviderType(name)] = provider_classes[name](config)
                    logger.info(f"Initialized provider: {name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize {name}: {e}")

    async def chat(
        self,
        params: ChatParams,
        agent_type: Optional[str] = None
    ) -> ChatResponse:
        """
        Send chat completion with intelligent routing.

        Args:
            params: Chat parameters
            agent_type: Optional agent type for rule-based routing

        Returns:
            ChatResponse from selected provider
        """
        start_time = time.time()

        provider = await self._select_provider(params, agent_type)

        try:
            response = await provider.chat(params)

            latency = time.time() - start_time
            self._track_metrics(provider.type.value, response, latency, agent_type)

            if response.metadata:
                response.metadata.latency = latency

            return response

        except ProviderError as e:
            if e.retryable and self.config.fallback_chain:
                return await self._handle_provider_error(e, params, agent_type)
            raise

    async def stream(
        self,
        params: ChatParams,
        agent_type: Optional[str] = None
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion."""
        provider = await self._select_provider(params, agent_type)
        async for chunk in provider.stream(params):
            yield chunk

    async def _select_provider(
        self,
        params: ChatParams,
        agent_type: Optional[str] = None
    ) -> LLMProvider:
        """Select appropriate provider based on routing mode."""
        if params.provider:
            provider_type = ProviderType(params.provider)
            if provider_type in self.providers:
                return self.providers[provider_type]

        routing = self.config.routing or RoutingConfig()

        if routing.mode == RoutingMode.RULE_BASED and routing.rules:
            return self._select_by_rules(params, agent_type)
        elif routing.mode == RoutingMode.COST_OPTIMIZED:
            return self._select_by_cost(params)
        elif routing.mode == RoutingMode.PERFORMANCE_OPTIMIZED:
            return self._select_by_performance(params)
        elif routing.mode == RoutingMode.MEMORY_INFLUENCED:
            # Phase 2: Holographic memory routing
            return self._select_by_memory(params, agent_type)
        else:
            if self.config.default_provider in self.providers:
                return self.providers[self.config.default_provider]
            return next(iter(self.providers.values()))

    def _select_by_rules(
        self,
        params: ChatParams,
        agent_type: Optional[str] = None
    ) -> LLMProvider:
        """Select provider based on routing rules."""
        routing = self.config.routing
        if not routing or not routing.rules:
            return self.providers[self.config.default_provider]

        for rule in routing.rules:
            condition = rule.condition

            if "agent_type" in condition:
                if agent_type not in condition["agent_type"]:
                    continue

            if "requires_tools" in condition:
                has_tools = params.tools is not None and len(params.tools) > 0
                if condition["requires_tools"] != has_tools:
                    continue

            if condition.get("local_only"):
                if ProviderType.OLLAMA in self.providers:
                    return self.providers[ProviderType.OLLAMA]
                if ProviderType.EXO in self.providers:
                    return self.providers[ProviderType.EXO]
                continue

            provider_type = ProviderType(rule.action["provider"])
            if provider_type in self.providers:
                logger.debug(f"Rule matched: {rule.reason or 'unnamed rule'}")
                return self.providers[provider_type]

        return self.providers[self.config.default_provider]

    def _select_by_cost(self, params: ChatParams) -> LLMProvider:
        """Select cheapest available provider."""
        costs = []
        for ptype, provider in self.providers.items():
            input_price, output_price = get_model_pricing(params.model)
            estimated_cost = (params.max_tokens / 1_000_000 * output_price +
                             1000 / 1_000_000 * input_price)
            costs.append((estimated_cost, ptype, provider))

        costs.sort(key=lambda x: x[0])

        for cost, ptype, provider in costs:
            return provider

        return self.providers[self.config.default_provider]

    def _select_by_performance(self, params: ChatParams) -> LLMProvider:
        """Select fastest provider based on historical latency."""
        latencies = []
        for ptype, provider in self.providers.items():
            ptype_str = ptype.value
            if ptype_str in self.metrics.provider_breakdown:
                avg_latency = self.metrics.provider_breakdown[ptype_str].avg_latency
            else:
                defaults = {"ollama": 0.5, "exo": 1.0, "anthropic": 2.0, "openai": 1.5}
                avg_latency = defaults.get(ptype_str, 5.0)
            latencies.append((avg_latency, ptype, provider))

        latencies.sort(key=lambda x: x[0])

        for latency, ptype, provider in latencies:
            return provider

        return self.providers[self.config.default_provider]

    def _select_by_memory(
        self,
        params: ChatParams,
        agent_type: Optional[str] = None
    ) -> LLMProvider:
        """
        Select provider based on holographic memory activation field.

        Phase 2 of holographic memory implementation - memory automatically
        influences model selection without explicit retrieval.

        Routing bias mapping:
        - simple: Fast/cheap models (Ollama, Haiku, GPT-4o-mini)
        - balanced: Mid-tier models (Sonnet, GPT-4o)
        - complex: Powerful models (Opus, O1)
        - local: Local inference only (Ollama, Exo)
        """
        try:
            from agi.activation_field import get_activation_field

            field = get_activation_field()

            # Extract query from messages for activation computation
            query = ""
            for msg in params.messages:
                if msg.role == "user":
                    query = msg.content if isinstance(msg.content, str) else str(msg.content)
                    break

            # Compute activation field from query context
            session_context = {"agent_type": agent_type} if agent_type else {}
            state = field.compute_from_context(
                query=query,
                session_context=session_context
            )

            # Get routing bias from activation field
            routing_bias = state.routing_bias

            # Determine dominant bias
            max_bias_key = max(routing_bias, key=routing_bias.get) if routing_bias else "balanced"
            max_bias_value = routing_bias.get(max_bias_key, 0.0) if routing_bias else 0.0

            logger.info(f"Memory-influenced routing: {max_bias_key}={max_bias_value:.2f}, "
                       f"confidence_modifier={state.confidence_modifier:.2f}")

            # Apply confidence modifier to uncertainty estimation
            if state.confidence_modifier != 1.0:
                # High confidence (>1) = lower uncertainty, low confidence (<1) = higher uncertainty
                self.uncertainty_estimator.config.boundary_threshold = (
                    0.5 / state.confidence_modifier
                )

            # Route based on dominant bias
            if max_bias_key == "local" or routing_bias.get("local", 0) > 0.5:
                # Prefer local inference
                if ProviderType.OLLAMA in self.providers:
                    return self.providers[ProviderType.OLLAMA]
                if ProviderType.EXO in self.providers:
                    return self.providers[ProviderType.EXO]

            elif max_bias_key == "simple":
                # Prefer fast/cheap models
                # Priority: Ollama > OpenAI (mini) > Anthropic (Haiku)
                if ProviderType.OLLAMA in self.providers:
                    return self.providers[ProviderType.OLLAMA]
                if ProviderType.OPENAI in self.providers:
                    # OpenAI with mini model preference
                    return self.providers[ProviderType.OPENAI]
                if ProviderType.ANTHROPIC in self.providers:
                    return self.providers[ProviderType.ANTHROPIC]

            elif max_bias_key == "complex":
                # Prefer powerful models
                # Priority: Anthropic (Opus) > OpenAI (O1) > others
                if ProviderType.ANTHROPIC in self.providers:
                    return self.providers[ProviderType.ANTHROPIC]
                if ProviderType.OPENAI in self.providers:
                    return self.providers[ProviderType.OPENAI]

            else:  # balanced
                # Default balanced selection
                if ProviderType.ANTHROPIC in self.providers:
                    return self.providers[ProviderType.ANTHROPIC]
                if ProviderType.OPENAI in self.providers:
                    return self.providers[ProviderType.OPENAI]

            # Fallback to default
            return self.providers.get(
                self.config.default_provider,
                next(iter(self.providers.values()))
            )

        except ImportError as e:
            logger.warning(f"Activation field not available: {e}, falling back to default")
            return self.providers.get(
                self.config.default_provider,
                next(iter(self.providers.values()))
            )
        except Exception as e:
            logger.error(f"Error in memory-influenced routing: {e}, falling back to default")
            return self.providers.get(
                self.config.default_provider,
                next(iter(self.providers.values()))
            )

    async def _handle_provider_error(
        self,
        error: ProviderError,
        params: ChatParams,
        agent_type: Optional[str]
    ) -> ChatResponse:
        """Handle provider error with fallback chain."""
        logger.warning(f"Provider {error.provider} failed: {error}")

        if error.provider in self.metrics.provider_breakdown:
            self.metrics.provider_breakdown[error.provider].errors += 1

        for fallback_type in self.config.fallback_chain:
            if fallback_type in self.providers:
                fallback = self.providers[fallback_type]
                if fallback_type.value == error.provider:
                    continue

                logger.info(f"Trying fallback: {fallback_type.value}")

                try:
                    fallback_params = ChatParams(
                        model=map_model_id(params.model, fallback_type.value),
                        messages=params.messages,
                        temperature=params.temperature,
                        max_tokens=params.max_tokens,
                        tools=params.tools,
                        tool_choice=params.tool_choice,
                        stream=params.stream,
                        metadata=params.metadata
                    )
                    return await fallback.chat(fallback_params)
                except Exception as e:
                    logger.warning(f"Fallback {fallback_type.value} also failed: {e}")
                    continue

        raise error

    def _track_metrics(
        self,
        provider: str,
        response: ChatResponse,
        latency: float,
        agent_type: Optional[str] = None
    ):
        """Track request metrics."""
        self.metrics.total_requests += 1
        if response.metadata:
            self.metrics.total_cost += response.metadata.cost
        if response.usage:
            self.metrics.total_tokens.input_tokens += response.usage.input_tokens
            self.metrics.total_tokens.output_tokens += response.usage.output_tokens

        if provider not in self.metrics.provider_breakdown:
            self.metrics.provider_breakdown[provider] = ProviderMetrics()

        pm = self.metrics.provider_breakdown[provider]
        pm.requests += 1
        pm.cost += response.metadata.cost if response.metadata else 0
        pm.total_latency += latency
        pm.avg_latency = pm.total_latency / pm.requests

        if agent_type:
            if agent_type not in self.metrics.agent_breakdown:
                self.metrics.agent_breakdown[agent_type] = {"requests": 0, "cost": 0.0}
            self.metrics.agent_breakdown[agent_type]["requests"] += 1
            if response.metadata:
                self.metrics.agent_breakdown[agent_type]["cost"] += response.metadata.cost

        # Record for uncertainty calibration
        # Success = non-empty content response with reasonable latency
        was_successful = (
            response.content and
            len(response.content) > 0 and
            latency < 30.0  # Within reasonable time
        )
        self.record_routing_outcome(provider, was_successful, latency)

    def get_metrics(self) -> RouterMetrics:
        """Get current metrics."""
        return self.metrics

    def get_config(self) -> RouterConfig:
        """Get router configuration."""
        return self.config

    def get_providers(self) -> Dict[ProviderType, LLMProvider]:
        """Get initialized providers."""
        return self.providers

    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = RouterMetrics()

    def record_routing_outcome(self, provider: str, was_successful: bool, latency: float):
        """
        Record routing outcome for uncertainty calibration.

        Args:
            provider: Provider that was used
            was_successful: Whether the request succeeded without errors
            latency: Request latency in seconds
        """
        # Use latency as a proxy for prediction confidence
        # Lower latency = higher confidence, normalized to [0, 1]
        max_latency = 30.0  # 30 seconds max expected
        prediction = 1.0 - min(latency / max_latency, 1.0)

        self.uncertainty_estimator.record_outcome(prediction, was_successful)

    def get_uncertainty_stats(self) -> Dict[str, Any]:
        """Get uncertainty estimation statistics."""
        return self.uncertainty_estimator.get_statistics()

    def get_routing_uncertainty(self, prediction: float) -> Dict[str, float]:
        """
        Get uncertainty for a routing prediction.

        Args:
            prediction: Routing confidence score [0, 1]

        Returns:
            Dict with raw and calibrated uncertainty
        """
        raw, calibrated = self.uncertainty_estimator.get_calibrated_uncertainty(prediction)
        return {"raw_uncertainty": raw, "calibrated_uncertainty": calibrated}
