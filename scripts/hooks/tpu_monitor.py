#!/usr/bin/env python3
"""
TPU Monitor - Track and report Coral Edge TPU usage across the agentic system.

Integrates with:
- XRG status bar display
- Claude Code hooks
- Enhanced Memory consolidation
- Security scanner
- Voice mode

Usage:
    from tpu_monitor import get_tpu_stats, record_tpu_usage, get_usage_summary

    # Get current stats
    stats = get_tpu_stats()

    # Record a TPU usage event
    record_tpu_usage("importance_scoring", latency_ms=45.2, model="mobilenet_v2")

    # Get usage summary
    summary = get_usage_summary(hours=24)
"""
import platform

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import sqlite3

logger = logging.getLogger("tpu_monitor")

# Stats file location (shared with XRG display)
TPU_STATS_FILE = Path("/tmp/xrg-coral-tpu-stats.json")
TPU_USAGE_DB = Path(os.path.join(
    os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)),
    "databases/tpu_usage.db"
))

# Ensure parent directory exists
TPU_USAGE_DB.parent.mkdir(parents=True, exist_ok=True)


def _ensure_db():
    """Ensure usage database exists with proper schema."""
    conn = sqlite3.connect(str(TPU_USAGE_DB))
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tpu_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            operation TEXT NOT NULL,
            model TEXT,
            latency_ms REAL,
            success INTEGER DEFAULT 1,
            source TEXT,
            metadata TEXT
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON tpu_usage(timestamp)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_usage_operation ON tpu_usage(operation)
    ''')
    conn.commit()
    conn.close()


def get_tpu_stats() -> Dict[str, Any]:
    """
    Get current TPU statistics from the MCP server stats file.

    Returns:
        Dict with TPU stats or empty dict if unavailable
    """
    try:
        if TPU_STATS_FILE.exists():
            with open(TPU_STATS_FILE) as f:
                return json.load(f)
    except Exception as e:
        logger.debug(f"Could not read TPU stats: {e}")

    return {
        "total_inferences": 0,
        "tpu_available": False,
        "loaded_models": [],
        "by_model": {}
    }


def _sync_xrg_stats() -> None:
    """
    Sync current usage stats to XRG stats file.

    This ensures XRG displays comprehensive TPU usage from all sources,
    not just direct coral-tpu-mcp calls.
    """
    try:
        _ensure_db()
        conn = sqlite3.connect(str(TPU_USAGE_DB))
        cursor = conn.cursor()

        # Get aggregated stats from the last hour for XRG display
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        # Total inferences and latency
        cursor.execute('''
            SELECT COUNT(*), SUM(latency_ms), AVG(latency_ms)
            FROM tpu_usage WHERE timestamp > ?
        ''', (hour_ago,))
        total, total_latency, avg_latency = cursor.fetchone()

        # Get by-model breakdown
        cursor.execute('''
            SELECT model, COUNT(*), SUM(latency_ms), AVG(latency_ms)
            FROM tpu_usage WHERE timestamp > ? AND model IS NOT NULL
            GROUP BY model
        ''', (hour_ago,))
        by_model = {}
        for row in cursor.fetchall():
            by_model[row[0] or "unknown"] = {
                "inferences": row[1],
                "total_latency_ms": row[2] or 0,
                "avg_latency_ms": round(row[3], 2) if row[3] else 0
            }

        # Get loaded models (from last 5 minutes as proxy for "active")
        five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
        cursor.execute('''
            SELECT DISTINCT model FROM tpu_usage
            WHERE timestamp > ? AND model IS NOT NULL
        ''', (five_min_ago,))
        loaded_models = [row[0] for row in cursor.fetchall() if row[0]]

        # Get by-source breakdown for XRG multi-color display
        cursor.execute('''
            SELECT source, COUNT(*), SUM(latency_ms), AVG(latency_ms)
            FROM tpu_usage WHERE timestamp > ?
            GROUP BY source
        ''', (hour_ago,))
        by_source = {}
        for row in cursor.fetchall():
            source_name = row[0] or "unknown"
            # Categorize sources for color coding
            if source_name in ["coral-tpu-mcp", "direct"]:
                category = "direct"
            elif source_name in ["action_pattern_matcher", "agent_router", "metacognitive_classifier", "session_classifier", "causal_recognizer", "knowledge_scorer"]:
                category = "hooked"
            else:
                category = "logged"

            by_source[source_name] = {
                "count": row[1],
                "total_latency_ms": row[2] or 0,
                "avg_latency_ms": round(row[3], 2) if row[3] else 0,
                "category": category
            }

        # Aggregate by category for XRG color streams
        by_category = {"direct": 0, "hooked": 0, "logged": 0}
        for source_info in by_source.values():
            cat = source_info.get("category", "logged")
            by_category[cat] += source_info["count"]

        conn.close()

        # Build XRG-compatible stats structure with multi-stream support
        xrg_stats = {
            "total_inferences": total or 0,
            "total_latency_ms": total_latency or 0,
            "avg_latency_ms": round(avg_latency, 2) if avg_latency else 0,
            "by_model": by_model,
            "by_source": by_source,
            "by_category": by_category,  # For XRG color coding
            "tpu_available": True,  # We're recording, so TPU is available
            "loaded_models": loaded_models,
            "timestamp": time.time()
        }

        # Write to XRG stats file
        with open(TPU_STATS_FILE, 'w') as f:
            json.dump(xrg_stats, f)

    except Exception as e:
        logger.debug(f"Failed to sync XRG stats: {e}")


def record_tpu_usage(
    operation: str,
    latency_ms: float = 0.0,
    model: Optional[str] = None,
    success: bool = True,
    source: str = "unknown",
    metadata: Optional[Dict] = None
) -> bool:
    """
    Record a TPU usage event for monitoring.

    Args:
        operation: Type of operation (importance_scoring, image_classify, etc.)
        latency_ms: Inference latency in milliseconds
        model: Model used (mobilenet_v2, efficientnet_s, etc.)
        success: Whether the operation succeeded
        source: Source component (enhanced-memory, voice-mode, etc.)
        metadata: Additional metadata

    Returns:
        True if recorded successfully
    """
    try:
        _ensure_db()
        conn = sqlite3.connect(str(TPU_USAGE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO tpu_usage (timestamp, operation, model, latency_ms, success, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            operation,
            model,
            latency_ms,
            1 if success else 0,
            source,
            json.dumps(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        # Sync to XRG stats file for display
        _sync_xrg_stats()

        return True
    except Exception as e:
        logger.error(f"Failed to record TPU usage: {e}")
        return False


def get_usage_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get TPU usage summary for the specified time period.

    Args:
        hours: Lookback period in hours

    Returns:
        Dict with usage statistics
    """
    try:
        _ensure_db()
        conn = sqlite3.connect(str(TPU_USAGE_DB))
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        # Total inferences
        cursor.execute('''
            SELECT COUNT(*), AVG(latency_ms), SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END)
            FROM tpu_usage WHERE timestamp > ?
        ''', (cutoff,))
        total, avg_latency, successes = cursor.fetchone()

        # By operation
        cursor.execute('''
            SELECT operation, COUNT(*), AVG(latency_ms)
            FROM tpu_usage WHERE timestamp > ?
            GROUP BY operation
        ''', (cutoff,))
        by_operation = {row[0]: {"count": row[1], "avg_latency_ms": row[2]} for row in cursor.fetchall()}

        # By model
        cursor.execute('''
            SELECT model, COUNT(*), AVG(latency_ms)
            FROM tpu_usage WHERE timestamp > ? AND model IS NOT NULL
            GROUP BY model
        ''', (cutoff,))
        by_model = {row[0]: {"count": row[1], "avg_latency_ms": row[2]} for row in cursor.fetchall()}

        # By source
        cursor.execute('''
            SELECT source, COUNT(*)
            FROM tpu_usage WHERE timestamp > ?
            GROUP BY source
        ''', (cutoff,))
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        return {
            "period_hours": hours,
            "total_inferences": total or 0,
            "avg_latency_ms": round(avg_latency, 2) if avg_latency else 0,
            "success_rate": round((successes or 0) / max(total or 1, 1), 3),
            "by_operation": by_operation,
            "by_model": by_model,
            "by_source": by_source,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        return {"error": str(e)}


def get_recent_usage(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent TPU usage events.

    Args:
        limit: Maximum events to return

    Returns:
        List of recent usage events
    """
    try:
        _ensure_db()
        conn = sqlite3.connect(str(TPU_USAGE_DB))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT timestamp, operation, model, latency_ms, success, source, metadata
            FROM tpu_usage
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        events = []
        for row in cursor.fetchall():
            events.append({
                "timestamp": row[0],
                "operation": row[1],
                "model": row[2],
                "latency_ms": row[3],
                "success": bool(row[4]),
                "source": row[5],
                "metadata": json.loads(row[6]) if row[6] else None
            })

        conn.close()
        return events
    except Exception as e:
        logger.error(f"Failed to get recent usage: {e}")
        return []


def get_health_status() -> Dict[str, Any]:
    """
    Get TPU health status combining live stats and historical usage.

    Returns:
        Dict with health status and recommendations
    """
    live_stats = get_tpu_stats()
    usage_summary = get_usage_summary(hours=1)

    health = {
        "tpu_available": live_stats.get("tpu_available", False),
        "loaded_models": live_stats.get("loaded_models", []),
        "total_session_inferences": live_stats.get("total_inferences", 0),
        "last_hour_inferences": usage_summary.get("total_inferences", 0),
        "avg_latency_ms": usage_summary.get("avg_latency_ms", 0),
        "success_rate": usage_summary.get("success_rate", 1.0),
        "status": "healthy",
        "recommendations": []
    }

    # Health checks
    if not health["tpu_available"]:
        health["status"] = "unavailable"
        health["recommendations"].append("Check TPU USB connection")
    elif health["last_hour_inferences"] == 0:
        health["status"] = "idle"
        health["recommendations"].append("TPU is underutilized - consider enabling more integrations")
    elif health["success_rate"] < 0.9:
        health["status"] = "degraded"
        health["recommendations"].append("High failure rate detected - check model compatibility")
    elif health["avg_latency_ms"] > 100:
        health["status"] = "slow"
        health["recommendations"].append("Higher than expected latency - check for resource contention")

    return health


# CLI interface
if __name__ == "__main__":
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


    parser = argparse.ArgumentParser(description="TPU Monitor CLI")
    parser.add_argument("command", choices=["stats", "summary", "recent", "health"],
                       help="Command to run")
    parser.add_argument("--hours", type=int, default=24, help="Lookback period for summary")
    parser.add_argument("--limit", type=int, default=10, help="Limit for recent events")

    args = parser.parse_args()

    if args.command == "stats":
        print(json.dumps(get_tpu_stats(), indent=2))
    elif args.command == "summary":
        print(json.dumps(get_usage_summary(args.hours), indent=2))
    elif args.command == "recent":
        print(json.dumps(get_recent_usage(args.limit), indent=2))
    elif args.command == "health":
        print(json.dumps(get_health_status(), indent=2))
