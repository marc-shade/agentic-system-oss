"""Shared CLI-based LLM providers for the agentic system.

Provides unified interface for Claude Code, Codex CLI, and Gemini CLI
with support for:
- Direct CLI execution
- Tmux session execution (persistent context)
- OAuth/subscription authentication
- Enhanced-memory integration
"""

from .cli_providers import (
    CLIProvider,
    ProviderType,
    PROVIDERS,
    query_cli_provider,
    query_providers_parallel,
    get_available_providers,
    get_provider_info,
    get_all_provider_info,
)

from .model_discovery import (
    discover_all_models,
    discover_cli_model,
    get_cached_models,
    run_discovery_pipeline,
)

from .tmux_providers import (
    ExecutionMode,
    TmuxProvider,
    query_in_tmux,
    query_providers_in_tmux,
    get_tmux_session_content,
    list_provider_sessions,
    kill_provider_session,
)

__all__ = [
    # Core providers
    "CLIProvider",
    "ProviderType",
    "PROVIDERS",
    "query_cli_provider",
    "query_providers_parallel",
    "get_available_providers",
    "get_provider_info",
    "get_all_provider_info",
    # Model discovery (automated pipeline)
    "discover_all_models",
    "discover_cli_model",
    "get_cached_models",
    "run_discovery_pipeline",
    # Tmux providers
    "ExecutionMode",
    "TmuxProvider",
    "query_in_tmux",
    "query_providers_in_tmux",
    "get_tmux_session_content",
    "list_provider_sessions",
    "kill_provider_session",
]
