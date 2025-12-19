#!/usr/bin/env python3
"""
Skills Activation Hook
Automatically suggests Agent Skills based on user messages and context.
Runs on SessionStart to provide proactive guidance.
"""

import sys
import json
import re

SKILL_TRIGGERS = {
    "Agentic Orchestration": {
        "keywords": ["multi-agent", "orchestrate", "coordinate", "distribute", "workflow", "autokitteh", "agi cycle"],
        "description": "Coordinate multi-agent systems and workflows",
        "when": "Managing complex agentic tasks or distributed systems"
    },
    "Context Optimization": {
        "keywords": ["context", "memory limit", "optimize", "compress", "too large", "exceed"],
        "description": "Optimize context through memory and Explore subagent",
        "when": "Approaching context limits or searching large codebases"
    },
    "Memory Orchestration": {
        "keywords": ["remember", "store", "recall", "previous", "pattern", "similar project", "knowledge"],
        "description": "Store and retrieve knowledge across sessions",
        "when": "Working with long-term knowledge or reusable patterns"
    },
    "Explore Integration": {
        "keywords": ["find", "search", "locate", "discover", "where is", "show me", "codebase"],
        "description": "Efficiently search codebase without loading files",
        "when": "Searching for code patterns or understanding structure"
    },
    "Claude Docs Query": {
        "keywords": ["how to", "claude code", "documentation", "reference", "guide", "tutorial", "example"],
        "description": "Search indexed Claude Code documentation",
        "when": "Need help with Claude Code features or configuration"
    }
}

def detect_relevant_skills(message: str) -> list:
    """Detect which Skills might be relevant based on message content."""
    message_lower = message.lower()
    relevant = []

    for skill_name, config in SKILL_TRIGGERS.items():
        # Check if any keywords match
        matches = sum(1 for kw in config["keywords"] if kw in message_lower)
        if matches > 0:
            relevant.append({
                "skill": skill_name,
                "matches": matches,
                "description": config["description"],
                "when": config["when"]
            })

    # Sort by number of matches
    relevant.sort(key=lambda x: x["matches"], reverse=True)
    return relevant

def suggest_skills_based_on_task(message: str) -> list:
    """Suggest Skills based on task type inference."""
    suggestions = []
    message_lower = message.lower()

    # Research/investigation tasks
    if any(term in message_lower for term in ["research", "investigate", "analyze", "understand"]):
        suggestions.append({
            "task": "research",
            "skills": ["Explore Integration", "Memory Orchestration", "Claude Docs Query"],
            "rationale": "Research tasks benefit from efficient searching and knowledge retrieval"
        })

    # Implementation tasks
    if any(term in message_lower for term in ["implement", "build", "create", "develop", "code"]):
        suggestions.append({
            "task": "implementation",
            "skills": ["Memory Orchestration", "Claude Docs Query"],
            "rationale": "Check for similar implementations and reference documentation"
        })

    # Large-scale tasks
    if any(term in message_lower for term in ["large", "complex", "many files", "entire", "all"]):
        suggestions.append({
            "task": "large-scale",
            "skills": ["Context Optimization", "Explore Integration", "Agentic Orchestration"],
            "rationale": "Large tasks need context management and efficient search"
        })

    # Documentation/help tasks
    if any(term in message_lower for term in ["help", "how", "what is", "explain", "guide"]):
        suggestions.append({
            "task": "help",
            "skills": ["Claude Docs Query", "Memory Orchestration"],
            "rationale": "Query indexed docs and search for similar solutions"
        })

    return suggestions

def main():
    """Hook entry point."""
    try:
        hook_data = json.loads(sys.stdin.read())
    except:
        sys.exit(0)

    event_type = hook_data.get("event", "")

    # Activate on SessionStart to provide guidance
    if event_type != "SessionStart":
        sys.exit(0)

    # Get session info if available
    session_data = hook_data.get("session", {})
    initial_message = session_data.get("initialMessage", "")

    if not initial_message:
        # No message to analyze
        sys.exit(0)

    # Detect relevant skills
    relevant_skills = detect_relevant_skills(initial_message)
    task_suggestions = suggest_skills_based_on_task(initial_message)

    # Output suggestions
    if relevant_skills:
        print("# Agent Skills Available:", file=sys.stderr)
        for skill in relevant_skills[:3]:  # Top 3 most relevant
            print(f"#   {skill['skill']}: {skill['description']}", file=sys.stderr)
            print(f"#   Use when: {skill['when']}", file=sys.stderr)

    if task_suggestions:
        print("#", file=sys.stderr)
        print("# Recommended Skills for this task:", file=sys.stderr)
        for suggestion in task_suggestions[:2]:  # Top 2 task types
            print(f"#   {suggestion['task'].title()} task detected", file=sys.stderr)
            print(f"#   Consider: {', '.join(suggestion['skills'])}", file=sys.stderr)
            print(f"#   Why: {suggestion['rationale']}", file=sys.stderr)

    # General tips
    print("#", file=sys.stderr)
    print("# Skills Tips:", file=sys.stderr)
    print("#   - Skills activate automatically based on task context", file=sys.stderr)
    print("#   - Check .claude/skills/ for full documentation", file=sys.stderr)
    print("#   - Use 'Claude Docs Query' skill to search indexed documentation", file=sys.stderr)

    sys.exit(0)

if __name__ == "__main__":
    main()
