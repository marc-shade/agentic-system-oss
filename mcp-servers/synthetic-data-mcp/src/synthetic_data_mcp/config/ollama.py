"""
Ollama server configuration and model management for private local inference.

This module provides configuration and model management for Ollama server,
enabling fully private, on-premises synthetic data generation.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from loguru import logger


@dataclass
class OllamaModelConfig:
    """Configuration for an Ollama model."""
    name: str
    size: str
    parameters: str
    description: str
    recommended_use: List[str]
    memory_requirements: str
    context_window: int


class OllamaManager:
    """Manages Ollama server connection and model configuration."""
    
    # Recommended models for synthetic data generation
    RECOMMENDED_MODELS = {
        "llama3.1:8b": OllamaModelConfig(
            name="llama3.1:8b",
            size="4.7GB",
            parameters="8B",
            description="Meta Llama 3.1 8B - Excellent for synthetic data generation",
            recommended_use=["healthcare", "finance", "general"],
            memory_requirements="8GB RAM minimum",
            context_window=128000
        ),
        "llama3.1:70b": OllamaModelConfig(
            name="llama3.1:70b",
            size="40GB",
            parameters="70B",
            description="Meta Llama 3.1 70B - Highest quality synthetic data",
            recommended_use=["complex_healthcare", "financial_modeling", "enterprise"],
            memory_requirements="64GB RAM minimum",
            context_window=128000
        ),
        "codellama:7b": OllamaModelConfig(
            name="codellama:7b",
            size="3.8GB",
            parameters="7B",
            description="Code Llama - Excellent for structured data generation",
            recommended_use=["json_generation", "api_data", "technical"],
            memory_requirements="8GB RAM minimum",
            context_window=16000
        ),
        "mistral:7b": OllamaModelConfig(
            name="mistral:7b",
            size="4.1GB",
            parameters="7B",
            description="Mistral 7B - Fast and efficient for general use",
            recommended_use=["general", "fast_generation", "development"],
            memory_requirements="8GB RAM minimum",
            context_window=32000
        ),
        "phi3:mini": OllamaModelConfig(
            name="phi3:mini",
            size="2.3GB",
            parameters="3.8B",
            description="Microsoft Phi-3 Mini - Lightweight for basic generation",
            recommended_use=["development", "testing", "low_resource"],
            memory_requirements="4GB RAM minimum",
            context_window=128000
        )
    }
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Initialize Ollama manager with server URL."""
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.openai_api_url = f"{self.base_url}/v1"
        
    def is_server_available(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of models currently available on the Ollama server."""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available on the server."""
        available_models = self.get_available_models()
        model_names = [model["name"] for model in available_models]
        return model_name in model_names
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model to the Ollama server."""
        try:
            logger.info(f"Pulling Ollama model: {model_name}")
            response = requests.post(
                f"{self.api_url}/pull",
                json={"name": model_name},
                timeout=600  # 10 minutes for model download
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        try:
            response = requests.post(
                f"{self.api_url}/show",
                json={"name": model_name},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return None
    
    def recommend_model_for_use_case(self, use_case: str, available_memory_gb: int = 16) -> Optional[str]:
        """Recommend the best model for a specific use case given memory constraints."""
        suitable_models = []
        
        for model_name, config in self.RECOMMENDED_MODELS.items():
            # Check memory requirements
            memory_req = int(config.memory_requirements.split()[0].replace("GB", ""))
            if memory_req <= available_memory_gb:
                # Check if model supports the use case
                if use_case in config.recommended_use or "general" in config.recommended_use:
                    suitable_models.append((model_name, config))
        
        if not suitable_models:
            return None
        
        # Sort by parameter count (higher is better, but within memory constraints)
        suitable_models.sort(key=lambda x: int(x[1].parameters.replace("B", "")), reverse=True)
        
        recommended_model = suitable_models[0][0]
        logger.info(f"Recommended model for {use_case}: {recommended_model}")
        return recommended_model
    
    def setup_for_synthetic_data(self, domain: str = "healthcare", memory_gb: int = 16) -> Optional[str]:
        """Set up Ollama with the best model for synthetic data generation."""
        if not self.is_server_available():
            logger.error("Ollama server is not available")
            return None
        
        # Get recommended model for domain
        recommended_model = self.recommend_model_for_use_case(domain, memory_gb)
        if not recommended_model:
            logger.warning(f"No suitable model found for {domain} with {memory_gb}GB memory")
            return None
        
        # Check if model is already available
        if self.is_model_available(recommended_model):
            logger.info(f"Model {recommended_model} is already available")
            return recommended_model
        
        # Try to pull the model
        if self.pull_model(recommended_model):
            return recommended_model
        
        # If recommended model fails, try a smaller fallback
        fallback_model = "phi3:mini" if memory_gb < 8 else "mistral:7b"
        logger.info(f"Trying fallback model: {fallback_model}")
        
        if not self.is_model_available(fallback_model):
            if self.pull_model(fallback_model):
                return fallback_model
        else:
            return fallback_model
        
        return None
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the Ollama server."""
        info = {
            "server_available": False,
            "base_url": self.base_url,
            "models": [],
            "recommended_models": [],
            "privacy_status": "🔒 FULLY LOCAL INFERENCE"
        }
        
        if not self.is_server_available():
            return info
        
        info["server_available"] = True
        info["models"] = self.get_available_models()
        
        # Add recommendations
        for model_name, config in self.RECOMMENDED_MODELS.items():
            info["recommended_models"].append({
                "name": model_name,
                "description": config.description,
                "size": config.size,
                "use_cases": config.recommended_use,
                "available": self.is_model_available(model_name)
            })
        
        return info
    
    def get_configuration_guide(self) -> Dict[str, Any]:
        """Get a configuration guide for setting up Ollama with synthetic data MCP."""
        return {
            "installation": {
                "macos": "brew install ollama",
                "linux": "curl -fsSL https://ollama.ai/install.sh | sh",
                "windows": "Download from https://ollama.ai/download"
            },
            "startup": {
                "command": "ollama serve",
                "background": "ollama serve &",
                "systemd": "systemctl start ollama"
            },
            "environment_variables": {
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "OLLAMA_MODEL": "llama3.1:8b",
                "OLLAMA_HOST": "0.0.0.0:11434",
                "OLLAMA_MODELS": "~/.ollama/models"
            },
            "recommended_models": [
                {
                    "name": "llama3.1:8b",
                    "command": "ollama pull llama3.1:8b",
                    "use_case": "General synthetic data generation"
                },
                {
                    "name": "codellama:7b", 
                    "command": "ollama pull codellama:7b",
                    "use_case": "Structured JSON data generation"
                },
                {
                    "name": "phi3:mini",
                    "command": "ollama pull phi3:mini",
                    "use_case": "Development and testing"
                }
            ],
            "privacy_benefits": [
                "🔒 100% Local Inference - No data leaves your infrastructure",
                "🛡️ No API Keys Required - No cloud service dependencies",
                "⚡ Fast Response Times - No network latency",
                "💰 Cost Effective - No per-token charges",
                "🔧 Full Control - Choose your models and configurations",
                "📊 Compliance Ready - Meets strictest data residency requirements"
            ]
        }


def get_ollama_config() -> Dict[str, str]:
    """Get Ollama configuration from environment variables."""
    return {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        "host": os.getenv("OLLAMA_HOST", "0.0.0.0:11434"),
        "models_dir": os.getenv("OLLAMA_MODELS", "~/.ollama/models")
    }


def print_ollama_status():
    """Print comprehensive Ollama status for debugging."""
    manager = OllamaManager()
    info = manager.get_server_info()
    
    print("🦙 OLLAMA SERVER STATUS")
    print("=" * 50)
    print(f"Server Available: {'✅' if info['server_available'] else '❌'}")
    print(f"Base URL: {info['base_url']}")
    print(f"Privacy Status: {info['privacy_status']}")
    
    if info['server_available']:
        print(f"\nInstalled Models ({len(info['models'])}):")
        for model in info['models']:
            print(f"  • {model['name']} ({model.get('size', 'unknown size')})")
        
        print(f"\nRecommended Models:")
        for model in info['recommended_models']:
            status = "✅ Installed" if model['available'] else "📥 Available to pull"
            print(f"  • {model['name']} - {status}")
            print(f"    {model['description']}")
            print(f"    Size: {model['size']}, Use cases: {', '.join(model['use_cases'])}")
    
    config = get_ollama_config()
    print(f"\nConfiguration:")
    for key, value in config.items():
        print(f"  {key.upper()}: {value}")


if __name__ == "__main__":
    print_ollama_status()