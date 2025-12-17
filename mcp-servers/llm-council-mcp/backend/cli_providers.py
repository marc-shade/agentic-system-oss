"""
CLI Provider Interface
======================

Async subprocess wrappers for CLI-based LLM tools:
- Claude Code CLI
- OpenAI Codex CLI
- Google Gemini CLI

These providers enable local multi-LLM deliberation without API costs.
"""

import asyncio
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from .config import PROVIDER_TIMEOUTS

logger = logging.getLogger(__name__)


@dataclass
class CLIProvider:
    """Configuration for a CLI-based LLM provider."""
    command: str
    args_template: List[str]
    env_override: Optional[Dict[str, str]] = None


# Provider configurations
PROVIDERS: Dict[str, CLIProvider] = {
    "claude": CLIProvider(
        command="claude",
        args_template=["-p", "{prompt}", "--print"],
        # Force OAuth/subscription auth by clearing API key
        env_override={"ANTHROPIC_API_KEY": ""}
    ),
    "codex": CLIProvider(
        command="codex",
        args_template=["{prompt}"]
    ),
    "gemini": CLIProvider(
        command="gemini",
        args_template=["-p", "{prompt}"]
    ),
}


def get_available_providers() -> List[str]:
    """Return list of CLI providers that are installed and available."""
    available = []
    for name, provider in PROVIDERS.items():
        if shutil.which(provider.command):
            available.append(name)
    return available


def _transform_gemini_prompt(prompt: str) -> str:
    """
    Transform prompt for Gemini CLI compatibility.

    Gemini CLI can have issues with certain prompt formats.
    This applies necessary transformations.
    """
    # Remove any file path references that might cause 404
    lines = prompt.split('\n')
    cleaned = []
    for line in lines:
        # Skip lines that look like file paths
        if not (line.strip().startswith('/') and '.' in line):
            cleaned.append(line)
    return '\n'.join(cleaned)


async def query_cli_provider(
    provider: str,
    prompt: str,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Query a single CLI provider asynchronously.

    Args:
        provider: Provider name (claude, codex, gemini)
        prompt: The prompt to send
        timeout: Optional timeout override

    Returns:
        Dict with 'content' and optional 'error' keys
    """
    if provider not in PROVIDERS:
        return {"content": None, "error": f"Unknown provider: {provider}"}

    config = PROVIDERS[provider]

    # Check if provider is installed
    if not shutil.which(config.command):
        return {"content": None, "error": f"{provider} CLI not installed"}

    # Apply provider-specific prompt transformations
    if provider == "gemini":
        prompt = _transform_gemini_prompt(prompt)

    # Build command arguments
    args = []
    for arg in config.args_template:
        if "{prompt}" in arg:
            args.append(arg.replace("{prompt}", prompt))
        else:
            args.append(arg)

    # Build environment
    env = os.environ.copy()
    if config.env_override:
        env.update(config.env_override)

    # Get timeout
    actual_timeout = timeout or PROVIDER_TIMEOUTS.get(provider, 120)

    try:
        logger.info(f"Querying {provider} with timeout {actual_timeout}s")

        process = await asyncio.create_subprocess_exec(
            config.command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=actual_timeout
        )

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else f"Exit code {process.returncode}"
            logger.warning(f"{provider} returned error: {error_msg}")
            return {"content": None, "error": error_msg}

        content = stdout.decode().strip()
        logger.info(f"{provider} returned {len(content)} chars")

        return {"content": content, "error": None}

    except asyncio.TimeoutError:
        logger.warning(f"{provider} timed out after {actual_timeout}s")
        return {"content": None, "error": f"Timeout after {actual_timeout}s"}
    except Exception as e:
        logger.error(f"{provider} error: {e}")
        return {"content": None, "error": str(e)}


async def query_providers_parallel(
    providers: List[str],
    prompt: str,
    timeout: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Query multiple CLI providers in parallel.

    Args:
        providers: List of provider names to query
        prompt: The prompt to send to all providers
        timeout: Optional timeout override

    Returns:
        Dict mapping provider names to their results
    """
    tasks = [
        query_cli_provider(provider, prompt, timeout)
        for provider in providers
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for provider, result in zip(providers, results):
        if isinstance(result, Exception):
            output[provider] = {"content": None, "error": str(result)}
        else:
            output[provider] = result

    return output


async def query_with_file(
    provider: str,
    prompt: str,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Query provider using a temporary file for the prompt.

    Useful for very long prompts that might exceed command line limits.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(prompt)
        temp_path = f.name

    try:
        # Modify args to use file
        if provider == "claude":
            # claude -p "$(cat file)" --print
            file_prompt = f"$(cat {temp_path})"
            return await query_cli_provider(provider, file_prompt, timeout)
        else:
            # For others, just use regular query
            return await query_cli_provider(provider, prompt, timeout)
    finally:
        os.unlink(temp_path)
