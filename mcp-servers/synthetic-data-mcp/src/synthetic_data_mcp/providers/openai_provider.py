"""
OpenAI provider implementation.
"""

import os
import logging
from typing import Dict, Any

from .base import BaseProvider, ProviderConfig, ProviderType

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider for synthetic data generation."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        
    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        try:
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            
            if not api_key or not api_key.startswith("sk-") or len(api_key) < 20:
                return False
                
            # Test the key
            import openai
            self.client = openai.OpenAI(api_key=api_key)
            
            # Simple test request
            response = self.client.models.list()
            return True
            
        except Exception as e:
            logger.debug(f"OpenAI not available: {e}")
            return False
            
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate using OpenAI."""
        if not self.client:
            if not self.is_available():
                raise RuntimeError("OpenAI not available")
                
        try:
            model = self.config.model or "gpt-4"
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": model,
                "provider": "openai",
                "usage": response.usage._asdict() if response.usage else {}
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
            
    def get_cost_estimate(self, record_count: int) -> float:
        """Estimate cost for OpenAI generation."""
        # Rough estimates based on GPT-4 pricing
        model = self.config.model or "gpt-4"
        
        cost_per_record = {
            "gpt-4": 0.03,        # ~$0.03 per record
            "gpt-4-turbo": 0.01,  # ~$0.01 per record  
            "gpt-3.5-turbo": 0.002 # ~$0.002 per record
        }
        
        return cost_per_record.get(model, 0.03) * record_count
        
    @staticmethod
    def create_from_env() -> 'OpenAIProvider':
        """Create OpenAI provider from environment variables."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
        )
        return OpenAIProvider(config)