#!/usr/bin/env python3
"""
Reasoning Scaffolds Framework
==============================

Counters compression bias and establishes quality bar through:
1. Deliberate Over-Instruction: Forceful anti-compression directives
2. Reference Class Priming: Show quality examples from memory
3. Zero-Shot CoT: Blank templates triggering decomposition

These techniques activate latent reasoning patterns and prevent
premature summarization/compression in model outputs.

Usage:
    scaffold = await build_full_scaffold(
        problem="Debug race condition",
        context_tags=["concurrency", "debugging"],
        template_type="debug",
        memory_client=enhanced_memory
    )
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

logger = logging.getLogger(__name__)


class ScaffoldType(Enum):
    """Types of reasoning scaffolds"""
    OVER_INSTRUCTION = "over_instruction"
    REFERENCE_PRIMING = "reference_priming"
    ZERO_SHOT_COT = "zero_shot_cot"
    HYBRID = "hybrid"


class DeliberateOverInstruction:
    """
    Deliberate Over-Instruction - Anti-compression directives

    Forceful instructions that prevent the model from summarizing
    or compressing its reasoning. Commands the model to be exhaustive.
    """

    # Standard over-instruction directives with emphasis levels
    DIRECTIVES = {
        "no_summarize": {
            "strong": "DO NOT SUMMARIZE. Provide complete, exhaustive details.",
            "moderate": "Avoid summarizing. Provide thorough details.",
            "subtle": "Please include all relevant details."
        },
        "show_work": {
            "strong": "SHOW ALL INTERMEDIATE STEPS. Do not skip any reasoning.",
            "moderate": "Show your work and intermediate steps.",
            "subtle": "Explain your reasoning process."
        },
        "be_exhaustive": {
            "strong": "BE EXHAUSTIVE. Cover every aspect comprehensively.",
            "moderate": "Be thorough and comprehensive.",
            "subtle": "Provide a complete analysis."
        },
        "think_aloud": {
            "strong": "THINK OUT LOUD. Verbalize every thought process.",
            "moderate": "Think aloud through the problem.",
            "subtle": "Share your thinking process."
        },
        "no_shortcuts": {
            "strong": "DO NOT TAKE SHORTCUTS. Follow the complete process.",
            "moderate": "Avoid shortcuts in your reasoning.",
            "subtle": "Be methodical in your approach."
        },
        "detail_priority": {
            "strong": "DETAIL is MORE IMPORTANT than brevity. Err toward over-explanation.",
            "moderate": "Prioritize detail over brevity.",
            "subtle": "Include necessary details."
        },
        "enumerate_steps": {
            "strong": "ENUMERATE every single step. Number them 1, 2, 3...",
            "moderate": "Number and enumerate your steps.",
            "subtle": "List your steps."
        },
        "explain_why": {
            "strong": "EXPLAIN WHY for every decision and choice made.",
            "moderate": "Explain your reasoning for each decision.",
            "subtle": "Provide reasoning for your choices."
        }
    }

    @staticmethod
    def build_instruction_block(
        context_tags: Optional[List[str]] = None,
        emphasis: str = "strong"
    ) -> str:
        """
        Build over-instruction directive block

        Args:
            context_tags: Context tags for customization
            emphasis: Directive emphasis level (strong/moderate/subtle)

        Returns:
            Instruction block text
        """
        context_tags = context_tags or []

        # Select directives based on context
        selected_directives = []

        # Always include core directives
        selected_directives.extend([
            DeliberateOverInstruction.DIRECTIVES["no_summarize"][emphasis],
            DeliberateOverInstruction.DIRECTIVES["show_work"][emphasis],
            DeliberateOverInstruction.DIRECTIVES["be_exhaustive"][emphasis]
        ])

        # Add context-specific directives
        if "debug" in context_tags or "analysis" in context_tags:
            selected_directives.append(
                DeliberateOverInstruction.DIRECTIVES["think_aloud"][emphasis]
            )

        if "planning" in context_tags or "design" in context_tags:
            selected_directives.append(
                DeliberateOverInstruction.DIRECTIVES["enumerate_steps"][emphasis]
            )

        if "critical" in context_tags or "security" in context_tags:
            selected_directives.extend([
                DeliberateOverInstruction.DIRECTIVES["no_shortcuts"][emphasis],
                DeliberateOverInstruction.DIRECTIVES["explain_why"][emphasis]
            ])

        # Build block
        block = "REASONING REQUIREMENTS:\n"
        for i, directive in enumerate(selected_directives, 1):
            block += f"{i}. {directive}\n"

        block += "\nYour response will be evaluated on thoroughness and depth, NOT brevity."

        return block


class ReferenceClassPriming:
    """
    Reference Class Priming - Quality examples from memory

    Shows high-quality reasoning examples from enhanced-memory
    to establish the expected quality bar before the task.
    """

    def __init__(self, memory_client: Optional[Any] = None):
        """
        Initialize ReferenceClassPriming

        Args:
            memory_client: Enhanced-memory MCP client for example retrieval
        """
        self.memory_client = memory_client
        logger.info(f"ReferenceClassPriming initialized (memory: {memory_client is not None})")

    async def fetch_examples_from_memory(
        self,
        query: str,
        context_tags: Optional[List[str]] = None,
        limit: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fetch quality examples from enhanced-memory

        Args:
            query: Search query for relevant examples
            context_tags: Context tags for filtering
            limit: Maximum examples to retrieve

        Returns:
            List of example dictionaries
        """
        if not self.memory_client:
            logger.warning("No memory client configured, using built-in examples")
            return self._get_builtin_examples(context_tags, limit)

        try:
            # This would call enhanced-memory MCP
            # results = await self.memory_client.search_nodes(query, limit=limit)
            logger.info(f"Would fetch {limit} examples for: {query}")
            return self._get_builtin_examples(context_tags, limit)

        except Exception as e:
            logger.error(f"Failed to fetch from memory: {e}")
            return self._get_builtin_examples(context_tags, limit)

    def _get_builtin_examples(
        self,
        context_tags: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get built-in high-quality examples"""
        examples = {
            "analysis": [
                {
                    "type": "thorough_analysis",
                    "content": """Problem: System latency increased by 200%

Analysis Process:
1. Gathered baseline metrics from monitoring
2. Identified correlation with deployment timestamp
3. Reviewed code changes in that deployment
4. Found database query modification adding full table scan
5. Tested query performance in isolation
6. Verified fix reduces latency to baseline

This demonstrates: systematic investigation, evidence gathering,
correlation analysis, hypothesis testing, and verification."""
                }
            ],
            "debug": [
                {
                    "type": "systematic_debugging",
                    "content": """Bug: Race condition in payment processing

Debug Process:
1. Reproduced issue consistently (10/10 attempts)
2. Added detailed logging at each step
3. Identified two threads accessing shared state
4. Traced execution timeline showing interleaving
5. Added synchronization primitive
6. Verified fix (0/100 failures in testing)

This demonstrates: reproducibility, instrumentation,
root cause identification, targeted fix, thorough validation."""
                }
            ]
        }

        # Select examples based on context tags
        selected = []
        context_tags = context_tags or []

        for tag in context_tags:
            if tag in examples:
                selected.extend(examples[tag][:limit])

        # Default examples if no context match
        if not selected:
            selected = examples["analysis"][:limit]

        return selected[:limit]

    def build_priming_block(self, examples: List[Dict[str, Any]]) -> str:
        """
        Build reference class priming block

        Args:
            examples: List of example dictionaries

        Returns:
            Priming block text
        """
        if not examples:
            return ""

        block = "REFERENCE EXAMPLES (quality bar):\n\n"

        for i, example in enumerate(examples, 1):
            block += f"Example {i} ({example.get('type', 'unknown')}):\n"
            block += f"{example.get('content', '')}\n\n"

        block += "Your response should match or exceed this level of thoroughness.\n"

        return block


class ZeroShotCoT:
    """
    Zero-Shot Chain of Thought - Blank templates

    Provides structured templates that trigger automatic problem
    decomposition and step-by-step reasoning.
    """

    # Problem-specific CoT templates
    TEMPLATES = {
        "analysis": """Let's analyze this problem step by step:

1. UNDERSTANDING THE PROBLEM
   - What is the core issue?
   - What are the symptoms?
   - What are the constraints?

2. GATHERING INFORMATION
   - What data do we have?
   - What data is missing?
   - What assumptions are we making?

3. IDENTIFYING CAUSES
   - What are potential root causes?
   - How can we verify each cause?
   - What evidence supports/contradicts each?

4. EVALUATING SOLUTIONS
   - What are possible approaches?
   - What are the tradeoffs?
   - What are the risks?

5. RECOMMENDATION
   - What is the best approach?
   - Why is it best?
   - What are next steps?
""",

        "debug": """Let's debug this systematically:

1. REPRODUCE THE ISSUE
   - Can we reproduce it consistently?
   - What are the exact steps?
   - What is the expected vs actual behavior?

2. ISOLATE THE PROBLEM
   - Where in the codebase is the issue?
   - What changed recently?
   - What logs/errors do we have?

3. FORM HYPOTHESES
   - What could cause this behavior?
   - How can we test each hypothesis?
   - What evidence do we need?

4. TEST HYPOTHESES
   - Test each hypothesis systematically
   - Document results
   - Eliminate possibilities

5. VERIFY FIX
   - Implement the fix
   - Test thoroughly
   - Confirm issue resolved
""",

        "design": """Let's design this solution step by step:

1. REQUIREMENTS
   - What are functional requirements?
   - What are non-functional requirements?
   - What are constraints?

2. ARCHITECTURE
   - What are the major components?
   - How do they interact?
   - What are the interfaces?

3. DATA MODEL
   - What data needs to be stored?
   - What are the relationships?
   - What are access patterns?

4. ALGORITHMS
   - What are the core algorithms?
   - What is the complexity?
   - What are edge cases?

5. IMPLEMENTATION PLAN
   - What is the development sequence?
   - What are milestones?
   - What are risks?
""",

        "optimization": """Let's optimize this systematically:

1. BASELINE MEASUREMENT
   - What is current performance?
   - What are the bottlenecks?
   - What are the metrics?

2. IDENTIFY OPPORTUNITIES
   - Where is time/resources spent?
   - What are low-hanging fruit?
   - What are high-impact changes?

3. DESIGN OPTIMIZATIONS
   - What optimizations can we apply?
   - What are expected improvements?
   - What are the tradeoffs?

4. IMPLEMENT AND MEASURE
   - Implement changes
   - Measure actual improvements
   - Compare to baseline

5. VALIDATE
   - Does it maintain correctness?
   - Are there side effects?
   - Is the improvement worth the complexity?
""",

        "planning": """Let's plan this project step by step:

1. DEFINE SCOPE
   - What are we building?
   - What is in scope?
   - What is out of scope?

2. BREAK DOWN WORK
   - What are major milestones?
   - What are tasks for each milestone?
   - What are dependencies?

3. ESTIMATE EFFORT
   - How long will each task take?
   - What is the critical path?
   - What is total timeline?

4. IDENTIFY RISKS
   - What could go wrong?
   - What are mitigations?
   - What are contingencies?

5. RESOURCE ALLOCATION
   - Who does what?
   - What tools are needed?
   - What is the schedule?
"""
    }

    @staticmethod
    def build_cot_prompt(problem: str, template_type: str = "analysis") -> str:
        """
        Build Chain of Thought prompt

        Args:
            problem: Problem to solve
            template_type: Template to use (analysis/debug/design/optimization/planning)

        Returns:
            CoT prompt text
        """
        template = ZeroShotCoT.TEMPLATES.get(
            template_type,
            ZeroShotCoT.TEMPLATES["analysis"]
        )

        prompt = f"""PROBLEM:
{problem}

{template}

Work through each step thoroughly. Fill in details for each section.
"""

        return prompt


class ReasoningScaffoldOrchestrator:
    """
    Orchestrates multiple scaffolding techniques

    Combines over-instruction, reference priming, and CoT
    for maximum reasoning quality.
    """

    def __init__(self, memory_client: Optional[Any] = None):
        """
        Initialize orchestrator

        Args:
            memory_client: Enhanced-memory client for examples
        """
        self.reference_priming = ReferenceClassPriming(memory_client)
        logger.info("ReasoningScaffoldOrchestrator initialized")

    async def build_scaffold(
        self,
        problem: str,
        scaffold_type: ScaffoldType = ScaffoldType.HYBRID,
        context_tags: Optional[List[str]] = None,
        template_type: str = "analysis",
        include_examples: bool = True,
        example_limit: int = 2
    ) -> str:
        """
        Build comprehensive reasoning scaffold

        Args:
            problem: Problem to solve
            scaffold_type: Type of scaffold to build
            context_tags: Context tags for customization
            template_type: CoT template type
            include_examples: Whether to include reference examples
            example_limit: Maximum examples

        Returns:
            Complete scaffold text
        """
        context_tags = context_tags or []

        scaffold_parts = []

        # Over-instruction (always include for hybrid)
        if scaffold_type in [ScaffoldType.OVER_INSTRUCTION, ScaffoldType.HYBRID]:
            instruction_block = DeliberateOverInstruction.build_instruction_block(
                context_tags, emphasis="strong"
            )
            scaffold_parts.append(instruction_block)

        # Reference priming
        if scaffold_type in [ScaffoldType.REFERENCE_PRIMING, ScaffoldType.HYBRID]:
            if include_examples:
                examples = await self.reference_priming.fetch_examples_from_memory(
                    query=problem[:100],  # Use problem as query
                    context_tags=context_tags,
                    limit=example_limit
                )
                if examples:
                    priming_block = self.reference_priming.build_priming_block(examples)
                    scaffold_parts.append(priming_block)

        # Zero-shot CoT
        if scaffold_type in [ScaffoldType.ZERO_SHOT_COT, ScaffoldType.HYBRID]:
            cot_prompt = ZeroShotCoT.build_cot_prompt(problem, template_type)
            scaffold_parts.append(cot_prompt)

        # Combine all parts
        full_scaffold = "\n\n".join(scaffold_parts)

        logger.info(f"Built {scaffold_type.value} scaffold ({len(full_scaffold)} chars)")

        return full_scaffold


# Convenience functions for common usage patterns

async def build_full_scaffold(
    problem: str,
    context_tags: Optional[List[str]] = None,
    template_type: str = "analysis",
    memory_client: Optional[Any] = None
) -> str:
    """
    Build full hybrid scaffold with all techniques

    Args:
        problem: Problem to solve
        context_tags: Context tags
        template_type: CoT template type
        memory_client: Enhanced-memory client

    Returns:
        Complete scaffold
    """
    orchestrator = ReasoningScaffoldOrchestrator(memory_client)
    return await orchestrator.build_scaffold(
        problem=problem,
        scaffold_type=ScaffoldType.HYBRID,
        context_tags=context_tags,
        template_type=template_type
    )


async def build_over_instructed_prompt(
    problem: str,
    context_tags: Optional[List[str]] = None
) -> str:
    """Build prompt with over-instruction only"""
    orchestrator = ReasoningScaffoldOrchestrator()
    return await orchestrator.build_scaffold(
        problem=problem,
        scaffold_type=ScaffoldType.OVER_INSTRUCTION,
        context_tags=context_tags
    )


async def build_primed_prompt(
    problem: str,
    context_tags: Optional[List[str]] = None,
    memory_client: Optional[Any] = None
) -> str:
    """Build prompt with reference priming only"""
    orchestrator = ReasoningScaffoldOrchestrator(memory_client)
    return await orchestrator.build_scaffold(
        problem=problem,
        scaffold_type=ScaffoldType.REFERENCE_PRIMING,
        context_tags=context_tags
    )


async def build_cot_prompt(
    problem: str,
    template_type: str = "analysis"
) -> str:
    """Build prompt with CoT template only"""
    orchestrator = ReasoningScaffoldOrchestrator()
    return await orchestrator.build_scaffold(
        problem=problem,
        scaffold_type=ScaffoldType.ZERO_SHOT_COT,
        template_type=template_type
    )
