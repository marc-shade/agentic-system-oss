#!/usr/bin/env python3
"""
DSPy-based Contextual Image Prompt Generator
=============================================

Generates meaningful, context-aware prompts for the Pixel Corgi based on
actual work being performed. Uses DSPy for intelligent prompt generation
that reflects the visual context of the current activity.

Example activities and their visual representations:
- Security scan → Corgi as detective with magnifying glass
- Code review → Corgi with glasses reviewing scrolls
- Git commit → Corgi carrying a package/delivery
- Error debugging → Corgi with confused expression, bugs around
- Research → Corgi in library with books
- Building/compiling → Corgi as construction worker
"""

import dspy
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

# Configure DSPy to use a remote LLM (Ollama on cluster node)
# Avoid local CPU inference - set OLLAMA_HOST to your GPU node
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@dataclass
class WorkContext:
    """Context about the current work activity."""
    event_type: str  # success, error, start, end, tool_use, etc.
    tool_name: Optional[str] = None  # Bash, Edit, Read, etc.
    tool_args: Optional[Dict] = None  # Arguments passed to tool
    task_description: Optional[str] = None  # What the task is about
    error_message: Optional[str] = None  # If there was an error
    file_types: Optional[List[str]] = None  # .py, .rs, .ts, etc.
    domain: Optional[str] = None  # security, web, database, etc.
    mood: str = "neutral"  # excited, focused, confused, tired, celebrating


class ContextToVisualMetaphor(dspy.Signature):
    """Convert work context into a visual metaphor for the Pixel Corgi.

    Think about what visual elements would represent this activity:
    - What props or accessories would the corgi have?
    - What environment/background fits the activity?
    - What pose or expression matches the mood?
    - What small details add context (floating icons, effects)?
    """

    event_type: str = dspy.InputField(desc="Type of event: success, error, thinking, coding, etc.")
    tool_name: str = dspy.InputField(desc="Tool being used: Bash, Edit, Read, Grep, etc.")
    task_summary: str = dspy.InputField(desc="Brief summary of what work is being done")
    domain: str = dspy.InputField(desc="Domain: security, web, database, devops, research, etc.")
    mood: str = dspy.InputField(desc="Current mood: excited, focused, confused, celebrating, tired")

    visual_props: str = dspy.OutputField(desc="Props/accessories for the corgi (e.g., 'tiny hardhat, wrench')")
    environment: str = dspy.OutputField(desc="Background/setting (e.g., 'construction site with code blocks')")
    pose_expression: str = dspy.OutputField(desc="Pose and facial expression (e.g., 'determined stance, tongue out')")
    visual_effects: str = dspy.OutputField(desc="Floating elements/effects (e.g., 'sparkles, binary numbers')")


class GeneratePixelCorgiPrompt(dspy.Signature):
    """Generate a complete NES-style pixel art prompt for the Pixel Corgi.

    The prompt should be optimized for image generation models like Flux.
    Include specific pixel art styling keywords and keep it concise but descriptive.
    """

    visual_props: str = dspy.InputField(desc="Props and accessories for the corgi")
    environment: str = dspy.InputField(desc="Background setting")
    pose_expression: str = dspy.InputField(desc="Pose and expression")
    visual_effects: str = dspy.InputField(desc="Floating elements and effects")

    image_prompt: str = dspy.OutputField(desc="Complete image generation prompt, 50-100 words")


