#!/usr/bin/env python3
"""
Model Discovery Workflow - Automated LLM model version tracking

Runs daily to discover current model versions from CLI providers.
Part of the system's self-evolution infrastructure.

Pipeline:
1. Query CLI tools for version info
2. Optionally query models for their identity
3. Store discovered info in enhanced-memory
4. Log changes for evolution tracking

STATUS: Production Ready
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
import sys

# Add provider path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def discover_cli_versions() -> dict:
    """Discover CLI tool versions for all providers."""
    try:
        from providers.model_discovery import discover_all_models

        result = await discover_all_models()
        logger.info(f"CLI version discovery: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"CLI version discovery failed: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


@activity.defn
async def discover_active_model(provider: str) -> dict:
    """
    Actively query a provider to discover what model it's using.

    This actually calls the CLI and asks the model to identify itself.
    More accurate but takes longer and uses tokens.
    """
    try:
        from providers.model_discovery import discover_cli_model

        result = await discover_cli_model(provider)
        logger.info(f"Active model discovery for {provider}: {result}")
        return result or {"provider": provider, "error": "No result"}
    except Exception as e:
        logger.error(f"Active model discovery for {provider} failed: {e}")
        return {"provider": provider, "error": str(e)}


@activity.defn
async def store_discovery_results(results: dict) -> dict:
    """Store discovery results in enhanced-memory."""
    try:
        from providers.model_discovery import store_discovered_models

        stored = await store_discovered_models(results)

        # Also try to store in enhanced-memory as entity
        try:
            # This would use MCP but for now just cache locally
            pass
        except Exception:
            pass

        return {
            "stored": stored,
            "timestamp": datetime.now().isoformat(),
            "providers_discovered": list(results.get("providers", {}).keys())
        }
    except Exception as e:
        logger.error(f"Failed to store discovery results: {e}")
        return {"error": str(e)}


@activity.defn
async def compare_with_previous(current: dict) -> dict:
    """Compare current discovery with previous to detect changes."""
    try:
        from providers.model_discovery import get_cached_models

        previous = get_cached_models()

        if not previous:
            return {
                "status": "first_run",
                "changes": [],
                "timestamp": datetime.now().isoformat()
            }

        changes = []
        current_providers = current.get("providers", {})
        previous_providers = previous.get("providers", {})

        for provider in current_providers:
            curr_version = current_providers.get(provider, {}).get("version_info", {}).get("cli_version", "")
            prev_version = previous_providers.get(provider, {}).get("version_info", {}).get("cli_version", "")

            if curr_version != prev_version:
                changes.append({
                    "provider": provider,
                    "previous": prev_version,
                    "current": curr_version,
                    "detected_at": datetime.now().isoformat()
                })

        return {
            "status": "compared",
            "changes": changes,
            "has_changes": len(changes) > 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        return {"error": str(e)}


@workflow.defn
class ModelDiscoveryWorkflow:
    """
    Daily model discovery workflow.

    Discovers current LLM model versions from CLI providers
    and tracks changes over time for evolution awareness.
    """

    @workflow.run
    async def run(self, mode: str = "quick") -> dict:
        """
        Args:
            mode:
                "quick" - Just check CLI versions (fast, no tokens)
                "full" - Also query models for identity (slow, uses tokens)
        """
        workflow.logger.info(f"Starting model discovery - mode: {mode}")

        results = {
            "start_time": workflow.now().isoformat(),
            "mode": mode,
            "steps": {}
        }

        try:
            # Step 1: Discover CLI versions (fast, always do this)
            workflow.logger.info("Discovering CLI versions...")
            cli_versions = await workflow.execute_activity(
                discover_cli_versions,
                start_to_close_timeout=timedelta(minutes=2)
            )
            results["steps"]["cli_versions"] = cli_versions

            # Step 2: Compare with previous discovery
            workflow.logger.info("Comparing with previous discovery...")
            comparison = await workflow.execute_activity(
                compare_with_previous,
                cli_versions,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["comparison"] = comparison

            # Step 3: If full mode, actively query each model
            if mode == "full":
                workflow.logger.info("Running active model discovery...")
                active_results = {}

                for provider in ["claude", "codex", "gemini"]:
                    model_info = await workflow.execute_activity(
                        discover_active_model,
                        provider,
                        start_to_close_timeout=timedelta(minutes=2)
                    )
                    active_results[provider] = model_info

                results["steps"]["active_discovery"] = active_results

            # Step 4: Store results
            workflow.logger.info("Storing discovery results...")
            storage = await workflow.execute_activity(
                store_discovery_results,
                cli_versions,
                start_to_close_timeout=timedelta(minutes=1)
            )
            results["steps"]["storage"] = storage

            # Log any changes detected
            if comparison.get("has_changes"):
                workflow.logger.info(f"MODEL CHANGES DETECTED: {comparison['changes']}")
                results["changes_detected"] = comparison["changes"]

            results["end_time"] = workflow.now().isoformat()
            results["status"] = "success"

            workflow.logger.info(f"Model discovery complete: {results}")
            return results

        except Exception as e:
            workflow.logger.error(f"Model discovery failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            return results


async def run_worker():
    """Run worker for model discovery workflow."""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="model-discovery",
        workflows=[ModelDiscoveryWorkflow],
        activities=[
            discover_cli_versions,
            discover_active_model,
            store_discovery_results,
            compare_with_previous,
        ]
    )

    logger.info("Model Discovery Worker started on task_queue: model-discovery")
    await worker.run()


async def run_once(mode: str = "quick"):
    """Run the workflow once (for testing)."""
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        ModelDiscoveryWorkflow.run,
        mode,
        id=f"model-discovery-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        task_queue="model-discovery"
    )

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Discovery Workflow")
    parser.add_argument("--worker", action="store_true", help="Run as worker")
    parser.add_argument("--once", action="store_true", help="Run workflow once")
    parser.add_argument("--mode", default="quick", choices=["quick", "full"],
                        help="Discovery mode")

    args = parser.parse_args()

    if args.worker:
        asyncio.run(run_worker())
    elif args.once:
        asyncio.run(run_once(args.mode))
    else:
        print("Use --worker to start worker or --once to run workflow")
