#!/usr/bin/env python3
"""
Performance Tracking Hook
Auto-tracks tool usage for GEPA evolution (Genetic Evolution of Prompts and Agents)

Integrates with:
- post-tool-use.py (captures tool execution data)
- performance-tracker.py (stores metrics)
- gepa-evolution-controller.py (triggers genetic evolution)
- darwin-godel-integrator.py (identifies candidates)
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add claude home to path
CLAUDE_HOME = Path.home() / ".claude"
sys.path.insert(0, str(CLAUDE_HOME))

# Import performance tracker
try:
    from performance_tracker import PerformanceTracker
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("performance_tracker", CLAUDE_HOME / "performance-tracker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    PerformanceTracker = module.PerformanceTracker


def track_tool_execution(tool_data: dict) -> None:
    """Track a tool execution in performance DB"""
    tracker = PerformanceTracker()

    try:
        # Extract tool info
        tool_name = tool_data.get("tool", "unknown")
        parameters = tool_data.get("parameters", {})
        success = tool_data.get("success", True)
        execution_time = tool_data.get("execution_time_ms", 0.0)
        error_message = tool_data.get("error", None)
        output_size = tool_data.get("output_size", 0)

        # Track in DB
        tracker.track_tool_execution(
            tool_name=tool_name,
            parameters=parameters,
            success=success,
            execution_time_ms=execution_time,
            error_message=error_message,
            output_size=output_size,
            context_tokens=None,  # Would come from Claude API metadata
            output_tokens=None,
            agent_type=tool_data.get("agent_type"),
            task_complexity=tool_data.get("complexity", 5)
        )

    finally:
        tracker.close()


def track_agent_task(agent_data: dict) -> None:
    """Track agent task completion"""
    tracker = PerformanceTracker()

    try:
        tracker.track_agent_performance(
            agent_type=agent_data.get("agent_type", "unknown"),
            agent_file=agent_data.get("agent_file", ""),
            task_description=agent_data.get("task", ""),
            success_rate=agent_data.get("success_rate", 1.0),
            avg_execution_time=agent_data.get("execution_time", 0.0),
            total_tasks=agent_data.get("total_tasks", 1),
            failed_tasks=agent_data.get("failed_tasks", 0),
            user_rating=agent_data.get("user_rating")
        )

    finally:
        tracker.close()


def should_trigger_evolution() -> bool:
    """Check if we should trigger evolution cycle"""
    # Check once per day
    last_check_file = CLAUDE_HOME / ".last_evolution_check"

    if last_check_file.exists():
        with open(last_check_file) as f:
            last_check = datetime.fromisoformat(f.read().strip())

        # Check if 24 hours have passed
        if (datetime.now() - last_check).total_seconds() < 86400:
            return False

    # Update last check time
    with open(last_check_file, 'w') as f:
        f.write(datetime.now().isoformat())

    return True


def trigger_evolution_if_needed() -> None:
    """Trigger GEPA evolution cycle if conditions are met"""
    if not should_trigger_evolution():
        return

    try:
        # Run GEPA evolution cycle in background
        import subprocess
        evolution_log = CLAUDE_HOME / "gepa_evolution.log"

        subprocess.Popen(
            [
                "python3",
                str(CLAUDE_HOME / "gepa-evolution-controller.py")
            ],
            stdout=open(evolution_log, 'a'),
            stderr=subprocess.STDOUT
        )

    except Exception as e:
        # Silent fail - don't break hook chain
        pass


def main():
    """
    Hook entry point
    Called by post-tool-use.py with tool execution data
    """
    # Read tool data from stdin or environment
    tool_data_str = os.getenv("TOOL_DATA", "{}")

    try:
        tool_data = json.loads(tool_data_str)
    except json.JSONDecodeError:
        # No data to track
        return

    # Track tool execution
    if tool_data:
        track_tool_execution(tool_data)

    # Check if we should trigger evolution
    trigger_evolution_if_needed()


if __name__ == "__main__":
    main()