class PixelCorgiPrompter(dspy.Module):
    """DSPy module for generating contextual Pixel Corgi prompts."""

    def __init__(self):
        super().__init__()
        self.context_to_visual = dspy.ChainOfThought(ContextToVisualMetaphor)
        self.generate_prompt = dspy.Predict(GeneratePixelCorgiPrompt)

        # Fallback visual mappings for when LLM is unavailable
        self.fallback_mappings = {
            "security": {
                "props": "detective hat, magnifying glass",
                "environment": "dark cyberpunk background with matrix code",
                "pose": "alert investigative stance, one paw raised",
                "effects": "floating lock icons, shield symbols"
            },
            "coding": {
                "props": "tiny glasses, mechanical keyboard",
                "environment": "cozy desk with monitors showing code",
                "pose": "focused typing pose, concentrated expression",
                "effects": "floating code brackets, semicolons"
            },
            "git": {
                "props": "delivery cap, small package",
                "environment": "branching tree paths, version timeline",
                "pose": "proud delivery stance, tail wagging",
                "effects": "floating git branch icons, checkmarks"
            },
            "database": {
                "props": "tiny filing cabinet, data scrolls",
                "environment": "organized library of glowing data cubes",
                "pose": "organized librarian pose, sorting",
                "effects": "floating table icons, query symbols"
            },
            "web": {
                "props": "painter beret, tiny brush",
                "environment": "canvas with website wireframes",
                "pose": "artistic creative pose, painting",
                "effects": "floating HTML tags, CSS brackets"
            },
            "devops": {
                "props": "hardhat, tiny wrench",
                "environment": "pipeline with gears and containers",
                "pose": "builder stance, working hard",
                "effects": "floating Docker whales, gear icons"
            },
            "research": {
                "props": "professor glasses, stack of papers",
                "environment": "cozy library with floating books",
                "pose": "thoughtful reading pose, paw on chin",
                "effects": "floating lightbulbs, question marks turning to exclamations"
            },
            "testing": {
                "props": "lab coat, test tubes",
                "environment": "laboratory with checkmark displays",
                "pose": "scientist examining pose",
                "effects": "green checkmarks, red X marks"
            },
            "error": {
                "props": "bandaid, confused swirl above head",
                "environment": "slightly glitchy background",
                "pose": "confused tilted head, worried expression",
                "effects": "floating error symbols, bug icons"
            },
            "success": {
                "props": "tiny trophy, confetti cannon",
                "environment": "celebration stage with sparkles",
                "pose": "jumping victory pose, huge smile",
                "effects": "confetti, stars, sparkles everywhere"
            }
        }

    def _detect_domain(self, context: WorkContext) -> str:
        """Detect the work domain from context."""
        tool = (context.tool_name or "").lower()
        task = (context.task_description or "").lower()

        # Security indicators
        if any(x in task for x in ["security", "scan", "vuln", "audit", "pentest", "exploit"]):
            return "security"
        if any(x in tool for x in ["nuclei", "nmap", "security"]):
            return "security"

        # Git indicators
        if any(x in task for x in ["commit", "push", "pull", "merge", "branch", "git"]):
            return "git"
        if "git" in tool:
            return "git"

        # Database indicators
        if any(x in task for x in ["database", "sql", "query", "migration", "schema"]):
            return "database"
        if any(x in tool for x in ["sqlite", "postgres", "mysql", "redis"]):
            return "database"

        # Web indicators
        if any(x in task for x in ["frontend", "css", "html", "react", "vue", "ui", "design"]):
            return "web"

        # DevOps indicators
        if any(x in task for x in ["docker", "deploy", "kubernetes", "ci/cd", "pipeline", "container"]):
            return "devops"

        # Research indicators
        if any(x in task for x in ["research", "paper", "arxiv", "study", "investigate", "analyze"]):
            return "research"

        # Testing indicators
        if any(x in task for x in ["test", "pytest", "jest", "spec", "coverage"]):
            return "testing"

        # Error state
        if context.event_type == "error" or context.error_message:
            return "error"

        # Success state
        if context.event_type == "success":
            return "success"

        # Default to coding
        return "coding"

    def _get_fallback_prompt(self, context: WorkContext) -> str:
        """Generate prompt using fallback mappings when LLM unavailable."""
        domain = context.domain or self._detect_domain(context)
        mapping = self.fallback_mappings.get(domain, self.fallback_mappings["coding"])

        base = "8-bit NES pixel art sprite, cute corgi dog Pixel, orange white black tricolor, clean pixels, retro game style"

        prompt = f"{base}, {mapping['props']}, {mapping['environment']}, {mapping['pose']}, {mapping['effects']}"

        # Add mood modifiers
        if context.mood == "excited":
            prompt += ", energetic bouncy pose, sparkling eyes"
        elif context.mood == "tired":
            prompt += ", sleepy droopy eyes, yawning"
        elif context.mood == "confused":
            prompt += ", tilted head, question mark above"
        elif context.mood == "celebrating":
            prompt += ", party hat, confetti, huge smile"

        return prompt

    def forward(self, context: WorkContext) -> str:
        """Generate a contextual prompt for the Pixel Corgi."""

        # Detect domain if not provided
        domain = context.domain or self._detect_domain(context)

        # Create task summary
        task_summary = context.task_description or f"{context.event_type} event"
        if context.tool_name:
            task_summary = f"Using {context.tool_name}: {task_summary}"

        try:
            # Try to use DSPy with LLM
            visual = self.context_to_visual(
                event_type=context.event_type,
                tool_name=context.tool_name or "general",
                task_summary=task_summary,
                domain=domain,
                mood=context.mood
            )

            result = self.generate_prompt(
                visual_props=visual.visual_props,
                environment=visual.environment,
                pose_expression=visual.pose_expression,
                visual_effects=visual.visual_effects
            )

            # Ensure NES pixel art styling
            prompt = result.image_prompt
            if "pixel" not in prompt.lower():
                prompt = f"8-bit NES pixel art sprite, {prompt}"
            if "corgi" not in prompt.lower():
                prompt = prompt.replace("pixel art sprite", "pixel art sprite cute corgi Pixel")

            return prompt

        except Exception as e:
            # Fallback to rule-based generation
            return self._get_fallback_prompt(context)


