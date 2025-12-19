#!/usr/bin/env python3
"""
Psychological Framing Layer for Cognitive Amplification

This module implements the 8 psychological prompt tricks as infrastructure:
1. False continuity → Real memory-based continuity
2. IQ scores → Dynamic expertise levels
3. "Obviously" → Critical evaluation triggers
4. Audience framing → Presentation modes
5. Fake constraints → Creative forcing functions
6. Stakes detection → Quality gate activation
7. Disagreement → Adversarial agent spawning
8. Version 2.0 → Innovation mandates

Usage:
    from psychological_framing import PsychologicalFramingLayer

    pfl = PsychologicalFramingLayer()
    analysis = pfl.analyze_prompt(user_prompt, tool_name, tool_params)
    frames = pfl.generate_frames(analysis)
    enhanced_prompt = pfl.apply_frames(original_prompt, frames)
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class FramingAnalysis:
    """Analysis results from prompt examination"""
    complexity_score: int  # 1-10
    expertise_level: str
    has_assumptions: bool
    assumption_patterns: List[str]
    stakes_level: int  # 1-10
    stakes_indicators: List[str]
    needs_creativity: bool
    has_audience_cues: bool
    audience_type: Optional[str]
    is_evaluation: bool
    is_iteration: bool
    should_spawn_adversarial: bool
    should_activate_quality_gates: bool


class PsychologicalFramingLayer:
    """
    Cognitive amplification through contextual priming.
    Transforms one-off prompt tricks into persistent infrastructure.
    """

    # Trick #2: Expertise level descriptors
    EXPERTISE_LEVELS = {
        1: "familiar with basic concepts",
        2: "competent practitioner",
        3: "proficient practitioner with solid foundations",
        4: "experienced professional",
        5: "senior specialist with 5+ years experience",
        6: "senior specialist with 10+ years experience",
        7: "expert operating at PhD-level depth",
        8: "complexity-8 authority with deep specialized knowledge",
        9: "world-class expert, top 1% globally",
        10: "preeminent authority, top 0.1% globally, defining the field"
    }

    # Trick #3: Assumption detection patterns
    ABSOLUTE_PATTERNS = [
        r'\balways\b',
        r'\bnever\b',
        r'\bobviously\b',
        r'\bclearly\b',
        r'\bevery(?:one|body)\b',
        r'\bno one\b',
        r'\bimpossible\b',
        r'\bthe best\b',
        r'\bthe only\b',
        r'\b\w+ is (?:better|worse|superior|inferior) than \w+\b',
        r'\bthe (?:right|correct|proper) way\b',
        r'\bmust\b.*\balways\b',
        r'\bcan.?t\b.*\bever\b'
    ]

    # Trick #6: Stakes detection patterns
    HIGH_STAKES_PATTERNS = [
        r'\bbet\b',
        r'\bcritical\b',
        r'\bproduction\b',
        r'\blive(?:s)?\b.*\bdepend',
        r'\bmission[\s-]critical\b',
        r'\bmoney\b.*\bline\b',
        r'\bcan.?t\b.*\bafford\b.*\bfail\b',
        r'\breputation\b.*\bstake\b',
        r'\bemergency\b',
        r'\burgent\b',
        r'\bdeadline\b',
        r'\bcrisis\b',
        r'\bcritical\b.*\bsecurity\b'
    ]

    # Trick #7: Evaluation request patterns
    EVALUATION_PATTERNS = [
        r'\bevaluate\b',
        r'\bassess\b',
        r'\banalyze\b',
        r'\breview\b',
        r'\bcompare\b',
        r'\bshould\s+(?:i|we)\b',
        r'\bwhich\s+(?:is\s+)?(?:better|best)\b',
        r'\bpros\s+and\s+cons\b',
        r'\btrade[\s-]offs?\b',
        r'\bis\s+this\s+(?:good|correct|right|optimal)\b'
    ]

    # Trick #4: Audience detection patterns
    AUDIENCE_PATTERNS = {
        'auditorium': [r'\bpresent(?:ation)?\b', r'\bexplain\s+to\s+(?:many|group|audience)\b', r'\bteach\b'],
        'boardroom': [r'\bexecutive\b', r'\bleadership\b', r'\bboard\b', r'\bstakeholder\b'],
        'workshop': [r'\bhands[\s-]on\b', r'\binteractive\b', r'\bworkshop\b', r'\btutorial\b'],
        'classroom': [r'\bstudent\b', r'\blearner\b', r'\bbeginner\b', r'\bteach\b.*\bclass\b']
    }

    # Trick #8: Version/iteration patterns
    ITERATION_PATTERNS = [
        r'\bv2\b',
        r'\bversion\s+2\b',
        r'\bnext\s+(?:version|generation|iteration)\b',
        r'\bimprove\b.*\bexisting\b',
        r'\brevolution(?:ize)?\b',
        r'\breimagine\b',
        r'\brethink\b'
    ]

    def __init__(self):
        """Initialize the psychological framing layer"""
        pass

    def analyze_prompt(self,
                      user_prompt: str,
                      tool_name: Optional[str] = None,
                      tool_params: Optional[Dict] = None) -> FramingAnalysis:
        """
        Analyze user prompt to determine appropriate psychological frames.

        Args:
            user_prompt: The user's input text
            tool_name: Name of tool being called (if applicable)
            tool_params: Parameters for the tool (if applicable)

        Returns:
            FramingAnalysis with recommended framing strategies
        """
        prompt_lower = user_prompt.lower()

        # Trick #2: Score complexity
        complexity = self._score_complexity(user_prompt, tool_name, tool_params)
        expertise = self.EXPERTISE_LEVELS.get(complexity, self.EXPERTISE_LEVELS[5])

        # Trick #3: Detect assumptions
        assumption_patterns = [p for p in self.ABSOLUTE_PATTERNS if re.search(p, prompt_lower, re.IGNORECASE)]
        has_assumptions = len(assumption_patterns) > 0

        # Trick #6: Detect stakes
        stakes_indicators = [p for p in self.HIGH_STAKES_PATTERNS if re.search(p, prompt_lower, re.IGNORECASE)]
        stakes_level = min(10, len(stakes_indicators) * 3 + (5 if 'production' in prompt_lower else 0))

        # Trick #7: Detect evaluation requests
        is_evaluation = any(re.search(p, prompt_lower, re.IGNORECASE) for p in self.EVALUATION_PATTERNS)

        # Trick #4: Detect audience cues
        audience_type = None
        for aud_type, patterns in self.AUDIENCE_PATTERNS.items():
            if any(re.search(p, prompt_lower, re.IGNORECASE) for p in patterns):
                audience_type = aud_type
                break
        has_audience_cues = audience_type is not None

        # Trick #8: Detect iteration requests
        is_iteration = any(re.search(p, prompt_lower, re.IGNORECASE) for p in self.ITERATION_PATTERNS)

        # Trick #5: Detect need for creative constraints (heuristic: agent stuck or vague request)
        needs_creativity = self._detect_need_for_creativity(user_prompt)

        # Derived decisions
        should_spawn_adversarial = is_evaluation or complexity >= 7
        should_activate_quality_gates = stakes_level >= 7 or complexity >= 8

        return FramingAnalysis(
            complexity_score=complexity,
            expertise_level=expertise,
            has_assumptions=has_assumptions,
            assumption_patterns=assumption_patterns,
            stakes_level=stakes_level,
            stakes_indicators=stakes_indicators,
            needs_creativity=needs_creativity,
            has_audience_cues=has_audience_cues,
            audience_type=audience_type,
            is_evaluation=is_evaluation,
            is_iteration=is_iteration,
            should_spawn_adversarial=should_spawn_adversarial,
            should_activate_quality_gates=should_activate_quality_gates
        )

    def _score_complexity(self,
                         prompt: str,
                         tool_name: Optional[str] = None,
                         tool_params: Optional[Dict] = None) -> int:
        """
        Score task complexity from 1-10.

        Factors:
        - Length and detail of prompt
        - Technical terminology density
        - Tool being used (Task spawning = higher complexity)
        - Multiple steps required
        - Domain expertise required
        """
        score = 5  # baseline

        # Length factor
        word_count = len(prompt.split())
        if word_count > 200:
            score += 2
        elif word_count > 100:
            score += 1

        # Technical terminology (rough heuristic)
        technical_terms = len(re.findall(r'\b(?:API|database|architecture|algorithm|optimization|distributed|concurrent|async|paradigm|framework|infrastructure)\b', prompt, re.IGNORECASE))
        score += min(2, technical_terms // 3)

        # Tool complexity
        if tool_name == 'Task':  # Agent spawning indicates complexity
            score += 2
        elif tool_name in ['Write', 'Edit', 'MultiEdit']:
            score += 1

        # Multi-step indicators
        multi_step_patterns = [r'\band then\b', r'\bafter that\b', r'\bnext\b', r'\bfinally\b', r'\bfirst.*second.*third\b']
        if any(re.search(p, prompt, re.IGNORECASE) for p in multi_step_patterns):
            score += 1

        # Domain expertise indicators
        expert_domains = [r'\barchitecture\b', r'\bsecurity\b', r'\bperformance\b', r'\bscaling\b', r'\boptimization\b']
        if any(re.search(p, prompt, re.IGNORECASE) for p in expert_domains):
            score += 1

        return min(10, max(1, score))

    def _detect_need_for_creativity(self, prompt: str) -> bool:
        """
        Detect if creative constraints might help.
        Heuristic: Vague requests or "explain" without specific framing.
        """
        prompt_lower = prompt.lower()

        # Vague explanation requests
        if 'explain' in prompt_lower or 'describe' in prompt_lower:
            # But no specific framing mentioned
            if not any(word in prompt_lower for word in ['like', 'as if', 'using', 'analogy', 'metaphor']):
                return True

        return False

    def generate_frames(self, analysis: FramingAnalysis) -> List[str]:
        """
        Generate psychological framing text based on analysis.

        Returns:
            List of framing strings to inject into context
        """
        frames = []

        # Trick #2: Expertise level framing
        if analysis.complexity_score >= 5:
            frames.append(
                f"You are {analysis.expertise_level} in this domain. "
                f"Your responses should demonstrate depth appropriate to complexity level {analysis.complexity_score}/10."
            )

        # Trick #3: Critical evaluation framing
        if analysis.has_assumptions:
            frames.append(
                "CRITICAL EVALUATION REQUIRED: The request contains absolute statements or assumptions. "
                "Challenge these if incorrect. Provide nuanced analysis. Do not simply agree."
            )

        # Trick #6: Quality gate framing
        if analysis.should_activate_quality_gates:
            frames.append(
                f"HIGH STAKES DETECTED (level {analysis.stakes_level}/10). Quality gates activated:\n"
                "1. Introspection: Assess your own reasoning quality\n"
                "2. Confidence scoring: Assign confidence % to each claim\n"
                "3. Verification: Test/validate before responding\n"
                "4. Edge cases: Explicitly consider failure modes"
            )

        # Trick #7: Adversarial framing
        if analysis.should_spawn_adversarial:
            frames.append(
                "ADVERSARIAL REVIEW RECOMMENDED: This task warrants multiple perspectives. "
                "Consider spawning parallel agents: one defending the approach, one attacking it. "
                "Synthesize their outputs for balanced evaluation."
            )

        # Trick #4: Audience framing
        if analysis.has_audience_cues and analysis.audience_type:
            audience_frames = {
                'auditorium': "Present as if speaking to 200+ people in an auditorium. Use emphasis, examples, anticipate questions.",
                'boardroom': "Present as executive summary for leadership. Focus on business impact, risks, ROI.",
                'workshop': "Present as hands-on, interactive tutorial. Include exercises and check-ins.",
                'classroom': "Present as teaching material for learners. Build from fundamentals, check understanding."
            }
            frames.append(audience_frames.get(analysis.audience_type, ''))

        # Trick #8: Innovation framing
        if analysis.is_iteration:
            frames.append(
                "VERSION 2.0 MANDATE: This is a sequel, not an update. You must INNOVATE, not just improve. "
                "Think: What would make V1 obsolete? What fundamental capabilities are missing? "
                "Polishing V1 is failure. Revolutionary thinking required."
            )

        # Trick #5: Creativity framing (conditional)
        if analysis.needs_creativity:
            import random
            constraint_domains = ['kitchen', 'sports', 'nature', 'music', 'construction', 'ocean', 'garden', 'theater']
            random_domain = random.choice(constraint_domains)
            frames.append(
                f"CREATIVE CONSTRAINT: Consider explaining key concepts using {random_domain} analogies. "
                f"Forced constraints reveal unexpected insights."
            )

        return [f for f in frames if f]  # Filter empty strings

    def apply_frames(self, original_context: str, frames: List[str]) -> str:
        """
        Apply psychological frames to context.

        Args:
            original_context: Original prompt or context
            frames: List of framing strings from generate_frames()

        Returns:
            Enhanced context with frames injected
        """
        if not frames:
            return original_context

        frame_section = "\n\n" + "="*60 + "\n"
        frame_section += "COGNITIVE AMPLIFICATION FRAMES ACTIVATED\n"
        frame_section += "="*60 + "\n\n"
        frame_section += "\n\n".join(f"[FRAME {i+1}]\n{frame}" for i, frame in enumerate(frames))
        frame_section += "\n\n" + "="*60 + "\n"

        return original_context + frame_section

    def should_search_memory_for_continuity(self,
                                           user_prompt: str,
                                           tool_name: Optional[str] = None) -> bool:
        """
        Trick #1: Determine if we should search memory to inject continuity.

        Returns:
            True if memory search would provide valuable continuity context
        """
        # Always search for Task spawning (agent might benefit from past learning)
        if tool_name == 'Task':
            return True

        # Search for implementation tasks
        impl_patterns = [r'\bimplement\b', r'\bbuild\b', r'\bcreate\b', r'\bdevelop\b', r'\bfix\b', r'\boptimize\b']
        if any(re.search(p, user_prompt, re.IGNORECASE) for p in impl_patterns):
            return True

        # Search for complex analysis
        if len(user_prompt.split()) > 50:
            return True

        return False

    def format_memory_continuity(self, memory_results: List[Dict]) -> str:
        """
        Trick #1: Format memory search results as continuity injection.

        Args:
            memory_results: Results from enhanced-memory search

        Returns:
            Formatted continuity frame
        """
        if not memory_results:
            return ""

        continuity_frame = (
            "MEMORY CONTINUITY INJECTION:\n"
            "You have worked on related tasks before. Here's what you learned:\n\n"
        )

        for i, result in enumerate(memory_results[:3], 1):  # Top 3 results
            continuity_frame += f"{i}. {result.get('name', 'Unknown')}\n"
            observations = result.get('observations', [])
            if observations:
                continuity_frame += f"   Key insights: {', '.join(observations[:3])}\n"
            continuity_frame += "\n"

        continuity_frame += (
            "Build on this foundation. Apply patterns that worked. "
            "Avoid approaches that failed. Maintain consistency with established solutions.\n"
        )

        return continuity_frame


# Convenience function for quick integration
def enhance_prompt_with_psychological_frames(user_prompt: str,
                                             tool_name: Optional[str] = None,
                                             tool_params: Optional[Dict] = None) -> tuple[str, FramingAnalysis]:
    """
    Quick helper to analyze and enhance a prompt.

    Returns:
        (enhanced_prompt, analysis)
    """
    pfl = PsychologicalFramingLayer()
    analysis = pfl.analyze_prompt(user_prompt, tool_name, tool_params)
    frames = pfl.generate_frames(analysis)
    enhanced = pfl.apply_frames(user_prompt, frames)
    return enhanced, analysis


if __name__ == '__main__':
    # Test cases
    test_prompts = [
        ("Obviously Python is better than JavaScript for web development", None, None),
        ("I need to build a distributed caching system with sub-millisecond latency", "Task", {"subagent_type": "system-architect"}),
        ("Let's bet $100 this authentication flow is secure", None, None),
        ("Explain React hooks to me", None, None),
        ("Should we use microservices or monolith for this project?", None, None),
    ]

    print("="*80)
    print("PSYCHOLOGICAL FRAMING LAYER TEST")
    print("="*80)

    for prompt, tool, params in test_prompts:
        print(f"\n{'='*80}")
        print(f"PROMPT: {prompt}")
        print(f"TOOL: {tool}")
        print(f"{'='*80}\n")

        enhanced, analysis = enhance_prompt_with_psychological_frames(prompt, tool, params)

        print("ANALYSIS:")
        print(f"  Complexity: {analysis.complexity_score}/10")
        print(f"  Expertise: {analysis.expertise_level}")
        print(f"  Has Assumptions: {analysis.has_assumptions}")
        print(f"  Stakes Level: {analysis.stakes_level}/10")
        print(f"  Is Evaluation: {analysis.is_evaluation}")
        print(f"  Spawn Adversarial: {analysis.should_spawn_adversarial}")
        print(f"  Quality Gates: {analysis.should_activate_quality_gates}")
        print(f"\nENHANCED PROMPT:\n{enhanced}\n")
