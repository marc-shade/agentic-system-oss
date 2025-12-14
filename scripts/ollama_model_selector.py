#!/usr/bin/env python3
"""
Ollama Model Selector - Cloud-First Strategy

Implements intelligent model selection:
1. PREFER: Cloud models (API-routed, zero compute)
2. FALLBACK: Remote node models (completeu-server, mac-studio)
3. LOCAL ONLY: Embedding models (node-specific datasets)

Usage:
    from scripts.ollama_model_selector import OllamaModelSelector

    selector = OllamaModelSelector()
    model = selector.get_model(task_type="chat")
    # Returns: "gpt-oss:20b-cloud"
"""

import os
import requests
from typing import Optional, Dict, List
from enum import Enum


class TaskType(Enum):
    """Task types for model selection"""
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    VISION = "vision"
    EMBEDDING = "embedding"


class OllamaModelSelector:
    """
    Intelligent model selector with cloud-first strategy
    """

    # Cloud models (API-routed, zero compute)
    CLOUD_MODELS = {
        TaskType.CHAT: "gpt-oss:20b-cloud",
        TaskType.CODE: "gpt-oss:20b-cloud",
        TaskType.REASONING: "gpt-oss:120b-cloud",
        TaskType.TOOL_USE: "gpt-oss:20b-cloud",
    }

    # Remote models (fallback when cloud doesn't support feature)
    REMOTE_MODELS = {
        TaskType.CHAT: "llama3-groq-tool-use:8b-fp16",
        TaskType.CODE: "qwen3-coder:30b",
        TaskType.REASONING: "deepseek-r1:32b-qwen-distill-fp16",
        TaskType.TOOL_USE: "llama3-groq-tool-use:8b-fp16",
        TaskType.VISION: "llama3.2-vision:11b-instruct-q8_0",  # mac-studio only
    }

    # Local models (embeddings only - node-specific)
    LOCAL_MODELS = {
        TaskType.EMBEDDING: "nomic-embed-text:latest",
    }

    # Endpoints
    PRIMARY_ENDPOINT = "http://192.168.1.186:11434"  # completeu-server
    SECONDARY_ENDPOINT = "http://192.168.1.16:11434"  # mac-studio
    LOCAL_ENDPOINT = "http://localhost:11434"

    def __init__(self):
        """Initialize model selector"""
        self.ollama_url = os.environ.get('OLLAMA_URL', self.PRIMARY_ENDPOINT)
        self.ollama_api_key = os.environ.get('OLLAMA_API_KEY', '')

    def get_model(
        self,
        task_type: str = "chat",
        prefer_cloud: bool = True,
        allow_local: bool = False
    ) -> str:
        """
        Get best model for task type

        Args:
            task_type: Type of task (chat, code, reasoning, tool_use, vision, embedding)
            prefer_cloud: Prefer cloud models (default: True)
            allow_local: Allow local inference for non-embedding tasks (default: False)

        Returns:
            Model name string
        """
        task = TaskType(task_type)

        # Embeddings must be local (node-specific datasets)
        if task == TaskType.EMBEDDING:
            return self.LOCAL_MODELS[TaskType.EMBEDDING]

        # Try cloud first (if preferred and available)
        if prefer_cloud and task in self.CLOUD_MODELS:
            cloud_model = self.CLOUD_MODELS[task]
            if self._is_model_available(cloud_model, self.PRIMARY_ENDPOINT):
                return cloud_model

        # Fallback to remote models
        if task in self.REMOTE_MODELS:
            remote_model = self.REMOTE_MODELS[task]

            # Try primary endpoint
            if self._is_model_available(remote_model, self.PRIMARY_ENDPOINT):
                return remote_model

            # Try secondary endpoint (mac-studio for vision)
            if task == TaskType.VISION:
                if self._is_model_available(remote_model, self.SECONDARY_ENDPOINT):
                    return remote_model

        # Should not reach here - throw error
        if not allow_local:
            raise ValueError(
                f"No cloud or remote model available for task: {task_type}. "
                f"Local inference not allowed (CPU-only node)."
            )

        # Emergency fallback (should not be used)
        return "llama3.2:latest"

    def get_endpoint(self, model: str) -> str:
        """
        Get endpoint URL for model

        Args:
            model: Model name

        Returns:
            Endpoint URL
        """
        # Cloud models use primary endpoint
        if model.endswith("-cloud"):
            return self.PRIMARY_ENDPOINT

        # Embeddings use local endpoint
        if "embed" in model.lower():
            return self.LOCAL_ENDPOINT

        # Vision models use secondary endpoint (mac-studio)
        if "vision" in model.lower():
            return self.SECONDARY_ENDPOINT

        # Default to primary endpoint
        return self.PRIMARY_ENDPOINT

    def _is_model_available(self, model: str, endpoint: str) -> bool:
        """
        Check if model is available at endpoint

        Args:
            model: Model name
            endpoint: Endpoint URL

        Returns:
            True if available, False otherwise
        """
        try:
            response = requests.get(f"{endpoint}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return any(m['name'] == model for m in models)
        except Exception:
            pass
        return False

    def get_available_models(self, endpoint: Optional[str] = None) -> List[Dict]:
        """
        Get list of available models

        Args:
            endpoint: Specific endpoint to query (default: primary)

        Returns:
            List of model dictionaries
        """
        if endpoint is None:
            endpoint = self.PRIMARY_ENDPOINT

        try:
            response = requests.get(f"{endpoint}/api/tags", timeout=2)
            if response.status_code == 200:
                return response.json().get('models', [])
        except Exception:
            pass
        return []


# Convenience function
def get_ollama_model(task_type: str = "chat", prefer_cloud: bool = True) -> str:
    """
    Quick helper to get model for task

    Args:
        task_type: Type of task (chat, code, reasoning, tool_use, vision, embedding)
        prefer_cloud: Prefer cloud models (default: True)

    Returns:
        Model name string
    """
    selector = OllamaModelSelector()
    return selector.get_model(task_type=task_type, prefer_cloud=prefer_cloud)


if __name__ == "__main__":
    # Demo usage
    selector = OllamaModelSelector()

    print("🤖 Ollama Model Selector - Cloud-First Strategy\n")

    tasks = ["chat", "code", "reasoning", "tool_use", "embedding"]

    for task in tasks:
        try:
            model = selector.get_model(task_type=task)
            endpoint = selector.get_endpoint(model)

            # Determine type
            if model.endswith("-cloud"):
                type_str = "☁️  CLOUD"
            elif "embed" in model.lower():
                type_str = "💾 LOCAL"
            else:
                type_str = "🌐 REMOTE"

            print(f"{task.upper():<12} → {type_str} → {model}")
            print(f"             Endpoint: {endpoint}\n")
        except Exception as e:
            print(f"{task.upper():<12} → ❌ ERROR: {e}\n")

    # Show available cloud models
    print("\n☁️  Available Cloud Models:")
    for task, model in selector.CLOUD_MODELS.items():
        print(f"  - {model} ({task.value})")
