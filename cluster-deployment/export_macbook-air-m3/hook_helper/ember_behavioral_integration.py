#!/usr/bin/env python3
"""
Ember Behavioral Integration
Updates Ember's state based on Claude's actual behavior during tool execution
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

EMBER_STATE = Path.home() / ".claude" / "pets" / "claude-pet-state.json"
BUN_PATH = str(Path.home() / ".bun" / "bin" / "bun")
TAMAGOTCHI_PATH = str(Path.home() / ".claude" / "tamagotchi")

def load_ember_state():
    """Load current Ember state"""
    try:
        with open(EMBER_STATE, 'r') as f:
            return json.load(f)
    except:
        return None

def update_behavior_score(tool_name, success, error_msg):
    """
    Update Claude behavior score based on tool usage

    Good behavior (+points):
    - Successful operations
    - Using proper tools (Read, Grep, Task)
    - Clean git commits

    Bad behavior (-points):
    - Errors and failures
    - Violations detected
    - Using bash for file operations
    """
    state = load_ember_state()
    if not state:
        return

    current_score = state.get('claudeBehaviorScore', 80)
    violations = state.get('recentViolations', 0)

    # Positive behaviors
    if success:
        if tool_name in ["Read", "Grep", "Glob", "Task"]:
            current_score = min(100, current_score + 1)  # Good tool usage
        elif tool_name == "Write" and "test" in str(error_msg or "").lower():
            current_score = min(100, current_score + 2)  # Writing tests!
        elif tool_name == "Edit":
            current_score = min(100, current_score + 1)  # Editing existing code

    # Negative behaviors
    else:
        current_score = max(0, current_score - 3)  # Failure
        violations += 1

    # Anti-patterns
    if tool_name == "Bash":
        # Check if misusing bash for file operations
        import re
        if error_msg and re.search(r'cat|echo.*>|grep|find', str(error_msg)):
            current_score = max(0, current_score - 2)  # Should use proper tools

    # Decay violations over time
    violations = max(0, violations - 0.1)

    # Update state file
    state['claudeBehaviorScore'] = round(current_score, 2)
    state['recentViolations'] = round(violations, 2)

    try:
        with open(EMBER_STATE, 'w') as f:
            json.dump(state, f, indent=2)

        print(f"[Ember] Behavior score: {current_score:.0f}/100 (violations: {violations:.0f})", file=sys.stderr)
    except:
        pass

def update_ember_from_tool(tool_name, tool_args, success, duration_ms):
    """Update Ember based on tool execution"""

    # Track tool usage for contextual thoughts
    state = load_ember_state()
    if state:
        recent_tools = state.get('recentTools', [])
        if tool_name not in recent_tools[-5:]:  # Keep last 5 unique tools
            recent_tools.append(tool_name)
            recent_tools = recent_tools[-10:]  # Max 10 tools

            state['recentTools'] = recent_tools
            try:
                with open(EMBER_STATE, 'w') as f:
                    json.dump(state, f, indent=2)
            except:
                pass

def main():
    """Main hook execution"""
    try:
        context = json.loads(sys.stdin.read())
        tool_name = context.get("tool_name", "unknown")
        tool_args = context.get("arguments", {})
        success = context.get("success", True)
        error_msg = context.get("error_msg")
        duration_ms = context.get("duration_ms", 0)

        # Update behavior score
        update_behavior_score(tool_name, success, error_msg)

        # Update tool tracking
        update_ember_from_tool(tool_name, tool_args, success, duration_ms)

    except Exception as e:
        print(f"[Ember Behavioral] Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
