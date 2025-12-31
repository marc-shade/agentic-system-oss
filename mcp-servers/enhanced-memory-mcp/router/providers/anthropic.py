"""
Anthropic Claude provider implementation.
"""

import os
from typing import List

from ..config import ProviderConfig
from ..models import (
    ChatParams,
    ChatResponse,
    ContentBlock,
    ProviderType,
    ResponseMetadata,
    StopReason,
    UsageStats,
)
from .base import LLMProvider, ProviderError


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    name = "anthropic"
    type = ProviderType.ANTHROPIC
    supports_streaming = True
    supports_tools = True
    supports_mcp = True

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client = None

    async def chat(self, params: ChatParams) -> ChatResponse:
        """Send chat request to Anthropic."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")

        # Extract system message
        system_msg = None
        messages = []
        for msg in params.messages:
            if msg.role == "system":
                system_msg = msg.content if isinstance(msg.content, str) else str(msg.content)
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else [
                        {"type": b.type, "text": b.text} if b.type == "text" else
                        {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                        for b in msg.content
                    ]
                })

        kwargs = {
            "model": params.model,
            "messages": messages,
            "max_tokens": params.max_tokens,
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if system_msg:
            kwargs["system"] = system_msg
        if params.tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in params.tools
            ]
        if params.tool_choice:
            kwargs["tool_choice"] = params.tool_choice

        async_client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        try:
            response = await async_client.messages.create(**kwargs)
        except Exception as e:
            raise ProviderError(
                str(e), provider="anthropic",
                retryable="rate" in str(e).lower() or "timeout" in str(e).lower()
            )

        content_blocks = []
        for block in response.content:
            if hasattr(block, 'text'):
                content_blocks.append(ContentBlock(type="text", text=block.text))
            elif hasattr(block, 'name'):
                content_blocks.append(ContentBlock(
                    type="tool_use", id=block.id, name=block.name, input=block.input
                ))

        usage = UsageStats(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens
        )

        return ChatResponse(
            id=response.id,
            model=response.model,
            content=content_blocks,
            stop_reason=StopReason(response.stop_reason) if response.stop_reason else None,
            usage=usage,
            metadata=ResponseMetadata(
                provider="anthropic", model=response.model,
                cost=self.calculate_cost(usage, response.model)
            )
        )

    def validate_capabilities(self, features: List[str]) -> bool:
        return all(f in ["chat", "streaming", "tools", "mcp"] for f in features)
