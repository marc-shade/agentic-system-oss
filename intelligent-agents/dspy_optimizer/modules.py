#!/usr/bin/env python3
"""
Reusable DSPy Modules
=====================

Production-ready DSPy modules for common agentic tasks:
- ChainOfThought reasoning
- ReAct agents
- Code analysis
- Prompt evolution
"""

import dspy
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ====================
# Signature Definitions
# ====================

class ReasoningSignature(dspy.Signature):
    """Signature for step-by-step reasoning"""
    context: str = dspy.InputField(desc="Background context and relevant information")
    question: str = dspy.InputField(desc="The question or task to reason about")
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning process")
    answer: str = dspy.OutputField(desc="Final answer or conclusion")


class CodeAnalysisSignature(dspy.Signature):
    """Signature for code analysis tasks"""
    code: str = dspy.InputField(desc="Source code to analyze")
    analysis_type: str = dspy.InputField(desc="Type of analysis: security, performance, style, bugs")
    analysis: str = dspy.OutputField(desc="Detailed analysis findings")
    recommendations: str = dspy.OutputField(desc="Specific improvement recommendations")
    severity: str = dspy.OutputField(desc="Overall severity: low, medium, high, critical")


class PromptEvolutionSignature(dspy.Signature):
    """Signature for evolving prompts"""
    original_prompt: str = dspy.InputField(desc="The current prompt to improve")
    performance_data: str = dspy.InputField(desc="Performance metrics and feedback")
    task_description: str = dspy.InputField(desc="What the prompt should accomplish")
    evolved_prompt: str = dspy.OutputField(desc="Improved version of the prompt")
    changes_made: str = dspy.OutputField(desc="Summary of changes and rationale")
    expected_improvement: str = dspy.OutputField(desc="Expected performance improvement")


class TaskDecompositionSignature(dspy.Signature):
    """Signature for breaking down complex tasks"""
    task: str = dspy.InputField(desc="Complex task to decompose")
    constraints: str = dspy.InputField(desc="Constraints and requirements")
    subtasks: str = dspy.OutputField(desc="List of atomic subtasks in execution order")
    dependencies: str = dspy.OutputField(desc="Dependencies between subtasks")
    estimated_complexity: str = dspy.OutputField(desc="Complexity estimate for each subtask")


class ReActSignature(dspy.Signature):
    """Signature for ReAct-style reasoning and acting"""
    context: str = dspy.InputField(desc="Current context and state")
    goal: str = dspy.InputField(desc="Goal to achieve")
    available_tools: str = dspy.InputField(desc="Available tools and their descriptions")
    thought: str = dspy.OutputField(desc="Reasoning about what to do next")
    action: str = dspy.OutputField(desc="Action to take (tool name and arguments)")
    observation_needed: str = dspy.OutputField(desc="What observation is expected")


# ====================
# Module Implementations
# ====================

class AgentReasoningModule(dspy.Module):
    """
    Chain-of-thought reasoning module for agentic tasks.

    Provides structured reasoning with explicit thought steps
    before arriving at conclusions.
    """

    def __init__(self):
        super().__init__()
        self.reason = dspy.ChainOfThought(ReasoningSignature)

    def forward(self, context: str, question: str) -> dspy.Prediction:
        """Execute reasoning with chain-of-thought"""
        try:
            result = self.reason(context=context, question=question)
            return result
        except Exception as e:
            logger.error(f"Reasoning error: {e}")
            return dspy.Prediction(
                reasoning=f"Error in reasoning: {str(e)}",
                answer="Unable to complete reasoning"
            )


class CodeAnalysisModule(dspy.Module):
    """
    Code analysis module for security, performance, and style checks.

    Integrates with the agentic system for automated code review.
    """

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought(CodeAnalysisSignature)

    def forward(
        self,
        code: str,
        analysis_type: str = "all"
    ) -> dspy.Prediction:
        """Analyze code and provide recommendations"""
        try:
            result = self.analyze(code=code, analysis_type=analysis_type)
            return result
        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return dspy.Prediction(
                analysis=f"Error in analysis: {str(e)}",
                recommendations="Unable to complete analysis",
                severity="unknown"
            )


