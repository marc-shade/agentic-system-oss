"""Ollama integration for local model support."""
import httpx
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class OllamaModel:
    name: str
    size: int
    modified_at: str
    digest: str


class OllamaClient:
    """Client for Ollama local model inference."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[OllamaModel]:
        """List available models."""
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [
                OllamaModel(
                    name=m["name"],
                    size=m.get("size", 0),
                    modified_at=m.get("modified_at", ""),
                    digest=m.get("digest", "")
                )
                for m in data.get("models", [])
            ]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        format: Optional[str] = None,  # "json" for JSON mode
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generate text with specified model."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        if stop:
            payload["options"]["stop"] = stop

        try:
            response = await self._client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    async def generate_with_schema(
        self,
        model: str,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Generate JSON output conforming to schema."""
        schema_instruction = f"""You must respond with valid JSON that conforms to this schema:
{json.dumps(schema, indent=2)}

Output ONLY the JSON, no other text."""

        full_system = schema_instruction
        if system:
            full_system = f"{system}\n\n{schema_instruction}"

        response = await self.generate(
            model=model,
            prompt=prompt,
            system=full_system,
            temperature=temperature,
            max_tokens=max_tokens,
            format="json"
        )

        # Parse and validate JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Invalid JSON response: {e}")

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        format: Optional[str] = None,
    ) -> str:
        """Chat completion with message history."""
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }

        if format:
            payload["format"] = format

        try:
            response = await self._client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Default client instance
_default_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create default Ollama client."""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client


async def cleanup():
    """Cleanup resources."""
    global _default_client
    if _default_client:
        await _default_client.close()
        _default_client = None
