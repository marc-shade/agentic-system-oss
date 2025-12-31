#!/usr/bin/env python3
"""
ModelRouter - Multi-Provider LLM Routing System

FACADE MODULE - This file maintains backward compatibility.
All implementations have been moved to the router/ package.

Comprehensive routing system ported from ruvnet/agentic-flow TypeScript implementation.
Provides intelligent routing across multiple LLM providers with:

1. Multiple Providers: Anthropic, OpenAI, OpenRouter, Ollama, Exo, Gemini, LiteLLM
2. 4 Routing Modes: manual, rule-based, cost-optimized, performance-optimized
3. Provider Fallback Chains: Automatic failover on errors
4. Metrics Tracking: Per-provider and per-agent-type statistics
5. Streaming Support: Async generators for streaming responses
6. Integration: MCP tools for enhanced-memory integration

Also includes legacy IntelligentModelRouter for backward compatibility.

https://github.com/ruvnet/agentic-flow

Refactored Structure (2,032 lines -> modular package):
- router/models.py: Data classes and enums
- router/config.py: Configuration classes
- router/uncertainty.py: UncertaintyEstimator
- router/utils.py: Model mappings and utilities
- router/providers/: LLM provider implementations
- router/intelligent_router.py: Legacy IntelligentModelRouter
- router/router.py: Main ModelRouter class
- router/tools.py: MCP tool registration
"""

from __future__ import annotations

# =============================================================================
# Re-export everything from the router package for backward compatibility
# =============================================================================

from router import (
    # Enums
    ProviderType,
    RoutingMode,
    StopReason,
    # Data classes
    ContentBlock,
    Message,
    Tool,
    ChatParams,
    UsageStats,
    ResponseMetadata,
    ChatResponse,
    StreamChunk,
    # Config classes
    ProviderConfig,
    RoutingRule,
    RoutingConfig,
    MonitoringConfig,
    CacheConfig,
    UncertaintyConfig,
    RouterConfig,
    # Uncertainty
    UncertaintyEstimator,
    # Providers
    LLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider,
    ExoProvider,
    ProviderError,
    # Routers
    IntelligentModelRouter,
    ModelRouter,
    ProviderMetrics,
    RouterMetrics,
    # Tools and convenience functions
    register_model_router_tools,
    chat,
    get_router,
    # Utils
    map_model_id,
    get_model_pricing,
    MODEL_PRICING,
    OPENAI_MODELS,
    CLAUDE_MODELS,
)


__all__ = [
    # Enums
    "ProviderType",
    "RoutingMode",
    "StopReason",
    # Data classes
    "ContentBlock",
    "Message",
    "Tool",
    "ChatParams",
    "UsageStats",
    "ResponseMetadata",
    "ChatResponse",
    "StreamChunk",
    # Config classes
    "ProviderConfig",
    "RoutingRule",
    "RoutingConfig",
    "MonitoringConfig",
    "CacheConfig",
    "UncertaintyConfig",
    "RouterConfig",
    # Uncertainty
    "UncertaintyEstimator",
    # Providers
    "LLMProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "ExoProvider",
    "ProviderError",
    # Routers
    "IntelligentModelRouter",
    "ModelRouter",
    "ProviderMetrics",
    "RouterMetrics",
    # Tools and convenience functions
    "register_model_router_tools",
    "chat",
    "get_router",
    # Utils
    "map_model_id",
    "get_model_pricing",
    "MODEL_PRICING",
    "OPENAI_MODELS",
    "CLAUDE_MODELS",
]
