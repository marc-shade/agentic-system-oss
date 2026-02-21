#!/usr/bin/env python3
"""
Pre-Tool-Use Security Hook
===========================

Validates tool calls before execution. Implements layered defense:
1. Dangerous command detection (destructive patterns)
2. Injection detection (SQL, command, path traversal)
3. Credential leak prevention (detects secrets in arguments)
4. Sensitive path access warnings

Environment variables from Claude Code:
- CLAUDE_TOOL_NAME: Name of the tool being called
- CLAUDE_TOOL_ARGUMENTS: JSON string of arguments

Exit codes:
- 0: Allow tool execution
- 1: Block tool execution (stderr message shown to user)
"""

import json
import os
import re
import sys
from datetime import datetime


# --- Pattern Definitions ---

DANGEROUS_COMMANDS = [
    r"rm\s+(-rf?|--recursive)\s+/\s*$",   # rm -rf /
    r"rm\s+(-rf?|--recursive)\s+/[a-z]+",  # rm -rf /usr, /etc, etc.
    r"dd\s+if=.*\s+of=/dev/[sh]d",         # dd to disk device
    r"mkfs\.\w+\s+/dev/",                  # format disk
    r":\(\)\{.*\|.*&\}\s*;",              # fork bomb
    r"chmod\s+(-R\s+)?777\s+/",           # chmod 777 on root
    r">\s*/dev/sd[a-z]",                   # write to raw disk
    r"curl.*\|\s*(ba)?sh",                 # pipe curl to shell (warn only)
    r"wget.*\|\s*(ba)?sh",                 # pipe wget to shell (warn only)
]

INJECTION_PATTERNS = [
    # SQL injection
    (r"(?i)(union\s+select|;\s*drop\s+table|;\s*delete\s+from|'\s*or\s+1\s*=\s*1)", "SQL injection"),
    # Command injection
    (r"[;&|`]\s*(cat|nc|curl|wget|python|perl|ruby|bash)\s", "command injection"),
    (r"\$\(.*\)", "command substitution"),
    # Path traversal
    (r"\.\./\.\./\.\.", "path traversal"),
    (r"/etc/(passwd|shadow|sudoers)", "sensitive system file access"),
]

CREDENTIAL_PATTERNS = [
    (r"sk-ant-api[a-zA-Z0-9_-]{20,}", "Anthropic API key"),
    (r"sk-proj-[a-zA-Z0-9_-]{20,}", "OpenAI API key"),
    (r"gsk_[a-zA-Z0-9_-]{20,}", "Groq API key"),
    (r"AIzaSy[a-zA-Z0-9_-]{30,}", "Google API key"),
    (r"ghp_[a-zA-Z0-9]{30,}", "GitHub personal access token"),
    (r"xoxb-[a-zA-Z0-9-]+", "Slack bot token"),
    (r"(?i)password\s*[=:]\s*['\"][^'\"]{8,}", "hardcoded password"),
    (r"(?i)api[_-]?key\s*[=:]\s*['\"][a-zA-Z0-9_-]{16,}", "hardcoded API key"),
]

SENSITIVE_PATHS = [
    ".env", "credentials", "secrets", ".ssh/",
    "private", ".aws/", ".gnupg/", "id_rsa",
    ".netrc", ".npmrc", ".pypirc",
]


def audit_log(level: str, message: str) -> None:
    """Write structured audit log to stderr."""
    timestamp = datetime.now().isoformat()
    tool = os.environ.get("CLAUDE_TOOL_NAME", "unknown")
    print(f"[{timestamp}] [{level}] [pre-tool] [{tool}] {message}", file=sys.stderr)


def check_dangerous_commands(command: str) -> tuple[bool, str]:
    """Check for destructive or dangerous command patterns."""
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, command):
            # Pipe-to-shell is a warning, not a block
            if "curl" in pattern or "wget" in pattern:
                audit_log("WARN", f"Pipe-to-shell pattern detected: {pattern}")
                return False, ""
            return True, f"Dangerous command pattern: {pattern}"
    return False, ""


def check_injections(text: str) -> tuple[bool, str]:
    """Check for injection attack patterns."""
    for pattern, description in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True, f"Potential {description} detected"
    return False, ""


def check_credentials(text: str) -> tuple[bool, str]:
    """Check for credential leaks in tool arguments."""
    for pattern, description in CREDENTIAL_PATTERNS:
        if re.search(pattern, text):
            return True, f"Credential detected in arguments: {description}"
    return False, ""


def check_sensitive_paths(file_path: str) -> None:
    """Warn on access to sensitive file paths (does not block)."""
    lower_path = file_path.lower()
    for sensitive in SENSITIVE_PATHS:
        if sensitive in lower_path:
            audit_log("WARN", f"Accessing sensitive path: {file_path}")
            return


def main() -> None:
    tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
    tool_args_str = os.environ.get("CLAUDE_TOOL_ARGUMENTS", "{}")

    try:
        tool_args = json.loads(tool_args_str)
    except json.JSONDecodeError:
        tool_args = {}

    # Full argument text for broad scanning
    args_text = json.dumps(tool_args)

    # --- Layer 1: Credential leak detection (all tools) ---
    blocked, reason = check_credentials(args_text)
    if blocked:
        audit_log("BLOCK", reason)
        print(f"BLOCKED: {reason}", file=sys.stderr)
        sys.exit(1)

    # --- Layer 2: Bash command validation ---
    if tool_name == "Bash":
        command = tool_args.get("command", "")

        # Check dangerous commands
        blocked, reason = check_dangerous_commands(command)
        if blocked:
            audit_log("BLOCK", reason)
            print(f"BLOCKED: {reason}", file=sys.stderr)
            sys.exit(1)

        # Check injection patterns in commands
        blocked, reason = check_injections(command)
        if blocked:
            audit_log("BLOCK", reason)
            print(f"BLOCKED: {reason}", file=sys.stderr)
            sys.exit(1)

    # --- Layer 3: File operation validation ---
    if tool_name in ("Read", "Write", "Edit"):
        file_path = tool_args.get("file_path", "")
        check_sensitive_paths(file_path)

        # Check for path traversal in file operations
        if "../../../" in file_path:
            audit_log("BLOCK", f"Path traversal in file path: {file_path}")
            print(f"BLOCKED: Path traversal detected in file path", file=sys.stderr)
            sys.exit(1)

    # --- Layer 4: Write/Edit content validation ---
    if tool_name in ("Write", "Edit"):
        content = tool_args.get("content", "") or tool_args.get("new_string", "")
        blocked, reason = check_credentials(content)
        if blocked:
            audit_log("BLOCK", f"Credential in file content: {reason}")
            print(f"BLOCKED: {reason} (in file content)", file=sys.stderr)
            sys.exit(1)

    # --- Layer 5: Injection detection in all arguments ---
    blocked, reason = check_injections(args_text)
    if blocked:
        audit_log("WARN", f"Injection pattern in arguments: {reason}")
        # Warning only for non-Bash tools (could be legitimate data)

    # All checks passed
    audit_log("ALLOW", f"Tool {tool_name} approved")
    sys.exit(0)


if __name__ == "__main__":
    main()
