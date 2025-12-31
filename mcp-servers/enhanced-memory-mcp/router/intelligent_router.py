"""
Legacy IntelligentModelRouter for backward compatibility.

Routes AI tasks to optimal models based on complexity and requirements.
Supports both local Ollama models and cloud-based models.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("model_router")


class IntelligentModelRouter:
    """
    Routes AI tasks to optimal models based on complexity and requirements.

    Supports both local Ollama models and cloud-based Ollama models.
    Tracks performance statistics for continuous optimization.
    """

    def __init__(self, stats_file: Optional[str] = None):
        """
        Initialize the intelligent model router.

        Args:
            stats_file: Path to JSON file for tracking routing statistics
        """
        self.stats_file = Path(stats_file) if stats_file else None
        self.ollama_base_url = "http://localhost:11434"

        # Model configuration
        self.models = {
            "local_reasoning": "deepseek-r1:32b-qwen-distill-fp16",
            "local_powerful": "gpt-oss:120b",
            "cloud_powerful": "gpt-oss:20b-cloud"
        }

        # Routing thresholds
        self.complexity_thresholds = {
            "simple": 40,      # < 40: basic local model
            "moderate": 70,    # 40-70: powerful local model
            "complex": 100     # > 70: cloud or reasoning model
        }

        # Initialize stats
        self.stats = self._load_stats()

        logger.info(f"IntelligentModelRouter initialized with {len(self.models)} models")

    def _load_stats(self) -> Dict[str, Any]:
        """Load routing statistics from file."""
        if self.stats_file and self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load stats from {self.stats_file}: {e}")

        return {
            "total_requests": 0,
            "local_requests": 0,
            "cloud_requests": 0,
            "total_duration": 0.0,
            "model_usage": {},
            "complexity_distribution": {
                "simple": 0,
                "moderate": 0,
                "complex": 0
            }
        }

    def _save_stats(self):
        """Save routing statistics to file."""
        if self.stats_file:
            try:
                self.stats_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.stats_file, 'w') as f:
                    json.dump(self.stats, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save stats to {self.stats_file}: {e}")

    def _select_model(self, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Select the optimal model based on task context.

        Args:
            context: Task context with complexity, requires_reasoning, etc.

        Returns:
            Tuple of (model_name, location) where location is 'local' or 'cloud'
        """
        complexity = context.get("complexity", 50)
        requires_reasoning = context.get("requires_reasoning", False)
        multi_step = context.get("multi_step", False)

        # Reasoning tasks always use reasoning model
        if requires_reasoning or multi_step:
            logger.info(f"Routing to reasoning model (reasoning={requires_reasoning}, multi_step={multi_step})")
            return self.models["local_reasoning"], "local"

        # Route based on complexity
        if complexity < self.complexity_thresholds["simple"]:
            # Simple tasks - use local powerful model
            return self.models["local_powerful"], "local"
        elif complexity < self.complexity_thresholds["moderate"]:
            # Moderate tasks - use local powerful model
            return self.models["local_powerful"], "local"
        else:
            # Complex tasks - prefer cloud for best results
            logger.info(f"High complexity ({complexity}) - routing to cloud model")
            return self.models["cloud_powerful"], "cloud"

    async def _execute_ollama_request(
        self,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute request to Ollama API.

        Args:
            model: Model name to use
            prompt: Prompt text
            options: Optional model parameters

        Returns:
            Response dictionary from Ollama
        """
        if httpx is None:
            raise ImportError("httpx package required: pip install httpx")

        url = f"{self.ollama_base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Ollama API error for model {model}: {e}")
                raise

    async def execute_with_routing(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task with intelligent model routing.

        Args:
            task: Task description/prompt
            context: Task context (complexity, requires_reasoning, etc.)
            **kwargs: Additional parameters passed to model

        Returns:
            Dictionary containing:
                - response: Model's response text
                - model_used: Name of model that processed the task
                - location: 'local' or 'cloud'
                - duration_seconds: Processing time
                - complexity: Task complexity level
        """
        start_time = time.time()
        context = context or {}

        # Select optimal model
        model_name, location = self._select_model(context)

        logger.info(f"Executing task with {model_name} ({location})")

        try:
            # Execute the task
            result = await self._execute_ollama_request(
                model=model_name,
                prompt=task,
                options=kwargs.get("options")
            )

            duration = time.time() - start_time

            # Update statistics
            self._update_stats(
                model=model_name,
                location=location,
                complexity=context.get("complexity", 50),
                duration=duration
            )

            return {
                "response": result.get("response", ""),
                "model_used": model_name,
                "location": location,
                "duration_seconds": duration,
                "complexity": context.get("complexity", 50),
                "tokens_generated": result.get("eval_count", 0),
                "tokens_prompt": result.get("prompt_eval_count", 0)
            }

        except Exception as e:
            logger.error(f"Error executing task with {model_name}: {e}")
            # Return error response
            return {
                "response": f"Error: Failed to process task - {str(e)}",
                "model_used": model_name,
                "location": location,
                "duration_seconds": time.time() - start_time,
                "complexity": context.get("complexity", 50),
                "error": str(e)
            }

    def _update_stats(
        self,
        model: str,
        location: str,
        complexity: int,
        duration: float
    ):
        """Update routing statistics."""
        self.stats["total_requests"] += 1
        self.stats["total_duration"] += duration

        if location == "local":
            self.stats["local_requests"] += 1
        else:
            self.stats["cloud_requests"] += 1

        # Track model usage
        if model not in self.stats["model_usage"]:
            self.stats["model_usage"][model] = {
                "count": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0
            }

        model_stats = self.stats["model_usage"][model]
        model_stats["count"] += 1
        model_stats["total_duration"] += duration
        model_stats["avg_duration"] = model_stats["total_duration"] / model_stats["count"]

        # Track complexity distribution
        if complexity < self.complexity_thresholds["simple"]:
            self.stats["complexity_distribution"]["simple"] += 1
        elif complexity < self.complexity_thresholds["moderate"]:
            self.stats["complexity_distribution"]["moderate"] += 1
        else:
            self.stats["complexity_distribution"]["complex"] += 1

        # Save updated stats
        self._save_stats()

    def get_stats(self) -> Dict[str, Any]:
        """Get current routing statistics."""
        return self.stats.copy()

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of available models.

        Returns:
            Dictionary with model availability status
        """
        if httpx is None:
            return {
                "ollama_available": False,
                "models_available": {},
                "timestamp": time.time(),
                "error": "httpx package required"
            }

        health = {
            "ollama_available": False,
            "models_available": {},
            "timestamp": time.time()
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check Ollama availability
                response = await client.get(f"{self.ollama_base_url}/api/tags")
                response.raise_for_status()
                health["ollama_available"] = True

                # Check each configured model
                available_models = response.json().get("models", [])
                available_names = [m["name"] for m in available_models]

                for model_type, model_name in self.models.items():
                    health["models_available"][model_type] = {
                        "name": model_name,
                        "available": model_name in available_names
                    }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health["error"] = str(e)

        return health
