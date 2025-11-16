#!/usr/bin/env python3
"""
Meta-Prompting Framework
========================

Enables agents to design their own optimal prompts before executing tasks.
Leverages the model's absorbed prompt engineering knowledge for self-optimization.

Key Components:
- MetaPrompter: Designs optimal prompts for tasks
- PromptOptimizer: Recursive refinement (constraints → ambiguities → depth)
- ReversePrompter: Analyze → Design → Execute workflow

Usage:
    meta_prompter = MetaPrompter()
    optimizer = PromptOptimizer(meta_prompter)
    reverse = ReversePrompter(meta_prompter, optimizer)

    result = await reverse.execute(
        task="Optimize database query",
        context={'framework': 'PostgreSQL'},
        optimize=True
    )
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# Add SDK agents to path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk_agents"))
from cli_agent import CLIAgent

logger = logging.getLogger(__name__)


class OptimizationPhase(Enum):
    """Phases of prompt optimization"""
    CONSTRAINTS = "constraints"
    AMBIGUITIES = "ambiguities"
    DEPTH = "depth"


@dataclass
class DesignedPrompt:
    """A prompt designed by the meta-prompter"""
    original_task: str
    designed_prompt: str
    design_rationale: str
    estimated_quality: float = 0.0
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MetaPromptResult:
    """Complete meta-prompting execution result"""
    task: str
    designed_prompt: DesignedPrompt
    execution_result: Optional[str] = None
    optimized_prompt: Optional[str] = None
    total_iterations: int = 0
    success: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class MetaPrompter:
    """
    Meta-Prompter - Designs optimal prompts for tasks

    Leverages model's absorbed prompt engineering knowledge to
    design better prompts than humans would write manually.
    """

    def __init__(self, cli_tool: str = "gemini"):
        """
        Initialize MetaPrompter

        Args:
            cli_tool: CLI tool to use (gemini, codex, claude)
        """
        self.cli_tool = cli_tool
        self.design_history: List[DesignedPrompt] = []
        logger.info(f"MetaPrompter initialized with {cli_tool}")

    async def design_prompt(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        quality_criteria: Optional[List[str]] = None,
        agent: Optional[CLIAgent] = None
    ) -> DesignedPrompt:
        """
        Design an optimal prompt for the given task

        Args:
            task: The task to create a prompt for
            context: Additional context about the task
            quality_criteria: Specific quality requirements
            agent: Optional agent instance for CLI execution

        Returns:
            DesignedPrompt with optimized prompt and rationale
        """
        logger.info(f"Designing prompt for task: {task[:100]}")

        context = context or {}
        quality_criteria = quality_criteria or ["clear", "specific", "actionable"]

        # Create meta-prompt that asks the model to design a prompt
        meta_prompt = f"""You are a prompt engineering expert. Design an optimal prompt for this task:

TASK: {task}

CONTEXT:
{json.dumps(context, indent=2)}

QUALITY CRITERIA:
{', '.join(quality_criteria)}

Your job is to design the BEST POSSIBLE PROMPT that will:
1. Clearly specify what needs to be done
2. Include all necessary context and constraints
3. Guide the model toward high-quality output
4. Avoid ambiguities and edge cases
5. Structure the task for optimal reasoning

Provide your designed prompt in this format:
DESIGNED PROMPT:
<your optimized prompt here>

DESIGN RATIONALE:
<explanation of why this prompt will work well>

