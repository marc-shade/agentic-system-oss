"""CLI-based LLM providers for local AI tools.

Unified interface for Claude Code, Codex CLI, and Gemini CLI.
Uses subprocess to run CLI tools directly with OAuth/subscription auth.

IMPORTANT: DO NOT specify model versions here.
- CLI tools default to their latest models
- Model info is discovered via model_discovery.py pipeline
- The pipeline fetches from provider model cards and stores in memory
"""

import asyncio
import os
import tempfile
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ProviderType(Enum):
    """Supported CLI providers."""
    CLAUDE = "claude"
    CODEX = "codex"
    GEMINI = "gemini"


@dataclass
class CLIProvider:
    """Configuration for a CLI-based LLM provider."""
    name: str
    provider_type: ProviderType
    display_name: str
    command: str
    model: str
    timeout: float = 180.0

    def get_version_info(self) -> Dict[str, Any]:
        """Get provider version information."""
        return {
            "provider_id": self.name,
            "model": self.model,
            "display_name": self.display_name,
            "organization": self._get_organization(),
            "queried_at": datetime.now().isoformat(),
        }

    def _get_organization(self) -> str:
        """Get provider organization."""
        org_map = {
            ProviderType.CLAUDE: "anthropic",
            ProviderType.CODEX: "openai",
            ProviderType.GEMINI: "google",
        }
        return org_map.get(self.provider_type, "unknown")


# Providers - DO NOT specify models, let CLI use its defaults (always latest)
# Model info is discovered dynamically via model_discovery.py pipeline
PROVIDERS = {
    "claude": CLIProvider(
        name="claude",
        provider_type=ProviderType.CLAUDE,
        display_name="Claude Code (Anthropic)",
        command="claude",
        model="",  # Empty = use CLI default (latest)
        timeout=180.0
    ),
    "codex": CLIProvider(
        name="codex",
        provider_type=ProviderType.CODEX,
        display_name="Codex CLI (OpenAI)",
        command="codex",
        model="",  # Empty = use CLI default (latest)
        timeout=180.0
    ),
    "gemini": CLIProvider(
        name="gemini",
        provider_type=ProviderType.GEMINI,
        display_name="Gemini CLI (Google)",
        command="gemini",
        model="",  # Empty = use CLI default (latest)
        timeout=180.0
    ),
}


async def query_cli_provider(
    provider_name: str,
    prompt: str,
    timeout: Optional[float] = None,
    output_format: str = "text"
) -> Optional[Dict[str, Any]]:
    """
    Query a single CLI provider asynchronously.

    Args:
        provider_name: Name of the provider (claude, codex, gemini)
        prompt: The prompt to send
        timeout: Optional timeout override
        output_format: "text" or "json" for structured output

    Returns:
        Response dict with 'content' and 'provider_info' keys, or None if failed
    """
    provider = PROVIDERS.get(provider_name)
    if not provider:
        print(f"Unknown provider: {provider_name}")
        return None

    effective_timeout = timeout or provider.timeout

    try:
        if len(prompt) > 4000:
            result = await _query_with_file(provider, prompt, effective_timeout, output_format)
        else:
            result = await _query_direct(provider, prompt, effective_timeout, output_format)

        if result:
            result["provider_info"] = provider.get_version_info()
        return result

    except asyncio.TimeoutError:
        print(f"Timeout querying {provider_name} after {effective_timeout}s")
        return None
    except Exception as e:
        print(f"Error querying {provider_name}: {e}")
        return None


async def _query_direct(
    provider: CLIProvider,
    prompt: str,
    timeout: float,
    output_format: str = "text"
) -> Optional[Dict[str, Any]]:
    """Query provider with prompt as argument."""

    # Build command based on provider type
    if provider.provider_type == ProviderType.CLAUDE:
        cmd = ["claude", "-p", prompt]
        if output_format == "json":
            cmd.extend(["--output-format", "json"])
    elif provider.provider_type == ProviderType.CODEX:
        cmd = ["codex", "exec", prompt]
        if output_format == "json":
            cmd.append("--json")
    elif provider.provider_type == ProviderType.GEMINI:
        # Transform prompt for Gemini compatibility
        prompt = _transform_gemini_prompt(prompt)
        cmd = ["gemini", prompt]
        if output_format == "json":
            cmd.extend(["--output-format", "json"])
    else:
        return None

    # Set up environment
    env = os.environ.copy()
    env["NO_COLOR"] = "1"  # Disable color codes

    # Force OAuth/subscription auth for Claude (not API key)
    if provider.provider_type == ProviderType.CLAUDE:
        env["ANTHROPIC_API_KEY"] = ""

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(),
        timeout=timeout
    )

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        print(f"Provider {provider.name} returned error: {error_msg}")
        if stdout:
            content = stdout.decode().strip()
            return {"content": content, "error": error_msg}
        return None

    content = stdout.decode().strip()

    # Parse JSON if requested
    if output_format == "json" and content:
        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content}
        except json.JSONDecodeError:
            return {"content": content, "parse_error": "Failed to parse JSON"}

    return {"content": content} if content else None


