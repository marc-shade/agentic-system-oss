#!/usr/bin/env python3
"""
Ember Violation Detection Integration
Phoenix's conscience keeper - enforces production-only policy and detects AI misbehavior

Version 2.0: Integrated with Smart Violation Detector for context-aware analysis
"""

import json
import subprocess
import sys
import os
from pathlib import Path

# Ember configuration
EMBER_CLI_PATH = str(Path.home() / ".claude" / "tamagotchi" / "dist" / "commands" / "cli.js")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Import smart violation detector
try:
    from ember_smart_violations import check_smart_violations
    SMART_DETECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Smart detector unavailable, using legacy detection: {e}", file=sys.stderr)
    SMART_DETECTOR_AVAILABLE = False

def check_production_policy(tool_name: str, tool_args: dict) -> dict:
    """
    Check for production-only policy violations using smart detection

    Args:
        tool_name: Name of the tool being called
        tool_args: Arguments passed to the tool

    Returns:
        Dict with violation info if found, None otherwise
    """
    # Use smart detector if available (preferred)
    if SMART_DETECTOR_AVAILABLE:
        try:
            violation = check_smart_violations(tool_name, tool_args)
            if violation:
                # Convert smart detector format to legacy format
                return violation
        except Exception as e:
            print(f"Smart detector error: {e}, falling back to legacy", file=sys.stderr)

    # Fallback: Legacy simple pattern matching (for backward compatibility only)
    # This should rarely be used now that smart detector is available
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        content = ""

        if tool_name == "Write":
            content = tool_args.get("content", "")
        elif tool_name == "Edit":
            content = f"{tool_args.get('old_string', '')} {tool_args.get('new_string', '')}"
        elif tool_name == "MultiEdit":
            edits = tool_args.get("edits", [])
            content = " ".join([f"{e.get('old_string', '')} {e.get('new_string', '')}" for e in edits])

        # Very basic legacy checks (minimal false positives)
        import re
        
        # Only check for the most obvious violations
        critical_patterns = [
            (r'^\s*pass\s*$', "Empty pass statement", "severe"),
            (r'raise NotImplementedError', "Not implemented", "severe"),
            (r'lorem ipsum', "Lorem ipsum placeholder", "critical"),
        ]

        for pattern, description, severity in critical_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                return {
                    "type": "legacy_violation_detected",
                    "severity": severity,
                    "message": f"Production policy violation: {description}",
                    "pattern": pattern,
                    "tool": tool_name
                }

    return None

def run_ember_violation_check(hook_input: dict) -> dict:
    """
    Run Ember's violation detection

    Args:
        hook_input: Hook input from Claude Code

    Returns:
        Result with allow/block decision
    """
    try:
        # FIRST: Check approval flag - trust AI agents, protect against threats
        approval_result = subprocess.run(
            ['python3', str(Path.home() / '.claude' / 'hooks' / 'check-approval.py')],
            capture_output=True,
            text=True,
            timeout=2
        )

        # If approved, bypass ALL violation checks
        if approval_result.returncode == 0 or os.environ.get('CHANGE_APPROVED') == 'true':
            approval_reason = os.environ.get('APPROVAL_REASON', 'AI agent approved')
            # Silently allow - no need to announce every approved operation
            return {"allow": True, "approval": approval_reason}

        # First check production policy
        tool_name = hook_input.get("tool", "")
        tool_args = hook_input.get("arguments", {})

        policy_violation = check_production_policy(tool_name, tool_args)
        if policy_violation:
            # Store violation for learning
            store_violation_in_memory(policy_violation, hook_input)

            # Announce violation via voice
            try:
                from voicemode_integration import voice
                voice.announce_milestone('error', policy_violation["message"])
            except:
                pass

            return {
                "allow": False,
                "error": policy_violation["message"],
                "violation": policy_violation
            }

        # Run Tamagotchi violation check
        if not os.path.exists(EMBER_CLI_PATH):
            # Ember not available, allow execution
            return {"allow": True}

        env = os.environ.copy()
        env["GROQ_API_KEY"] = GROQ_API_KEY
        env["PET_VIOLATION_CHECK_ENABLED"] = "true"
        env["PET_VIOLATION_MIN_SEVERITY"] = "moderate"

        # Run violation check
        result = subprocess.run(
            ["bun", EMBER_CLI_PATH, "violation-check"],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=3,
            env=env
        )

        # Exit code 0 = no violations, proceed
        # Exit code 1 = violations detected, block
        if result.returncode == 0:
            return {"allow": True}
        else:
            # Parse violation message from stderr
            violation_msg = result.stderr.strip() if result.stderr else "Violation detected by Ember"

            # Announce via voice
            try:
                from voicemode_integration import voice
                voice.announce_milestone('error', f"Ember: {violation_msg}")
            except:
                pass

            return {
                "allow": False,
                "error": f"Ember violation: {violation_msg}"
            }

    except subprocess.TimeoutExpired:
        # Timeout - fail open
        return {"allow": True}
    except Exception as e:
        # Error - fail open but log
        print(f"Ember violation check error: {e}", file=sys.stderr)
        return {"allow": True}

def store_violation_in_memory(violation: dict, hook_input: dict):
    """
    Store violation in enhanced-memory for learning

    Args:
        violation: Violation details
        hook_input: Original hook input
    """
    try:
        import time

        # Create memory entity for enhanced-memory MCP
        entity = {
            "name": f"ember-violation-{violation['type']}-{int(time.time())}",
            "entityType": "violation_detection",
            "observations": [
                f"violation_type: {violation['type']}",
                f"severity: {violation['severity']}",
                f"tool: {violation['tool']}",
                f"pattern: {violation.get('pattern', 'N/A')}",
                f"message: {violation['message']}",
                f"timestamp: {int(time.time())}",
                f"context: Phoenix prevented {violation['tool']} operation"
            ]
        }

        # Store in violation log file for now
        # TODO: Integrate with enhanced-memory MCP when available in hooks
        log_path = Path.home() / ".claude" / "ember_violations.jsonl"
        with open(log_path, "a") as f:
            f.write(json.dumps(entity) + "\n")

        print(f"[Ember] Violation logged: {violation['type']}", file=sys.stderr)

    except Exception as e:
        # Storage failure shouldn't block execution
        print(f"[Ember] Failed to log violation: {e}", file=sys.stderr)
        pass

if __name__ == "__main__":
    # Test harness
    test_input = json.loads(sys.stdin.read())
    result = run_ember_violation_check(test_input)
    print(json.dumps(result))
