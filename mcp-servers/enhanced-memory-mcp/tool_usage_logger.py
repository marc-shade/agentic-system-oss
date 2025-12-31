#!/usr/bin/env python3
"""
Tool Usage Logger for Enhanced Memory MCP

Tracks tool invocations to enable data-driven refinement of ORCHESTRATOR_MODULES.
Logs to JSONL for easy analysis and aggregation.

Usage:
    from tool_usage_logger import ToolUsageLogger, log_tool_call

    # Initialize (done once at server startup)
    logger = ToolUsageLogger.get_instance()

    # Log a tool invocation (in tool decorator or handler)
    log_tool_call("nmf_remember", "nmf_tools", success=True, duration_ms=45)

    # Get usage summary
    summary = logger.get_usage_summary()
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from functools import wraps
import threading
import logging

logger = logging.getLogger(__name__)

# Log file location
LOG_DIR = Path(os.environ.get(
    "TOOL_USAGE_LOG_DIR",
    str(Path.home() / ".claude" / "tool_usage_logs")
))


class ToolUsageLogger:
    """Singleton logger for tool usage tracking."""

    _instance: Optional['ToolUsageLogger'] = None
    _lock = threading.Lock()

    def __init__(self):
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.memory_profile = os.getenv("MEMORY_PROFILE", "full")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"usage_{self.session_id}.jsonl"
        self._write_lock = threading.Lock()

        # In-memory stats for fast access
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "call_count": 0,
            "success_count": 0,
            "total_duration_ms": 0,
            "module": None,
            "first_call": None,
            "last_call": None
        })

        # Log session start
        self._write_entry({
            "event": "session_start",
            "memory_profile": self.memory_profile,
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat()
        })
        logger.info(f"Tool usage logging enabled: {self.log_file}")

    @classmethod
    def get_instance(cls) -> 'ToolUsageLogger':
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Thread-safe write to log file."""
        with self._write_lock:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.warning(f"Failed to write tool usage log: {e}")

    def log_call(
        self,
        tool_name: str,
        module: str,
        success: bool = True,
        duration_ms: float = 0,
        params: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a tool invocation."""
        timestamp = datetime.now().isoformat()

        # Update in-memory stats
        stats = self._stats[tool_name]
        stats["call_count"] += 1
        if success:
            stats["success_count"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["module"] = module
        if stats["first_call"] is None:
            stats["first_call"] = timestamp
        stats["last_call"] = timestamp

        # Write to log file
        entry = {
            "event": "tool_call",
            "tool": tool_name,
            "module": module,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": timestamp,
            "memory_profile": self.memory_profile
        }
        if error:
            entry["error"] = error
        if params and os.getenv("TOOL_USAGE_LOG_PARAMS", "false").lower() == "true":
            # Only log params if explicitly enabled (privacy/size concerns)
            entry["params_keys"] = list(params.keys()) if isinstance(params, dict) else None

        self._write_entry(entry)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current session usage summary."""
        return {
            "session_id": self.session_id,
            "memory_profile": self.memory_profile,
            "tools": dict(self._stats),
            "total_calls": sum(s["call_count"] for s in self._stats.values()),
            "unique_tools": len(self._stats),
            "top_tools": sorted(
                [(k, v["call_count"]) for k, v in self._stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_module_summary(self) -> Dict[str, Dict[str, int]]:
        """Get usage grouped by module."""
        modules: Dict[str, Dict[str, int]] = defaultdict(lambda: {"calls": 0, "tools": 0})
        for tool_name, stats in self._stats.items():
            module = stats["module"] or "unknown"
            modules[module]["calls"] += stats["call_count"]
            modules[module]["tools"] += 1
        return dict(modules)


def log_tool_call(
    tool_name: str,
    module: str,
    success: bool = True,
    duration_ms: float = 0,
    params: Optional[Dict] = None,
    error: Optional[str] = None
) -> None:
    """Convenience function to log a tool call."""
    try:
        logger_instance = ToolUsageLogger.get_instance()
        logger_instance.log_call(tool_name, module, success, duration_ms, params, error)
    except Exception as e:
        # Never fail on logging
        pass


def track_tool_usage(module_name: str):
    """Decorator factory to track tool usage.

    Usage:
        @track_tool_usage("nmf_tools")
        async def nmf_remember(content: str, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                log_tool_call(func.__name__, module_name, True, duration_ms, kwargs)
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                log_tool_call(func.__name__, module_name, False, duration_ms, kwargs, str(e))
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                log_tool_call(func.__name__, module_name, True, duration_ms, kwargs)
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                log_tool_call(func.__name__, module_name, False, duration_ms, kwargs, str(e))
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def analyze_usage_logs(
    log_dir: Optional[Path] = None,
    days: int = 7
) -> Dict[str, Any]:
    """Analyze usage logs from multiple sessions.

    Returns aggregate statistics useful for refining ORCHESTRATOR_MODULES.
    """
    log_dir = log_dir or LOG_DIR
    if not log_dir.exists():
        return {"error": "No log directory found", "log_dir": str(log_dir)}

    cutoff = datetime.now() - timedelta(days=days)

    # Aggregate stats
    tool_calls: Dict[str, int] = defaultdict(int)
    module_calls: Dict[str, int] = defaultdict(int)
    orchestrator_calls: Dict[str, int] = defaultdict(int)
    full_calls: Dict[str, int] = defaultdict(int)
    sessions_analyzed = 0

    for log_file in log_dir.glob("usage_*.jsonl"):
        try:
            with open(log_file) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("event") == "tool_call":
                            tool = entry.get("tool", "unknown")
                            module = entry.get("module", "unknown")
                            profile = entry.get("memory_profile", "full")

                            tool_calls[tool] += 1
                            module_calls[module] += 1

                            if profile == "orchestrator":
                                orchestrator_calls[tool] += 1
                            else:
                                full_calls[tool] += 1
                        elif entry.get("event") == "session_start":
                            sessions_analyzed += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"Error reading {log_file}: {e}")

    # Calculate recommendations
    recommendations = []

    # Tools frequently used in orchestrator mode - good candidates
    for tool, count in sorted(orchestrator_calls.items(), key=lambda x: -x[1])[:10]:
        if count >= 5:
            recommendations.append({
                "action": "keep",
                "tool": tool,
                "reason": f"Frequently used in orchestrator mode ({count} calls)"
            })

    # Tools never used in orchestrator mode - candidates for removal
    orchestrator_tools = set(orchestrator_calls.keys())
    for tool, count in tool_calls.items():
        if tool not in orchestrator_tools and count >= 10:
            recommendations.append({
                "action": "consider_remove",
                "tool": tool,
                "reason": f"Never used in orchestrator mode (but {count} total calls)"
            })

    return {
        "sessions_analyzed": sessions_analyzed,
        "days_analyzed": days,
        "total_tool_calls": sum(tool_calls.values()),
        "unique_tools_used": len(tool_calls),
        "top_tools": sorted(tool_calls.items(), key=lambda x: -x[1])[:20],
        "top_modules": sorted(module_calls.items(), key=lambda x: -x[1]),
        "orchestrator_mode_tools": sorted(orchestrator_calls.items(), key=lambda x: -x[1]),
        "full_mode_tools": sorted(full_calls.items(), key=lambda x: -x[1])[:20],
        "recommendations": recommendations
    }


# MCP Tool for usage analysis
def register_usage_analysis_tools(app) -> None:
    """Register MCP tools for usage analysis."""

    @app.tool()
    def get_tool_usage_summary() -> str:
        """Get current session's tool usage summary.

        Returns statistics about which tools have been called in this session.
        Useful for understanding actual tool utilization patterns.
        """
        try:
            logger_instance = ToolUsageLogger.get_instance()
            summary = logger_instance.get_usage_summary()
            return json.dumps(summary, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @app.tool()
    def get_module_usage_summary() -> str:
        """Get tool usage grouped by module.

        Shows which modules are being used most frequently.
        Helps identify candidates for ORCHESTRATOR_MODULES inclusion/removal.
        """
        try:
            logger_instance = ToolUsageLogger.get_instance()
            summary = logger_instance.get_module_summary()
            return json.dumps(summary, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @app.tool()
    def analyze_historical_tool_usage(days: int = 7) -> str:
        """Analyze tool usage across multiple sessions.

        Aggregates usage data to provide recommendations for
        ORCHESTRATOR_MODULES refinement.

        Args:
            days: Number of days of history to analyze (default: 7)

        Returns:
            Analysis with top tools, module usage, and recommendations
        """
        try:
            analysis = analyze_usage_logs(days=days)
            return json.dumps(analysis, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


if __name__ == "__main__":
    # Test the logger
    logger = ToolUsageLogger.get_instance()

    # Simulate some tool calls
    log_tool_call("nmf_remember", "nmf_tools", True, 45.2)
    log_tool_call("nmf_recall", "nmf_tools", True, 23.1)
    log_tool_call("search_nodes", "core", True, 150.5)
    log_tool_call("create_entities", "core", True, 89.3)
    log_tool_call("nmf_remember", "nmf_tools", True, 51.0)

    # Print summary
    print("\nUsage Summary:")
    print(json.dumps(logger.get_usage_summary(), indent=2))

    print("\nModule Summary:")
    print(json.dumps(logger.get_module_summary(), indent=2))

    print(f"\nLog file: {logger.log_file}")