ESTIMATED QUALITY: <0.0-1.0>
"""

        response = await self._run_cli(meta_prompt, agent)

        # Parse response
        designed_prompt_text = self._extract_section(response, "DESIGNED PROMPT:")
        rationale = self._extract_section(response, "DESIGN RATIONALE:")
        quality = self._extract_quality(response)

        designed_prompt = DesignedPrompt(
            original_task=task,
            designed_prompt=designed_prompt_text or response,
            design_rationale=rationale or "No rationale provided",
            estimated_quality=quality
        )

        self.design_history.append(designed_prompt)
        logger.info(f"Prompt designed with estimated quality: {quality:.2f}")

        return designed_prompt

    async def _run_cli(self, prompt: str, agent: Optional[CLIAgent]) -> str:
        """Run CLI tool to process prompt"""
        if agent:
            try:
                result = agent.run_headless_cli(prompt, format="text")
                if result.get("status") == "success":
                    return result.get("output", "")
            except Exception as e:
                logger.error(f"Agent CLI execution failed: {e}")

        # Fallback to direct CLI execution
        import subprocess
        try:
            result = subprocess.run(
                [self.cli_tool, prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"CLI execution failed: {e}")
            return f"ERROR: {e}"

    def _extract_section(self, response: str, marker: str) -> Optional[str]:
        """Extract section from response"""
        if marker not in response:
            return None

        parts = response.split(marker, 1)
        if len(parts) < 2:
            return None

        # Get text until next marker or end
        text = parts[1].strip()

        # Find next section marker
        next_markers = ["DESIGN RATIONALE:", "ESTIMATED QUALITY:", "DESIGNED PROMPT:"]
        for next_marker in next_markers:
            if next_marker != marker and next_marker in text:
                text = text.split(next_marker)[0].strip()
                break

        return text

    def _extract_quality(self, response: str) -> float:
        """Extract quality score from response"""
        import re

        patterns = [
            r'ESTIMATED QUALITY[:\s]+([0-9.]+)',
            r'quality[:\s]+([0-9.]+)',
            r'([0-9.]+)/1\.0'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if value > 1.0:
                    value = value / 10.0  # Convert 8/10 to 0.8
                return value

        return 0.7  # Default moderate quality


class PromptOptimizer:
    """
    Prompt Optimizer - Recursive refinement of prompts

    Three-phase optimization:
    1. CONSTRAINTS - Add specifications and constraints
    2. AMBIGUITIES - Resolve unclear terms
    3. DEPTH - Increase detail and context
    """

    def __init__(self, meta_prompter: MetaPrompter):
        """
        Initialize PromptOptimizer

        Args:
            meta_prompter: MetaPrompter instance to use
        """
        self.meta_prompter = meta_prompter
        self.optimization_history: List[Dict[str, Any]] = []
        logger.info("PromptOptimizer initialized")

    async def optimize(
        self,
        designed_prompt: DesignedPrompt,
        max_iterations: int = 3,
        target_quality: float = 0.9,
        agent: Optional[CLIAgent] = None
    ) -> tuple[DesignedPrompt, List[Dict[str, Any]]]:
        """
        Optimize a designed prompt through multiple phases

        Args:
            designed_prompt: Initial designed prompt
            max_iterations: Maximum optimization iterations
            target_quality: Target quality score (0.0-1.0)
            agent: Optional agent instance

        Returns:
            (optimized_prompt, optimization_history)
        """
        logger.info(f"Optimizing prompt (target quality: {target_quality:.2f})")

        current_prompt = designed_prompt
        history = []

        phases = [
            OptimizationPhase.CONSTRAINTS,
            OptimizationPhase.AMBIGUITIES,
            OptimizationPhase.DEPTH
        ]

        for i, phase in enumerate(phases[:max_iterations]):
            if current_prompt.estimated_quality >= target_quality:
                logger.info(f"Target quality reached after {i} iterations")
                break

            logger.info(f"Optimization phase {i+1}/{max_iterations}: {phase.value}")

            optimized = await self._optimize_phase(current_prompt, phase, agent)

            history.append({
                "iteration": i + 1,
                "phase": phase.value,
                "before_quality": current_prompt.estimated_quality,
                "after_quality": optimized.estimated_quality,
                "improvement": optimized.estimated_quality - current_prompt.estimated_quality
            })

            current_prompt = optimized

        self.optimization_history.extend(history)
        logger.info(f"Optimization complete: quality {current_prompt.estimated_quality:.2f}")

        return current_prompt, history

    async def _optimize_phase(
        self,
        prompt: DesignedPrompt,
        phase: OptimizationPhase,
        agent: Optional[CLIAgent]
    ) -> DesignedPrompt:
        """Optimize prompt for specific phase"""

        phase_prompts = {
            OptimizationPhase.CONSTRAINTS: """Improve this prompt by adding specifications and constraints:

CURRENT PROMPT:
{prompt}

Add:
1. Explicit format requirements
2. Scope boundaries
3. Quality constraints
4. Output specifications
5. Edge case handling

IMPROVED PROMPT:
""",
            OptimizationPhase.AMBIGUITIES: """Improve this prompt by resolving ambiguities:

CURRENT PROMPT:
{prompt}

Clarify:
1. Ambiguous terms
2. Unclear requirements
3. Assumed context
4. Implicit expectations
5. Vague objectives

IMPROVED PROMPT:
""",
            OptimizationPhase.DEPTH: """Improve this prompt by increasing depth and context:

CURRENT PROMPT:
{prompt}

Add:
1. Background information
2. Relevant examples
3. Success criteria
4. Process guidelines
5. Context depth

