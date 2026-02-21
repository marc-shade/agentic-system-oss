#!/usr/bin/env python3
"""
Post-Tool-Use Security Hook
============================

Analyzes tool results after execution for:
1. Credential boundary scanning (detect secrets in output)
2. Audit logging of all tool usage
3. Output size warnings
4. Failure tracking for learning

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
import re
import sys
from datetime import datetime
from pathlib import Path

# Log directory
LOG_DIR = Path.home() / ".claude" / "hooks" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Credential patterns to detect in output
OUTPUT_CREDENTIAL_PATTERNS = [
    (r"sk-ant-api[a-zA-Z0-9_-]{20,}", "Anthropic API key"),
    (r"sk-proj-[a-zA-Z0-9_-]{20,}", "OpenAI API key"),
    (r"gsk_[a-zA-Z0-9_-]{20,}", "Groq API key"),
    (r"AIzaSy[a-zA-Z0-9_-]{30,}", "Google API key"),
    (r"ghp_[a-zA-Z0-9]{30,}", "GitHub PAT"),
    (r"xoxb-[a-zA-Z0-9-]+", "Slack token"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"(?i)password\s*[=:]\s*['\"][^'\"]+['\"]", "password value"),
    (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "private key"),
    (r"(?i)bearer\s+[a-zA-Z0-9_-]{20,}", "bearer token"),
]

# Output size thresholds
LARGE_OUTPUT_WARN = 50_000  # chars
HUGE_OUTPUT_WARN = 200_000  # chars


def audit_log(level: str, message: str) -> None:
    """Write structured audit log to stderr."""
    timestamp = datetime.now().isoformat()
    tool = os.environ.get("CLAUDE_TOOL_NAME", "unknown")
    print(f"[{timestamp}] [{level}] [post-tool] [{tool}] {message}", file=sys.stderr)


def scan_for_credentials(text: str) -> list[str]:
    """Scan text for potential credential leaks."""
    findings = []
    for pattern, description in OUTPUT_CREDENTIAL_PATTERNS:
        if re.search(pattern, text):
            findings.append(description)
    return findings


def log_tool_usage(tool_name: str, tool_args: dict, success: bool, duration_ms: int) -> None:
    """Append tool usage to daily audit log."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
    }

    # Add relevant context without exposing sensitive data
    if tool_name in ("Read", "Write", "Edit"):
        log_entry["file"] = tool_args.get("file_path", "")
    elif tool_name == "Bash":
        cmd = tool_args.get("command", "")
        log_entry["command_prefix"] = cmd.split()[0] if cmd else ""
        log_entry["command_length"] = len(cmd)
    elif tool_name == "Task":
        log_entry["subagent"] = tool_args.get("subagent_type", "")
    elif tool_name == "WebFetch":
        log_entry["url"] = tool_args.get("url", "")

    log_file = LOG_DIR / f"tool_usage_{datetime.now().strftime('%Y%m%d')}.jsonl"
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except OSError:
        pass  # Non-critical, don't fail the hook


def main() -> None:
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_args_str = os.environ.get("CLAUDE_TOOL_ARGUMENTS", "{}")
    tool_result = os.environ.get("CLAUDE_TOOL_RESULT", "")
    tool_success = os.environ.get("CLAUDE_TOOL_SUCCESS", "true") == "true"
    tool_duration = int(os.environ.get("CLAUDE_TOOL_DURATION_MS", "0"))

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError:
        tool_args = {}

    # --- Credential boundary scan ---
    if tool_result:
        credential_findings = scan_for_credentials(tool_result)
        if credential_findings:
            findings_str = ", ".join(credential_findings)
            audit_log("SECURITY", f"Potential credentials in output: {findings_str}")
            print(
                f"WARNING: Tool output may contain sensitive data: {findings_str}. "
                "Avoid including these in responses or committing to version control.",
                file=sys.stderr
            )

    # --- Output size warnings ---
    result_size = len(tool_result) if tool_result else 0
    if result_size > HUGE_OUTPUT_WARN:
        audit_log("WARN", f"Very large output: {result_size:,} chars")
    elif result_size > LARGE_OUTPUT_WARN:
        audit_log("INFO", f"Large output: {result_size:,} chars")

    # --- Slow operation tracking ---
    if tool_duration > 30_000:  # 30 seconds
        audit_log("WARN", f"Slow tool execution: {tool_duration}ms")
        slow_log = LOG_DIR / "slow_operations.jsonl"
        try:
            with open(slow_log, "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "tool": tool_name,
                    "duration_ms": tool_duration,
                    "success": tool_success,
                }) + "\n")
        except OSError:
            pass

    # --- Failure tracking ---
    if not tool_success:
        audit_log("FAIL", f"Tool failed after {tool_duration}ms")
        failure_log = LOG_DIR / "failures.jsonl"
        try:
            with open(failure_log, "a") as f:
                f.write(json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "tool": tool_name,
                    "duration_ms": tool_duration,
                    "args_summary": {
                        k: str(v)[:100] for k, v in tool_args.items()
                    } if tool_args else {},
                }) + "\n")
        except OSError:
            pass

    # --- Audit log ---
    log_tool_usage(tool_name, tool_args, tool_success, tool_duration)

    # Post-hooks always exit 0
    sys.exit(0)


if __name__ == "__main__":
    main()
