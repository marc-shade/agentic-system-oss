#!/usr/bin/env python3
"""
Post-Tool-Use Hook
==================

Runs after every tool call completes. Use for:
- Learning from outcomes
- Performance tracking
- Pattern detection
- Memory capture

Environment variables from Claude Code:
- CLAUDE_TOOL_NAME: Name of the tool that was called
- CLAUDE_TOOL_ARGUMENTS: JSON string of arguments
- CLAUDE_TOOL_RESULT: Result from the tool (may be truncated)
- CLAUDE_TOOL_SUCCESS: "true" or "false"
- CLAUDE_TOOL_DURATION_MS: Execution time in milliseconds

Exit codes:
- 0: Success (always return 0 in post-hooks)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Log directory
LOG_DIR = Path.home() / ".claude" / "hooks" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_args_str = os.environ.get("CLAUDE_TOOL_ARGUMENTS", "{}")
    tool_success = os.environ.get("CLAUDE_TOOL_SUCCESS", "true") == "true"
    tool_duration = os.environ.get("CLAUDE_TOOL_DURATION_MS", "0")

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError:
        tool_args = {}

    # Log all tool usage
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "success": tool_success,
        "duration_ms": int(tool_duration),
    }

    # Add relevant context without sensitive data
    if tool_name in ["Read", "Write", "Edit"]:
        log_entry["file"] = tool_args.get("file_path", "")
    elif tool_name == "Bash":
        # Just log the command type, not full command (security)
        cmd = tool_args.get("command", "")
        log_entry["command_type"] = cmd.split()[0] if cmd else ""
    elif tool_name == "Task":
        log_entry["subagent"] = tool_args.get("subagent_type", "")

    # Append to daily log
    log_file = LOG_DIR / f"tool_usage_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Track slow operations
    if int(tool_duration) > 10000:  # 10 seconds
        slow_log = LOG_DIR / "slow_operations.jsonl"
        with open(slow_log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    # Track failures for learning
    if not tool_success:
        failure_log = LOG_DIR / "failures.jsonl"
        with open(failure_log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    sys.exit(0)

if __name__ == "__main__":
    main()
