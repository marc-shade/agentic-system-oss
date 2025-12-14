#!/usr/bin/env python3
"""
20 Agentic Design Patterns Implementation
=========================================

Based on the video analysis of professional agentic architectures.
Implements 20 patterns that separate pros from beginners:

Core Patterns (Video Identified):
1. Prompt Chaining - Sequential task execution with validation
2. Routing - Intent-based specialist agent selection
3. Parallelization - Concurrent task distribution
4. Reflection - Generate → Critique → Revise loop

Extended Patterns (Inferred from Best Practices):
5. Tool Use - Structured external tool invocation
6. Planning - Multi-step plan generation before execution
7. Multi-agent Collaboration - Coordinated multi-agent workflows
8. Evaluation - Quality assessment and scoring
9. Self-consistency - Multiple solution paths with voting
10. Tree of Thoughts - Branching reasoning exploration
11. RAG (Retrieval-Augmented Generation) - Context-aware responses
12. ReAct (Reasoning + Acting) - Interleaved reasoning and action
13. Chain of Thought - Explicit reasoning steps
14. Constitutional AI - Value-aligned decision making
15. Meta-prompting - Dynamic prompt generation
16. Hierarchical Task Decomposition - Recursive task breakdown
17. Ensemble Methods - Multiple agent consensus
18. Feedback Loops - Continuous improvement cycles
19. Memory-Augmented - Long-term context retention
20. Adaptive Learning - Performance-based pattern selection

Integration:
- Works with multi_agent_coordinator for orchestration
- Uses quality_gates for validation
- Integrates with agent_auto_selector for routing
- Provides pattern recommendation engine
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of agentic patterns"""
    PROMPT_CHAINING = "prompt_chaining"
    ROUTING = "routing"
    PARALLELIZATION = "parallelization"
    REFLECTION = "reflection"
    TOOL_USE = "tool_use"
    PLANNING = "planning"
    MULTI_AGENT = "multi_agent"
    EVALUATION = "evaluation"
    SELF_CONSISTENCY = "self_consistency"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    RAG = "rag"
    REACT = "react"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    CONSTITUTIONAL = "constitutional"
    META_PROMPTING = "meta_prompting"
    HIERARCHICAL = "hierarchical"
    ENSEMBLE = "ensemble"
    FEEDBACK_LOOP = "feedback_loop"
    MEMORY_AUGMENTED = "memory_augmented"
    ADAPTIVE_LEARNING = "adaptive_learning"


class PatternComplexity(Enum):
    """Pattern implementation complexity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PatternMetadata:
    """Metadata about an agentic pattern"""
    pattern_type: PatternType
    name: str
    description: str
    complexity: PatternComplexity
    use_cases: List[str]
    pros: List[str]
    cons: List[str]
    best_for: List[str]
    implementation_status: str  # "implemented", "partial", "planned"


@dataclass
class PatternExecutionResult:
    """Result from pattern execution"""
    pattern_type: PatternType
    success: bool
    output: Any
    execution_time_ms: float
    steps_executed: int
    errors: List[str]
    metadata: Dict[str, Any]


class AgenticPattern(ABC):
    """Base class for all agentic patterns"""

    def __init__(self, pattern_type: PatternType):
        self.pattern_type = pattern_type
        self.execution_history: List[PatternExecutionResult] = []

    @abstractmethod
    async def execute(self, *args, **kwargs) -> PatternExecutionResult:
        """Execute the pattern"""
        pass

    def get_metadata(self) -> PatternMetadata:
        """Get pattern metadata"""
        return PATTERN_REGISTRY[self.pattern_type]


# ============================================================================
# PATTERN IMPLEMENTATIONS
# ============================================================================

class PromptChainingPattern(AgenticPattern):
    """
    Pattern 1: Prompt Chaining

    Break big task into smaller sequential steps with validation between each.
    Each step validates output before passing to next step.

    Flow: Task → Subtasks → Execute Step 1 → Validate → Execute Step 2 → ...
    """

    def __init__(self):
        super().__init__(PatternType.PROMPT_CHAINING)

    async def execute(
        self,
        task_description: str,
        chain_steps: List[Dict[str, Any]],
        validation_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """
        Execute prompt chain.

        Args:
            task_description: Overall task description
            chain_steps: List of step definitions [{"description": str, "validate": bool}, ...]
            validation_fn: Optional custom validation function

        Returns:
            PatternExecutionResult with chain execution details
        """
        start_time = datetime.now()
        logger.info(f"[PROMPT CHAINING] Executing {len(chain_steps)} steps for: {task_description}")

        results = []
        errors = []

        # Execute chain sequentially
        previous_output = None
        for i, step in enumerate(chain_steps, 1):
            logger.info(f"  Step {i}/{len(chain_steps)}: {step['description']}")

            try:
                # Execute step (simulated - in production, call actual agent/LLM)
                step_output = await self._execute_step(
                    step['description'],
                    previous_output,
                    step.get('context', {})
                )

                # Validate step output
                if step.get('validate', True):
                    is_valid, validation_msg = await self._validate_step_output(
                        step_output,
                        step.get('validation_criteria', {}),
                        validation_fn
                    )

                    if not is_valid:
                        errors.append(f"Step {i} validation failed: {validation_msg}")
                        # Retry once
                        logger.warning(f"  Retrying step {i} due to validation failure")
                        step_output = await self._execute_step(
                            step['description'],
                            previous_output,
                            step.get('context', {})
                        )

                        # Validate again
                        is_valid, validation_msg = await self._validate_step_output(
                            step_output,
                            step.get('validation_criteria', {}),
                            validation_fn
                        )

                        if not is_valid:
                            raise ValueError(f"Step {i} failed validation after retry: {validation_msg}")

                results.append({
                    'step': i,
                    'description': step['description'],
                    'output': step_output,
                    'validated': True
                })

                previous_output = step_output

            except Exception as e:
                error_msg = f"Step {i} failed: {str(e)}"
                logger.error(f"  {error_msg}")
                errors.append(error_msg)
                break

        # Calculate execution time
        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        # Assemble final result
        success = len(errors) == 0 and len(results) == len(chain_steps)

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=success,
            output={
                'steps_completed': len(results),
                'total_steps': len(chain_steps),
                'final_output': previous_output if results else None,
                'step_results': results
            },
            execution_time_ms=elapsed,
            steps_executed=len(results),
            errors=errors,
            metadata={
                'task_description': task_description,
                'validation_used': any(s.get('validate', True) for s in chain_steps)
            }
        )

        self.execution_history.append(result)
        logger.info(f"[PROMPT CHAINING] Complete: {success} ({elapsed:.1f}ms)")

        return result

    async def _execute_step(
        self,
        description: str,
        previous_output: Any,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single step in the chain"""
        # Simulated execution - in production, call agent/LLM
        await asyncio.sleep(0.1)

        return {
            'description': description,
            'input_from_previous': previous_output,
            'output': f"Result of: {description}",
            'timestamp': datetime.now().isoformat()
        }

    async def _validate_step_output(
        self,
        output: Any,
        criteria: Dict[str, Any],
        custom_fn: Optional[Callable]
    ) -> tuple[bool, str]:
        """Validate step output"""
        # Use custom validation if provided
        if custom_fn:
            return custom_fn(output, criteria)

        # Default validation - check output exists
        if output is None:
            return False, "Output is None"

        if isinstance(output, dict) and not output.get('output'):
            return False, "Output dict missing 'output' key"

        return True, "Valid"


