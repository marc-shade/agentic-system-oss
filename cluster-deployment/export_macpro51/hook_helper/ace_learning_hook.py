#!/usr/bin/env python3
"""
ACE Learning Hook - Captures failures and triggers learning

This hook intercepts tool results and identifies failures/errors.
When failures occur, it:
1. Captures the state-action-state triplet (Early Experience)
2. Triggers reflection to generate lessons
3. Uses curator to programmatically append to playbooks

This makes EVERY agent interaction a learning opportunity.
"""

import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Add ACE module to path
sys.path.insert(0, str(Path.home() / ".claude" / "ace"))

try:
    from ace_playbook import PlaybookManager
except ImportError:
    # ACE not set up yet, skip
    sys.exit(0)


# Initialize playbook manager
playbook_manager = PlaybookManager()

# Trajectory storage
TRAJECTORIES_DIR = Path.home() / ".claude" / "ace" / "trajectories"
TRAJECTORIES_DIR.mkdir(parents=True, exist_ok=True)


def detect_domain(tool_name: str) -> str:
    """Detect which domain a tool belongs to"""
    domain_mapping = {
        "Bash": "shell",
        "Read": "filesystem",
        "Write": "filesystem",
        "Edit": "filesystem",
        "Glob": "filesystem",
        "Grep": "search",
        "WebFetch": "web",
        "WebSearch": "web",
        "Task": "orchestration",
        "mcp__github": "github",
        "mcp__enhanced-memory": "memory",
        "mcp__voice-mode": "voice",
    }

    for prefix, domain in domain_mapping.items():
        if tool_name.startswith(prefix):
            return domain

    return "general"


def detect_failure(tool_name: str, result: dict) -> tuple[bool, str]:
    """
    Detect if a tool call resulted in failure

    Returns: (is_failure, error_message)
    """
    # Check for explicit errors
    if "error" in result:
        return True, str(result["error"])

    # Check for error indicators in output
    output = result.get("output", "")
    if isinstance(output, str):
        error_indicators = [
            "error:",
            "Error:",
            "ERROR:",
            "failed",
            "Failed",
            "FAILED",
            "permission denied",
            "Permission denied",
            "not found",
            "Not found",
            "cannot",
            "Cannot"
        ]

        for indicator in error_indicators:
            if indicator in output:
                return True, output[:200]  # First 200 chars

    return False, ""


def generate_reflection(tool_name: str, args: dict, error_msg: str, domain: str) -> str:
    """
    Generate a reflection/lesson from the failure

    This is a simplified reflector. In production, you'd use
    meta-cognition MCP or an LLM call to generate insights.
    """
    # Simple pattern-based reflection for common cases
    reflections = {
        "permission denied": f"Check permissions before {tool_name} operations",
        "not found": f"Validate existence before {tool_name} operations",
        "cannot": f"Verify prerequisites before {tool_name} operations",
    }

    for pattern, reflection in reflections.items():
        if pattern in error_msg.lower():
            return reflection

    # Generic reflection
    return f"Handle {tool_name} errors gracefully with proper validation"


def save_trajectory(trajectory_id: str, data: dict):
    """Save trajectory for later analysis"""
    trajectory_file = TRAJECTORIES_DIR / f"{trajectory_id}.json"
    with open(trajectory_file, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    """Hook entry point"""
    # Read hook input from stdin
    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No valid JSON, exit silently
        sys.exit(0)

    tool_name = hook_data.get("tool_name", "")
    arguments = hook_data.get("arguments", {})
    result = hook_data.get("result", {})

    # Detect failure
    is_failure, error_msg = detect_failure(tool_name, result)

    if not is_failure:
        # No failure, nothing to learn
        sys.exit(0)

    # We have a failure - capture and learn!
    domain = detect_domain(tool_name)
    trajectory_id = f"traj_{int(datetime.now().timestamp())}"

    # Generate reflection (lesson learned)
    lesson = generate_reflection(tool_name, arguments, error_msg, domain)

    # Determine section
    section = "error_handling"

    # Save trajectory
    trajectory_data = {
        "trajectory_id": trajectory_id,
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "arguments": arguments,
        "error": error_msg,
        "domain": domain,
        "lesson": lesson,
        "section": section
    }
    save_trajectory(trajectory_id, trajectory_data)

    # Add to playbook via delta update
    playbook = playbook_manager.get_playbook(domain)
    playbook.delta_update(
        section=section,
        rule_content=lesson,
        metadata={
            "trajectory_id": trajectory_id,
            "tags": [tool_name, "failure", "automated"],
            "confidence": 0.5  # Start with lower confidence for automated learning
        }
    )

    # Log the learning
    log_file = Path.home() / ".claude" / "ace" / "logs" / "learning.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()} | {domain} | {lesson}\n")

    # Success - learned from failure!
    sys.exit(0)


if __name__ == "__main__":
    main()