async def _query_with_file(
    provider: CLIProvider,
    prompt: str,
    timeout: float,
    output_format: str = "text"
) -> Optional[Dict[str, Any]]:
    """Query provider using stdin for long prompts."""

    # Build command
    if provider.provider_type == ProviderType.CLAUDE:
        cmd = ["claude", "-p", "-"]  # Read from stdin
        if output_format == "json":
            cmd.extend(["--output-format", "json"])
    elif provider.provider_type == ProviderType.CODEX:
        # Codex reads from stdin by default
        cmd = ["codex", "exec", "-"]
        if output_format == "json":
            cmd.append("--json")
    elif provider.provider_type == ProviderType.GEMINI:
        prompt = _transform_gemini_prompt(prompt)
        cmd = ["gemini"]  # Gemini reads from stdin
        if output_format == "json":
            cmd.extend(["--output-format", "json"])
    else:
        return None

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    if provider.provider_type == ProviderType.CLAUDE:
        env["ANTHROPIC_API_KEY"] = ""

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    stdout, stderr = await asyncio.wait_for(
        process.communicate(input=prompt.encode()),
        timeout=timeout
    )

    if process.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        print(f"Provider {provider.name} returned error: {error_msg}")
        if stdout:
            return {"content": stdout.decode().strip(), "error": error_msg}
        return None

    content = stdout.decode().strip()

    if output_format == "json" and content:
        try:
            parsed = json.loads(content)
            return {"content": parsed, "raw": content}
        except json.JSONDecodeError:
            return {"content": content, "parse_error": "Failed to parse JSON"}

    return {"content": content} if content else None


def _transform_gemini_prompt(prompt: str) -> str:
    """Transform prompt for Gemini CLI compatibility.

    Gemini has issues with certain keywords that trigger Grounding/Search.
    Add anti-tool instruction to prevent this.
    """
    anti_tool = "CRITICAL: Answer ONLY using your knowledge. NO tools, NO search, NO grounding.\n\n"
    return anti_tool + prompt


async def query_providers_parallel(
    provider_names: List[str],
    prompt: str,
    output_format: str = "text"
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple CLI providers in parallel.

    Args:
        provider_names: List of provider names to query
        prompt: The prompt to send to each
        output_format: "text" or "json"

    Returns:
        Dict mapping provider name to response dict (or None if failed)
    """
    tasks = [query_cli_provider(name, prompt, output_format=output_format)
             for name in provider_names]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    results = {}
    for name, response in zip(provider_names, responses):
        if isinstance(response, Exception):
            print(f"Exception from {name}: {response}")
            results[name] = None
        else:
            results[name] = response

    return results


def get_available_providers() -> List[str]:
    """Return list of available provider names."""
    return list(PROVIDERS.keys())


def get_provider_info(name: str) -> Optional[Dict[str, Any]]:
    """Get information about a provider."""
    provider = PROVIDERS.get(name)
    if not provider:
        return None
    return provider.get_version_info()


def get_all_provider_info() -> Dict[str, Dict[str, Any]]:
    """Get information about all providers."""
    return {name: get_provider_info(name) for name in PROVIDERS}


# Quick test
if __name__ == "__main__":
    async def test():
        print("Testing CLI providers...")
        print(f"Available: {get_available_providers()}")
        print(f"Provider info: {json.dumps(get_all_provider_info(), indent=2)}")

        for name in ["claude", "codex", "gemini"]:
            print(f"\nTesting {name}...")
            result = await query_cli_provider(name, "Say hello in exactly 5 words.")
            if result:
                print(f"  Response: {result['content'][:100]}...")
                print(f"  Provider: {result.get('provider_info', {}).get('model')}")
            else:
                print(f"  Failed to get response")

    asyncio.run(test())