class RoutingPattern(AgenticPattern):
    """
    Pattern 2: Routing

    Analyze incoming request and route to specialist agent based on intent.
    Clarifies ambiguity before routing.

    Flow: Request → Analyze Intent → Route to Specialist → Clarify if needed
    """

    def __init__(self, agent_registry: Optional[Dict[str, Any]] = None):
        super().__init__(PatternType.ROUTING)
        self.agent_registry = agent_registry or {}

    async def execute(
        self,
        request: str,
        confidence_threshold: float = 0.7,
        max_clarification_attempts: int = 2
    ) -> PatternExecutionResult:
        """
        Execute routing pattern.

        Args:
            request: User request to route
            confidence_threshold: Minimum confidence to route (0.0-1.0)
            max_clarification_attempts: Max times to ask for clarification

        Returns:
            PatternExecutionResult with routing decision
        """
        start_time = datetime.now()
        logger.info(f"[ROUTING] Analyzing request: {request[:100]}...")

        errors = []
        clarification_count = 0

        # Analyze intent
        intent_analysis = await self._analyze_intent(request)
        confidence = intent_analysis['confidence']
        agent_type = intent_analysis['agent_type']

        # Clarification loop
        while confidence < confidence_threshold and clarification_count < max_clarification_attempts:
            logger.info(f"  Confidence {confidence:.2f} below threshold {confidence_threshold}")
            clarification_count += 1

            # Request clarification (simulated)
            clarification = await self._request_clarification(intent_analysis)

            # Re-analyze with clarification
            intent_analysis = await self._analyze_intent(f"{request} {clarification}")
            confidence = intent_analysis['confidence']
            agent_type = intent_analysis['agent_type']

        # Route to agent
        if confidence >= confidence_threshold:
            routing_decision = {
                'agent_type': agent_type,
                'confidence': confidence,
                'clarifications_needed': clarification_count,
                'intent': intent_analysis['intent']
            }
            success = True
            logger.info(f"  Routed to: {agent_type} (confidence={confidence:.2f})")
        else:
            errors.append(f"Unable to route with sufficient confidence (max={confidence:.2f})")
            routing_decision = {
                'agent_type': 'general-purpose',  # Fallback
                'confidence': confidence,
                'clarifications_needed': clarification_count,
                'fallback': True
            }
            success = False

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=success,
            output=routing_decision,
            execution_time_ms=elapsed,
            steps_executed=1 + clarification_count,
            errors=errors,
            metadata={
                'request': request[:200],
                'threshold': confidence_threshold
            }
        )

        self.execution_history.append(result)
        return result

    async def _analyze_intent(self, request: str) -> Dict[str, Any]:
        """Analyze request intent"""
        # Simulated intent analysis - in production, use NLP/LLM
        await asyncio.sleep(0.05)

        request_lower = request.lower()

        # Simple keyword-based routing
        if any(word in request_lower for word in ['test', 'verify', 'validate']):
            return {
                'intent': 'testing',
                'agent_type': 'tester',
                'confidence': 0.85
            }
        elif any(word in request_lower for word in ['code', 'implement', 'develop']):
            return {
                'intent': 'development',
                'agent_type': 'coder',
                'confidence': 0.9
            }
        elif any(word in request_lower for word in ['research', 'analyze', 'investigate']):
            return {
                'intent': 'research',
                'agent_type': 'researcher',
                'confidence': 0.8
            }
        else:
            return {
                'intent': 'general',
                'agent_type': 'general-purpose',
                'confidence': 0.5
            }

    async def _request_clarification(self, intent_analysis: Dict[str, Any]) -> str:
        """Request clarification from user"""
        # Simulated clarification - in production, interact with user
        await asyncio.sleep(0.1)
        return "Additional context provided by user"


class ParallelizationPattern(AgenticPattern):
    """
    Pattern 3: Parallelization

    Split large job into independent chunks processed simultaneously.
    Normalizes and merges results.

    Flow: Large Input → Analyze → Split → Parallel Workers → Normalize → Merge
    """

    def __init__(self, max_workers: int = 5):
        super().__init__(PatternType.PARALLELIZATION)
        self.max_workers = max_workers

    async def execute(
        self,
        large_task: Any,
        split_fn: Callable,
        worker_fn: Callable,
        merge_fn: Callable
    ) -> PatternExecutionResult:
        """
        Execute parallelization pattern.

        Args:
            large_task: Task to parallelize
            split_fn: Function to split task into chunks
            worker_fn: Function each worker executes
            merge_fn: Function to merge worker results

        Returns:
            PatternExecutionResult with merged output
        """
        start_time = datetime.now()
        logger.info(f"[PARALLELIZATION] Splitting task across {self.max_workers} workers")

        errors = []

        # Split task
        try:
            chunks = split_fn(large_task, self.max_workers)
            logger.info(f"  Split into {len(chunks)} chunks")
        except Exception as e:
            errors.append(f"Task splitting failed: {str(e)}")
            return PatternExecutionResult(
                pattern_type=self.pattern_type,
                success=False,
                output=None,
                execution_time_ms=0,
                steps_executed=0,
                errors=errors,
                metadata={}
            )

        # Execute workers in parallel
        try:
            worker_tasks = [worker_fn(chunk, i) for i, chunk in enumerate(chunks)]
            worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)

            # Check for worker errors
            for i, result in enumerate(worker_results):
                if isinstance(result, Exception):
                    errors.append(f"Worker {i} failed: {str(result)}")
                    worker_results[i] = None  # Replace exception with None

            logger.info(f"  {len([r for r in worker_results if r])} workers completed successfully")

        except Exception as e:
            errors.append(f"Parallel execution failed: {str(e)}")
            worker_results = []

        # Merge results
        try:
            # Filter out None results from failed workers
            valid_results = [r for r in worker_results if r is not None]

            if valid_results:
                merged_output = merge_fn(valid_results)
                success = len(errors) == 0
                logger.info(f"  Merged {len(valid_results)} results")
            else:
                merged_output = None
                success = False
                errors.append("No valid worker results to merge")

        except Exception as e:
            errors.append(f"Result merging failed: {str(e)}")
            merged_output = None
            success = False

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=success,
            output=merged_output,
            execution_time_ms=elapsed,
            steps_executed=len(chunks) if chunks else 0,
            errors=errors,
            metadata={
                'num_chunks': len(chunks) if chunks else 0,
                'successful_workers': len([r for r in worker_results if r is not None]),
                'max_workers': self.max_workers
            }
        )

        self.execution_history.append(result)
        logger.info(f"[PARALLELIZATION] Complete: {success} ({elapsed:.1f}ms)")

        return result


class ReflectionPattern(AgenticPattern):
    """
    Pattern 4: Reflection

    Generate draft → Critic reviews → Revise → Repeat until quality met.

    Flow: Initial Request → Generate Draft → Quality Assessment → Feedback → Improve → Loop
    """

    def __init__(self, quality_threshold: float = 0.8, max_iterations: int = 3):
        super().__init__(PatternType.REFLECTION)
        self.quality_threshold = quality_threshold
        self.max_iterations = max_iterations

    async def execute(
        self,
        initial_prompt: str,
        generator_fn: Callable,
        critic_fn: Callable,
        quality_rubric: Optional[Dict[str, Any]] = None
    ) -> PatternExecutionResult:
        """
        Execute reflection pattern.

        Args:
            initial_prompt: Initial generation prompt
            generator_fn: Function to generate output
            critic_fn: Function to critique output
            quality_rubric: Optional quality criteria

        Returns:
            PatternExecutionResult with final refined output
        """
        start_time = datetime.now()
        logger.info(f"[REFLECTION] Starting reflection loop (max={self.max_iterations})")

        errors = []
        iteration = 0
        quality_score = 0.0
        current_output = None
        iteration_history = []

        while iteration < self.max_iterations and quality_score < self.quality_threshold:
            iteration += 1
            logger.info(f"  Iteration {iteration}/{self.max_iterations}")

            # Generate (or regenerate)
            try:
                if iteration == 1:
                    current_output = await generator_fn(initial_prompt)
                else:
                    # Regenerate with feedback
                    current_output = await generator_fn(
                        initial_prompt,
                        feedback=critique_result['feedback']
                    )
            except Exception as e:
                errors.append(f"Generation failed at iteration {iteration}: {str(e)}")
                break

            # Critique
            try:
                critique_result = await critic_fn(current_output, quality_rubric)
                quality_score = critique_result['score']

                logger.info(f"    Quality score: {quality_score:.2f}")

                iteration_history.append({
                    'iteration': iteration,
                    'output': current_output,
                    'score': quality_score,
                    'feedback': critique_result.get('feedback', '')
                })

                if quality_score >= self.quality_threshold:
                    logger.info(f"    Quality threshold met!")
                    break

            except Exception as e:
                errors.append(f"Critique failed at iteration {iteration}: {str(e)}")
                break

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        success = quality_score >= self.quality_threshold

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=success,
            output={
                'final_output': current_output,
                'final_score': quality_score,
                'iterations': iteration,
                'iteration_history': iteration_history
            },
            execution_time_ms=elapsed,
            steps_executed=iteration,
            errors=errors,
            metadata={
                'threshold': self.quality_threshold,
                'threshold_met': success
            }
        )

        self.execution_history.append(result)
        logger.info(f"[REFLECTION] Complete: {success} after {iteration} iterations ({elapsed:.1f}ms)")

        return result


