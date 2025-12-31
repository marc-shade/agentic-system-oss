"""
OpenAI provider implementation.
"""

import json
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


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    name = "openai"
    type = ProviderType.OPENAI
    supports_streaming = True
    supports_tools = True
    supports_mcp = False

    def __init__(self, config: ProviderConfig):
        self.config = config

    async def chat(self, params: ChatParams) -> ChatResponse:
        """Send chat request to OpenAI."""
        try:
            import openai
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        messages = [
            {"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)}
            for m in params.messages
        ]

        kwargs = {
            "model": params.model,
            "messages": messages,
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
        }

        if params.tools:
            kwargs["tools"] = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
                for t in params.tools
            ]

        client = openai.AsyncOpenAI(
            api_key=self.config.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=self.config.base_url,
            organization=self.config.organization,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries
        )

        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            raise ProviderError(
                str(e), provider="openai",
                retryable="rate" in str(e).lower() or "timeout" in str(e).lower()
            )

        choice = response.choices[0]
        content_blocks = []
        if choice.message.content:
            content_blocks.append(ContentBlock(type="text", text=choice.message.content))
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                content_blocks.append(ContentBlock(
                    type="tool_use", id=tc.id, name=tc.function.name,
                    input=json.loads(tc.function.arguments)
                ))

        usage = UsageStats(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens
        ) if response.usage else UsageStats()

        return ChatResponse(
            id=response.id,
            model=response.model,
            content=content_blocks,
            stop_reason=StopReason.END_TURN if choice.finish_reason == "stop" else
                       StopReason.TOOL_USE if choice.finish_reason == "tool_calls" else
                       StopReason.MAX_TOKENS if choice.finish_reason == "length" else None,
            usage=usage,
            metadata=ResponseMetadata(
                provider="openai", model=response.model,
                cost=self.calculate_cost(usage, response.model)
            )
        )

    def validate_capabilities(self, features: List[str]) -> bool:
        return all(f in ["chat", "streaming", "tools"] for f in features)
