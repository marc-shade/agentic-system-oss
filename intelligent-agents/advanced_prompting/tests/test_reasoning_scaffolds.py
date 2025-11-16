#!/usr/bin/env python3
"""
Unit tests for Reasoning Scaffolds framework
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from advanced_prompting import (
    DeliberateOverInstruction,
    ReferenceClassPriming,
    ZeroShotCoT,
    ReasoningScaffoldOrchestrator,
    ScaffoldType,
    build_full_scaffold
)


class TestDeliberateOverInstruction:
    """Test suite for DeliberateOverInstruction"""

    def test_build_instruction_block(self):
        """Test instruction block building"""
        block = DeliberateOverInstruction.build_instruction_block()

        assert len(block) > 0
        assert "REASONING REQUIREMENTS" in block
        assert "DO NOT SUMMARIZE" in block or "Avoid summarizing" in block

    def test_instruction_emphasis_levels(self):
        """Test different emphasis levels"""
        strong = DeliberateOverInstruction.build_instruction_block(emphasis="strong")
        moderate = DeliberateOverInstruction.build_instruction_block(emphasis="moderate")
        subtle = DeliberateOverInstruction.build_instruction_block(emphasis="subtle")

        assert "DO NOT SUMMARIZE" in strong
        assert len(strong) > len(subtle)

    def test_context_specific_instructions(self):
        """Test context-specific directives"""
        debug_block = DeliberateOverInstruction.build_instruction_block(
            context_tags=["debug"]
        )
        assert "THINK" in debug_block.upper() or "think aloud" in debug_block.lower()

        planning_block = DeliberateOverInstruction.build_instruction_block(
            context_tags=["planning"]
        )
        assert "ENUMERATE" in planning_block.upper() or "enumerate" in planning_block.lower()


class TestReferenceClassPriming:
    """Test suite for ReferenceClassPriming"""

    @pytest.fixture
    def priming(self):
        """Create ReferenceClassPriming instance"""
        return ReferenceClassPriming(memory_client=None)

    @pytest.mark.asyncio
    async def test_fetch_examples(self, priming):
        """Test example fetching"""
        examples = await priming.fetch_examples_from_memory(
            query="debugging",
            context_tags=["debug"],
            limit=2
        )

        assert isinstance(examples, list)
        assert len(examples) <= 2
        if len(examples) > 0:
            assert "type" in examples[0]
            assert "content" in examples[0]

    def test_build_priming_block(self, priming):
        """Test priming block building"""
        examples = [
            {"type": "analysis", "content": "Example analysis process"}
        ]

        block = priming.build_priming_block(examples)

        assert len(block) > 0
        assert "REFERENCE EXAMPLES" in block
        assert "Example analysis process" in block

    def test_empty_priming_block(self, priming):
        """Test priming block with no examples"""
        block = priming.build_priming_block([])
        assert block == ""


class TestZeroShotCoT:
    """Test suite for ZeroShotCoT"""

    def test_build_cot_prompt_analysis(self):
        """Test CoT prompt for analysis"""
        problem = "System experiencing high latency"
        prompt = ZeroShotCoT.build_cot_prompt(problem, "analysis")

        assert problem in prompt
        assert "UNDERSTANDING THE PROBLEM" in prompt
        assert "GATHERING INFORMATION" in prompt
        assert "RECOMMENDATION" in prompt

    def test_build_cot_prompt_debug(self):
        """Test CoT prompt for debugging"""
        problem = "Race condition in payment processing"
        prompt = ZeroShotCoT.build_cot_prompt(problem, "debug")

        assert problem in prompt
        assert "REPRODUCE THE ISSUE" in prompt
        assert "VERIFY FIX" in prompt

    def test_build_cot_prompt_design(self):
        """Test CoT prompt for design"""
        problem = "Design authentication system"
        prompt = ZeroShotCoT.build_cot_prompt(problem, "design")

        assert problem in prompt
        assert "REQUIREMENTS" in prompt
        assert "ARCHITECTURE" in prompt

    def test_all_template_types(self):
        """Test all template types are valid"""
        templates = ["analysis", "debug", "design", "optimization", "planning"]

        for template_type in templates:
            prompt = ZeroShotCoT.build_cot_prompt("Test problem", template_type)
            assert len(prompt) > 0
            assert "Test problem" in prompt


class TestReasoningScaffoldOrchestrator:
    """Test suite for ReasoningScaffoldOrchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance"""
        return ReasoningScaffoldOrchestrator(memory_client=None)

    @pytest.mark.asyncio
    async def test_build_hybrid_scaffold(self, orchestrator):
        """Test building hybrid scaffold"""
        scaffold = await orchestrator.build_scaffold(
            problem="Debug memory leak",
            scaffold_type=ScaffoldType.HYBRID,
            context_tags=["debug"],
            template_type="debug"
        )

        assert len(scaffold) > 0
        # Should contain over-instruction
        assert "REASONING REQUIREMENTS" in scaffold or "DO NOT" in scaffold.upper()
        # Should contain CoT template
        assert "REPRODUCE" in scaffold.upper() or "ISOLATE" in scaffold.upper()

    @pytest.mark.asyncio
    async def test_build_over_instruction_only(self, orchestrator):
        """Test over-instruction only scaffold"""
        scaffold = await orchestrator.build_scaffold(
            problem="Test",
            scaffold_type=ScaffoldType.OVER_INSTRUCTION
        )

        assert "REASONING REQUIREMENTS" in scaffold

    @pytest.mark.asyncio
    async def test_build_cot_only(self, orchestrator):
        """Test CoT only scaffold"""
        scaffold = await orchestrator.build_scaffold(
            problem="Test optimization",
            scaffold_type=ScaffoldType.ZERO_SHOT_COT,
            template_type="optimization"
        )

        assert "BASELINE MEASUREMENT" in scaffold

    @pytest.mark.asyncio
    async def test_build_with_examples(self, orchestrator):
        """Test scaffold with examples included"""
        scaffold = await orchestrator.build_scaffold(
            problem="Test",
            scaffold_type=ScaffoldType.HYBRID,
            include_examples=True,
            example_limit=2
        )

        assert len(scaffold) > 0


class TestHelperFunctions:
    """Test helper functions"""

    @pytest.mark.asyncio
    async def test_build_full_scaffold(self):
        """Test build_full_scaffold helper"""
        scaffold = await build_full_scaffold(
            problem="Test problem",
            context_tags=["analysis"],
            template_type="analysis"
        )

        assert len(scaffold) > 0
        assert isinstance(scaffold, str)


def test_scaffold_types():
    """Test scaffold type enum"""
    assert ScaffoldType.OVER_INSTRUCTION.value == "over_instruction"
    assert ScaffoldType.REFERENCE_PRIMING.value == "reference_priming"
    assert ScaffoldType.ZERO_SHOT_COT.value == "zero_shot_cot"
    assert ScaffoldType.HYBRID.value == "hybrid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