class ToolUsePattern(AgenticPattern):
    """
    Pattern 5: Tool Use

    Structured external tool invocation with result integration.
    Enables agents to call APIs, run commands, query databases, etc.

    Flow: Task → Identify Tools → Invoke Tools → Integrate Results
    """

    def __init__(self, available_tools: Optional[Dict[str, Callable]] = None):
        super().__init__(PatternType.TOOL_USE)
        self.available_tools = available_tools or {}

    async def execute(
        self,
        task_description: str,
        tool_selection_fn: Optional[Callable] = None,
        result_integration_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """Execute tool use pattern"""
        start_time = datetime.now()
        logger.info(f"[TOOL_USE] Identifying required tools for task")

        errors = []
        tool_results = []

        try:
            # Select appropriate tools
            if tool_selection_fn:
                selected_tools = await tool_selection_fn(task_description, self.available_tools)
            else:
                selected_tools = list(self.available_tools.keys())

            logger.info(f"  Selected tools: {selected_tools}")

            # Invoke each tool
            for tool_name in selected_tools:
                if tool_name in self.available_tools:
                    try:
                        tool_fn = self.available_tools[tool_name]
                        result = await tool_fn(task_description)
                        tool_results.append({'tool': tool_name, 'result': result})
                    except Exception as e:
                        errors.append(f"Tool {tool_name} failed: {str(e)}")

            # Integrate results
            if result_integration_fn:
                integrated_output = await result_integration_fn(tool_results)
            else:
                integrated_output = tool_results

        except Exception as e:
            errors.append(f"Tool use failed: {str(e)}")
            integrated_output = None

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(errors) == 0 and integrated_output is not None,
            output=integrated_output,
            execution_time_ms=elapsed,
            steps_executed=len(tool_results),
            errors=errors,
            metadata={'tools_used': [tr['tool'] for tr in tool_results]}
        )

        self.execution_history.append(result)
        logger.info(f"[TOOL_USE] Complete ({elapsed:.1f}ms)")

        return result


