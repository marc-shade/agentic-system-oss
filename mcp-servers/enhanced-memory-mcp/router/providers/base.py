"""
Base provider interface and common types.
"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional

from ..models import (
    ChatParams,
    ChatResponse,
    ProviderType,
    StreamChunk,
    UsageStats,
)
from ..utils import get_model_pricing


class ProviderError(Exception):
    """Provider-specific error."""
    def __init__(
        self,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str
    type: ProviderType
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_mcp: bool = False

    @abstractmethod
    async def chat(self, params: ChatParams) -> ChatResponse:
        """Send chat completion request."""
        pass

    async def stream(self, params: ChatParams) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion. Default implementation wraps chat()."""
        response = await self.chat(params)
        yield StreamChunk(
            type="message_start",
            message={"id": response.id, "model": response.model}
        )
        for block in response.content:
            yield StreamChunk(type="content_block_start", content_block=block)
        yield StreamChunk(type="message_stop", usage=response.usage)

    @abstractmethod
    def validate_capabilities(self, features: List[str]) -> bool:
        """Validate that provider supports required features."""
        pass

    def calculate_cost(self, usage: UsageStats, model: str) -> float:
        """Calculate cost for usage."""
        input_price, output_price = get_model_pricing(model)
        return (usage.input_tokens / 1_000_000 * input_price +
                usage.output_tokens / 1_000_000 * output_price)
