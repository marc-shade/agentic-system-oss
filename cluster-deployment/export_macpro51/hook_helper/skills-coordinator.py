#!/usr/bin/env python3
"""
Skills Coordinator Hook
Automatically suggests and activates relevant Agent Skills based on context.
"""

import sys
import json
import re
from pathlib import Path

def get_skill_suggestions(tool_name: str, params: dict) -> list:
    """Suggest relevant Skills based on tool usage patterns."""
    suggestions = []

    # Context optimization triggers
    if tool_name in ["Read", "Grep", "Glob"] and "pattern" in str(params):
        suggestions.append({
            "skill": "Explore Integration",
            "reason": "Consider using Explore subagent for context-efficient searching",
            "alternative": "Task(subagent_type='Explore', prompt='...')"
        })

    # Memory orchestration triggers
    if "project" in str(params).lower() or "pattern" in str(params).lower():
        suggestions.append({
            "skill": "Memory Orchestration",
            "reason": "Consider storing outcomes or searching for similar work",
            "alternative": "mcp__enhanced-memory-mcp__search_nodes(query='...')"
        })

    # Documentation query triggers
    if any(term in str(params).lower() for term in ["claude", "skill", "hook", "mcp", "subagent", "plugin"]):
        suggestions.append({
            "skill": "Claude Docs Query",
            "reason": "Check indexed documentation for official guidance",
            "alternative": "mcp__enhanced-memory-mcp__search_nodes(query='...', entity_types=['documentation'])"
        })

    # Agentic orchestration triggers
    if tool_name == "Task" or "agent" in str(params).lower():
        suggestions.append({
            "skill": "Agentic Orchestration",
            "reason": "Review coordination patterns and complexity scaling",
            "note": "Prefer single-agent for complexity 1-3"
        })

    return suggestions

def analyze_context_usage() -> dict:
    """Analyze current context usage and recommend optimization."""
    # This would integrate with actual context metrics
    # For now, provide static recommendations
    return {
        "status": "monitoring",
        "recommendations": [
            "Use Explore subagent for codebase searches to save context",
            "Store project outcomes in memory for cross-session knowledge",
            "Query indexed documentation instead of WebFetch when possible"
        ]
    }

def main():
    """Hook entry point."""
    # Read hook input from stdin
    try:
        hook_data = json.loads(sys.stdin.read())
    except:
        # No input, exit silently
        sys.exit(0)

    event_type = hook_data.get("event", "")
    tool_name = hook_data.get("toolName", "")
    params = hook_data.get("params", {})

    # Only activate on PreToolUse events
    if event_type != "PreToolUse":
        sys.exit(0)

    # Get skill suggestions
    suggestions = get_skill_suggestions(tool_name, params)

    # Output suggestions as comments (won't block execution)
    if suggestions:
        print("# Skills Coordinator Suggestions:", file=sys.stderr)
        for suggestion in suggestions:
            print(f"#   - {suggestion['skill']}: {suggestion['reason']}", file=sys.stderr)
            if "alternative" in suggestion:
                print(f"#     Alternative: {suggestion['alternative']}", file=sys.stderr)
            if "note" in suggestion:
                print(f"#     Note: {suggestion['note']}", file=sys.stderr)

    # Context usage analysis
    context_analysis = analyze_context_usage()
    if context_analysis.get("recommendations"):
        print("# Context Optimization Tips:", file=sys.stderr)
        for rec in context_analysis["recommendations"]:
            print(f"#   - {rec}", file=sys.stderr)

    # Allow tool execution to proceed
    sys.exit(0)

if __name__ == "__main__":
    main()
