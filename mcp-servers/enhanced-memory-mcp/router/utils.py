"""
Utility functions and model mappings for the router package.

Extracted from model_router.py for better organization.
"""

from typing import Tuple


# =============================================================================
# Model Mapping (from model-mapping.ts)
# =============================================================================

CLAUDE_MODELS = {
    "claude-sonnet-4.5": {
        "anthropic": "claude-sonnet-4-5-20250929",
        "openrouter": "anthropic/claude-sonnet-4.5",
        "bedrock": "anthropic.claude-sonnet-4-5-v2:0",
        "canonical": "Claude Sonnet 4.5"
    },
    "claude-opus-4.5": {
        "anthropic": "claude-opus-4-5-20251101",
        "openrouter": "anthropic/claude-opus-4.5",
        "canonical": "Claude Opus 4.5"
    },
    "claude-3.5-sonnet": {
        "anthropic": "claude-3-5-sonnet-20241022",
        "openrouter": "anthropic/claude-3.5-sonnet-20241022",
        "bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "canonical": "Claude 3.5 Sonnet"
    },
    "claude-3.5-haiku": {
        "anthropic": "claude-3-5-haiku-20241022",
        "openrouter": "anthropic/claude-3.5-haiku-20241022",
        "canonical": "Claude 3.5 Haiku"
    }
}

OPENAI_MODELS = {
    "gpt-4o": {
        "openai": "gpt-4o",
        "openrouter": "openai/gpt-4o",
        "canonical": "GPT-4o"
    },
    "gpt-4o-mini": {
        "openai": "gpt-4o-mini",
        "openrouter": "openai/gpt-4o-mini",
        "canonical": "GPT-4o Mini"
    },
    "o1": {
        "openai": "o1",
        "openrouter": "openai/o1",
        "canonical": "O1"
    },
    "o1-mini": {
        "openai": "o1-mini",
        "openrouter": "openai/o1-mini",
        "canonical": "O1 Mini"
    }
}

# Pricing per 1M tokens (input, output)
MODEL_PRICING = {
    "claude-sonnet-4.5": (3.0, 15.0),
    "claude-opus-4.5": (15.0, 75.0),
    "claude-3.5-sonnet": (3.0, 15.0),
    "claude-3.5-haiku": (0.25, 1.25),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "o1": (15.0, 60.0),
    "o1-mini": (3.0, 12.0),
    # Ollama/local models are free
    "llama3.2": (0.0, 0.0),
    "mistral": (0.0, 0.0),
    "gemma2": (0.0, 0.0),
    "deepseek-r1": (0.0, 0.0),
}


def map_model_id(model_id: str, target_provider: str) -> str:
    """Map model ID between providers."""
    # Check Claude models
    for canonical, mapping in CLAUDE_MODELS.items():
        if model_id in [mapping.get("anthropic"), mapping.get("openrouter"),
                        mapping.get("bedrock"), canonical]:
            return mapping.get(target_provider, model_id)

    # Check OpenAI models
    for canonical, mapping in OPENAI_MODELS.items():
        if model_id in [mapping.get("openai"), mapping.get("openrouter"), canonical]:
            return mapping.get(target_provider, model_id)

    return model_id


def get_model_pricing(model_id: str) -> Tuple[float, float]:
    """Get pricing for model (input $/M, output $/M)."""
    normalized = model_id.lower()
    for key, pricing in MODEL_PRICING.items():
        if key in normalized:
            return pricing
    return (0.0, 0.0)  # Unknown model, assume free
