"""
Base provider interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    MOCK = "mock"


@dataclass
class ProviderConfig:
    """Configuration for LLM providers."""
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    additional_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_params is None:
            self.additional_params = {}


class BaseProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_type = config.provider_type
        
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate synthetic data using the provider."""
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass
        
    @abstractmethod
    def get_cost_estimate(self, record_count: int) -> float:
        """Get estimated cost for generating the specified number of records."""
        pass
        
    def get_privacy_level(self) -> str:
        """Get the privacy level for this provider."""
        if self.provider_type == ProviderType.OLLAMA:
            return "maximum"  # Local inference
        else:
            return "medium"   # Cloud-based inference
            
    def supports_compliance_framework(self, framework: str) -> bool:
        """Check if provider supports specific compliance framework."""
        # All providers support basic compliance, local providers offer more
        supported_frameworks = ["hipaa", "gdpr", "pci_dss", "sox"]
        return framework.lower() in supported_frameworks