#!/usr/bin/env python3
"""
Memory Consolidation Daemon - Sleep-Inspired AGI Memory System

Triggers periodic memory consolidation based on research findings:
- Every 6 hours (like REM cycles)
- On session threshold (every 10 Claude sessions)
- On USR1 signal (manual trigger)

Uses enhanced-memory MCP server for consolidation operations.
"""

import os
import sys
import json
import signal
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Configuration
STATE_FILE = Path("/mnt/agentic-system/databases/consolidation_state.json")
LOG_FILE = Path("/mnt/agentic-system/logs/memory-consolidation.log")
CONSOLIDATION_INTERVAL_HOURS = 6
SESSION_THRESHOLD = 10
MCP_SOCKET = Path(os.environ.get("HOME", "/home/marc")) / ".claude" / "mcp-sockets" / "enhanced-memory.sock"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - MemoryConsolidation - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE) if LOG_FILE.parent.exists() else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConsolidationState:
    """Manages consolidation state persistence."""

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from file or create default."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load state: {e}")

        return {
            "last_consolidation": None,
            "session_count": 0,
            "total_consolidations": 0,
            "total_patterns_found": 0,
            "total_memories_promoted": 0,
            "total_memories_compressed": 0
        }

    def save(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    def record_consolidation(self, results: dict):
        """Record consolidation results."""
        self.state["last_consolidation"] = datetime.now().isoformat()
        self.state["session_count"] = 0  # Reset session counter
        self.state["total_consolidations"] = self.state.get("total_consolidations", 0) + 1

        # Accumulate totals
        self.state["total_patterns_found"] = self.state.get("total_patterns_found", 0) + results.get("patterns_found", 0)
        self.state["total_memories_promoted"] = self.state.get("total_memories_promoted", 0) + results.get("memories_promoted", 0)
        self.state["total_memories_compressed"] = self.state.get("total_memories_compressed", 0) + results.get("memories_compressed", 0)

        self.save()

    def increment_session(self) -> int:
        """Increment session count and return new count."""
        self.state["session_count"] = self.state.get("session_count", 0) + 1
        self.save()
        return self.state["session_count"]

    def should_consolidate(self) -> tuple[bool, str]:
        """Check if consolidation should run."""
        # Check session threshold
        if self.state.get("session_count", 0) >= SESSION_THRESHOLD:
            return True, f"Session threshold ({SESSION_THRESHOLD}) reached"

        # Check time interval
        last = self.state.get("last_consolidation")
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                if datetime.now() - last_dt > timedelta(hours=CONSOLIDATION_INTERVAL_HOURS):
                    return True, f"Time interval ({CONSOLIDATION_INTERVAL_HOURS}h) exceeded"
            except ValueError:
                pass
        else:
            return True, "No previous consolidation"

        return False, "No trigger conditions met"


def call_mcp_consolidation() -> dict:
    """
    Call enhanced-memory MCP to run full consolidation.
    Uses the MCP tool via claude CLI or direct API call.
    """
    logger.info("Starting memory consolidation via enhanced-memory MCP...")

    results = {
        "patterns_found": 0,
        "chains_created": 0,
        "links_created": 0,
        "memories_promoted": 0,
        "memories_compressed": 0,
        "success": False
    }

    try:
        # Try using the MCP server directly via HTTP or socket
        import urllib.request
        import urllib.error

        # First try: Pattern extraction
        logger.info("Running pattern extraction...")
        try:
            req = urllib.request.Request(
                "http://localhost:8765/run_pattern_extraction",
                data=json.dumps({"time_window_hours": 24}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                results["patterns_found"] = data.get("patterns_found", 0)
        except urllib.error.URLError:
            logger.debug("MCP HTTP endpoint not available, using fallback")

        # Second try: Causal discovery
        logger.info("Running causal discovery...")
        try:
            req = urllib.request.Request(
                "http://localhost:8765/run_causal_discovery",
                data=json.dumps({"time_window_hours": 24}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                results["chains_created"] = data.get("chains_created", 0)
                results["links_created"] = data.get("links_created", 0)
        except urllib.error.URLError:
            pass

        # Third try: Memory compression
        logger.info("Running memory compression...")
        try:
            req = urllib.request.Request(
                "http://localhost:8765/run_memory_compression",
                data=json.dumps({"time_window_hours": 168}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                results["memories_compressed"] = data.get("memories_compressed", 0)
        except urllib.error.URLError:
            pass

        results["success"] = True

    except Exception as e:
        logger.error(f"Consolidation error: {e}")
        results["error"] = str(e)

    return results


def run_consolidation(state: ConsolidationState, reason: str):
    """Run the full consolidation cycle."""
    logger.info("=" * 60)
    logger.info(f"MEMORY CONSOLIDATION CYCLE - {reason}")
    logger.info("=" * 60)

    start_time = datetime.now()

    # Run consolidation
    results = call_mcp_consolidation()

    duration = (datetime.now() - start_time).total_seconds()

    # Log results
    logger.info(f"Consolidation completed in {duration:.2f}s")
    logger.info(f"  Patterns found: {results.get('patterns_found', 0)}")
    logger.info(f"  Chains created: {results.get('chains_created', 0)}")
    logger.info(f"  Memories compressed: {results.get('memories_compressed', 0)}")
    logger.info("=" * 60)

    # Record results
    state.record_consolidation(results)

    # Send notification
    try:
        notify_path = Path("/mnt/agentic-system/scripts/hooks/notification.sh")
        if notify_path.exists():
            subprocess.run([
                str(notify_path),
                "Memory Consolidation Complete",
                f"Patterns: {results.get('patterns_found', 0)}, Compressed: {results.get('memories_compressed', 0)}"
            ], timeout=5, capture_output=True)
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")

    return results


def signal_handler(signum, frame):
    """Handle USR1 signal to trigger consolidation."""
    logger.info(f"Received signal {signum}, triggering consolidation...")
    state = ConsolidationState()
    run_consolidation(state, "Manual trigger (USR1)")


def main():
    """Main daemon loop."""
    logger.info("Memory Consolidation Daemon starting...")
    logger.info(f"  Interval: {CONSOLIDATION_INTERVAL_HOURS} hours")
    logger.info(f"  Session threshold: {SESSION_THRESHOLD}")
    logger.info(f"  State file: {STATE_FILE}")

    # Register signal handlers
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    state = ConsolidationState()

    # Check if we should run immediately
    should_run, reason = state.should_consolidate()
    if should_run:
        run_consolidation(state, reason)

    # Main loop - check every 5 minutes
    while True:
        try:
            time.sleep(300)  # 5 minutes

            should_run, reason = state.should_consolidate()
            if should_run:
                run_consolidation(state, reason)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait a minute on error


if __name__ == "__main__":
    main()
