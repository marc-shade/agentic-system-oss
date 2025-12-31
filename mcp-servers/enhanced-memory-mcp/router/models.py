"""
Data models and enums for the router package.

Extracted from model_router.py for better organization.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    LITELLM = "litellm"
    GEMINI = "gemini"
    ONNX = "onnx"
    EXO = "exo"  # Distributed inference cluster
    CUSTOM = "custom"


class RoutingMode(str, Enum):
    """Available routing strategies."""
    MANUAL = "manual"
    RULE_BASED = "rule-based"
    COST_OPTIMIZED = "cost-optimized"
    PERFORMANCE_OPTIMIZED = "performance-optimized"
    QUALITY_OPTIMIZED = "quality-optimized"
    MEMORY_INFLUENCED = "memory-influenced"  # Phase 2: Holographic memory routing


class StopReason(str, Enum):
    """Reasons for completion."""
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    TOOL_USE = "tool_use"
    STOP_SEQUENCE = "stop_sequence"


@dataclass
class ContentBlock:
    """Content block in a message."""
    type: Literal["text", "tool_use", "tool_result"]
    text: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[Any] = None
    content: Optional[Any] = None
    is_error: bool = False


@dataclass
class Message:
    """Chat message."""
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[ContentBlock]]


@dataclass
class Tool:
    """Tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ChatParams:
    """Parameters for chat completion."""
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None  # Force specific provider


@dataclass
class UsageStats:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ResponseMetadata:
    """Response metadata."""
    provider: str
    model: Optional[str] = None
    cost: float = 0.0
    latency: float = 0.0
    execution_providers: Optional[List[str]] = None


@dataclass
class ChatResponse:
    """Chat completion response."""
    id: str
    model: str
    content: List[ContentBlock]
    stop_reason: Optional[StopReason] = None
    usage: Optional[UsageStats] = None
    metadata: Optional[ResponseMetadata] = None


@dataclass
class StreamChunk:
    """Streaming response chunk."""
    type: str
    delta: Optional[Dict[str, Any]] = None
    content_block: Optional[ContentBlock] = None
    message: Optional[Dict[str, Any]] = None
    usage: Optional[UsageStats] = None