class PlanningPattern(AgenticPattern):
    """
    Pattern 6: Planning

    Multi-step plan generation before execution.
    Creates comprehensive execution plan with dependencies and resources.

    Flow: Task → Analyze → Generate Plan → Validate → Execute Plan
    """

    def __init__(self):
        super().__init__(PatternType.PLANNING)

    async def execute(
        self,
        task_description: str,
        planning_fn: Callable,
        validation_fn: Optional[Callable] = None,
        execution_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """Execute planning pattern"""
        start_time = datetime.now()
        logger.info(f"[PLANNING] Generating execution plan")

        errors = []
        plan = None
        execution_result = None

        try:
            # Generate plan
            plan = await planning_fn(task_description)
            logger.info(f"  Plan generated with {len(plan.get('steps', []))} steps")

            # Validate plan
            if validation_fn:
                is_valid, validation_msg = await validation_fn(plan)
                if not is_valid:
                    errors.append(f"Plan validation failed: {validation_msg}")
                    plan = None

            # Execute plan if provided
            if plan and execution_fn:
                execution_result = await execution_fn(plan)

        except Exception as e:
            errors.append(f"Planning failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=plan is not None and len(errors) == 0,
            output={'plan': plan, 'execution_result': execution_result},
            execution_time_ms=elapsed,
            steps_executed=len(plan.get('steps', [])) if plan else 0,
            errors=errors,
            metadata={'plan_steps': len(plan.get('steps', [])) if plan else 0}
        )

        self.execution_history.append(result)
        logger.info(f"[PLANNING] Complete ({elapsed:.1f}ms)")

        return result


class MultiAgentCollaborationPattern(AgenticPattern):
    """
    Pattern 7: Multi-Agent Collaboration

    Coordinated workflows with multiple specialized agents.
    Agents communicate and share context to solve complex problems.

    Flow: Task → Decompose → Assign Agents → Collaborate → Synthesize
    """

    def __init__(self, max_agents: int = 5):
        super().__init__(PatternType.MULTI_AGENT_COLLABORATION)
        self.max_agents = max_agents

    async def execute(
        self,
        task_description: str,
        agent_pool: List[Dict[str, Any]],
        coordination_strategy: str = "sequential"
    ) -> PatternExecutionResult:
        """Execute multi-agent collaboration"""
        start_time = datetime.now()
        logger.info(f"[MULTI_AGENT] Coordinating {len(agent_pool[:self.max_agents])} agents")

        errors = []
        agent_results = []
        shared_context = {}

        try:
            selected_agents = agent_pool[:self.max_agents]

            if coordination_strategy == "parallel":
                # Parallel execution
                tasks = [self._execute_agent(agent, task_description, shared_context)
                        for agent in selected_agents]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                agent_results = [r for r in results if not isinstance(r, Exception)]
            else:
                # Sequential execution with context sharing
                for agent in selected_agents:
                    result = await self._execute_agent(agent, task_description, shared_context)
                    agent_results.append(result)
                    shared_context.update(result.get('context', {}))

        except Exception as e:
            errors.append(f"Collaboration failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(agent_results) > 0 and len(errors) == 0,
            output={'agent_results': agent_results, 'shared_context': shared_context},
            execution_time_ms=elapsed,
            steps_executed=len(agent_results),
            errors=errors,
            metadata={'num_agents': len(agent_results), 'strategy': coordination_strategy}
        )

        self.execution_history.append(result)
        logger.info(f"[MULTI_AGENT] Complete ({elapsed:.1f}ms)")

        return result

    async def _execute_agent(self, agent: Dict[str, Any], task: str, context: Dict) -> Dict:
        """Execute single agent with context"""
        # Simulate agent execution
        await asyncio.sleep(0.1)
        return {
            'agent_id': agent.get('id', 'unknown'),
            'output': f"Processed: {task[:50]}...",
            'context': {'agent_type': agent.get('type', 'generic')}
        }


class EvaluationPattern(AgenticPattern):
    """
    Pattern 8: Evaluation

    Quality assessment and scoring of outputs.
    Uses rubrics and criteria to objectively evaluate results.

    Flow: Output → Define Criteria → Assess → Score → Report
    """

    def __init__(self):
        super().__init__(PatternType.EVALUATION)

    async def execute(
        self,
        output_to_evaluate: Any,
        evaluation_criteria: Dict[str, Any],
        scorer_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """Execute evaluation pattern"""
        start_time = datetime.now()
        logger.info(f"[EVALUATION] Assessing output against {len(evaluation_criteria)} criteria")

        errors = []
        scores = {}
        overall_score = 0.0

        try:
            if scorer_fn:
                scores = await scorer_fn(output_to_evaluate, evaluation_criteria)
            else:
                # Default scoring
                for criterion, weight in evaluation_criteria.items():
                    scores[criterion] = 0.8  # Default score

            # Calculate weighted average
            total_weight = sum(evaluation_criteria.values())
            overall_score = sum(scores[k] * evaluation_criteria[k] for k in scores) / total_weight

        except Exception as e:
            errors.append(f"Evaluation failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(errors) == 0,
            output={'scores': scores, 'overall_score': overall_score},
            execution_time_ms=elapsed,
            steps_executed=len(scores),
            errors=errors,
            metadata={'criteria_count': len(evaluation_criteria)}
        )

        self.execution_history.append(result)
        logger.info(f"[EVALUATION] Complete: {overall_score:.2f} ({elapsed:.1f}ms)")

        return result


class SelfConsistencyPattern(AgenticPattern):
    """
    Pattern 9: Self-Consistency

    Generate multiple solution paths and vote on best answer.
    Improves reliability through consensus.

    Flow: Problem → Generate N Solutions → Vote → Select Best
    """

    def __init__(self, num_samples: int = 5):
        super().__init__(PatternType.SELF_CONSISTENCY)
        self.num_samples = num_samples

    async def execute(
        self,
        problem: str,
        solution_generator_fn: Callable,
        voting_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """Execute self-consistency pattern"""
        start_time = datetime.now()
        logger.info(f"[SELF_CONSISTENCY] Generating {self.num_samples} solutions")

        errors = []
        solutions = []

        try:
            # Generate multiple solutions
            tasks = [solution_generator_fn(problem) for _ in range(self.num_samples)]
            solutions = await asyncio.gather(*tasks, return_exceptions=True)
            solutions = [s for s in solutions if not isinstance(s, Exception)]

            logger.info(f"  Generated {len(solutions)} valid solutions")

            # Vote on best solution
            if voting_fn:
                best_solution = await voting_fn(solutions)
            else:
                # Majority voting by default
                from collections import Counter
                solution_counts = Counter(str(s) for s in solutions)
                best_solution = eval(solution_counts.most_common(1)[0][0])

        except Exception as e:
            errors.append(f"Self-consistency failed: {str(e)}")
            best_solution = None

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=best_solution is not None and len(errors) == 0,
            output={'best_solution': best_solution, 'all_solutions': solutions},
            execution_time_ms=elapsed,
            steps_executed=len(solutions),
            errors=errors,
            metadata={'num_solutions': len(solutions)}
        )

        self.execution_history.append(result)
        logger.info(f"[SELF_CONSISTENCY] Complete ({elapsed:.1f}ms)")

        return result


class TreeOfThoughtsPattern(AgenticPattern):
    """
    Pattern 10: Tree of Thoughts

    Branching reasoning exploration with backtracking.
    Explores multiple reasoning paths systematically.

    Flow: Problem → Generate Branches → Evaluate Paths → Prune → Expand Best → Solution
    """

    def __init__(self, max_depth: int = 3, branch_factor: int = 3):
        super().__init__(PatternType.TREE_OF_THOUGHTS)
        self.max_depth = max_depth
        self.branch_factor = branch_factor

    async def execute(
        self,
        problem: str,
        thought_generator_fn: Callable,
        evaluator_fn: Callable
    ) -> PatternExecutionResult:
        """Execute tree of thoughts pattern"""
        start_time = datetime.now()
        logger.info(f"[TREE_OF_THOUGHTS] Exploring reasoning tree (depth={self.max_depth})")

        errors = []
        thoughts_tree = {'root': problem, 'children': []}
        best_path = []

        try:
            # BFS exploration
            queue = [(thoughts_tree, 0, [])]  # (node, depth, path)
            explored_nodes = 0

            while queue and explored_nodes < 100:  # Safety limit
                node, depth, path = queue.pop(0)
                explored_nodes += 1

                if depth >= self.max_depth:
                    continue

                # Generate thought branches
                branches = await thought_generator_fn(node.get('root', ''), self.branch_factor)

                for branch in branches:
                    branch_node = {'root': branch, 'children': []}
                    node['children'].append(branch_node)

                    # Evaluate branch
                    score = await evaluator_fn(branch)

                    if score > 0.7:  # Threshold for promising paths
                        queue.append((branch_node, depth + 1, path + [branch]))

            # Find best path
            best_path = await self._find_best_path(thoughts_tree, evaluator_fn)

        except Exception as e:
            errors.append(f"Tree of thoughts failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(best_path) > 0 and len(errors) == 0,
            output={'best_path': best_path, 'tree': thoughts_tree},
            execution_time_ms=elapsed,
            steps_executed=explored_nodes,
            errors=errors,
            metadata={'nodes_explored': explored_nodes, 'max_depth': self.max_depth}
        )

        self.execution_history.append(result)
        logger.info(f"[TREE_OF_THOUGHTS] Complete ({elapsed:.1f}ms)")

        return result

    async def _find_best_path(self, tree: Dict, evaluator_fn: Callable) -> List[str]:
        """Find highest scoring path in tree"""
        # DFS to find best path
        best_path = []
        best_score = 0.0

        async def dfs(node, current_path):
            nonlocal best_path, best_score

            if not node.get('children'):
                score = await evaluator_fn(current_path)
                if score > best_score:
                    best_score = score
                    best_path = current_path.copy()
                return

            for child in node['children']:
                await dfs(child, current_path + [child['root']])

        await dfs(tree, [tree['root']])
        return best_path


class RAGPattern(AgenticPattern):
    """
    Pattern 11: RAG (Retrieval-Augmented Generation)

    Retrieve relevant context before generation for grounded responses.
    Combines retrieval with generation for factual accuracy.

    Flow: Query → Retrieve Context → Augment Prompt → Generate → Return
    """

    def __init__(self, knowledge_base: Optional[Any] = None):
        super().__init__(PatternType.RAG)
        self.knowledge_base = knowledge_base

    async def execute(
        self,
        query: str,
        retrieval_fn: Callable,
        generation_fn: Callable,
        top_k: int = 5
    ) -> PatternExecutionResult:
        """Execute RAG pattern"""
        start_time = datetime.now()
        logger.info(f"[RAG] Retrieving context for query")

        errors = []
        retrieved_context = []
        generated_output = None

        try:
            # Retrieve relevant documents/passages
            retrieved_context = await retrieval_fn(query, top_k=top_k)
            logger.info(f"  Retrieved {len(retrieved_context)} context items")

            # Augment prompt with retrieved context
            augmented_prompt = self._augment_prompt(query, retrieved_context)

            # Generate with context
            generated_output = await generation_fn(augmented_prompt)

        except Exception as e:
            errors.append(f"RAG failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=generated_output is not None and len(errors) == 0,
            output={'generated': generated_output, 'context': retrieved_context},
            execution_time_ms=elapsed,
            steps_executed=len(retrieved_context) + 1,
            errors=errors,
            metadata={'context_items': len(retrieved_context)}
        )

        self.execution_history.append(result)
        logger.info(f"[RAG] Complete ({elapsed:.1f}ms)")

        return result

    def _augment_prompt(self, query: str, context: List[str]) -> str:
        """Augment prompt with retrieved context"""
        context_str = "\n\n".join(f"Context {i+1}: {c}" for i, c in enumerate(context))
        return f"Context:\n{context_str}\n\nQuestion: {query}\n\nAnswer based on the provided context:"


class ReActPattern(AgenticPattern):
    """
    Pattern 12: ReAct (Reasoning + Acting)

    Interleave reasoning traces with actions.
    Think about what to do, take action, observe result, repeat.

    Flow: Task → Reason → Act → Observe → Reason → Act → ... → Solution
    """

    def __init__(self, max_steps: int = 5):
        super().__init__(PatternType.REACT)
        self.max_steps = max_steps

    async def execute(
        self,
        task: str,
        reasoning_fn: Callable,
        action_fn: Callable,
        observation_fn: Callable
    ) -> PatternExecutionResult:
        """Execute ReAct pattern"""
        start_time = datetime.now()
        logger.info(f"[REACT] Starting reasoning-action loop")

        errors = []
        trajectory = []
        final_answer = None

        try:
            context = task
            for step in range(self.max_steps):
                # Reason about next action
                thought = await reasoning_fn(context)
                trajectory.append({'step': step + 1, 'thought': thought})

                # Take action
                action_result = await action_fn(thought)
                trajectory[-1]['action'] = action_result

                # Observe result
                observation = await observation_fn(action_result)
                trajectory[-1]['observation'] = observation

                # Update context
                context = f"{context}\nThought: {thought}\nAction: {action_result}\nObservation: {observation}"

                # Check if task complete
                if 'final answer' in str(observation).lower() or 'complete' in str(observation).lower():
                    final_answer = observation
                    break

        except Exception as e:
            errors.append(f"ReAct failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=final_answer is not None and len(errors) == 0,
            output={'final_answer': final_answer, 'trajectory': trajectory},
            execution_time_ms=elapsed,
            steps_executed=len(trajectory),
            errors=errors,
            metadata={'reasoning_steps': len(trajectory)}
        )

        self.execution_history.append(result)
        logger.info(f"[REACT] Complete after {len(trajectory)} steps ({elapsed:.1f}ms)")

        return result


class ChainOfThoughtPattern(AgenticPattern):
    """
    Pattern 13: Chain of Thought

    Explicit step-by-step reasoning before final answer.
    Makes reasoning process transparent and verifiable.

    Flow: Problem → Reason Step 1 → Reason Step 2 → ... → Conclusion
    """

    def __init__(self):
        super().__init__(PatternType.CHAIN_OF_THOUGHT)

    async def execute(
        self,
        problem: str,
        reasoning_fn: Callable,
        num_reasoning_steps: Optional[int] = None
    ) -> PatternExecutionResult:
        """Execute chain of thought pattern"""
        start_time = datetime.now()
        logger.info(f"[CHAIN_OF_THOUGHT] Generating reasoning chain")

        errors = []
        reasoning_chain = []
        final_answer = None

        try:
            # Generate reasoning chain
            reasoning_output = await reasoning_fn(problem)

            # Parse reasoning steps
            if isinstance(reasoning_output, dict) and 'steps' in reasoning_output:
                reasoning_chain = reasoning_output['steps']
                final_answer = reasoning_output.get('answer')
            else:
                # Extract steps from text
                steps = str(reasoning_output).split('\n')
                reasoning_chain = [s.strip() for s in steps if s.strip()]
                final_answer = reasoning_chain[-1] if reasoning_chain else None

        except Exception as e:
            errors.append(f"Chain of thought failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(reasoning_chain) > 0 and len(errors) == 0,
            output={'reasoning_chain': reasoning_chain, 'final_answer': final_answer},
            execution_time_ms=elapsed,
            steps_executed=len(reasoning_chain),
            errors=errors,
            metadata={'reasoning_steps': len(reasoning_chain)}
        )

        self.execution_history.append(result)
        logger.info(f"[CHAIN_OF_THOUGHT] Complete with {len(reasoning_chain)} steps ({elapsed:.1f}ms)")

        return result


class ConstitutionalAIPattern(AgenticPattern):
    """
    Pattern 14: Constitutional AI

    Value-aligned decision making with ethical principles.
    Ensures outputs align with defined values and principles.

    Flow: Input → Generate → Check Principles → Revise if Needed → Output
    """

    def __init__(self, principles: Optional[List[str]] = None):
        super().__init__(PatternType.CONSTITUTIONAL_AI)
        self.principles = principles or [
            "Be helpful and harmless",
            "Respect user privacy",
            "Avoid bias and discrimination",
            "Be honest and transparent"
        ]

    async def execute(
        self,
        input_text: str,
        generator_fn: Callable,
        principle_checker_fn: Callable,
        max_revisions: int = 3
    ) -> PatternExecutionResult:
        """Execute constitutional AI pattern"""
        start_time = datetime.now()
        logger.info(f"[CONSTITUTIONAL_AI] Generating with {len(self.principles)} principles")

        errors = []
        output = None
        revisions = 0
        violations = []

        try:
            # Generate initial output
            output = await generator_fn(input_text)

            # Check against principles
            while revisions < max_revisions:
                violations = await principle_checker_fn(output, self.principles)

                if not violations:
                    break

                # Revise to address violations
                revision_prompt = self._create_revision_prompt(input_text, output, violations)
                output = await generator_fn(revision_prompt)
                revisions += 1

        except Exception as e:
            errors.append(f"Constitutional AI failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(violations) == 0 and len(errors) == 0,
            output={'final_output': output, 'revisions': revisions, 'violations': violations},
            execution_time_ms=elapsed,
            steps_executed=revisions + 1,
            errors=errors,
            metadata={'principles_checked': len(self.principles), 'revisions': revisions}
        )

        self.execution_history.append(result)
        logger.info(f"[CONSTITUTIONAL_AI] Complete after {revisions} revisions ({elapsed:.1f}ms)")

        return result

    def _create_revision_prompt(self, original: str, output: str, violations: List[str]) -> str:
        """Create revision prompt addressing violations"""
        violations_str = "\n".join(f"- {v}" for v in violations)
        return f"Original: {original}\n\nPrevious output:\n{output}\n\nViolations:\n{violations_str}\n\nRevise to address these issues:"


class MetaPromptingPattern(AgenticPattern):
    """
    Pattern 15: Meta-Prompting

    Dynamic prompt generation based on task characteristics.
    Generates optimal prompts for different scenarios.

    Flow: Task → Analyze → Generate Optimal Prompt → Execute → Result
    """

    def __init__(self):
        super().__init__(PatternType.META_PROMPTING)

    async def execute(
        self,
        task: str,
        prompt_generator_fn: Callable,
        executor_fn: Callable
    ) -> PatternExecutionResult:
        """Execute meta-prompting pattern"""
        start_time = datetime.now()
        logger.info(f"[META_PROMPTING] Generating optimal prompt")

        errors = []
        generated_prompt = None
        execution_result = None

        try:
            # Analyze task and generate optimal prompt
            generated_prompt = await prompt_generator_fn(task)
            logger.info(f"  Generated prompt: {generated_prompt[:100]}...")

            # Execute with generated prompt
            execution_result = await executor_fn(generated_prompt)

        except Exception as e:
            errors.append(f"Meta-prompting failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=execution_result is not None and len(errors) == 0,
            output={'generated_prompt': generated_prompt, 'result': execution_result},
            execution_time_ms=elapsed,
            steps_executed=2,
            errors=errors,
            metadata={'prompt_length': len(generated_prompt) if generated_prompt else 0}
        )

        self.execution_history.append(result)
        logger.info(f"[META_PROMPTING] Complete ({elapsed:.1f}ms)")

        return result


class HierarchicalDecompositionPattern(AgenticPattern):
    """
    Pattern 16: Hierarchical Task Decomposition

    Recursive breakdown of complex tasks into subtask hierarchies.
    Creates tree structure of manageable subtasks.

    Flow: Task → Decompose → Sub-decompose → ... → Atomic Tasks → Execute → Aggregate
    """

    def __init__(self, max_depth: int = 3):
        super().__init__(PatternType.HIERARCHICAL_DECOMPOSITION)
        self.max_depth = max_depth

    async def execute(
        self,
        task: str,
        decomposition_fn: Callable,
        execution_fn: Optional[Callable] = None
    ) -> PatternExecutionResult:
        """Execute hierarchical decomposition pattern"""
        start_time = datetime.now()
        logger.info(f"[HIERARCHICAL] Decomposing task hierarchically")

        errors = []
        task_tree = {'task': task, 'subtasks': []}
        execution_results = []

        try:
            # Recursively decompose
            await self._decompose_recursive(task_tree, decomposition_fn, depth=0)

            # Execute atomic tasks if executor provided
            if execution_fn:
                atomic_tasks = self._extract_atomic_tasks(task_tree)
                for atomic_task in atomic_tasks:
                    result = await execution_fn(atomic_task)
                    execution_results.append(result)

        except Exception as e:
            errors.append(f"Hierarchical decomposition failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=len(task_tree.get('subtasks', [])) > 0 and len(errors) == 0,
            output={'task_tree': task_tree, 'execution_results': execution_results},
            execution_time_ms=elapsed,
            steps_executed=len(execution_results),
            errors=errors,
            metadata={'tree_depth': self._calculate_depth(task_tree)}
        )

        self.execution_history.append(result)
        logger.info(f"[HIERARCHICAL] Complete ({elapsed:.1f}ms)")

        return result

    async def _decompose_recursive(self, node: Dict, decomposition_fn: Callable, depth: int):
        """Recursively decompose task"""
        if depth >= self.max_depth:
            return

        subtasks = await decomposition_fn(node['task'])
        for subtask in subtasks:
            subtask_node = {'task': subtask, 'subtasks': []}
            node['subtasks'].append(subtask_node)
            await self._decompose_recursive(subtask_node, decomposition_fn, depth + 1)

    def _extract_atomic_tasks(self, tree: Dict) -> List[str]:
        """Extract leaf nodes (atomic tasks)"""
        if not tree.get('subtasks'):
            return [tree['task']]

        atomic = []
        for subtask in tree['subtasks']:
            atomic.extend(self._extract_atomic_tasks(subtask))
        return atomic

    def _calculate_depth(self, tree: Dict) -> int:
        """Calculate tree depth"""
        if not tree.get('subtasks'):
            return 1
        return 1 + max(self._calculate_depth(st) for st in tree['subtasks'])


class EnsembleMethodsPattern(AgenticPattern):
    """
    Pattern 17: Ensemble Methods

    Combine multiple agent outputs through voting or averaging.
    Improves robustness through diversity.

    Flow: Task → Distribute to Agents → Collect Outputs → Combine → Final Result
    """

    def __init__(self, num_models: int = 3):
        super().__init__(PatternType.ENSEMBLE_METHODS)
        self.num_models = num_models

    async def execute(
        self,
        task: str,
        model_fns: List[Callable],
        combination_strategy: str = "voting"
    ) -> PatternExecutionResult:
        """Execute ensemble methods pattern"""
        start_time = datetime.now()
        logger.info(f"[ENSEMBLE] Running {len(model_fns)} models")

        errors = []
        model_outputs = []
        combined_output = None

        try:
            # Execute all models in parallel
            tasks = [model_fn(task) for model_fn in model_fns[:self.num_models]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            model_outputs = [r for r in results if not isinstance(r, Exception)]

            # Combine outputs
            if combination_strategy == "voting":
                combined_output = self._majority_vote(model_outputs)
            elif combination_strategy == "averaging":
                combined_output = self._average_outputs(model_outputs)
            else:
                combined_output = model_outputs[0] if model_outputs else None

        except Exception as e:
            errors.append(f"Ensemble methods failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=combined_output is not None and len(errors) == 0,
            output={'combined': combined_output, 'individual': model_outputs},
            execution_time_ms=elapsed,
            steps_executed=len(model_outputs),
            errors=errors,
            metadata={'num_models': len(model_outputs), 'strategy': combination_strategy}
        )

        self.execution_history.append(result)
        logger.info(f"[ENSEMBLE] Complete ({elapsed:.1f}ms)")

        return result

    def _majority_vote(self, outputs: List[Any]) -> Any:
        """Select most common output"""
        from collections import Counter
        counts = Counter(str(o) for o in outputs)
        return eval(counts.most_common(1)[0][0])

    def _average_outputs(self, outputs: List[Any]) -> Any:
        """Average numeric outputs"""
        try:
            numeric_outputs = [float(o) for o in outputs]
            return sum(numeric_outputs) / len(numeric_outputs)
        except:
            return outputs[0] if outputs else None


class FeedbackLoopsPattern(AgenticPattern):
    """
    Pattern 18: Feedback Loops

    Continuous improvement through iterative feedback.
    Learns from outcomes and adjusts approach.

    Flow: Execute → Measure → Analyze → Adjust → Execute → ...
    """

    def __init__(self, max_iterations: int = 5):
        super().__init__(PatternType.FEEDBACK_LOOPS)
        self.max_iterations = max_iterations

    async def execute(
        self,
        initial_task: str,
        executor_fn: Callable,
        feedback_fn: Callable,
        adjustment_fn: Callable
    ) -> PatternExecutionResult:
        """Execute feedback loops pattern"""
        start_time = datetime.now()
        logger.info(f"[FEEDBACK_LOOPS] Starting feedback loop")

        errors = []
        iteration_history = []
        current_task = initial_task
        final_output = None

        try:
            for iteration in range(self.max_iterations):
                # Execute current approach
                output = await executor_fn(current_task)

                # Get feedback
                feedback = await feedback_fn(output)

                iteration_history.append({
                    'iteration': iteration + 1,
                    'output': output,
                    'feedback': feedback
                })

                # Check if satisfactory
                if feedback.get('satisfactory', False):
                    final_output = output
                    break

                # Adjust approach based on feedback
                current_task = await adjustment_fn(current_task, feedback)

        except Exception as e:
            errors.append(f"Feedback loops failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=final_output is not None and len(errors) == 0,
            output={'final_output': final_output, 'history': iteration_history},
            execution_time_ms=elapsed,
            steps_executed=len(iteration_history),
            errors=errors,
            metadata={'iterations': len(iteration_history)}
        )

        self.execution_history.append(result)
        logger.info(f"[FEEDBACK_LOOPS] Complete after {len(iteration_history)} iterations ({elapsed:.1f}ms)")

        return result


class MemoryAugmentedPattern(AgenticPattern):
    """
    Pattern 19: Memory-Augmented

    Long-term context retention across interactions.
    Maintains state and learns from history.

    Flow: Input → Retrieve Relevant Memory → Process with Context → Store → Output
    """

    def __init__(self, memory_store: Optional[Dict] = None):
        super().__init__(PatternType.MEMORY_AUGMENTED)
        self.memory_store = memory_store or {}

    async def execute(
        self,
        input_text: str,
        memory_retrieval_fn: Callable,
        processor_fn: Callable,
        memory_storage_fn: Callable
    ) -> PatternExecutionResult:
        """Execute memory-augmented pattern"""
        start_time = datetime.now()
        logger.info(f"[MEMORY_AUGMENTED] Processing with memory context")

        errors = []
        retrieved_memories = []
        output = None

        try:
            # Retrieve relevant memories
            retrieved_memories = await memory_retrieval_fn(input_text, self.memory_store)
            logger.info(f"  Retrieved {len(retrieved_memories)} memories")

            # Process with memory context
            output = await processor_fn(input_text, retrieved_memories)

            # Store new memory
            await memory_storage_fn(input_text, output, self.memory_store)

        except Exception as e:
            errors.append(f"Memory-augmented failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=output is not None and len(errors) == 0,
            output={'result': output, 'memories_used': retrieved_memories},
            execution_time_ms=elapsed,
            steps_executed=len(retrieved_memories) + 1,
            errors=errors,
            metadata={'memories_retrieved': len(retrieved_memories)}
        )

        self.execution_history.append(result)
        logger.info(f"[MEMORY_AUGMENTED] Complete ({elapsed:.1f}ms)")

        return result


class AdaptiveLearningPattern(AgenticPattern):
    """
    Pattern 20: Adaptive Learning

    Performance-based pattern selection and optimization.
    Learns which approaches work best for which tasks.

    Flow: Task → Analyze History → Select Best Pattern → Execute → Record Outcome
    """

    def __init__(self):
        super().__init__(PatternType.ADAPTIVE_LEARNING)
        self.performance_history = {}

    async def execute(
        self,
        task: str,
        task_analyzer_fn: Callable,
        available_patterns: List[PatternType],
        pattern_executor_fn: Callable
    ) -> PatternExecutionResult:
        """Execute adaptive learning pattern"""
        start_time = datetime.now()
        logger.info(f"[ADAPTIVE_LEARNING] Selecting optimal pattern from history")

        errors = []
        selected_pattern = None
        execution_result = None

        try:
            # Analyze task characteristics
            task_features = await task_analyzer_fn(task)

            # Select best pattern based on history
            selected_pattern = self._select_best_pattern(task_features, available_patterns)
            logger.info(f"  Selected pattern: {selected_pattern.value}")

            # Execute with selected pattern
            execution_result = await pattern_executor_fn(task, selected_pattern)

            # Record outcome for learning
            self._record_outcome(task_features, selected_pattern, execution_result.get('success', False))

        except Exception as e:
            errors.append(f"Adaptive learning failed: {str(e)}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        result = PatternExecutionResult(
            pattern_type=self.pattern_type,
            success=execution_result is not None and len(errors) == 0,
            output={'selected_pattern': selected_pattern.value if selected_pattern else None,
                   'execution_result': execution_result},
            execution_time_ms=elapsed,
            steps_executed=1,
            errors=errors,
            metadata={'pattern_selected': selected_pattern.value if selected_pattern else None}
        )

        self.execution_history.append(result)
        logger.info(f"[ADAPTIVE_LEARNING] Complete ({elapsed:.1f}ms)")

        return result

    def _select_best_pattern(self, task_features: Dict, available_patterns: List[PatternType]) -> PatternType:
        """Select pattern with best historical performance for task type"""
        task_type = task_features.get('type', 'general')

        if task_type in self.performance_history:
            pattern_scores = self.performance_history[task_type]
            best_pattern = max(pattern_scores.items(), key=lambda x: x[1])[0]
            return best_pattern

        # Default to routing if no history
        return PatternType.ROUTING

    def _record_outcome(self, task_features: Dict, pattern: PatternType, success: bool):
        """Record pattern performance for learning"""
        task_type = task_features.get('type', 'general')

        if task_type not in self.performance_history:
            self.performance_history[task_type] = {}

        if pattern not in self.performance_history[task_type]:
            self.performance_history[task_type][pattern] = 0.5

        # Update with exponential moving average
        current_score = self.performance_history[task_type][pattern]
        new_score = 1.0 if success else 0.0
        self.performance_history[task_type][pattern] = 0.7 * current_score + 0.3 * new_score


# ============================================================================
# PATTERN REGISTRY
# ============================================================================

PATTERN_REGISTRY: Dict[PatternType, PatternMetadata] = {
    PatternType.PROMPT_CHAINING: PatternMetadata(
        pattern_type=PatternType.PROMPT_CHAINING,
        name="Prompt Chaining",
        description="Break big task into smaller sequential steps with validation between each",
        complexity=PatternComplexity.LOW,
        use_cases=[
            "Data transformation pipelines",
            "Document processing",
            "Content creation workflows",
            "Code generation with steps"
        ],
        pros=[
            "Modular and swappable components",
            "Multiple validation points catch errors early",
            "Easy to debug specific steps",
            "Clear provenance tracking"
        ],
        cons=[
            "Context explosion with too many steps",
            "Error propagation across chain",
            "Slower due to sequential execution",
            "Requires well-tested prompts"
        ],
        best_for=[
            "Multi-step processes",
            "Complex workflows with dependencies",
            "ETL pipelines",
            "Sequential transformations"
        ],
        implementation_status="implemented"
    ),

    PatternType.ROUTING: PatternMetadata(
        pattern_type=PatternType.ROUTING,
        name="Routing",
        description="Analyze requests and route to specialist agents based on intent",
        complexity=PatternComplexity.MEDIUM,
        use_cases=[
            "Customer service automation",
            "Enterprise workflow automation",
            "Healthcare triage",
            "Multi-domain chatbots"
        ],
        pros=[
            "Agent specialization improves quality",
            "Scalable to many agents",
            "Efficient resource utilization",
            "Prevents tool misfires"
        ],
        cons=[
            "Potential routing errors",
            "Complexity increases with agents",
            "Edge cases require fallbacks",
            "Confidence scoring can be unreliable"
        ],
        best_for=[
            "Multiple specialist domains",
            "Tool-specific workflows",
            "Triage systems",
            "Intent-based automation"
        ],
        implementation_status="implemented"
    ),

    PatternType.PARALLELIZATION: PatternMetadata(
        pattern_type=PatternType.PARALLELIZATION,
        name="Parallelization",
        description="Split large jobs into independent chunks processed simultaneously",
        complexity=PatternComplexity.MEDIUM,
        use_cases=[
            "Large-scale data processing",
            "Document analysis at scale",
            "Research automation",
            "Web scraping"
        ],
        pros=[
            "Significant speed improvements (2-4x)",
            "Scalable to available resources",
            "Efficient for independent tasks",
            "Good cost/performance ratio"
        ],
        cons=[
            "Coordination overhead",
            "Difficult to unify heterogeneous outputs",
            "Requires independent subtasks",
            "Debugging is more complex"
        ],
        best_for=[
            "Embarrassingly parallel tasks",
            "Batch processing",
            "Testing frameworks",
            "Data enrichment"
        ],
        implementation_status="implemented"
    ),

    PatternType.REFLECTION: PatternMetadata(
        pattern_type=PatternType.REFLECTION,
        name="Reflection",
        description="Generate draft, critique against quality standards, revise, repeat",
        complexity=PatternComplexity.MEDIUM,
        use_cases=[
            "Code generation with quality checks",
            "Content writing and editing",
            "Creative tasks requiring iteration",
            "High-quality output generation"
        ],
        pros=[
            "Continuous quality improvement",
            "Self-correction capabilities",
            "Explicit quality criteria",
            "Produces higher quality outputs"
        ],
        cons=[
            "Multiple LLM calls increase cost",
            "Slower than single-pass generation",
            "Can get stuck in local optima",
            "Quality rubric design is critical"
        ],
        best_for=[
            "Quality-critical tasks",
            "Iterative refinement workflows",
            "Creative generation",
            "High-stakes outputs"
        ],
        implementation_status="implemented"
    ),

    PatternType.TOOL_USE: PatternMetadata(
        pattern_type=PatternType.TOOL_USE,
        name="Tool Use",
        description="Structured external tool invocation with result integration",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["API integration", "Database queries", "File operations", "Web scraping"],
        pros=["Extends capabilities beyond LLM", "Deterministic actions", "Access to real-time data"],
        cons=["Tool reliability dependency", "Error handling complexity", "Security considerations"],
        best_for=["External system integration", "Deterministic operations", "Data retrieval"],
        implementation_status="implemented"
    ),

    PatternType.PLANNING: PatternMetadata(
        pattern_type=PatternType.PLANNING,
        name="Planning",
        description="Multi-step plan generation before execution",
        complexity=PatternComplexity.HIGH,
        use_cases=["Complex task orchestration", "Project planning", "Resource allocation"],
        pros=["Holistic approach", "Anticipates dependencies", "Optimizes resource usage"],
        cons=["Upfront overhead", "Plans may need adjustment", "Rigid execution"],
        best_for=["Multi-step projects", "Resource-constrained tasks", "Long-running processes"],
        implementation_status="implemented"
    ),

    PatternType.MULTI_AGENT_COLLABORATION: PatternMetadata(
        pattern_type=PatternType.MULTI_AGENT_COLLABORATION,
        name="Multi-Agent Collaboration",
        description="Coordinated workflows with multiple specialized agents",
        complexity=PatternComplexity.HIGH,
        use_cases=["Complex problem solving", "Diverse expertise needs", "Large-scale projects"],
        pros=["Leverages specialization", "Parallel progress", "Comprehensive coverage"],
        cons=["Coordination overhead", "Communication complexity", "Potential conflicts"],
        best_for=["Cross-domain tasks", "Large complex projects", "Specialized workflows"],
        implementation_status="implemented"
    ),

    PatternType.EVALUATION: PatternMetadata(
        pattern_type=PatternType.EVALUATION,
        name="Evaluation",
        description="Quality assessment and scoring of outputs",
        complexity=PatternComplexity.LOW,
        use_cases=["Quality assurance", "Performance measurement", "Output validation"],
        pros=["Objective assessment", "Quantifiable metrics", "Continuous improvement"],
        cons=["Rubric design challenges", "Subjective criteria", "Overhead cost"],
        best_for=["Quality-critical outputs", "Performance tracking", "A/B testing"],
        implementation_status="implemented"
    ),

    PatternType.SELF_CONSISTENCY: PatternMetadata(
        pattern_type=PatternType.SELF_CONSISTENCY,
        name="Self-Consistency",
        description="Generate multiple solution paths and vote on best answer",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Reasoning tasks", "Math problems", "Logical puzzles"],
        pros=["Improved reliability", "Error reduction", "Consensus-based confidence"],
        cons=["Higher cost (multiple calls)", "Slower execution", "May miss edge cases"],
        best_for=["High-stakes decisions", "Reasoning problems", "Uncertainty reduction"],
        implementation_status="implemented"
    ),

    PatternType.TREE_OF_THOUGHTS: PatternMetadata(
        pattern_type=PatternType.TREE_OF_THOUGHTS,
        name="Tree of Thoughts",
        description="Branching reasoning exploration with backtracking",
        complexity=PatternComplexity.HIGH,
        use_cases=["Strategic planning", "Complex problem solving", "Game playing"],
        pros=["Explores multiple paths", "Systematic exploration", "Can backtrack"],
        cons=["Computationally expensive", "Complex to implement", "May explore bad paths"],
        best_for=["Strategic decisions", "Complex reasoning", "Optimization problems"],
        implementation_status="implemented"
    ),

    PatternType.RAG: PatternMetadata(
        pattern_type=PatternType.RAG,
        name="RAG (Retrieval-Augmented Generation)",
        description="Retrieve relevant context before generation for grounded responses",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Knowledge-intensive tasks", "QA systems", "Document-based chat"],
        pros=["Factually grounded", "Up-to-date information", "Reduced hallucination"],
        cons=["Retrieval quality dependency", "Context limits", "Requires knowledge base"],
        best_for=["Question answering", "Knowledge retrieval", "Document analysis"],
        implementation_status="implemented"
    ),

    PatternType.REACT: PatternMetadata(
        pattern_type=PatternType.REACT,
        name="ReAct (Reasoning + Acting)",
        description="Interleave reasoning traces with actions",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Interactive tasks", "Agent systems", "Tool-based workflows"],
        pros=["Transparent reasoning", "Action-oriented", "Iterative refinement"],
        cons=["Can get stuck in loops", "Requires good action space", "Verbose"],
        best_for=["Agent tasks", "Interactive systems", "Tool orchestration"],
        implementation_status="implemented"
    ),

    PatternType.CHAIN_OF_THOUGHT: PatternMetadata(
        pattern_type=PatternType.CHAIN_OF_THOUGHT,
        name="Chain of Thought",
        description="Explicit step-by-step reasoning before final answer",
        complexity=PatternComplexity.LOW,
        use_cases=["Math problems", "Logical reasoning", "Step-by-step explanations"],
        pros=["Transparent reasoning", "Easier to verify", "Improves accuracy"],
        cons=["Longer outputs", "May be verbose", "Requires prompting"],
        best_for=["Reasoning tasks", "Educational content", "Explainable AI"],
        implementation_status="implemented"
    ),

    PatternType.CONSTITUTIONAL_AI: PatternMetadata(
        pattern_type=PatternType.CONSTITUTIONAL_AI,
        name="Constitutional AI",
        description="Value-aligned decision making with ethical principles",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Safety-critical systems", "Ethical AI", "Moderation"],
        pros=["Aligned with values", "Ethical safeguards", "Reduces harm"],
        cons=["Principle design challenges", "May be overly cautious", "Revision overhead"],
        best_for=["Safety-critical apps", "Public-facing systems", "Ethical AI"],
        implementation_status="implemented"
    ),

    PatternType.META_PROMPTING: PatternMetadata(
        pattern_type=PatternType.META_PROMPTING,
        name="Meta-Prompting",
        description="Dynamic prompt generation based on task characteristics",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Adaptive systems", "Prompt optimization", "Task-specific prompting"],
        pros=["Optimized prompts", "Task-adaptive", "Better performance"],
        cons=["Meta-prompt quality dependency", "Additional overhead", "Complexity"],
        best_for=["Varied task types", "Prompt optimization", "Adaptive systems"],
        implementation_status="implemented"
    ),

    PatternType.HIERARCHICAL_DECOMPOSITION: PatternMetadata(
        pattern_type=PatternType.HIERARCHICAL_DECOMPOSITION,
        name="Hierarchical Task Decomposition",
        description="Recursive breakdown of complex tasks into subtask hierarchies",
        complexity=PatternComplexity.HIGH,
        use_cases=["Project planning", "Complex workflows", "Systematic problem solving"],
        pros=["Structured approach", "Manageable subtasks", "Clear dependencies"],
        cons=["Decomposition quality critical", "May over-decompose", "Tree management"],
        best_for=["Large complex projects", "Systematic workflows", "Planning systems"],
        implementation_status="implemented"
    ),

    PatternType.ENSEMBLE_METHODS: PatternMetadata(
        pattern_type=PatternType.ENSEMBLE_METHODS,
        name="Ensemble Methods",
        description="Combine multiple agent outputs through voting or averaging",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Robustness improvement", "Consensus building", "Error reduction"],
        pros=["Improved robustness", "Diversity benefits", "Reduced variance"],
        cons=["Higher cost", "Slower execution", "Combination strategy matters"],
        best_for=["High-reliability needs", "Uncertainty reduction", "Consensus tasks"],
        implementation_status="implemented"
    ),

    PatternType.FEEDBACK_LOOPS: PatternMetadata(
        pattern_type=PatternType.FEEDBACK_LOOPS,
        name="Feedback Loops",
        description="Continuous improvement through iterative feedback",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Iterative refinement", "Learning systems", "Continuous improvement"],
        pros=["Continuous improvement", "Adaptive", "Learning from mistakes"],
        cons=["May converge slowly", "Feedback quality critical", "Iteration overhead"],
        best_for=["Learning systems", "Iterative tasks", "Continuous optimization"],
        implementation_status="implemented"
    ),

    PatternType.MEMORY_AUGMENTED: PatternMetadata(
        pattern_type=PatternType.MEMORY_AUGMENTED,
        name="Memory-Augmented",
        description="Long-term context retention across interactions",
        complexity=PatternComplexity.MEDIUM,
        use_cases=["Conversational AI", "Long-running tasks", "Stateful systems"],
        pros=["Context continuity", "Learning from history", "Personalization"],
        cons=["Memory management complexity", "Privacy concerns", "Storage costs"],
        best_for=["Conversational AI", "Long-term projects", "Personalized systems"],
        implementation_status="implemented"
    ),

    PatternType.ADAPTIVE_LEARNING: PatternMetadata(
        pattern_type=PatternType.ADAPTIVE_LEARNING,
        name="Adaptive Learning",
        description="Performance-based pattern selection and optimization",
        complexity=PatternComplexity.HIGH,
        use_cases=["Meta-learning", "Performance optimization", "Adaptive systems"],
        pros=["Learns best approaches", "Performance improvement", "Adaptive"],
        cons=["Requires performance data", "Cold start problem", "Complexity"],
        best_for=["Long-running systems", "Performance optimization", "Adaptive AI"],
        implementation_status="implemented"
    ),
}


# ============================================================================
# PATTERN ORCHESTRATOR
# ============================================================================

class AgenticPatternOrchestrator:
    """
    Orchestrates selection and execution of agentic patterns.

    Recommends best pattern based on task characteristics and
    manages pattern execution with monitoring.
    """

    def __init__(self):
        self.patterns: Dict[PatternType, AgenticPattern] = {
            # Core 4 patterns
            PatternType.PROMPT_CHAINING: PromptChainingPattern(),
            PatternType.ROUTING: RoutingPattern(),
            PatternType.PARALLELIZATION: ParallelizationPattern(),
            PatternType.REFLECTION: ReflectionPattern(),

            # Extended patterns (5-20)
            PatternType.TOOL_USE: ToolUsePattern(),
            PatternType.PLANNING: PlanningPattern(),
            PatternType.MULTI_AGENT_COLLABORATION: MultiAgentCollaborationPattern(),
            PatternType.EVALUATION: EvaluationPattern(),
            PatternType.SELF_CONSISTENCY: SelfConsistencyPattern(),
            PatternType.TREE_OF_THOUGHTS: TreeOfThoughtsPattern(),
            PatternType.RAG: RAGPattern(),
            PatternType.REACT: ReActPattern(),
            PatternType.CHAIN_OF_THOUGHT: ChainOfThoughtPattern(),
            PatternType.CONSTITUTIONAL_AI: ConstitutionalAIPattern(),
            PatternType.META_PROMPTING: MetaPromptingPattern(),
            PatternType.HIERARCHICAL_DECOMPOSITION: HierarchicalDecompositionPattern(),
            PatternType.ENSEMBLE_METHODS: EnsembleMethodsPattern(),
            PatternType.FEEDBACK_LOOPS: FeedbackLoopsPattern(),
            PatternType.MEMORY_AUGMENTED: MemoryAugmentedPattern(),
            PatternType.ADAPTIVE_LEARNING: AdaptiveLearningPattern(),
        }

        self.execution_history: List[Dict[str, Any]] = []

    def recommend_pattern(
        self,
        task_description: str,
        task_complexity: str = "medium",
        requires_quality: bool = False,
        time_sensitive: bool = False,
        multiple_domains: bool = False
    ) -> List[PatternType]:
        """
        Recommend best pattern(s) for a task.

        Args:
            task_description: Description of the task
            task_complexity: "low", "medium", "high"
            requires_quality: Whether quality is critical
            time_sensitive: Whether speed is critical
            multiple_domains: Whether task spans multiple domains

        Returns:
            List of recommended patterns (ordered by relevance)
        """
        recommendations = []

        # Routing for multi-domain tasks
        if multiple_domains:
            recommendations.append(PatternType.ROUTING)

        # Parallelization for time-sensitive tasks
        if time_sensitive and task_complexity in ["medium", "high"]:
            recommendations.append(PatternType.PARALLELIZATION)

        # Reflection for quality-critical tasks
        if requires_quality:
            recommendations.append(PatternType.REFLECTION)

        # Prompt chaining for sequential workflows
        if any(word in task_description.lower() for word in ["step", "then", "after", "pipeline"]):
            recommendations.append(PatternType.PROMPT_CHAINING)

        # Default to routing if no specific pattern matches
        if not recommendations:
            recommendations.append(PatternType.ROUTING)

        logger.info(f"Recommended patterns: {[p.value for p in recommendations]}")

        return recommendations

    async def execute_pattern(
        self,
        pattern_type: PatternType,
        *args,
        **kwargs
    ) -> PatternExecutionResult:
        """Execute a specific pattern"""
        if pattern_type not in self.patterns:
            raise ValueError(f"Pattern {pattern_type} not implemented")

        pattern = self.patterns[pattern_type]
        result = await pattern.execute(*args, **kwargs)

        # Record execution
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'pattern': pattern_type.value,
            'success': result.success,
            'execution_time_ms': result.execution_time_ms
        })

        return result

    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern usage statistics"""
        if not self.execution_history:
            return {}

        stats = {}
        for pattern_type in PatternType:
            pattern_executions = [
                e for e in self.execution_history
                if e['pattern'] == pattern_type.value
            ]

            if pattern_executions:
                success_rate = sum(1 for e in pattern_executions if e['success']) / len(pattern_executions)
                avg_time = sum(e['execution_time_ms'] for e in pattern_executions) / len(pattern_executions)

                stats[pattern_type.value] = {
                    'total_executions': len(pattern_executions),
                    'success_rate': success_rate,
                    'avg_execution_time_ms': avg_time
                }

        return stats


async def main():
    """Demo of agentic patterns"""
    print("\n" + "=" * 70)
    print("AGENTIC PATTERNS SYSTEM DEMO")
    print("=" * 70)
    print()

    orchestrator = AgenticPatternOrchestrator()

    # Demo 1: Prompt Chaining
    print("Demo 1: Prompt Chaining Pattern")
    print("-" * 70)

    chain_steps = [
        {"description": "Analyze requirements", "validate": True},
        {"description": "Design architecture", "validate": True},
        {"description": "Implement solution", "validate": True},
        {"description": "Test implementation", "validate": True}
    ]

    result = await orchestrator.execute_pattern(
        PatternType.PROMPT_CHAINING,
        task_description="Build authentication system",
        chain_steps=chain_steps
    )

    print(f"Success: {result.success}")
    print(f"Steps executed: {result.steps_executed}/{len(chain_steps)}")
    print(f"Execution time: {result.execution_time_ms:.1f}ms")
    print()

    # Demo 2: Routing Pattern
    print("Demo 2: Routing Pattern")
    print("-" * 70)

    result = await orchestrator.execute_pattern(
        PatternType.ROUTING,
        request="I need to test my web application for performance issues"
    )

    print(f"Success: {result.success}")
    print(f"Routed to: {result.output.get('agent_type')}")
    print(f"Confidence: {result.output.get('confidence'):.2f}")
    print()

    # Demo 3: Pattern Recommendation
    print("Demo 3: Pattern Recommendation")
    print("-" * 70)

    recommendations = orchestrator.recommend_pattern(
        task_description="Process 10,000 documents and generate summaries",
        task_complexity="high",
        time_sensitive=True
    )

    print(f"Recommended patterns: {[p.value for p in recommendations]}")
    print()

    # Show stats
    print("Pattern Usage Statistics")
    print("-" * 70)
    stats = orchestrator.get_pattern_stats()
    print(json.dumps(stats, indent=2))
    print()


if __name__ == "__main__":
    asyncio.run(main())