class PromptEvolutionModule(dspy.Module):
    """
    Prompt evolution module for self-improving prompts.

    Uses performance feedback to iteratively improve prompt quality.
    Integrates with Darwin-Gödel machine for evolutionary optimization.
    """

    def __init__(self):
        super().__init__()
        self.evolve = dspy.ChainOfThought(PromptEvolutionSignature)

    def forward(
        self,
        original_prompt: str,
        performance_data: str,
        task_description: str
    ) -> dspy.Prediction:
        """Evolve a prompt based on performance feedback"""
        try:
            result = self.evolve(
                original_prompt=original_prompt,
                performance_data=performance_data,
                task_description=task_description
            )
            return result
        except Exception as e:
            logger.error(f"Prompt evolution error: {e}")
            return dspy.Prediction(
                evolved_prompt=original_prompt,
                changes_made=f"Error: {str(e)}",
                expected_improvement="0%"
            )


class ChainOfThoughtAgent(dspy.Module):
    """
    Multi-step chain-of-thought agent for complex reasoning.

    Breaks down problems into steps and reasons through each.
    """

    def __init__(self, max_steps: int = 5):
        super().__init__()
        self.max_steps = max_steps
        self.decompose = dspy.ChainOfThought(TaskDecompositionSignature)
        self.reason_step = dspy.ChainOfThought(ReasoningSignature)

    def forward(self, task: str, constraints: str = "") -> dspy.Prediction:
        """Execute multi-step reasoning"""
        try:
            # Decompose the task
            decomposition = self.decompose(task=task, constraints=constraints)

            # Parse subtasks
            subtasks = decomposition.subtasks.split("\n")
            subtasks = [s.strip() for s in subtasks if s.strip()][:self.max_steps]

            # Reason through each subtask
            step_results = []
            accumulated_context = f"Original task: {task}\n"

            for i, subtask in enumerate(subtasks):
                step_result = self.reason_step(
                    context=accumulated_context,
                    question=subtask
                )
                step_results.append({
                    "step": i + 1,
                    "subtask": subtask,
                    "reasoning": step_result.reasoning,
                    "answer": step_result.answer
                })
                accumulated_context += f"\nStep {i+1}: {subtask}\nResult: {step_result.answer}\n"

            # Compile final answer
            final_answer = step_results[-1]["answer"] if step_results else "No solution found"

            return dspy.Prediction(
                subtasks=decomposition.subtasks,
                step_results=step_results,
                final_answer=final_answer
            )

        except Exception as e:
            logger.error(f"ChainOfThought agent error: {e}")
            return dspy.Prediction(
                subtasks="Error decomposing task",
                step_results=[],
                final_answer=f"Error: {str(e)}"
            )


