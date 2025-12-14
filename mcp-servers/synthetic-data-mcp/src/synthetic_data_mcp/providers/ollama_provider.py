"""
Ollama provider implementation for local LLM inference.
"""

import os
import logging
import requests
from typing import Dict, Any

from .base import BaseProvider, ProviderConfig, ProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama provider for local LLM inference."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
            
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate using Ollama."""
        if not self.is_available():
            raise RuntimeError("Ollama server not available")
            
        try:
            model = self.config.model or "llama3.1:8b"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "content": result.get("response", ""),
                "model": model,
                "provider": "ollama",
                "usage": {
                    "total_duration": result.get("total_duration", 0),
                    "load_duration": result.get("load_duration", 0),
                    "prompt_eval_count": result.get("prompt_eval_count", 0),
                    "eval_count": result.get("eval_count", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
            
    def get_cost_estimate(self, record_count: int) -> float:
        """Ollama is free - local inference."""
        return 0.0
        
    def get_available_models(self) -> list:
        """Get list of available Ollama models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception:
            return []
            
    def get_privacy_level(self) -> str:
        """Ollama provides maximum privacy with local inference."""
        return "maximum"
        
    @staticmethod
    def create_from_env() -> 'OllamaProvider':
        """Create Ollama provider from environment variables."""
        config = ProviderConfig(
            provider_type=ProviderType.OLLAMA,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "2000"))
        )
        return OllamaProvider(config)