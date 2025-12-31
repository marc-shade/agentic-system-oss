"""
Model Discovery Pipeline

Automated discovery of current model versions from provider sources.
This is part of the system's self-evolution infrastructure.

Pipeline:
1. Fetch model cards from provider documentation/APIs
2. Parse and extract model information
3. Store in enhanced-memory for system-wide access
4. Run regularly via Temporal/AutoKitteh workflows

Sources:
- Anthropic: https://docs.anthropic.com/en/docs/about-claude/models
- OpenAI: https://platform.openai.com/docs/models
- Google: https://ai.google.dev/gemini-api/docs/models/gemini
"""

import asyncio
import subprocess
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class DiscoveredModel:
    """Model information discovered from provider."""
    provider: str
    model_id: str
    display_name: str
    family: str
    context_window: Optional[int] = None
    capabilities: Optional[List[str]] = None
    release_date: Optional[str] = None
    is_latest: bool = False
    source_url: str = ""
    discovered_at: str = ""


# Provider documentation URLs for model cards
MODEL_CARD_SOURCES = {
    "anthropic": "https://docs.anthropic.com/en/docs/about-claude/models",
    "openai": "https://platform.openai.com/docs/models",
    "google": "https://ai.google.dev/gemini-api/docs/models/gemini",
}


async def discover_cli_model(provider: str) -> Optional[Dict[str, Any]]:
    """
    Discover current model by querying the CLI tool directly.

    This is the most reliable method - ask the CLI what it's using.
    """
    try:
        if provider == "claude":
            # Ask Claude Code what model it's using
            cmd = ["claude", "-p", "What exact model ID are you? Reply with ONLY the model ID string, nothing else.", "--output-format", "json"]
        elif provider == "codex":
            cmd = ["codex", "exec", "What exact model ID are you? Reply with ONLY the model ID string."]
        elif provider == "gemini":
            cmd = ["gemini", "What exact model ID are you? Reply with ONLY the model ID string, nothing else."]
        else:
            return None

        env = dict(__import__('os').environ)
        env["NO_COLOR"] = "1"
        if provider == "claude":
            env["ANTHROPIC_API_KEY"] = ""  # Force OAuth

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60
        )

        if process.returncode == 0:
            content = stdout.decode().strip()

            # Parse JSON if claude
            if provider == "claude" and content.startswith("{"):
                try:
                    data = json.loads(content)
                    content = data.get("result", content)
                except json.JSONDecodeError:
                    pass

            # Extract model ID from response
            # Models typically look like: claude-opus-4-5-20251101, gpt-5.2-thinking, gemini-3-flash
            model_patterns = [
                r'claude-[\w\-\.]+',
                r'gpt-[\w\-\.]+',
                r'gemini-[\w\-\.]+',
                r'o\d+-[\w\-\.]+',  # o3-mini, o4-mini
            ]

            for pattern in model_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return {
                        "provider": provider,
                        "model_id": match.group(0),
                        "discovered_via": "cli_query",
                        "raw_response": content[:200],
                        "discovered_at": datetime.now().isoformat(),
                    }

            # If no pattern match, return raw (might still be useful)
            return {
                "provider": provider,
                "model_id": content[:100],  # Truncate
                "discovered_via": "cli_query_raw",
                "discovered_at": datetime.now().isoformat(),
            }

    except asyncio.TimeoutError:
        return {"provider": provider, "error": "timeout"}
    except Exception as e:
        return {"provider": provider, "error": str(e)}

    return None


async def discover_from_version_command(provider: str) -> Optional[Dict[str, Any]]:
    """
    Get model info from CLI version/info commands.
    """
    try:
        if provider == "claude":
            cmd = ["claude", "--version"]
        elif provider == "codex":
            cmd = ["codex", "--version"]
        elif provider == "gemini":
            cmd = ["gemini", "--version"]
        else:
            return None

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=10
        )

        version_info = stdout.decode().strip()

        return {
            "provider": provider,
            "cli_version": version_info,
            "discovered_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"provider": provider, "error": str(e)}


async def discover_all_models() -> Dict[str, Any]:
    """
    Discover current models from all providers.

    Returns dict with model info for each provider.
    """
    results = {}

    # First get CLI versions
    version_tasks = [
        discover_from_version_command("claude"),
        discover_from_version_command("codex"),
        discover_from_version_command("gemini"),
    ]

    versions = await asyncio.gather(*version_tasks, return_exceptions=True)

    for i, provider in enumerate(["claude", "codex", "gemini"]):
        if isinstance(versions[i], dict):
            results[provider] = {"version_info": versions[i]}
        else:
            results[provider] = {"version_info": {"error": str(versions[i])}}

    # Then try to discover actual models (this takes longer)
    # Only do this if specifically requested

    return {
        "discovered_at": datetime.now().isoformat(),
        "providers": results,
        "note": "CLI tools use their default (latest) models. Use discover_cli_model() for active discovery.",
    }


async def store_discovered_models(models: Dict[str, Any]) -> bool:
    """
    Store discovered model information in enhanced-memory.

    This enables the rest of the system to query current model info.
    """
    try:
        # Import MCP client or use direct API
        # For now, just save to a local file that can be read
        cache_path = Path(__file__).parent / "discovered_models.json"

        with open(cache_path, "w") as f:
            json.dump(models, f, indent=2)

        return True
    except Exception as e:
        print(f"Failed to store models: {e}")
        return False


def get_cached_models() -> Optional[Dict[str, Any]]:
    """Get previously discovered models from cache."""
    cache_path = Path(__file__).parent / "discovered_models.json"

    if cache_path.exists():
        try:
            with open(cache_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return None


async def run_discovery_pipeline() -> Dict[str, Any]:
    """
    Run the full model discovery pipeline.

    This should be scheduled to run regularly (daily or on model releases).
    """
    print("Starting model discovery pipeline...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Discover models
    results = await discover_all_models()

    print("CLI Version Info:")
    for provider, info in results.get("providers", {}).items():
        version = info.get("version_info", {}).get("cli_version", "unknown")
        print(f"  {provider}: {version}")

    # Store results
    stored = await store_discovered_models(results)
    print(f"\nResults cached: {stored}")

    return results


# Workflow integration points
def create_temporal_workflow_config() -> Dict[str, Any]:
    """
    Generate Temporal workflow configuration for scheduled discovery.
    """
    return {
        "workflow_id": "model-discovery-pipeline",
        "task_queue": "model-discovery",
        "schedule": "0 0 * * *",  # Daily at midnight
        "handler": "run_discovery_pipeline",
        "retry_policy": {
            "maximum_attempts": 3,
            "initial_interval": "1m",
        },
    }


def create_autokitteh_trigger() -> Dict[str, Any]:
    """
    Generate AutoKitteh trigger configuration.
    """
    return {
        "trigger": {
            "type": "schedule",
            "cron": "0 0 * * *",  # Daily
        },
        "action": {
            "type": "python",
            "module": "model_discovery",
            "function": "run_discovery_pipeline",
        },
    }


if __name__ == "__main__":
    print("Model Discovery Pipeline")
    print("=" * 50)

    results = asyncio.run(run_discovery_pipeline())

    print("\nFull Results:")
    print(json.dumps(results, indent=2))
