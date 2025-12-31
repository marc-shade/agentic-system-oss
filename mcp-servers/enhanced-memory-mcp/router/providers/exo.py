"""
Exo distributed inference cluster provider implementation.
"""

import time
from typing import List

try:
    import httpx
except ImportError:
    httpx = None

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


class ExoProvider(LLMProvider):
    """Exo distributed inference cluster provider."""

    name = "exo"
    type = ProviderType.EXO
    supports_streaming = True
    supports_tools = False
    supports_mcp = False

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:52415"

    async def chat(self, params: ChatParams) -> ChatResponse:
        """Send chat request to Exo cluster."""
        if httpx is None:
            raise ImportError("httpx package required: pip install httpx")

        messages = [
            {"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)}
            for m in params.messages
        ]

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout)) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": params.model,
                        "messages": messages,
                        "temperature": params.temperature,
                        "max_tokens": params.max_tokens,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                raise ProviderError(str(e), provider="exo", retryable=True)

        choice = data["choices"][0]
        content_blocks = [ContentBlock(type="text", text=choice["message"]["content"])]
        usage = UsageStats(
            input_tokens=data.get("usage", {}).get("prompt_tokens", 0),
            output_tokens=data.get("usage", {}).get("completion_tokens", 0)
        )

        return ChatResponse(
            id=data.get("id", f"exo-{int(time.time())}"),
            model=params.model,
            content=content_blocks,
            stop_reason=StopReason.END_TURN,
            usage=usage,
            metadata=ResponseMetadata(provider="exo", model=params.model, cost=0.0)
        )

    def validate_capabilities(self, features: List[str]) -> bool:
        return all(f in ["chat", "streaming"] for f in features)
