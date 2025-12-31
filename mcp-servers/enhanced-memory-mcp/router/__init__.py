"""
Router Package - Modular LLM Routing System

Extracted from model_router.py (2,032 lines) for better maintainability.
"""

from .models import (
    ProviderType,
    RoutingMode,
    StopReason,
    ContentBlock,
    Message,
    Tool,
    ChatParams,
    UsageStats,
    ResponseMetadata,
    ChatResponse,
    StreamChunk,
)

from .config import (
    ProviderConfig,
    RoutingRule,
    RoutingConfig,
    MonitoringConfig,
    CacheConfig,
    UncertaintyConfig,
    RouterConfig,
)

from .uncertainty import UncertaintyEstimator

from .providers import (
    LLMProvider,
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider,
    ExoProvider,
    ProviderError,
)

from .intelligent_router import IntelligentModelRouter
from .router import ModelRouter, ProviderMetrics, RouterMetrics
from .tools import register_model_router_tools, chat, get_router
from .utils import map_model_id, get_model_pricing, MODEL_PRICING, OPENAI_MODELS, CLAUDE_MODELS

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
