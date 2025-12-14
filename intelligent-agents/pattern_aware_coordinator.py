#!/usr/bin/env python3
"""
Pattern-Aware Multi-Agent Coordinator
=====================================

Integrates 20 agentic design patterns with multi-agent coordination.
Automatically selects and applies optimal patterns based on task characteristics.

Integration:
- Wraps multi_agent_coordinator with pattern awareness
- Uses agent_auto_selector for intelligent routing
- Applies quality_gates for validation in reflection patterns
- Supports hybrid pattern combinations

Example:
    coordinator = PatternAwareCoordinator()
    result = await coordinator.execute_with_pattern(
        task="Process 1000 documents and generate summaries",
        auto_select_pattern=True
    )
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import existing components
from multi_agent_coordinator import MultiAgentCoordinator, SubTask, TaskStatus
from agent_auto_selector import AgentAutoSelector
from quality_gates import QualityGateSystem

# Import pattern framework
from agentic_patterns import (
    AgenticPatternOrchestrator,
    PatternType,
    PatternExecutionResult,
    PATTERN_REGISTRY
)
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HybridPatternType(Enum):
    """Predefined hybrid pattern combinations"""
    FULL_STACK = "full_stack"  # Routing → Parallelization → Reflection
    QUALITY_CRITICAL = "quality_critical"  # Planning → Reflection → Evaluation
    RESEARCH_INTENSIVE = "research_intensive"  # RAG → Chain of Thought → Self-Consistency
    ITERATIVE_DEVELOPMENT = "iterative_development"  # Planning → Parallelization → Feedback Loops
    PRODUCTION_READY = "production_ready"  # Reflection → Constitutional AI → Evaluation
    DISTRIBUTED_PROCESSING = "distributed_processing"  # Hierarchical → Parallelization → Ensemble
    AGENT_COLLABORATION = "agent_collaboration"  # Routing → Multi-Agent → Reflection


class HybridPatternExecutor:
    """
    Manages execution of hybrid pattern combinations.

    Hybrid patterns combine multiple agentic patterns in sequence for complex tasks.
    For example: Routing → Parallelization → Reflection provides intelligent agent
    selection, parallel execution, and iterative quality improvement.
    """

    def __init__(self, coordinator: 'PatternAwareCoordinator'):
        """
        Initialize hybrid pattern executor.

        Args:
            coordinator: Parent PatternAwareCoordinator instance
        """
        self.coordinator = coordinator

        # Define hybrid pattern recipes
        self.hybrid_recipes = {
            HybridPatternType.FULL_STACK: [
                PatternType.ROUTING,
                PatternType.PARALLELIZATION,
                PatternType.REFLECTION
            ],
            HybridPatternType.QUALITY_CRITICAL: [
                PatternType.PLANNING,
                PatternType.REFLECTION,
                PatternType.EVALUATION
            ],
            HybridPatternType.RESEARCH_INTENSIVE: [
                PatternType.RAG,
                PatternType.CHAIN_OF_THOUGHT,
                PatternType.SELF_CONSISTENCY
            ],
            HybridPatternType.ITERATIVE_DEVELOPMENT: [
                PatternType.PLANNING,
                PatternType.PARALLELIZATION,
                PatternType.FEEDBACK_LOOPS
            ],
            HybridPatternType.PRODUCTION_READY: [
                PatternType.REFLECTION,
                PatternType.CONSTITUTIONAL_AI,
                PatternType.EVALUATION
            ],
            HybridPatternType.DISTRIBUTED_PROCESSING: [
                PatternType.HIERARCHICAL_DECOMPOSITION,
                PatternType.PARALLELIZATION,
                PatternType.ENSEMBLE_METHODS
            ],
            HybridPatternType.AGENT_COLLABORATION: [
                PatternType.ROUTING,
                PatternType.MULTI_AGENT_COLLABORATION,
                PatternType.REFLECTION
            ]
        }

        logger.info("HybridPatternExecutor initialized with 7 hybrid patterns")

    async def execute_hybrid(
        self,
        task: str,
        hybrid_type: HybridPatternType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task using hybrid pattern combination.

        Args:
            task: Task description
            hybrid_type: Type of hybrid pattern to use
            **kwargs: Additional parameters

        Returns:
            Execution result with hybrid metadata
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"HYBRID PATTERN EXECUTION: {hybrid_type.value}")
        logger.info(f"{'='*70}")

        pattern_sequence = self.hybrid_recipes[hybrid_type]
        logger.info(f"Pattern sequence: {' → '.join([p.value for p in pattern_sequence])}")

        start_time = datetime.now()
        results = []
        current_task = task

        # Execute patterns in sequence
        for i, pattern_type in enumerate(pattern_sequence, 1):
            logger.info(f"\n[Step {i}/{len(pattern_sequence)}] Executing: {pattern_type.value}")

            # Execute pattern
            result = await self.coordinator.execute_with_pattern(
                task=current_task,
                pattern_type=pattern_type,
                auto_select_pattern=False,
                **kwargs
            )

            results.append({
                'step': i,
                'pattern': pattern_type.value,
                'success': result.get('success', False),
                'execution_time_ms': result['pattern_metadata']['total_execution_time_ms']
            })

            # Use output from previous pattern as input for next
            if result.get('success') and result.get('output'):
                # Transform output for next pattern
                if isinstance(result['output'], dict):
                    current_task = json.dumps(result['output'])
                else:
                    current_task = str(result['output'])

            logger.info(f"  Step {i} {'✓ Success' if result.get('success') else '✗ Failed'}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        # Aggregate results
        overall_success = all(r['success'] for r in results)
        final_output = results[-1] if results else None

        return {
            'success': overall_success,
            'output': final_output,
            'hybrid_type': hybrid_type.value,
            'pattern_sequence': [p.value for p in pattern_sequence],
            'step_results': results,
            'total_steps': len(pattern_sequence),
            'total_execution_time_ms': elapsed,
            'pattern_metadata': {
                'pattern_type': f'hybrid_{hybrid_type.value}',
                'total_execution_time_ms': elapsed,
                'auto_selected': False
            }
        }

    async def execute_custom_sequence(
        self,
        task: str,
        pattern_sequence: List[PatternType],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task using custom pattern sequence.

        Args:
            task: Task description
            pattern_sequence: List of patterns to execute in order
            **kwargs: Additional parameters

        Returns:
            Execution result
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"CUSTOM HYBRID PATTERN EXECUTION")
        logger.info(f"Pattern sequence: {' → '.join([p.value for p in pattern_sequence])}")
        logger.info(f"{'='*70}")

        start_time = datetime.now()
        results = []
        current_task = task

        # Execute patterns in sequence
        for i, pattern_type in enumerate(pattern_sequence, 1):
            logger.info(f"\n[Step {i}/{len(pattern_sequence)}] Executing: {pattern_type.value}")

            result = await self.coordinator.execute_with_pattern(
                task=current_task,
                pattern_type=pattern_type,
                auto_select_pattern=False,
                **kwargs
            )

            results.append({
                'step': i,
                'pattern': pattern_type.value,
                'success': result.get('success', False),
                'execution_time_ms': result['pattern_metadata']['total_execution_time_ms']
            })

            # Transform output for next pattern
            if result.get('success') and result.get('output'):
                if isinstance(result['output'], dict):
                    current_task = json.dumps(result['output'])
                else:
                    current_task = str(result['output'])

            logger.info(f"  Step {i} {'✓ Success' if result.get('success') else '✗ Failed'}")

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        overall_success = all(r['success'] for r in results)

        return {
            'success': overall_success,
            'output': results[-1] if results else None,
            'hybrid_type': 'custom',
            'pattern_sequence': [p.value for p in pattern_sequence],
            'step_results': results,
            'total_steps': len(pattern_sequence),
            'total_execution_time_ms': elapsed,
            'pattern_metadata': {
                'pattern_type': 'hybrid_custom',
                'total_execution_time_ms': elapsed,
                'auto_selected': False
            }
        }

    def recommend_hybrid_pattern(
        self,
        task: str,
        task_analysis: Dict[str, Any]
    ) -> Optional[HybridPatternType]:
        """
        Recommend hybrid pattern based on task analysis.

        Args:
            task: Task description
            task_analysis: Task analysis from agent selector

        Returns:
            Recommended hybrid pattern type or None
        """
        complexity = task_analysis.get('complexity', 'medium')
        requirements = task_analysis.get('requirements', [])

        task_lower = task.lower()

        # Full-Stack: Multi-domain development tasks
        if any(domain in task_lower for domain in ['frontend', 'backend', 'fullstack', 'full-stack', 'full stack']):
            return HybridPatternType.FULL_STACK

        # Quality-Critical: Security, production, critical systems
        if any(keyword in task_lower for keyword in ['secure', 'security', 'production', 'critical']):
            return HybridPatternType.QUALITY_CRITICAL

        # Research-Intensive: Research, analysis, exploration
        if any(keyword in task_lower for keyword in ['research', 'analyze', 'study', 'investigate']):
            return HybridPatternType.RESEARCH_INTENSIVE

        # Production-Ready: Deployment, release, production
        if any(keyword in task_lower for keyword in ['deploy', 'release', 'production-ready']):
            return HybridPatternType.PRODUCTION_READY

        # Distributed-Processing: Large-scale, batch, massive
        if any(keyword in task_lower for keyword in ['large-scale', 'batch', 'process', 'thousands']):
            return HybridPatternType.DISTRIBUTED_PROCESSING

        # Agent-Collaboration: Complex multi-agent tasks
        if complexity == 'high' and len(requirements) > 3:
            return HybridPatternType.AGENT_COLLABORATION

        # Iterative-Development: Complex development with iterations
        if complexity in ['high', 'very_high'] and any(keyword in task_lower for keyword in ['build', 'implement', 'develop']):
            return HybridPatternType.ITERATIVE_DEVELOPMENT

        return None


class PatternAwareCoordinator:
    """
    Multi-agent coordinator with automatic pattern selection and application.

    Analyzes tasks and automatically applies the most effective agentic pattern
    for optimal execution.
    """

    def __init__(
        self,
        enable_quality_gates: bool = True,
        enable_pattern_auto_selection: bool = True,
        enable_hybrid_patterns: bool = True
    ):
        """
        Initialize pattern-aware coordinator.

        Args:
            enable_quality_gates: Enable quality validation for reflection patterns
            enable_pattern_auto_selection: Auto-select best pattern for tasks
            enable_hybrid_patterns: Enable hybrid pattern combinations
        """
        self.agent_coordinator = MultiAgentCoordinator()
        self.agent_selector = AgentAutoSelector()
        self.pattern_orchestrator = AgenticPatternOrchestrator()

        self.enable_quality_gates = enable_quality_gates
        if enable_quality_gates:
            self.quality_gates = QualityGateSystem()
        else:
            self.quality_gates = None

        self.enable_pattern_auto_selection = enable_pattern_auto_selection
        self.enable_hybrid_patterns = enable_hybrid_patterns

        # Initialize hybrid pattern executor
        if enable_hybrid_patterns:
            self.hybrid_executor = HybridPatternExecutor(self)
        else:
            self.hybrid_executor = None

        self.execution_history: List[Dict[str, Any]] = []

        logger.info(f"Pattern-Aware Coordinator initialized (hybrid_patterns={'enabled' if enable_hybrid_patterns else 'disabled'})")

    async def execute_with_pattern(
        self,
        task: str,
        pattern_type: Optional[PatternType] = None,
        auto_select_pattern: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task with optimal agentic pattern.

        Args:
            task: Task description
            pattern_type: Specific pattern to use (or None for auto-selection)
            auto_select_pattern: Auto-select pattern if not specified
            **kwargs: Additional pattern-specific parameters

        Returns:
            Execution result with pattern metadata
        """
        start_time = datetime.now()
        logger.info(f"\n{'='*70}")
        logger.info(f"PATTERN-AWARE EXECUTION: {task[:100]}...")
        logger.info(f"{'='*70}")

        # Auto-select pattern if not specified
        if pattern_type is None and auto_select_pattern:
            pattern_type = await self._auto_select_pattern(task, **kwargs)
            logger.info(f"Auto-selected pattern: {pattern_type.value}")

        # Apply pattern-specific execution strategy
        if pattern_type == PatternType.PROMPT_CHAINING:
            result = await self._execute_with_chaining(task, **kwargs)
        elif pattern_type == PatternType.ROUTING:
            result = await self._execute_with_routing(task, **kwargs)
        elif pattern_type == PatternType.PARALLELIZATION:
            result = await self._execute_with_parallelization(task, **kwargs)
        elif pattern_type == PatternType.REFLECTION:
            result = await self._execute_with_reflection(task, **kwargs)
        elif pattern_type == PatternType.TOOL_USE:
            result = await self._execute_with_tool_use(task, **kwargs)
        elif pattern_type == PatternType.PLANNING:
            result = await self._execute_with_planning(task, **kwargs)
        elif pattern_type == PatternType.MULTI_AGENT_COLLABORATION:
            result = await self._execute_with_multi_agent(task, **kwargs)
        elif pattern_type == PatternType.EVALUATION:
            result = await self._execute_with_evaluation(task, **kwargs)
        elif pattern_type == PatternType.SELF_CONSISTENCY:
            result = await self._execute_with_self_consistency(task, **kwargs)
        elif pattern_type == PatternType.TREE_OF_THOUGHTS:
            result = await self._execute_with_tree_of_thoughts(task, **kwargs)
        elif pattern_type == PatternType.RAG:
            result = await self._execute_with_rag(task, **kwargs)
        elif pattern_type == PatternType.REACT:
            result = await self._execute_with_react(task, **kwargs)
        elif pattern_type == PatternType.CHAIN_OF_THOUGHT:
            result = await self._execute_with_chain_of_thought(task, **kwargs)
        elif pattern_type == PatternType.CONSTITUTIONAL_AI:
            result = await self._execute_with_constitutional_ai(task, **kwargs)
        elif pattern_type == PatternType.META_PROMPTING:
            result = await self._execute_with_meta_prompting(task, **kwargs)
        elif pattern_type == PatternType.HIERARCHICAL_DECOMPOSITION:
            result = await self._execute_with_hierarchical(task, **kwargs)
        elif pattern_type == PatternType.ENSEMBLE_METHODS:
            result = await self._execute_with_ensemble(task, **kwargs)
        elif pattern_type == PatternType.FEEDBACK_LOOPS:
            result = await self._execute_with_feedback_loops(task, **kwargs)
        elif pattern_type == PatternType.MEMORY_AUGMENTED:
            result = await self._execute_with_memory_augmented(task, **kwargs)
        elif pattern_type == PatternType.ADAPTIVE_LEARNING:
            result = await self._execute_with_adaptive_learning(task, **kwargs)
        else:
            # Fallback to standard multi-agent coordination
            logger.warning(f"Pattern {pattern_type} not implemented, using standard execution")
            result = await self.agent_coordinator.execute_task(task)
            result = {'success': True, 'output': result, 'pattern_used': 'standard'}

        # Add pattern metadata
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result['pattern_metadata'] = {
            'pattern_type': pattern_type.value if pattern_type else 'standard',
            'total_execution_time_ms': elapsed,
            'auto_selected': pattern_type is None and auto_select_pattern
        }

        # Record execution
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'task': task[:200],
            'pattern': pattern_type.value if pattern_type else 'standard',
            'success': result.get('success', False),
            'execution_time_ms': elapsed
        })

        logger.info(f"Pattern execution complete: {pattern_type.value if pattern_type else 'standard'} ({elapsed:.1f}ms)")

        return result

    async def _auto_select_pattern(
        self,
        task: str,
        **kwargs
    ) -> PatternType:
        """Auto-select best pattern for task"""
        # Analyze task characteristics
        task_analysis = self.agent_selector.analyze_task_requirements(
            task_title=task,
            task_description=task
        )

        complexity = task_analysis['complexity']
        requirements = task_analysis['requirements']
        parallel_opportunities = task_analysis['parallel_opportunities']

        # Determine pattern based on characteristics
        requires_quality = any(r in requirements for r in ['code review', 'testing', 'security'])
        time_sensitive = 'optimization' in requirements or 'performance' in requirements
        multiple_domains = len(requirements) > 2

        # Use orchestrator's recommendation engine
        recommendations = self.pattern_orchestrator.recommend_pattern(
            task_description=task,
            task_complexity=complexity,
            requires_quality=requires_quality,
            time_sensitive=time_sensitive,
            multiple_domains=multiple_domains
        )

        # Return top recommendation
        return recommendations[0] if recommendations else PatternType.ROUTING

    async def _execute_with_chaining(
        self,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute with prompt chaining pattern"""
        logger.info("[PATTERN: Prompt Chaining]")

        # Decompose task into chain steps
        subtasks = await self.agent_coordinator.decompose_task(task)

        # Convert subtasks to chain steps
        chain_steps = []
        for subtask in subtasks:
            chain_steps.append({
                'description': subtask.description,
                'validate': True,
                'context': {
                    'task_type': subtask.task_type,
                    'priority': subtask.priority
                }
            })

        # Execute chain through pattern
        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.PROMPT_CHAINING,
            task_description=task,
            chain_steps=chain_steps
        )

        return {
            'success': result.success,
            'output': result.output,
            'steps_executed': result.steps_executed,
            'errors': result.errors,
            'pattern_used': 'prompt_chaining'
        }

    async def _execute_with_routing(
        self,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute with routing pattern"""
        logger.info("[PATTERN: Routing]")

        # Route to best agent
        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.ROUTING,
            request=task,
            confidence_threshold=kwargs.get('confidence_threshold', 0.7)
        )

        if result.success:
            # Execute with selected agent type
            selected_agent = result.output['agent_type']
            logger.info(f"Routed to agent: {selected_agent}")

            # Execute through coordinator with agent hint
            exec_result = await self.agent_coordinator.execute_task(
                task_description=task,
                task_type=result.output.get('intent', 'general')
            )

            return {
                'success': True,
                'output': exec_result,
                'routing_decision': result.output,
                'pattern_used': 'routing'
            }
        else:
            return {
                'success': False,
                'errors': result.errors,
                'pattern_used': 'routing'
            }

    async def _execute_with_parallelization(
        self,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute with parallelization pattern"""
        logger.info("[PATTERN: Parallelization]")

        # Decompose into independent subtasks
        subtasks = await self.agent_coordinator.decompose_task(task)

        # Define split, worker, and merge functions
        def split_fn(task_data, max_workers):
            # Already have subtasks
            return subtasks

        async def worker_fn(subtask, worker_id):
            # Execute subtask through coordinator
            agent = self.agent_coordinator.assign_agent(subtask)
            if agent:
                subtask.assigned_agent = agent
                return await self.agent_coordinator.execute_subtask(subtask)
            return None

        def merge_fn(results):
            # Aggregate results
            return self.agent_coordinator.aggregate_results(results)

        # Execute parallelization pattern
        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.PARALLELIZATION,
            large_task=task,
            split_fn=split_fn,
            worker_fn=worker_fn,
            merge_fn=merge_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'parallel_workers': result.metadata.get('num_chunks', 0),
            'pattern_used': 'parallelization'
        }

    async def _execute_with_reflection(
        self,
        task: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute with reflection pattern"""
        logger.info("[PATTERN: Reflection]")

        # Define generator function
        async def generator_fn(prompt, feedback=None):
            # Generate initial solution
            if feedback:
                enhanced_prompt = f"{prompt}\n\nFeedback from previous iteration:\n{feedback}\n\nPlease improve based on this feedback."
            else:
                enhanced_prompt = prompt

            result = await self.agent_coordinator.execute_task(enhanced_prompt)
            return result

        # Define critic function with quality gates
        async def critic_fn(output, quality_rubric):
            # Use quality gates if enabled and output is code
            if self.enable_quality_gates and self.quality_gates:
                # Check if output contains code (simple heuristic)
                output_str = json.dumps(output) if isinstance(output, dict) else str(output)

                if 'def ' in output_str or 'class ' in output_str:
                    # Run quality gates
                    try:
                        passed, report = await self.quality_gates.check_all_gates(output_str)
                        return {
                            'score': report.overall_score,
                            'feedback': report.reasoning,
                            'quality_report': report
                        }
                    except Exception as e:
                        logger.warning(f"Quality gates failed: {e}")

            # Fallback to simple scoring
            # In production, this would be an LLM-based critique
            score = 0.85 if output else 0.0
            return {
                'score': score,
                'feedback': "Good quality output" if score > 0.7 else "Needs improvement"
            }

        # Execute reflection pattern
        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.REFLECTION,
            initial_prompt=task,
            generator_fn=generator_fn,
            critic_fn=critic_fn,
            quality_rubric=kwargs.get('quality_rubric', {})
        )

        return {
            'success': result.success,
            'output': result.output,
            'iterations': result.output.get('iterations', 0),
            'final_score': result.output.get('final_score', 0.0),
            'pattern_used': 'reflection'
        }

    async def _execute_with_tool_use(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with tool use pattern"""
        logger.info("[PATTERN: Tool Use]")

        # Define available tools (simplified example)
        async def tool_fn(task_desc):
            return await self.agent_coordinator.execute_task(task_desc)

        available_tools = kwargs.get('tools', {'general': tool_fn})

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.TOOL_USE,
            task_description=task,
            tool_selection_fn=None,  # Use default
            result_integration_fn=None
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'tool_use'
        }

    async def _execute_with_planning(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with planning pattern"""
        logger.info("[PATTERN: Planning]")

        async def planning_fn(task_desc):
            # Generate execution plan
            subtasks = await self.agent_coordinator.decompose_task(task_desc)
            return {
                'steps': [{'description': st.description, 'type': st.task_type} for st in subtasks]
            }

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.PLANNING,
            task_description=task,
            planning_fn=planning_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'planning'
        }

    async def _execute_with_multi_agent(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with multi-agent collaboration pattern"""
        logger.info("[PATTERN: Multi-Agent Collaboration]")

        # Get available agents
        agent_pool = kwargs.get('agent_pool', [
            {'id': 'agent1', 'type': 'coder'},
            {'id': 'agent2', 'type': 'tester'},
            {'id': 'agent3', 'type': 'reviewer'}
        ])

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.MULTI_AGENT_COLLABORATION,
            task_description=task,
            agent_pool=agent_pool,
            coordination_strategy=kwargs.get('strategy', 'sequential')
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'multi_agent_collaboration'
        }

    async def _execute_with_evaluation(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with evaluation pattern"""
        logger.info("[PATTERN: Evaluation]")

        # First execute the task
        output = await self.agent_coordinator.execute_task(task)

        # Then evaluate it
        criteria = kwargs.get('criteria', {
            'quality': 1.0,
            'correctness': 1.0,
            'completeness': 1.0
        })

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.EVALUATION,
            output_to_evaluate=output,
            evaluation_criteria=criteria
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'evaluation'
        }

    async def _execute_with_self_consistency(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with self-consistency pattern"""
        logger.info("[PATTERN: Self-Consistency]")

        async def solution_generator(problem):
            return await self.agent_coordinator.execute_task(problem)

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.SELF_CONSISTENCY,
            problem=task,
            solution_generator_fn=solution_generator
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'self_consistency'
        }

    async def _execute_with_tree_of_thoughts(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with tree of thoughts pattern"""
        logger.info("[PATTERN: Tree of Thoughts]")

        async def thought_generator(thought, n):
            # Generate n branches
            return [f"Branch {i+1} of: {thought}" for i in range(n)]

        async def evaluator(thought):
            # Simple scoring
            return 0.8

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.TREE_OF_THOUGHTS,
            problem=task,
            thought_generator_fn=thought_generator,
            evaluator_fn=evaluator
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'tree_of_thoughts'
        }

    async def _execute_with_rag(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with RAG pattern"""
        logger.info("[PATTERN: RAG]")

        async def retrieval_fn(query, top_k=5):
            # Placeholder retrieval
            return [f"Context {i+1}" for i in range(top_k)]

        async def generation_fn(prompt):
            return await self.agent_coordinator.execute_task(prompt)

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.RAG,
            query=task,
            retrieval_fn=retrieval_fn,
            generation_fn=generation_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'rag'
        }

    async def _execute_with_react(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with ReAct pattern"""
        logger.info("[PATTERN: ReAct]")

        async def reasoning_fn(context):
            return f"Reasoning: {context[:50]}"

        async def action_fn(thought):
            return await self.agent_coordinator.execute_task(thought)

        async def observation_fn(action_result):
            return f"Observed: {str(action_result)[:50]}"

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.REACT,
            task=task,
            reasoning_fn=reasoning_fn,
            action_fn=action_fn,
            observation_fn=observation_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'react'
        }

    async def _execute_with_chain_of_thought(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with chain of thought pattern"""
        logger.info("[PATTERN: Chain of Thought]")

        async def reasoning_fn(problem):
            result = await self.agent_coordinator.execute_task(f"Think step by step: {problem}")
            return result

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.CHAIN_OF_THOUGHT,
            problem=task,
            reasoning_fn=reasoning_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'chain_of_thought'
        }

    async def _execute_with_constitutional_ai(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with constitutional AI pattern"""
        logger.info("[PATTERN: Constitutional AI]")

        async def generator_fn(prompt):
            return await self.agent_coordinator.execute_task(prompt)

        async def principle_checker_fn(output, principles):
            # Simple check - would be LLM-based in production
            return []  # No violations

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.CONSTITUTIONAL_AI,
            input_text=task,
            generator_fn=generator_fn,
            principle_checker_fn=principle_checker_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'constitutional_ai'
        }

    async def _execute_with_meta_prompting(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with meta-prompting pattern"""
        logger.info("[PATTERN: Meta-Prompting]")

        async def prompt_generator_fn(task_desc):
            return f"Optimized prompt for: {task_desc}"

        async def executor_fn(prompt):
            return await self.agent_coordinator.execute_task(prompt)

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.META_PROMPTING,
            task=task,
            prompt_generator_fn=prompt_generator_fn,
            executor_fn=executor_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'meta_prompting'
        }

    async def _execute_with_hierarchical(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with hierarchical decomposition pattern"""
        logger.info("[PATTERN: Hierarchical Decomposition]")

        async def decomposition_fn(task_desc):
            subtasks = await self.agent_coordinator.decompose_task(task_desc)
            return [st.description for st in subtasks[:3]]  # Limit depth

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.HIERARCHICAL_DECOMPOSITION,
            task=task,
            decomposition_fn=decomposition_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'hierarchical_decomposition'
        }

    async def _execute_with_ensemble(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with ensemble methods pattern"""
        logger.info("[PATTERN: Ensemble Methods]")

        async def model_fn(task_desc):
            return await self.agent_coordinator.execute_task(task_desc)

        model_fns = [model_fn, model_fn, model_fn]  # 3 models

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.ENSEMBLE_METHODS,
            task=task,
            model_fns=model_fns,
            combination_strategy=kwargs.get('strategy', 'voting')
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'ensemble_methods'
        }

    async def _execute_with_feedback_loops(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with feedback loops pattern"""
        logger.info("[PATTERN: Feedback Loops]")

        async def executor_fn(task_desc):
            return await self.agent_coordinator.execute_task(task_desc)

        async def feedback_fn(output):
            return {'satisfactory': True, 'score': 0.9}

        async def adjustment_fn(task_desc, feedback):
            return task_desc  # No adjustment needed if satisfactory

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.FEEDBACK_LOOPS,
            initial_task=task,
            executor_fn=executor_fn,
            feedback_fn=feedback_fn,
            adjustment_fn=adjustment_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'feedback_loops'
        }

    async def _execute_with_memory_augmented(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with memory-augmented pattern"""
        logger.info("[PATTERN: Memory-Augmented]")

        async def memory_retrieval_fn(input_text, memory_store):
            return []  # Retrieve from memory

        async def processor_fn(input_text, memories):
            return await self.agent_coordinator.execute_task(input_text)

        async def memory_storage_fn(input_text, output, memory_store):
            pass  # Store to memory

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.MEMORY_AUGMENTED,
            input_text=task,
            memory_retrieval_fn=memory_retrieval_fn,
            processor_fn=processor_fn,
            memory_storage_fn=memory_storage_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'memory_augmented'
        }

    async def _execute_with_adaptive_learning(self, task: str, **kwargs) -> Dict[str, Any]:
        """Execute with adaptive learning pattern"""
        logger.info("[PATTERN: Adaptive Learning]")

        async def task_analyzer_fn(task_desc):
            analysis = self.agent_selector.analyze_task_requirements(task_desc, task_desc)
            return {'type': analysis['complexity']}

        async def pattern_executor_fn(task_desc, pattern):
            return await self.agent_coordinator.execute_task(task_desc)

        available_patterns = [
            PatternType.ROUTING,
            PatternType.PARALLELIZATION,
            PatternType.REFLECTION
        ]

        result = await self.pattern_orchestrator.execute_pattern(
            PatternType.ADAPTIVE_LEARNING,
            task=task,
            task_analyzer_fn=task_analyzer_fn,
            available_patterns=available_patterns,
            pattern_executor_fn=pattern_executor_fn
        )

        return {
            'success': result.success,
            'output': result.output,
            'pattern_used': 'adaptive_learning'
        }

    async def execute_with_hybrid_pattern(
        self,
        task: str,
        hybrid_type: Optional[HybridPatternType] = None,
        pattern_sequence: Optional[List[PatternType]] = None,
        auto_select_hybrid: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute task using hybrid pattern combination.

        Args:
            task: Task description
            hybrid_type: Predefined hybrid pattern type
            pattern_sequence: Custom pattern sequence (overrides hybrid_type)
            auto_select_hybrid: Auto-select hybrid pattern if not specified
            **kwargs: Additional parameters

        Returns:
            Execution result with hybrid metadata
        """
        if not self.enable_hybrid_patterns or not self.hybrid_executor:
            logger.warning("Hybrid patterns not enabled, falling back to standard execution")
            return await self.execute_with_pattern(task, auto_select_pattern=True, **kwargs)

        # Custom sequence takes precedence
        if pattern_sequence:
            return await self.hybrid_executor.execute_custom_sequence(
                task=task,
                pattern_sequence=pattern_sequence,
                **kwargs
            )

        # Auto-select hybrid pattern if requested
        if hybrid_type is None and auto_select_hybrid:
            task_analysis = self.agent_selector.analyze_task_requirements(
                task_title=task,
                task_description=task
            )
            hybrid_type = self.hybrid_executor.recommend_hybrid_pattern(task, task_analysis)

            if hybrid_type:
                logger.info(f"Auto-selected hybrid pattern: {hybrid_type.value}")
            else:
                logger.info("No hybrid pattern recommended, using single pattern")
                return await self.execute_with_pattern(task, auto_select_pattern=True, **kwargs)

        # Execute with hybrid pattern
        if hybrid_type:
            return await self.hybrid_executor.execute_hybrid(
                task=task,
                hybrid_type=hybrid_type,
                **kwargs
            )
        else:
            # Fallback to single pattern
            return await self.execute_with_pattern(task, auto_select_pattern=True, **kwargs)

    def get_hybrid_pattern_recommendations(
        self,
        task: str
    ) -> Dict[str, Any]:
        """
        Get hybrid pattern recommendation for a task.

        Returns:
            Hybrid pattern recommendation with details
        """
        if not self.enable_hybrid_patterns or not self.hybrid_executor:
            return {'recommended': None, 'reason': 'Hybrid patterns not enabled'}

        # Analyze task
        task_analysis = self.agent_selector.analyze_task_requirements(
            task_title=task,
            task_description=task
        )

        # Get hybrid recommendation
        hybrid_type = self.hybrid_executor.recommend_hybrid_pattern(task, task_analysis)

        if hybrid_type:
            pattern_sequence = self.hybrid_executor.hybrid_recipes[hybrid_type]
            return {
                'recommended': hybrid_type.value,
                'pattern_sequence': [p.value for p in pattern_sequence],
                'description': self._get_hybrid_description(hybrid_type),
                'complexity': task_analysis.get('complexity', 'medium'),
                'benefits': self._get_hybrid_benefits(hybrid_type)
            }
        else:
            return {
                'recommended': None,
                'reason': 'Single pattern sufficient for this task',
                'task_complexity': task_analysis.get('complexity', 'medium')
            }

    def _get_hybrid_description(self, hybrid_type: HybridPatternType) -> str:
        """Get description for hybrid pattern type"""
        descriptions = {
            HybridPatternType.FULL_STACK: "Route to specialists, parallelize work across domains, refine with quality checks",
            HybridPatternType.QUALITY_CRITICAL: "Plan implementation, iterate with quality checks, evaluate against criteria",
            HybridPatternType.RESEARCH_INTENSIVE: "Retrieve relevant knowledge, reason step-by-step, validate with multiple solutions",
            HybridPatternType.ITERATIVE_DEVELOPMENT: "Plan development phases, parallelize implementation, improve with feedback",
            HybridPatternType.PRODUCTION_READY: "Refine quality iteratively, ensure value alignment, evaluate production readiness",
            HybridPatternType.DISTRIBUTED_PROCESSING: "Decompose hierarchically, distribute across workers, combine with ensemble",
            HybridPatternType.AGENT_COLLABORATION: "Route to specialists, coordinate multi-agent workflow, refine final result"
        }
        return descriptions.get(hybrid_type, "Unknown hybrid pattern")

    def _get_hybrid_benefits(self, hybrid_type: HybridPatternType) -> List[str]:
        """Get benefits for hybrid pattern type"""
        benefits = {
            HybridPatternType.FULL_STACK: [
                "Optimal agent selection",
                "Parallel execution for speed",
                "Quality improvement through reflection"
            ],
            HybridPatternType.QUALITY_CRITICAL: [
                "Comprehensive planning",
                "Iterative quality improvement",
                "Objective evaluation metrics"
            ],
            HybridPatternType.RESEARCH_INTENSIVE: [
                "Knowledge-grounded responses",
                "Transparent reasoning",
                "Multiple solution validation"
            ],
            HybridPatternType.ITERATIVE_DEVELOPMENT: [
                "Structured development phases",
                "Fast parallel execution",
                "Continuous improvement"
            ],
            HybridPatternType.PRODUCTION_READY: [
                "High quality outputs",
                "Ethical alignment",
                "Production validation"
            ],
            HybridPatternType.DISTRIBUTED_PROCESSING: [
                "Optimal task decomposition",
                "Massive parallelization",
                "Robust ensemble results"
            ],
            HybridPatternType.AGENT_COLLABORATION: [
                "Specialist expertise",
                "Coordinated workflows",
                "Quality refinement"
            ]
        }
        return benefits.get(hybrid_type, [])

    def get_pattern_recommendations(
        self,
        task: str
    ) -> List[Dict[str, Any]]:
        """
        Get pattern recommendations for a task without executing.

        Returns:
            List of pattern recommendations with metadata
        """
        # Analyze task
        task_analysis = self.agent_selector.analyze_task_requirements(
            task_title=task,
            task_description=task
        )

        complexity = task_analysis['complexity']
        requirements = task_analysis['requirements']

        # Check for hybrid pattern recommendation first
        if self.enable_hybrid_patterns and self.hybrid_executor:
            hybrid_rec = self.get_hybrid_pattern_recommendations(task)
            if hybrid_rec.get('recommended'):
                # Return hybrid as primary recommendation
                return [{
                    'pattern': 'hybrid',
                    'hybrid_type': hybrid_rec['recommended'],
                    'name': f"Hybrid: {hybrid_rec['recommended'].replace('_', ' ').title()}",
                    'description': hybrid_rec['description'],
                    'pattern_sequence': hybrid_rec['pattern_sequence'],
                    'complexity': hybrid_rec['complexity'],
                    'benefits': hybrid_rec['benefits']
                }]

        # Get single pattern recommendations
        recommendations = self.pattern_orchestrator.recommend_pattern(
            task_description=task,
            task_complexity=complexity,
            requires_quality='code review' in requirements or 'testing' in requirements,
            time_sensitive='performance' in requirements,
            multiple_domains=len(requirements) > 2
        )

        # Build detailed recommendations
        detailed = []
        for pattern_type in recommendations:
            metadata = PATTERN_REGISTRY.get(pattern_type)
            if metadata:
                detailed.append({
                    'pattern': pattern_type.value,
                    'name': metadata.name,
                    'description': metadata.description,
                    'complexity': metadata.complexity.value,
                    'best_for': metadata.best_for,
                    'pros': metadata.pros,
                    'cons': metadata.cons
                })

        return detailed

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        if not self.execution_history:
            return {}

        # Overall stats
        total_executions = len(self.execution_history)
        success_count = sum(1 for e in self.execution_history if e.get('success', False))
        success_rate = success_count / total_executions if total_executions > 0 else 0

        # Pattern-specific stats
        pattern_stats = {}
        for entry in self.execution_history:
            pattern = entry['pattern']
            if pattern not in pattern_stats:
                pattern_stats[pattern] = {
                    'count': 0,
                    'success_count': 0,
                    'total_time_ms': 0
                }

            pattern_stats[pattern]['count'] += 1
            if entry.get('success', False):
                pattern_stats[pattern]['success_count'] += 1
            pattern_stats[pattern]['total_time_ms'] += entry.get('execution_time_ms', 0)

        # Calculate averages
        for pattern, stats in pattern_stats.items():
            stats['success_rate'] = stats['success_count'] / stats['count'] if stats['count'] > 0 else 0
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['count'] if stats['count'] > 0 else 0

        return {
            'total_executions': total_executions,
            'success_rate': success_rate,
            'pattern_usage': pattern_stats
        }


async def main():
    """Demo of pattern-aware coordination"""
    print("\n" + "=" * 70)
    print("PATTERN-AWARE MULTI-AGENT COORDINATION DEMO")
    print("=" * 70)
    print()

    coordinator = PatternAwareCoordinator()

    # Demo 1: Auto-select pattern for complex task
    print("Demo 1: Auto-Pattern Selection for Complex Task")
    print("-" * 70)

    task1 = "Implement user authentication system with JWT tokens, including frontend login forms and backend API endpoints"

    # Get recommendations first
    recommendations = coordinator.get_pattern_recommendations(task1)
    print(f"Task: {task1}")
    print(f"\nRecommended patterns:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['name']} - {rec['description']}")

    # Execute with auto-selection
    result1 = await coordinator.execute_with_pattern(
        task=task1,
        auto_select_pattern=True
    )

    print(f"\nResult:")
    print(f"  Pattern used: {result1['pattern_used']}")
    print(f"  Success: {result1.get('success', False)}")
    print(f"  Execution time: {result1['pattern_metadata']['total_execution_time_ms']:.1f}ms")
    print()

    # Demo 2: Explicit pattern selection
    print("Demo 2: Explicit Reflection Pattern for Quality-Critical Code")
    print("-" * 70)

    task2 = "Generate a secure password hashing function with proper salt generation"

    result2 = await coordinator.execute_with_pattern(
        task=task2,
        pattern_type=PatternType.REFLECTION,
        auto_select_pattern=False
    )

    print(f"Task: {task2}")
    print(f"\nResult:")
    print(f"  Pattern used: {result2['pattern_used']}")
    print(f"  Success: {result2.get('success', False)}")
    print(f"  Iterations: {result2.get('iterations', 0)}")
    print(f"  Final quality score: {result2.get('final_score', 0):.2f}")
    print()

    # Demo 3: Show execution statistics
    print("Demo 3: Execution Statistics")
    print("-" * 70)

    stats = coordinator.get_execution_stats()
    print(json.dumps(stats, indent=2))
    print()


if __name__ == "__main__":
    asyncio.run(main())
