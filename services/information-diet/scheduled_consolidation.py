#!/usr/bin/env python3
"""
Scheduled Consolidation - Information Diet System
Cron-based memory consolidation: extract patterns, prune low-value content.

Usage:
    python3 scheduled_consolidation.py                # Run once
    python3 scheduled_consolidation.py --daemon       # Run continuously
    python3 scheduled_consolidation.py --full         # Full consolidation
"""
import platform

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    import httpx
except ImportError:
    os.system("pip3 install httpx")
    import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("consolidation")

AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
STATE_FILE = AGENTIC_PATH / "databases" / "consolidation-state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_run": None, "runs": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def sync_pending_memories():
    """Sync any pending memories from fallback files to MCP."""
    pending_files = [
        AGENTIC_PATH / "databases" / "pending_memories.jsonl",
        AGENTIC_PATH / "databases" / "pending_papers.jsonl",
        AGENTIC_PATH / "databases" / "pending_videos.jsonl",
        AGENTIC_PATH / "databases" / "pending_webhook_memories.jsonl"
    ]

    total_synced = 0

    for pending_file in pending_files:
        if not pending_file.exists():
            continue

        synced = 0
        failed = []

        with open(pending_file) as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            "http://localhost:8101/nmf/remember",
                            json={
                                "content": item.get("content", ""),
                                "agent_id": "consolidation-sync",
                                "tags": item.get("tags", []),
                                "metadata": item.get("metadata", {})
                            }
                        )
                        if response.status_code == 200:
                            synced += 1
                        else:
                            failed.append(line)
                except Exception as e:
                    failed.append(line)
                    logger.debug(f"Sync failed: {e}")

        # Rewrite file with only failed items
        if synced > 0:
            if failed:
                with open(pending_file, "w") as f:
                    f.writelines(failed)
            else:
                pending_file.unlink()

        total_synced += synced
        if synced > 0:
            logger.info(f"Synced {synced} items from {pending_file.name}")

    return total_synced


async def run_memory_consolidation(time_window_hours: int = 24):
    """Run memory consolidation via MCP."""
    results = {}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Run full consolidation
            response = await client.post(
                "http://localhost:8101/run_full_consolidation",
                json={"time_window_hours": time_window_hours}
            )
            if response.status_code == 200:
                results["consolidation"] = response.json()
                logger.info(f"Consolidation complete: {results['consolidation']}")
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        results["error"] = str(e)

    return results


async def run_pattern_extraction():
    """Extract patterns from recent memories."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8101/run_pattern_extraction",
                json={"time_window_hours": 24, "min_pattern_frequency": 2}
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Pattern extraction: {result}")
                return result
    except Exception as e:
        logger.debug(f"Pattern extraction failed: {e}")
    return {}


async def run_surprise_consolidation():
    """Run surprise-based consolidation."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8101/run_surprise_consolidation",
                json={"time_window_hours": 24, "min_surprise_threshold": 0.4}
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Surprise consolidation: {result}")
                return result
    except Exception as e:
        logger.debug(f"Surprise consolidation failed: {e}")
    return {}


async def run_memory_curation():
    """Run autonomous memory curation."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8101/autonomous_memory_curation",
                json={}
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Memory curation: {result}")
                return result
    except Exception as e:
        logger.debug(f"Memory curation failed: {e}")
    return {}


async def consolidate(full: bool = False):
    """Run consolidation cycle."""
    state = load_state()
    results = {
        "started_at": datetime.now().isoformat(),
        "synced_pending": 0,
        "consolidation": {},
        "patterns": {},
        "surprise": {},
        "curation": {}
    }

    # Sync pending memories first
    results["synced_pending"] = await sync_pending_memories()

    if full:
        # Full consolidation
        results["consolidation"] = await run_memory_consolidation(48)
        results["patterns"] = await run_pattern_extraction()
        results["surprise"] = await run_surprise_consolidation()
        results["curation"] = await run_memory_curation()
    else:
        # Light consolidation
        results["consolidation"] = await run_memory_consolidation(24)

    results["completed_at"] = datetime.now().isoformat()

    # Update state
    state["runs"].append({
        "timestamp": results["completed_at"],
        "full": full,
        "synced": results["synced_pending"]
    })
    # Keep only last 50 runs
    state["runs"] = state["runs"][-50:]
    save_state(state)

    logger.info(f"Consolidation complete: synced={results['synced_pending']}")
    return results


async def daemon_loop(interval_hours: int = 6, full_interval_hours: int = 24):
    """Run continuously with periodic full consolidation."""
    logger.info(f"Starting consolidation daemon (interval={interval_hours}h, full={full_interval_hours}h)")

    last_full = datetime.now()

    while True:
        try:
            # Check if time for full consolidation
            hours_since_full = (datetime.now() - last_full).total_seconds() / 3600
            full = hours_since_full >= full_interval_hours

            await consolidate(full=full)

            if full:
                last_full = datetime.now()

        except Exception as e:
            logger.error(f"Daemon error: {e}")

        await asyncio.sleep(interval_hours * 3600)


def main():
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    parser = argparse.ArgumentParser(description="Scheduled Consolidation")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--full", action="store_true", help="Run full consolidation")
    parser.add_argument("--interval", type=int, default=6, help="Daemon interval (hours)")
    args = parser.parse_args()

    if args.daemon:
        asyncio.run(daemon_loop(args.interval))
    else:
        results = asyncio.run(consolidate(full=args.full))
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
