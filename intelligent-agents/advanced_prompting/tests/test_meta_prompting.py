#!/usr/bin/env python3
"""
Unit tests for Meta-Prompting framework
"""

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from advanced_prompting import (
    MetaPrompter,
    PromptOptimizer,
    ReversePrompter,
    DesignedPrompt,
    MetaPromptResult
)


class TestMetaPrompter:
    """Test suite for MetaPrompter"""

    @pytest.fixture
    def meta_prompter(self):
        """Create a MetaPrompter instance"""
        return MetaPrompter(cli_tool="gemini")

    def test_initialization(self, meta_prompter):
        """Test meta prompter initialization"""
        assert meta_prompter.cli_tool == "gemini"
        assert len(meta_prompter.design_history) == 0

    @pytest.mark.asyncio
    async def test_design_prompt(self, meta_prompter):
        """Test prompt design"""
        task = "Optimize database query performance"
        context = {"framework": "PostgreSQL", "current_latency": "2.3s"}

        designed = await meta_prompter.design_prompt(task, context)

        assert isinstance(designed, DesignedPrompt)
        assert designed.original_task == task
        assert len(designed.designed_prompt) > 0
        assert 0.0 <= designed.estimated_quality <= 1.0

    @pytest.mark.asyncio
    async def test_design_with_quality_criteria(self, meta_prompter):
        """Test prompt design with quality criteria"""
        task = "Write unit tests"
        criteria = ["comprehensive", "clear", "maintainable"]

        designed = await meta_prompter.design_prompt(
            task, quality_criteria=criteria
        )

        assert isinstance(designed, DesignedPrompt)
        assert designed.original_task == task

    def test_design_history(self, meta_prompter):
        """Test that design history is recorded"""
        initial_count = len(meta_prompter.design_history)
        # After async design, history should increase
        assert initial_count == 0

    def test_extract_quality(self, meta_prompter):
        """Test quality score extraction"""
        response1 = "ESTIMATED QUALITY: 0.9"
        assert meta_prompter._extract_quality(response1) == 0.9

        response2 = "quality: 0.75"
        assert meta_prompter._extract_quality(response2) == 0.75


class TestPromptOptimizer:
    """Test suite for PromptOptimizer"""

    @pytest.fixture
    def optimizer(self):
        """Create a PromptOptimizer instance"""
        meta_prompter = MetaPrompter()
        return PromptOptimizer(meta_prompter)

    @pytest.mark.asyncio
    async def test_optimize_prompt(self, optimizer):
        """Test prompt optimization"""
        designed = DesignedPrompt(
            original_task="Test task",
            designed_prompt="Initial prompt",
            design_rationale="Test rationale",
            estimated_quality=0.6
        )

        optimized, history = await optimizer.optimize(
            designed, max_iterations=2, target_quality=0.9
        )

        assert isinstance(optimized, DesignedPrompt)
        assert len(history) > 0
        assert optimized.estimated_quality >= designed.estimated_quality

    @pytest.mark.asyncio
    async def test_optimization_phases(self, optimizer):
        """Test optimization phases"""
        designed = DesignedPrompt(
            original_task="Test",
            designed_prompt="Prompt",
            design_rationale="Rationale",
            estimated_quality=0.5
        )

        optimized, history = await optimizer.optimize(designed, max_iterations=3)

        # Should have phase information
        assert len(history) <= 3
        for iteration in history:
            assert "phase" in iteration
            assert "improvement" in iteration


class TestReversePrompter:
    """Test suite for ReversePrompter"""

    @pytest.fixture
    def reverse_prompter(self):
        """Create a ReversePrompter instance"""
        meta_prompter = MetaPrompter()
        optimizer = PromptOptimizer(meta_prompter)
        return ReversePrompter(meta_prompter, optimizer)

    def test_initialization(self, reverse_prompter):
        """Test reverse prompter initialization"""
        assert reverse_prompter.meta_prompter is not None
        assert reverse_prompter.optimizer is not None
        assert len(reverse_prompter.execution_history) == 0

    @pytest.mark.asyncio
    async def test_execute_task(self, reverse_prompter):
        """Test task execution with reverse prompting"""
        task = "Analyze code quality"
        context = {"language": "Python", "files": 10}

        result = await reverse_prompter.execute(
            task, context, use_memory=False, optimize=False
        )

        assert isinstance(result, MetaPromptResult)
        assert result.task == task
        assert result.designed_prompt is not None
        assert isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_execute_with_optimization(self, reverse_prompter):
        """Test execution with optimization enabled"""
        task = "Refactor legacy code"

        result = await reverse_prompter.execute(
            task, optimize=True, use_memory=False
        )

        assert isinstance(result, MetaPromptResult)
        assert result.total_iterations > 0 if result.optimized_prompt else True

    @pytest.mark.asyncio
    async def test_execution_history(self, reverse_prompter):
        """Test execution history recording"""
        initial_count = len(reverse_prompter.execution_history)

        await reverse_prompter.execute(
            "Test task", use_memory=False, optimize=False
        )

        assert len(reverse_prompter.execution_history) == initial_count + 1


def test_designed_prompt_dataclass():
    """Test DesignedPrompt dataclass"""
    prompt = DesignedPrompt(
        original_task="Test task",
        designed_prompt="Designed prompt text",
        design_rationale="Because it's better",
        estimated_quality=0.85
    )

    assert prompt.original_task == "Test task"
    assert prompt.designed_prompt == "Designed prompt text"
    assert prompt.estimated_quality == 0.85
    assert len(prompt.optimization_history) == 0


def test_meta_prompt_result_dataclass():
    """Test MetaPromptResult dataclass"""
    designed = DesignedPrompt(
        original_task="Task",
        designed_prompt="Prompt",
        design_rationale="Rationale",
        estimated_quality=0.8
    )

    result = MetaPromptResult(
        task="Task",
        designed_prompt=designed,
        execution_result="Result",
        success=True,
        total_iterations=3
    )

    assert result.task == "Task"
    assert result.success is True
    assert result.total_iterations == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
