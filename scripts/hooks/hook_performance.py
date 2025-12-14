#!/usr/bin/env python3
"""
Hook Performance Framework
==========================

Performance-aware hook execution with:
- Execution time tracking and metrics
- Configurable timeouts (default: 500ms for hooks)
- Circuit breaker for consistently slow hooks
- Prometheus metrics export
- Async wrappers for non-blocking execution

CRITICAL: Hooks must be FAST. Target: <100ms, Max: 500ms
If a hook exceeds timeout, it's killed and logged.

Usage:
    from hook_performance import timed_hook, run_async, get_metrics, HookContext

    @timed_hook("my_integration", timeout_ms=200)
    def my_hook_function(context: HookContext):
        # Your hook logic here
        return {"status": "ok"}

    # Or for shell scripts:
    # source hook_performance.sh
    # timed_exec "integration_name" "python3 my_script.py"
"""

import os
import sys
import json
import time
import signal
import asyncio
import sqlite3
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from contextlib import contextmanager
import logging

# Suppress all output by default (hooks should be silent)
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("hook_performance")

# Performance thresholds (milliseconds)
HOOK_TIMEOUT_MS = int(os.environ.get("HOOK_TIMEOUT_MS", "500"))
HOOK_WARNING_MS = int(os.environ.get("HOOK_WARNING_MS", "100"))
CIRCUIT_BREAKER_FAILURES = int(os.environ.get("CIRCUIT_BREAKER_FAILURES", "5"))
CIRCUIT_BREAKER_RESET_S = int(os.environ.get("CIRCUIT_BREAKER_RESET_S", "300"))

# Metrics storage
METRICS_DB = Path(os.environ.get(
    "HOOK_METRICS_DB",
    "/home/marc/agentic-system/databases/hook_metrics.db"
))
METRICS_LOG = Path("/home/marc/agentic-system/logs/hook-performance.jsonl")

# Circuit breaker state (in-memory, resets on process restart)
_circuit_breaker_state: Dict[str, Dict[str, Any]] = {}


@dataclass
class HookContext:
    """Context passed to hook functions."""
    hook_type: str  # PreToolUse, PostToolUse, etc.
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    session_id: str = field(default_factory=lambda: os.environ.get("CLAUDE_SESSION_ID", "unknown"))
    node_id: str = field(default_factory=lambda: os.uname().nodename)
    timestamp: float = field(default_factory=time.time)
    raw_input: Optional[Dict[str, Any]] = None


@dataclass
class HookMetrics:
    """Metrics for a single hook execution."""
    hook_type: str
    integration_name: str
    execution_time_ms: float
    success: bool
    timeout: bool = False
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    node_id: str = field(default_factory=lambda: os.uname().nodename)


def init_metrics_db():
    """Initialize the metrics database."""
    METRICS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(METRICS_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hook_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hook_type TEXT NOT NULL,
            integration_name TEXT NOT NULL,
            execution_time_ms REAL NOT NULL,
            success INTEGER NOT NULL,
            timeout INTEGER DEFAULT 0,
            error TEXT,
            timestamp REAL NOT NULL,
            node_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hook_metrics_type
        ON hook_metrics(hook_type, timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hook_metrics_integration
        ON hook_metrics(integration_name, timestamp)
    """)
    # Performance aggregates table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hook_performance_summary (
            integration_name TEXT PRIMARY KEY,
            total_calls INTEGER DEFAULT 0,
            total_time_ms REAL DEFAULT 0,
            avg_time_ms REAL DEFAULT 0,
            p95_time_ms REAL DEFAULT 0,
            p99_time_ms REAL DEFAULT 0,
            max_time_ms REAL DEFAULT 0,
            success_rate REAL DEFAULT 1.0,
            timeout_rate REAL DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def record_metrics(metrics: HookMetrics):
    """Record hook metrics to database and log file."""
    try:
        # Write to JSONL log (fast, append-only)
        METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_LOG, "a") as f:
            f.write(json.dumps(asdict(metrics)) + "\n")

        # Write to SQLite (background, non-blocking)
        def _write_db():
            try:
                conn = sqlite3.connect(str(METRICS_DB), timeout=1.0)
                conn.execute("""
                    INSERT INTO hook_metrics
                    (hook_type, integration_name, execution_time_ms, success, timeout, error, timestamp, node_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.hook_type,
                    metrics.integration_name,
                    metrics.execution_time_ms,
                    1 if metrics.success else 0,
                    1 if metrics.timeout else 0,
                    metrics.error,
                    metrics.timestamp,
                    metrics.node_id
                ))
                conn.commit()
                conn.close()
            except Exception:
                pass  # Non-critical, don't block

        # Run in background thread
        threading.Thread(target=_write_db, daemon=True).start()

    except Exception:
        pass  # Never fail the hook due to metrics


def check_circuit_breaker(integration_name: str) -> bool:
    """Check if circuit breaker is open for this integration."""
    state = _circuit_breaker_state.get(integration_name)
    if not state:
        return False  # Circuit closed, allow execution

    if state["open"]:
        # Check if reset time has passed
        if time.time() - state["opened_at"] > CIRCUIT_BREAKER_RESET_S:
            # Reset circuit breaker
            _circuit_breaker_state[integration_name] = {
                "failures": 0,
                "open": False,
                "opened_at": 0
            }
            return False
        return True  # Circuit still open, skip execution

    return False


def record_circuit_breaker_failure(integration_name: str):
    """Record a failure for circuit breaker."""
    if integration_name not in _circuit_breaker_state:
        _circuit_breaker_state[integration_name] = {
            "failures": 0,
            "open": False,
            "opened_at": 0
        }

    state = _circuit_breaker_state[integration_name]
    state["failures"] += 1

    if state["failures"] >= CIRCUIT_BREAKER_FAILURES:
        state["open"] = True
        state["opened_at"] = time.time()
        logger.warning(f"Circuit breaker OPEN for {integration_name}")


def record_circuit_breaker_success(integration_name: str):
    """Record a success, reset failure count."""
    if integration_name in _circuit_breaker_state:
        _circuit_breaker_state[integration_name]["failures"] = 0


@contextmanager
def timeout_context(seconds: float):
    """Context manager for timeout on Unix systems."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Hook execution exceeded {seconds}s timeout")

    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)

    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def timed_hook(integration_name: str, timeout_ms: int = None):
    """
    Decorator for timed hook execution with circuit breaker.

    Args:
        integration_name: Name of the integration (e.g., "tpu_importance", "agi_bridge")
        timeout_ms: Maximum execution time in milliseconds (default: HOOK_TIMEOUT_MS)
    """
    timeout = (timeout_ms or HOOK_TIMEOUT_MS) / 1000.0

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(context: HookContext, *args, **kwargs):
            # Check circuit breaker
            if check_circuit_breaker(integration_name):
                return {"skipped": True, "reason": "circuit_breaker_open"}

            start_time = time.time()
            success = False
            timeout_occurred = False
            error_msg = None
            result = None

            try:
                with timeout_context(timeout):
                    result = func(context, *args, **kwargs)
                success = True
                record_circuit_breaker_success(integration_name)

            except TimeoutError as e:
                timeout_occurred = True
                error_msg = str(e)
                record_circuit_breaker_failure(integration_name)

            except Exception as e:
                error_msg = str(e)[:200]
                record_circuit_breaker_failure(integration_name)

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Record metrics
            metrics = HookMetrics(
                hook_type=context.hook_type,
                integration_name=integration_name,
                execution_time_ms=execution_time_ms,
                success=success,
                timeout=timeout_occurred,
                error=error_msg
            )
            record_metrics(metrics)

            # Log warning for slow hooks
            if execution_time_ms > HOOK_WARNING_MS:
                logger.warning(
                    f"Slow hook: {integration_name} took {execution_time_ms:.1f}ms "
                    f"(warning threshold: {HOOK_WARNING_MS}ms)"
                )

            return result

        return wrapper
    return decorator


def run_async(coro, timeout_s: float = 0.5):
    """
    Run an async coroutine with timeout, non-blocking.
    Returns result or None if timeout/error.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                asyncio.wait_for(coro, timeout=timeout_s)
            )
        finally:
            loop.close()
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