def configure_dspy(model: str = "llama3.2:3b"):
    """Configure DSPy with Ollama backend on cluster node."""
    try:
        lm = dspy.LM(
            model=f"ollama_chat/{model}",
            api_base=OLLAMA_HOST,
            api_key="",  # Ollama doesn't need API key
            temperature=0.7,
            max_tokens=200
        )
        dspy.configure(lm=lm)
        return True
    except Exception as e:
        print(f"Failed to configure DSPy: {e}")
        return False


def generate_contextual_prompt(
    event_type: str,
    tool_name: Optional[str] = None,
    task_description: Optional[str] = None,
    error_message: Optional[str] = None,
    mood: str = "neutral",
    use_llm: bool = True
) -> str:
    """
    Generate a contextual Pixel Corgi prompt.

    Args:
        event_type: Type of event (success, error, start, end, tool_use)
        tool_name: Name of the tool being used
        task_description: Description of the current task
        error_message: Error message if applicable
        mood: Current mood (excited, focused, confused, tired, celebrating)
        use_llm: Whether to use LLM (requires cluster node)

    Returns:
        Image generation prompt for Pixel Corgi
    """
    context = WorkContext(
        event_type=event_type,
        tool_name=tool_name,
        task_description=task_description,
        error_message=error_message,
        mood=mood
    )

    prompter = PixelCorgiPrompter()

    if use_llm:
        configured = configure_dspy()
        if not configured:
            use_llm = False

    if use_llm:
        return prompter.forward(context)
    else:
        return prompter._get_fallback_prompt(context)


# CLI interface for shell script integration
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate contextual Pixel Corgi prompts")
    parser.add_argument("--event", default="idle", help="Event type")
    parser.add_argument("--tool", default=None, help="Tool name")
    parser.add_argument("--task", default=None, help="Task description")
    parser.add_argument("--error", default=None, help="Error message")
    parser.add_argument("--mood", default="neutral", help="Mood")
    parser.add_argument("--no-llm", action="store_true", help="Use fallback only (no LLM)")

    args = parser.parse_args()

    prompt = generate_contextual_prompt(
        event_type=args.event,
        tool_name=args.tool,
        task_description=args.task,
        error_message=args.error,
        mood=args.mood,
        use_llm=not args.no_llm
    )

    print(prompt)
