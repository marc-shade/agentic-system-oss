"""
LLM Council Configuration
=========================

Environment-based configuration for multi-provider LLM deliberation.

Environment Variables:
- PROVIDER_MODE: "cli" (default) or "openrouter"
- CLI_COUNCIL_MODELS: Comma-separated list of CLI providers (default: claude,codex,gemini)
- CLI_CHAIRMAN_MODEL: Model for final synthesis (default: codex)
- OPENROUTER_API_KEY: Required for openrouter mode
- COUNCIL_MODELS: Comma-separated OpenRouter models for council
- CHAIRMAN_MODEL: OpenRouter model for chairman
"""

import os
from typing import List, Dict, Any


# Provider mode: "cli" uses local CLI tools, "openrouter" uses API
PROVIDER_MODE = os.getenv("PROVIDER_MODE", "cli")

# CLI provider configuration
CLI_COUNCIL_MODELS = os.getenv("CLI_COUNCIL_MODELS", "claude,codex,gemini").split(",")
CLI_CHAIRMAN_MODEL = os.getenv("CLI_CHAIRMAN_MODEL", "codex")

# OpenRouter configuration (alternative to CLI mode)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Default OpenRouter models (if PROVIDER_MODE=openrouter)
DEFAULT_COUNCIL_MODELS = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o",
    "google/gemini-pro-1.5",
]
DEFAULT_CHAIRMAN_MODEL = "anthropic/claude-3.5-sonnet"

# Parse from environment or use defaults
_council_models_env = os.getenv("COUNCIL_MODELS", "")
COUNCIL_MODELS = _council_models_env.split(",") if _council_models_env else DEFAULT_COUNCIL_MODELS
CHAIRMAN_MODEL = os.getenv("CHAIRMAN_MODEL", DEFAULT_CHAIRMAN_MODEL)

# Timeouts (seconds)
PROVIDER_TIMEOUTS: Dict[str, int] = {
    "claude": int(os.getenv("CLAUDE_TIMEOUT", "120")),
    "codex": int(os.getenv("CODEX_TIMEOUT", "120")),
    "gemini": int(os.getenv("GEMINI_TIMEOUT", "120")),
    "openrouter": int(os.getenv("OPENROUTER_TIMEOUT", "60")),
}

# Deliberation settings
MAX_RANKING_RETRIES = int(os.getenv("MAX_RANKING_RETRIES", "2"))
PARALLEL_QUERIES = os.getenv("PARALLEL_QUERIES", "true").lower() == "true"


def get_active_config() -> Dict[str, Any]:
    """Return current active configuration."""
    return {
        "provider_mode": PROVIDER_MODE,
        "cli_models": CLI_COUNCIL_MODELS if PROVIDER_MODE == "cli" else None,
        "cli_chairman": CLI_CHAIRMAN_MODEL if PROVIDER_MODE == "cli" else None,
        "openrouter_models": COUNCIL_MODELS if PROVIDER_MODE == "openrouter" else None,
        "openrouter_chairman": CHAIRMAN_MODEL if PROVIDER_MODE == "openrouter" else None,
        "timeouts": PROVIDER_TIMEOUTS,
        "parallel_queries": PARALLEL_QUERIES,
    }