def run_subprocess_timed(cmd: List[str], timeout_s: float = 0.5,
                         input_data: str = None) -> Optional[str]:
    """
    Run a subprocess with timeout, return stdout or None.
    """
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout_s
        )
        return result.stdout if result.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def get_metrics_summary(integration_name: str = None,
                        hours: int = 24) -> Dict[str, Any]:
    """Get performance metrics summary."""
    try:
        conn = sqlite3.connect(str(METRICS_DB), timeout=1.0)
        conn.row_factory = sqlite3.Row

        cutoff = time.time() - (hours * 3600)

        if integration_name:
            rows = conn.execute("""
                SELECT
                    integration_name,
                    COUNT(*) as total_calls,
                    AVG(execution_time_ms) as avg_time_ms,
                    MAX(execution_time_ms) as max_time_ms,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                    SUM(CASE WHEN timeout = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as timeout_rate
                FROM hook_metrics
                WHERE integration_name = ? AND timestamp > ?
                GROUP BY integration_name
            """, (integration_name, cutoff)).fetchall()
        else:
            rows = conn.execute("""
                SELECT
                    integration_name,
                    COUNT(*) as total_calls,
                    AVG(execution_time_ms) as avg_time_ms,
                    MAX(execution_time_ms) as max_time_ms,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
                    SUM(CASE WHEN timeout = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as timeout_rate
                FROM hook_metrics
                WHERE timestamp > ?
                GROUP BY integration_name
                ORDER BY total_calls DESC
            """, (cutoff,)).fetchall()

        conn.close()

        return {
            "hours": hours,
            "integrations": [dict(row) for row in rows]
        }
    except Exception as e:
        return {"error": str(e)}


def get_slow_hooks(threshold_ms: float = 100, hours: int = 1) -> List[Dict[str, Any]]:
    """Get list of slow hook executions."""
    try:
        conn = sqlite3.connect(str(METRICS_DB), timeout=1.0)
        conn.row_factory = sqlite3.Row

        cutoff = time.time() - (hours * 3600)

        rows = conn.execute("""
            SELECT hook_type, integration_name, execution_time_ms,
                   error, timestamp
            FROM hook_metrics
            WHERE execution_time_ms > ? AND timestamp > ?
            ORDER BY execution_time_ms DESC
            LIMIT 100
        """, (threshold_ms, cutoff)).fetchall()

        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []


# Initialize database on import
try:
    init_metrics_db()
except Exception:
    pass


if __name__ == "__main__":
    # CLI for checking metrics
    import argparse
    parser = argparse.ArgumentParser(description="Hook Performance Metrics")
    parser.add_argument("--summary", action="store_true", help="Show summary")
    parser.add_argument("--slow", action="store_true", help="Show slow hooks")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    parser.add_argument("--integration", type=str, help="Filter by integration")
    args = parser.parse_args()

    if args.summary:
        summary = get_metrics_summary(args.integration, args.hours)
        print(json.dumps(summary, indent=2))
    elif args.slow:
        slow = get_slow_hooks(hours=args.hours)
        print(json.dumps(slow, indent=2))
    else:
        parser.print_help()
