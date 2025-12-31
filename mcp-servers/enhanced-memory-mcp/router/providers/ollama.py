"""
Ollama local inference provider implementation.
"""

import os
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


class OllamaProvider(LLMProvider):
    """Ollama local inference provider."""

    name = "ollama"
    type = ProviderType.OLLAMA
    supports_streaming = True
    supports_tools = True
    supports_mcp = False

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.base_url = config.base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    async def chat(self, params: ChatParams) -> ChatResponse:
        """Send chat request to Ollama."""
        if httpx is None:
            raise ImportError("httpx package required: pip install httpx")

        messages = [
            {"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)}
            for m in params.messages
        ]

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.config.timeout)) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": params.model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": params.temperature, "num_predict": params.max_tokens}
                    }
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                raise ProviderError(str(e), provider="ollama", retryable=True)

        content_blocks = [ContentBlock(type="text", text=data.get("message", {}).get("content", ""))]
        usage = UsageStats(
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0)
        )

        return ChatResponse(
            id=f"ollama-{int(time.time())}",
            model=params.model,
            content=content_blocks,
            stop_reason=StopReason.END_TURN,
            usage=usage,
            metadata=ResponseMetadata(provider="ollama", model=params.model, cost=0.0)
        )

    def validate_capabilities(self, features: List[str]) -> bool:
        return all(f in ["chat", "streaming"] for f in features)
