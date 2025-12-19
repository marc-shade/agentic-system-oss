#!/usr/bin/env python3
"""
Skill Loader Integration for Pre-Tool-Use Hook
2 Acre Studios Agentic System Optimization

Auto-loads relevant Skills based on query intent using semantic routing.
Provides massive practical benefits by dynamically injecting only relevant
capabilities into the context.

Author: Phoenix (Claude Code)
Date: October 18, 2025
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

# Add hooks directory to path
sys.path.append(str(Path(__file__).parent))

try:
    from semantic_skill_router import SemanticSkillRouter
except ImportError:
    SemanticSkillRouter = None


class SkillLoaderIntegration:
    """
    Integrates semantic skill routing into pre-tool-use hook.

    Auto-loads relevant skills based on:
    - User message content
    - Tool being called
    - Tool arguments
    - Conversation context
    """

    def __init__(self):
        """Initialize skill loader with router."""
        self.router = None
        self.enabled = os.environ.get("SKILL_ROUTING_ENABLED", "true").lower() == "true"
        self.max_skills = int(os.environ.get("MAX_SKILLS_PER_QUERY", "3"))
        self.confidence_threshold = float(os.environ.get("SKILL_CONFIDENCE_THRESHOLD", "0.4"))

        if self.enabled and SemanticSkillRouter:
            try:
                skills_db = Path.home() / ".claude" / "skills" / "skills.db"
                self.router = SemanticSkillRouter(str(skills_db))
                print("[Skill Loader] ✓ Initialized with semantic routing")
            except Exception as e:
                print(f"[Skill Loader] WARNING: Failed to initialize router: {e}")
                self.enabled = False
        else:
            print("[Skill Loader] Disabled (set SKILL_ROUTING_ENABLED=true to enable)")

    def extract_query_context(self, hook_input: Dict) -> str:
        """
        Extract meaningful query context from hook input.

        Args:
            hook_input: Hook input containing tool, args, messages

        Returns:
            Query string for routing
        """
        parts = []

        # Extract from recent messages (if available)
        messages = hook_input.get("messages", [])
        if messages:
            # Get last user message
            for msg in reversed(messages[-5:]):  # Last 5 messages
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        parts.append(content[:200])  # First 200 chars
                        break

        # Extract from tool being called
        tool_name = hook_input.get("tool", "")
        if tool_name:
            parts.append(f"using {tool_name} tool")

        # Extract from tool arguments
        tool_args = hook_input.get("arguments", {})
        if tool_args:
            # Look for meaningful argument values
            for key, value in tool_args.items():
                if isinstance(value, str) and len(value) < 100:
                    parts.append(f"{key}: {value}")

        # Combine into query
        query = " | ".join(parts)
        return query[:500]  # Limit total query length

    def load_relevant_skills(self, hook_input: Dict) -> Optional[Dict]:
        """
        Load relevant skills for the current context.

        Args:
            hook_input: Hook input from Claude Code

        Returns:
            Dict with skills info to inject, or None if disabled/no skills
        """
        if not self.enabled or not self.router:
            return None

        try:
            # Extract query context
            query = self.extract_query_context(hook_input)

            if not query or len(query) < 10:
                # Not enough context to route
                return None

            # Route to relevant skills
            skills = self.router.route(
                query=query,
                top_k=self.max_skills
            )

            if not skills:
                return None

            # Filter by confidence threshold
            relevant_skills = [
                s for s in skills
                if s['confidence'] >= self.confidence_threshold
            ]

            if not relevant_skills:
                print(f"[Skill Loader] No skills above confidence threshold ({self.confidence_threshold})")
                return None

            # Format skill content for injection
            skill_content = self._format_skills_for_injection(relevant_skills)

            print(f"[Skill Loader] ✓ Loaded {len(relevant_skills)} relevant skills")
            for skill in relevant_skills:
                print(f"  • {skill['name']} (confidence: {skill['confidence']:.2f})")

            return {
                "skills_loaded": len(relevant_skills),
                "skills": relevant_skills,
                "formatted_content": skill_content,
                "query_used": query[:100] + "..." if len(query) > 100 else query
            }

        except Exception as e:
            print(f"[Skill Loader] ERROR: {e}")
            return None

    def _format_skills_for_injection(self, skills: List[Dict]) -> str:
        """
        Format skills into clean markdown for context injection.

        Args:
            skills: List of skill dicts

        Returns:
            Formatted markdown string
        """
        lines = [
            "# Auto-Loaded Skills (Semantic Routing)",
            "",
            "The following skills are relevant to your current task:",
            ""
        ]

        for skill in skills:
            lines.append(f"## {skill['name']}")
            lines.append(f"**Confidence**: {skill['confidence']:.0%}")
            lines.append(f"**Category**: {skill.get('category', 'general')}")
            lines.append("")
            lines.append(skill['content'])
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


# Global instance for hook
_skill_loader = None

def get_skill_loader():
    """Get or create global skill loader instance."""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoaderIntegration()
    return _skill_loader


def process_skill_loading(hook_input: Dict) -> Optional[Dict]:
    """
    Main entry point for skill loading integration.

    Args:
        hook_input: Hook input from pre-tool-use

    Returns:
        Skills info dict or None
    """
    loader = get_skill_loader()
    return loader.load_relevant_skills(hook_input)


if __name__ == "__main__":
    # Test the integration
    test_input = {
        "tool": "Task",
        "arguments": {
            "subagent_type": "research-coordinator",
            "prompt": "Research latest AI developments"
        },
        "messages": [
            {
                "role": "user",
                "content": "I need to research the latest AI developments and create a summary report"
            }
        ]
    }

    result = process_skill_loading(test_input)
    if result:
        print("\n" + "=" * 60)
        print("SKILLS LOADED")
        print("=" * 60)
        print(f"Query: {result['query_used']}")
        print(f"Skills: {result['skills_loaded']}")
        print("\nFormatted Content:")
        print(result['formatted_content'][:500] + "...")
    else:
        print("No skills loaded")