IMPROVED PROMPT:
"""
        }

        optimization_prompt = phase_prompts[phase].format(
            prompt=prompt.designed_prompt
        )

        response = await self.meta_prompter._run_cli(optimization_prompt, agent)

        # Extract improved prompt
        improved_text = self._extract_improved_prompt(response)

        # Estimate new quality (incremental improvement)
        new_quality = min(prompt.estimated_quality + 0.1, 1.0)

        optimized = DesignedPrompt(
            original_task=prompt.original_task,
            designed_prompt=improved_text,
            design_rationale=f"Optimized for {phase.value}: {prompt.design_rationale}",
            estimated_quality=new_quality,
            optimization_history=prompt.optimization_history + [phase.value]
        )

        return optimized

    def _extract_improved_prompt(self, response: str) -> str:
        """Extract improved prompt from response"""
        markers = ["IMPROVED PROMPT:", "OPTIMIZED PROMPT:", "ENHANCED PROMPT:"]

        for marker in markers:
            if marker in response:
                parts = response.split(marker, 1)
                if len(parts) > 1:
                    return parts[1].strip()

        # If no marker, return whole response
        return response.strip()


class ReversePrompter:
    """
    Reverse Prompter - Analyze → Design → Execute workflow

    Instead of executing directly, first:
    1. Analyze what the task really needs
    2. Design an optimal prompt
    3. Optionally optimize the prompt
    4. Execute with the optimized prompt
    """

    def __init__(
        self,
        meta_prompter: MetaPrompter,
        optimizer: Optional[PromptOptimizer] = None
    ):
        """
        Initialize ReversePrompter

        Args:
            meta_prompter: MetaPrompter instance
            optimizer: Optional PromptOptimizer instance
        """
        self.meta_prompter = meta_prompter
        self.optimizer = optimizer or PromptOptimizer(meta_prompter)
        self.execution_history: List[MetaPromptResult] = []
        logger.info("ReversePrompter initialized")

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        use_memory: bool = True,
        optimize: bool = True,
        agent: Optional[CLIAgent] = None
    ) -> MetaPromptResult:
        """
        Execute task using reverse prompting workflow

        Args:
            task: The task to execute
            context: Additional context
            use_memory: Whether to check memory for similar prompts
            optimize: Whether to optimize the designed prompt
            agent: Optional agent instance

        Returns:
            MetaPromptResult with execution details
        """
        logger.info(f"Reverse prompting for task: {task[:100]}")

        # Phase 1: Analyze task
        analysis = await self._analyze_task(task, context, agent)
        logger.info(f"Task analysis complete")

        # Phase 2: Design prompt
        designed_prompt = await self.meta_prompter.design_prompt(
            task, context, agent=agent
        )
        logger.info(f"Prompt designed: quality {designed_prompt.estimated_quality:.2f}")

        # Phase 3: Optimize (if requested)
        optimization_history = []
        if optimize:
            designed_prompt, optimization_history = await self.optimizer.optimize(
                designed_prompt, agent=agent
            )
            logger.info(f"Prompt optimized: {len(optimization_history)} iterations")

        # Phase 4: Execute with optimized prompt
        execution_result = await self._execute_with_prompt(
            task, designed_prompt.designed_prompt, agent
        )
        logger.info(f"Execution complete")

        result = MetaPromptResult(
            task=task,
            designed_prompt=designed_prompt,
            execution_result=execution_result,
            optimized_prompt=designed_prompt.designed_prompt if optimize else None,
            total_iterations=len(optimization_history),
            success=bool(execution_result)
        )

        self.execution_history.append(result)

        # Store in memory if available and use_memory is True
        if use_memory:
            await self._store_in_memory(result)

        return result

    async def _analyze_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        agent: Optional[CLIAgent]
    ) -> Dict[str, Any]:
        """Analyze what the task really needs"""
        analysis_prompt = f"""Analyze this task to understand what it really needs:

TASK: {task}

CONTEXT: {json.dumps(context or {}, indent=2)}

Provide analysis:
1. Core objective
2. Key requirements
3. Success criteria
4. Potential challenges
5. Recommended approach
"""

        response = await self.meta_prompter._run_cli(analysis_prompt, agent)

        return {
            "analysis": response,
            "task": task,
            "context": context
        }

    async def _execute_with_prompt(
        self,
        task: str,
        prompt: str,
        agent: Optional[CLIAgent]
    ) -> str:
        """Execute the task using the optimized prompt"""
        execution_prompt = f"""{prompt}

Execute this task now and provide the complete result.
"""

        result = await self.meta_prompter._run_cli(execution_prompt, agent)
        return result

    async def _store_in_memory(self, result: MetaPromptResult):
        """Store successful prompts in memory for reuse"""
        try:
            # Store in simple JSON file (enhanced-memory integration would go here)
            storage_path = Path("/mnt/agentic-system/databases/mcp/meta_prompts.json")
            storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing
            if storage_path.exists():
                with open(storage_path, 'r') as f:
                    stored_prompts = json.load(f)
            else:
                stored_prompts = []

            # Add new prompt
            stored_prompts.append({
                "task": result.task,
                "prompt": result.designed_prompt.designed_prompt,
                "quality": result.designed_prompt.estimated_quality,
                "timestamp": result.timestamp.isoformat(),
                "success": result.success
            })

            # Save
            with open(storage_path, 'w') as f:
                json.dump(stored_prompts, f, indent=2)

            logger.info(f"Stored prompt in memory: {storage_path}")

        except Exception as e:
            logger.error(f"Failed to store in memory: {e}")
