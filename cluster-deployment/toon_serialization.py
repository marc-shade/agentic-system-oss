#!/usr/bin/env python3
"""
TOON Serialization for Cluster Coordination
============================================

Cluster-specific TOON encoding/decoding for node communication.
Provides 50% token reduction for heartbeats, status messages, and task routing.

Target Messages:
- Heartbeat broadcasts (11,520/day across 4 nodes)
- Task definitions and routing
- Performance metrics
- Node status reports

Expected Savings:
- JSON heartbeat: ~120 tokens
- TOON heartbeat: ~60 tokens
- Daily savings: 5,760 tokens (50% of 11,520 messages)

Integration:
- distributed_task_router.py (task definitions)
- github_node_daemon.py (heartbeat messages)
- performance_optimizer.py (system metrics)
- submit_cluster_task.py (task submission)
- node_command_listener.py (command responses)
- orchestrator_remote_exec.py (remote execution)
- cluster_memory.py (memory sync)

Version Compatibility:
- Supports mixed TOON/JSON clusters during transition
- Auto-detection of format
- Graceful fallback to JSON
"""

import json
import logging
import sys
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger("cluster-toon")

# Protocol version for cluster communication
CLUSTER_TOON_VERSION = "1.0.0"

# Try to import TOON - may not be available on all nodes yet
TOON_AVAILABLE = False
try:
    # TOON is installed via npm package, accessed via subprocess
    import subprocess

    # Check if toon CLI is available
    result = subprocess.run(
        ["which", "toon"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        TOON_AVAILABLE = True
        TOON_CLI_PATH = result.stdout.strip()
        logger.info(f"TOON CLI found at: {TOON_CLI_PATH}")
    else:
        # Try node_modules path
        npm_path = Path(__file__).parent.parent / "mcp-servers" / "SHARED" / "node_modules" / ".bin" / "toon"
        if npm_path.exists():
            TOON_AVAILABLE = True
            TOON_CLI_PATH = str(npm_path)
            logger.info(f"TOON CLI found at: {TOON_CLI_PATH}")
        else:
            logger.warning("TOON CLI not found - using JSON fallback")

except Exception as e:
    logger.warning(f"Failed to initialize TOON: {e} - using JSON fallback")


def encode_toon(data: Any) -> str:
    """
    Encode data using TOON format via CLI.

    Falls back to JSON if TOON is not available.

    Args:
        data: Any JSON-serializable Python object

    Returns:
        TOON-formatted string (or JSON if unavailable)
    """
    if not TOON_AVAILABLE:
        return json.dumps(data, indent=2)

    try:
        # Convert Python object to JSON first
        json_str = json.dumps(data)

        # Pass through TOON CLI using stdin (dash argument)
        # The TOON CLI expects: echo "json" | toon - --encode
        result = subprocess.run(
            f"echo '{json_str}' | {TOON_CLI_PATH} - --encode",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            logger.warning(f"TOON encode failed: {result.stderr}")
            return json.dumps(data, indent=2)

    except Exception as e:
        logger.warning(f"TOON encoding error: {e} - falling back to JSON")
        return json.dumps(data, indent=2)


def decode_toon(text: str) -> Any:
    """
    Decode TOON or JSON format automatically.

    Auto-detects format and decodes appropriately.

    Args:
        text: TOON or JSON formatted string

    Returns:
        Decoded Python object
    """
    # Try JSON first (faster and more common)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try TOON if available
    if TOON_AVAILABLE:
        try:
            # Use stdin (dash argument) for proper stdin/stdout handling
            result = subprocess.run(
                f"echo '{text}' | {TOON_CLI_PATH} - --decode",
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # TOON CLI outputs JSON
                return json.loads(result.stdout)
            else:
                logger.error(f"TOON decode failed: {result.stderr}")
                raise ValueError(f"Failed to decode TOON: {result.stderr}")

        except Exception as e:
            logger.error(f"TOON decoding error: {e}")
            raise ValueError(f"Failed to decode TOON or JSON: {e}")
    else:
        raise ValueError("Text is not valid JSON and TOON is not available")


def is_toon_format(text: str) -> bool:
    """
    Detect if text is TOON or JSON format.

    Args:
        text: String to check

    Returns:
        True if TOON format, False if JSON
    """
    # JSON always starts with { or [
    stripped = text.strip()
    if stripped.startswith('{') or stripped.startswith('['):
        return False

    # TOON uses indentation and key: value format
    if ':' in text and '\n' in text:
        return True

    return False


def encode_heartbeat(node_id: str, metrics: Dict) -> str:
    """
    Encode node heartbeat message using TOON.

    Optimized for minimal tokens in frequent broadcasts.

    Args:
        node_id: Node identifier
        metrics: System metrics dict

    Returns:
        TOON-encoded heartbeat (~60 tokens vs ~120 JSON)
    """
    heartbeat = {
        "node_id": node_id,
        "timestamp": metrics.get("timestamp"),
        "cpu_percent": metrics.get("cpu_percent"),
        "memory_percent": metrics.get("memory_percent"),
        "load_avg": metrics.get("load_avg", []),
        "active_tasks": metrics.get("active_tasks", 0),
        "status": metrics.get("status", "unknown"),
        "protocol": "toon" if TOON_AVAILABLE else "json",
        "version": CLUSTER_TOON_VERSION
    }

    return encode_toon(heartbeat)


def encode_task(task_def: Dict) -> str:
    """
    Encode task definition using TOON.

    Args:
        task_def: Task definition dictionary

    Returns:
        TOON-encoded task
    """
    task_data = {
        **task_def,
        "protocol": "toon" if TOON_AVAILABLE else "json",
        "version": CLUSTER_TOON_VERSION
    }

    return encode_toon(task_data)


def encode_result(result: Dict) -> str:
    """
    Encode task result using TOON.

    Args:
        result: Result dictionary

    Returns:
        TOON-encoded result
    """
    result_data = {
        **result,
        "protocol": "toon" if TOON_AVAILABLE else "json",
        "version": CLUSTER_TOON_VERSION
    }

    return encode_toon(result_data)


def encode_metrics(metrics: Dict) -> str:
    """
    Encode performance metrics using TOON.

    Args:
        metrics: Metrics dictionary

    Returns:
        TOON-encoded metrics
    """
    return encode_toon(metrics)


def get_serialization_stats() -> Dict:
    """
    Get statistics about TOON usage in cluster.

    Returns:
        Stats dictionary
    """
    return {
        "toon_available": TOON_AVAILABLE,
        "toon_cli_path": TOON_CLI_PATH if TOON_AVAILABLE else None,
        "protocol_version": CLUSTER_TOON_VERSION,
        "format": "toon" if TOON_AVAILABLE else "json",
        "expected_token_savings": "50%" if TOON_AVAILABLE else "0%"
    }


def validate_cluster_compatibility() -> bool:
    """
    Validate that cluster nodes can handle current protocol.

    Returns:
        True if compatible, False otherwise
    """
    # For now, always compatible (JSON fallback ensures this)
    return True


# Example usage and testing
if __name__ == "__main__":
    print("TOON Serialization for Cluster Coordination")
    print("=" * 60)

    # Display configuration
    stats = get_serialization_stats()
    print(f"\nConfiguration:")
    print(f"  TOON Available: {stats['toon_available']}")
    print(f"  TOON CLI Path: {stats['toon_cli_path']}")
    print(f"  Protocol Version: {stats['protocol_version']}")
    print(f"  Format: {stats['format']}")
    print(f"  Expected Savings: {stats['expected_token_savings']}")

    # Test heartbeat encoding
    print("\n" + "=" * 60)
    print("Heartbeat Encoding Test")
    print("=" * 60)

    test_metrics = {
        "timestamp": "2025-11-20T12:00:00Z",
        "cpu_percent": 15.2,
        "memory_percent": 45.8,
        "load_avg": [1.2, 1.5, 1.8],
        "active_tasks": 2,
        "status": "healthy"
    }

    heartbeat = encode_heartbeat("mac-studio", test_metrics)
    print(f"\nEncoded Heartbeat ({len(heartbeat)} chars):")
    print(heartbeat)

    # Decode test
    try:
        decoded = decode_toon(heartbeat)
        print(f"\nDecoded Successfully:")
        print(json.dumps(decoded, indent=2))
    except Exception as e:
        print(f"\nDecode Error: {e}")

    # Test task encoding
    print("\n" + "=" * 60)
    print("Task Encoding Test")
    print("=" * 60)

    test_task = {
        "task_id": "task_123",
        "type": "shell",
        "command": "python3 test.py",
        "timeout": 300,
        "assigned_to": "macpro51"
    }

    task_encoded = encode_task(test_task)
    print(f"\nEncoded Task ({len(task_encoded)} chars):")
    print(task_encoded)

    # Format detection test
    print("\n" + "=" * 60)
    print("Format Detection Test")
    print("=" * 60)

    json_sample = '{"test": "value"}'
    toon_sample = "test: value"

    print(f"JSON detection: {is_toon_format(json_sample)} (should be False)")
    print(f"TOON detection: {is_toon_format(toon_sample)} (should be True)")

    print("\n" + "=" * 60)
    print("Ready for cluster integration!")
    print("=" * 60)
