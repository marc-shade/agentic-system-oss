"""LLM Council Backend - Multi-provider deliberation system."""

from .config import (
    PROVIDER_MODE,
    CLI_COUNCIL_MODELS,
    CLI_CHAIRMAN_MODEL,
    PROVIDER_TIMEOUTS,
)
from .council import (
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    run_full_council,
)
from .cli_providers import (
    query_cli_provider,
    query_providers_parallel,
    get_available_providers,
)
from .patterns import (
    list_patterns,
    run_pattern,
    PATTERNS,
)

__all__ = [
    "PROVIDER_MODE",
    "CLI_COUNCIL_MODELS",
    "CLI_CHAIRMAN_MODEL",
    "PROVIDER_TIMEOUTS",
    "stage1_collect_responses",
    "stage2_collect_rankings",
    "stage3_synthesize_final",
    "run_full_council",
    "query_cli_provider",
    "query_providers_parallel",
    "get_available_providers",
    "list_patterns",
    "run_pattern",
    "PATTERNS",
]