class ReActAgent(dspy.Module):
    """
    ReAct (Reasoning and Acting) agent for tool-using tasks.

    Interleaves reasoning with tool execution for grounded responses.
    """

    def __init__(self, tools: Optional[Dict[str, callable]] = None, max_iterations: int = 5):
        super().__init__()
        self.tools = tools or {}
        self.max_iterations = max_iterations
        self.react_step = dspy.ChainOfThought(ReActSignature)

    def forward(self, goal: str, initial_context: str = "") -> dspy.Prediction:
        """Execute ReAct loop"""
        context = initial_context
        tool_descriptions = self._format_tools()
        trajectory = []

        for i in range(self.max_iterations):
            try:
                # Get next action
                step = self.react_step(
                    context=context,
                    goal=goal,
                    available_tools=tool_descriptions
                )

                trajectory.append({
                    "iteration": i + 1,
                    "thought": step.thought,
                    "action": step.action,
                    "observation_needed": step.observation_needed
                })

                # Check for completion
                if "FINISH" in step.action.upper() or "DONE" in step.action.upper():
                    break

                # Execute action if tool exists
                observation = self._execute_action(step.action)
                context += f"\nThought: {step.thought}\nAction: {step.action}\nObservation: {observation}\n"

            except Exception as e:
                logger.error(f"ReAct iteration error: {e}")
                trajectory.append({
                    "iteration": i + 1,
                    "error": str(e)
                })
                break

        return dspy.Prediction(
            trajectory=trajectory,
            final_context=context,
            iterations=len(trajectory)
        )

    def _format_tools(self) -> str:
        """Format tool descriptions for the prompt"""
        if not self.tools:
            return "No tools available. Reason to conclusion."

        descriptions = []
        for name, func in self.tools.items():
            doc = func.__doc__ or "No description"
            descriptions.append(f"- {name}: {doc.strip()}")

        return "\n".join(descriptions)

    def _execute_action(self, action: str) -> str:
        """Execute a tool action and return observation"""
        # Parse action (format: "tool_name(args)")
        try:
            if "(" not in action:
                return "Invalid action format. Use: tool_name(arguments)"

            tool_name = action.split("(")[0].strip()
            args_str = action.split("(", 1)[1].rsplit(")", 1)[0]

            if tool_name not in self.tools:
                return f"Tool '{tool_name}' not found. Available: {list(self.tools.keys())}"

            # Execute tool
            result = self.tools[tool_name](args_str)
            return str(result)

        except Exception as e:
            return f"Error executing action: {str(e)}"

    def add_tool(self, name: str, func: callable):
        """Add a tool to the agent"""
        self.tools[name] = func


class SelfImprovingModule(dspy.Module):
    """
    Meta-module that can improve its own prompts based on feedback.

    Integrates with the DSPy optimizer for automatic improvement.
    """

    def __init__(self, base_module: dspy.Module):
        super().__init__()
        self.base_module = base_module
        self.evolution = PromptEvolutionModule()
        self.performance_history: List[Dict] = []

    def forward(self, **kwargs) -> dspy.Prediction:
        """Execute base module and track performance"""
        result = self.base_module(**kwargs)

        # Track for future improvement
        self.performance_history.append({
            "inputs": kwargs,
            "outputs": result.toDict() if hasattr(result, 'toDict') else str(result),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })

        return result

    def improve(self, feedback: str, task_description: str) -> dspy.Prediction:
        """Trigger self-improvement based on feedback"""
        # Get current prompt representation
        current_prompt = self._extract_prompt()

        # Format performance data
        perf_data = f"Recent executions: {len(self.performance_history)}\n"
        perf_data += f"Feedback: {feedback}\n"

        # Evolve prompt
        evolution_result = self.evolution(
            original_prompt=current_prompt,
            performance_data=perf_data,
            task_description=task_description
        )

        return evolution_result

    def _extract_prompt(self) -> str:
        """Extract current prompt from base module"""
        prompts = []
        for name, predictor in self.base_module.named_predictors():
            if hasattr(predictor, 'signature'):
                prompts.append(f"{name}: {predictor.signature}")
        return "\n".join(prompts) if prompts else "No prompts found"


# ====================
# Utility Functions
# ====================

def create_example(
    inputs: Dict[str, str],
    outputs: Optional[Dict[str, str]] = None
) -> dspy.Example:
    """Create a DSPy example from inputs and optional outputs"""
    example = dspy.Example(**inputs)
    if outputs:
        example = example.with_inputs(*inputs.keys())
        for key, value in outputs.items():
            setattr(example, key, value)
    return example


def batch_create_examples(data: List[Dict]) -> List[dspy.Example]:
    """Create multiple examples from a list of dictionaries"""
    examples = []
    for item in data:
        inputs = item.get("inputs", item)
        outputs = item.get("outputs", None)
        examples.append(create_example(inputs, outputs))
    return examples
