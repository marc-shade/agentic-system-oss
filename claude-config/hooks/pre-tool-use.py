#!/usr/bin/env python3
"""
Pre-Tool-Use Hook
=================

Runs before every tool call. Use for:
- Security validation
- Pattern tracking
- Confidence scoring
- Logging

Environment variables from Claude Code:
- CLAUDE_TOOL_NAME: Name of the tool being called
- CLAUDE_TOOL_ARGUMENTS: JSON string of arguments

Exit codes:
- 0: Allow tool execution
- 1: Block tool execution (prints message to user)
"""

import json
import os
import sys
from datetime import datetime

def main():
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_args_str = os.environ.get("CLAUDE_TOOL_ARGUMENTS", "{}")

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError:
        tool_args = {}

    # Example: Block dangerous commands
    if tool_name == "Bash":
        command = tool_args.get("command", "")
        dangerous_patterns = [
            "rm -rf /",
            "dd if=",
            "> /dev/sd",
            "mkfs",
            ":(){:|:&};:",  # Fork bomb
        ]
        for pattern in dangerous_patterns:
            if pattern in command:
                print(f"BLOCKED: Dangerous command pattern detected: {pattern}")
                sys.exit(1)

    # Example: Warn on sensitive file access
    if tool_name in ["Read", "Write", "Edit"]:
        file_path = tool_args.get("file_path", "")
        sensitive_paths = [
            ".env",
            "credentials",
            "secrets",
            ".ssh/",
            "private",
        ]
        for sensitive in sensitive_paths:
            if sensitive in file_path.lower():
                # Just log warning, don't block
                log_message = f"[{datetime.now().isoformat()}] Accessing sensitive path: {file_path}"
                print(log_message, file=sys.stderr)

    # Allow execution
    sys.exit(0)

if __name__ == "__main__":
    main()
