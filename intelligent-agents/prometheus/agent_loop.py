"""
Prometheus Agent Loop - Core autonomous execution engine.

Key patterns from Manus:
1. Multi-agent architecture (Planner, Executor, Verifier, Knowledge)
2. One tool call per iteration (prevents runaway) OR parallel execution
3. Event stream for working memory
4. todo.md for attention manipulation
5. Error preservation for learning
6. PARALLEL EXECUTION: Multiple independent steps can run concurrently
"""

import asyncio
import time
import uuid
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from enum import Enum

from .event_stream import EventStream, Event, EventType
from .todo_manager import TodoManager, StepStatus
from .llm_client import get_llm_client
from .agents.planner import PlannerAgent
from .agents.executor import ExecutorAgent
from .agents.verifier import VerifierAgent
from .agents.knowledge import KnowledgeAgent
from .parallel_executor import (
    ParallelExecutor,
    ParallelStrategy,
    ParallelBatchResult,
    add_dependency_hints
)
from .streaming import (
    StreamingServer,
    StreamingMixin,
    get_streaming_server,
    WEBSOCKETS_AVAILABLE
)

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of the overall task."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    EXECUTING_PARALLEL = "executing_parallel"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ExecutionMode(Enum):
    """How to execute steps."""
    SEQUENTIAL = "sequential"   # One step at a time (default, safe)
    PARALLEL = "parallel"       # Parallel when possible (Manus-style)
    AUTO = "auto"              # Analyze and choose best strategy


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    success: bool
    summary: str
    outputs: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    steps_completed: int = 0
    steps_total: int = 0
    execution_time: float = 0.0
    # Parallel execution metrics
    parallel_groups: int = 0
    parallel_speedup: float = 1.0  # Estimated speedup vs sequential


@dataclass
class Action:
    """Single tool action to execute."""
    tool: str
    params: dict
    expected_outcome: Optional[str] = None
    step_number: int = 0


class PrometheusAgentLoop(StreamingMixin):
    """
    Core autonomous execution loop.

    This is the main orchestrator that coordinates:
    - Planner Agent: Decomposes tasks into steps
    - Executor Agent: Runs one tool per iteration
    - Verifier Agent: Validates results
    - Knowledge Agent: Retrieves information

    CRITICAL RULE: Only ONE tool call per iteration.
    This prevents runaway execution and allows observation.

    STREAMING: Real-time WebSocket output via StreamingMixin.
    """

    def __init__(
        self,
        workspace_base: Path = None,
        max_iterations: int = 100,
        max_retries: int = 3,
        sandbox_node: str = "macpro51",
        execution_mode: ExecutionMode = ExecutionMode.AUTO,
        max_parallelism: int = 10,
        enable_streaming: bool = True
    ):
        self.workspace_base = workspace_base or Path("/tmp/prometheus")
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.sandbox_node = sandbox_node
        self.execution_mode = execution_mode
        self.max_parallelism = max_parallelism
        self.enable_streaming = enable_streaming

        # Will be set per-task
        self.workspace: Optional[Path] = None
        self.event_stream: Optional[EventStream] = None
        self.todo_manager: Optional[TodoManager] = None
        self.task_id: Optional[str] = None
        self._parallel_executor: Optional[ParallelExecutor] = None

        # Initialize streaming
        self.init_streaming(enable=enable_streaming)

        # Agent instances (lazy loaded)
        self._planner = None
        self._executor = None
        self._verifier = None
        self._knowledge = None
        self._llm_client = None

    @property
    def llm_client(self):
        """Get or create LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    @property
    def planner(self):
        """Get or create Planner agent."""
        if self._planner is None:
            self._planner = PlannerAgent(llm_client=self.llm_client)
        return self._planner

    @property
    def executor(self):
        """Get or create Executor agent."""
        if self._executor is None:
            self._executor = ExecutorAgent(
                sandbox_node=self.sandbox_node,
                llm_client=self.llm_client
            )
        return self._executor

    @property
    def verifier(self):
        """Get or create Verifier agent."""
        if self._verifier is None:
            self._verifier = VerifierAgent(llm_client=self.llm_client)
        return self._verifier

    @property
    def knowledge(self):
        """Get or create Knowledge agent."""
        if self._knowledge is None:
            from .mcp_client import get_mcp_client
            self._knowledge = KnowledgeAgent(
                mcp_client=get_mcp_client(),
                llm_client=self.llm_client
            )
        return self._knowledge

    @property
    def parallel_executor(self):
        """Get or create ParallelExecutor instance."""
        if self._parallel_executor is None:
            self._parallel_executor = ParallelExecutor(
                executor_factory=self._create_executor_instance,
                max_parallelism=self.max_parallelism,
                strategy=ParallelStrategy.DEPENDENCY_AWARE
            )
        return self._parallel_executor

    def _create_executor_instance(self) -> ExecutorAgent:
        """Factory function to create executor instances for parallel execution."""
        return ExecutorAgent(
            sandbox_node=self.sandbox_node,
            llm_client=self.llm_client
        )

    def _should_use_parallel(self, steps: list[dict]) -> bool:
        """
        Determine if parallel execution should be used.

        Factors:
        - Number of steps (need >= 2 for parallel to help)
        - Execution mode setting
        - Presence of dependencies
        """
        if self.execution_mode == ExecutionMode.SEQUENTIAL:
            return False

        if self.execution_mode == ExecutionMode.PARALLEL:
            return len(steps) >= 2

        # AUTO mode: analyze steps
        if len(steps) < 2:
            return False

        # Check if any steps have explicit no-deps
        enhanced_steps = add_dependency_hints(steps)
        independent_count = sum(
            1 for s in enhanced_steps
            if not s.get("depends_on", [])
        )

        # Use parallel if at least 2 independent steps
        return independent_count >= 2

    async def execute_task(self, request: str, context: dict = None) -> TaskResult:
        """
        Execute an autonomous task.

        Args:
            request: Natural language task description
            context: Optional context (files, preferences, etc.)

        Returns:
            TaskResult with success status and outputs
        """
        start_time = time.time()
        self.task_id = f"prom_{uuid.uuid4().hex[:8]}"

        # 1. Create workspace
        self.workspace = self._create_workspace()
        self.event_stream = EventStream(workspace=self.workspace)
        self.todo_manager = TodoManager(self.workspace)

        logger.info(f"Starting task {self.task_id}: {request[:50]}...")

        # Set streaming task ID
        self.set_stream_task_id(self.task_id)
        self.stream_task_start(request)

        try:
            # 2. Planning phase
            plan = await self._plan(request, context)

            if not plan:
                return TaskResult(
                    task_id=self.task_id,
                    status=TaskStatus.FAILED,
                    success=False,
                    summary="Failed to create execution plan",
                    execution_time=time.time() - start_time
                )

            # Enhance steps with dependency hints
            steps = add_dependency_hints(plan["steps"])

            # Initialize todo.md
            self.todo_manager.initialize(request, steps)
            self.event_stream.append_plan([s["description"] for s in steps])

            # Stream plan steps
            for step in steps:
                self.stream_plan_step(step.get("number", 0), step.get("description", ""))

            # 3. Choose execution strategy
            use_parallel = self._should_use_parallel(steps)
            parallel_groups = 0

            if use_parallel:
                logger.info(f"Using PARALLEL execution mode for {len(steps)} steps")
                parallel_groups = await self._execute_parallel(steps, context)
            else:
                logger.info(f"Using SEQUENTIAL execution mode for {len(steps)} steps")
                await self._execute_sequential()

            # 4. Compile results
            completed, total = self.todo_manager.get_progress()
            sequential_time = sum(s.get("expected_time", 1.0) for s in steps)
            parallel_speedup = sequential_time / max(time.time() - start_time, 0.1) if use_parallel else 1.0

            summary = self._generate_summary()
            success = self.todo_manager.is_complete()

            # Stream task completion
            self.stream_task_complete(success, summary)

            return TaskResult(
                task_id=self.task_id,
                status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                success=success,
                summary=summary,
                outputs=self._collect_outputs(),
                errors=[e.data["error"] for e in self.event_stream.get_errors()],
                steps_completed=completed,
                steps_total=total,
                execution_time=time.time() - start_time,
                parallel_groups=parallel_groups,
                parallel_speedup=parallel_speedup
            )

        except Exception as e:
            logger.exception(f"Task {self.task_id} failed with exception")
            self.event_stream.append_error(str(e), traceback=str(e.__traceback__))

            # Stream error
            self.stream_error(str(e), str(e.__traceback__))
            self.stream_task_complete(False, f"Task failed: {str(e)}")

            return TaskResult(
                task_id=self.task_id,
                status=TaskStatus.FAILED,
                success=False,
                summary=f"Task failed: {str(e)}",
                errors=[str(e)],
                execution_time=time.time() - start_time
            )

    async def _execute_sequential(self) -> None:
        """
        Execute steps sequentially (original behavior).

        CRITICAL: One tool call per iteration.
        """
        iteration = 0
        retries = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Check if complete
            if self.todo_manager.is_complete():
                break

            # Get current step
            current_step = self.todo_manager.get_current_step()
            if not current_step:
                break

            # Mark step as in progress
            self.todo_manager.start_step(current_step.number)

            # Select action (ONE tool only)
            action = await self._select_action(current_step)

            if not action:
                # Executor couldn't determine action
                retries += 1
                if retries >= self.max_retries:
                    self.todo_manager.fail_step(
                        current_step.number,
                        "Could not determine action after retries"
                    )
                continue

            # Stream action start
            self.stream_action_start(action.tool, action.params)

            # Execute action in sandbox
            observation = await self._execute_action(action)

            # Stream action complete
            success = "error" not in observation.lower()
            self.stream_action_complete(action.tool, success, observation)
            self.stream_observation(observation)

            # Log to event stream
            self.event_stream.append_action_observation(
                tool=action.tool,
                params=action.params,
                result=observation,
                success=success
            )

            # Verify result
            verified = await self._verify(action, observation, current_step)

            if verified["success"]:
                self.todo_manager.complete_step(
                    current_step.number,
                    notes=verified.get("notes", "")
                )
                retries = 0
            else:
                # Preserve error in context (model learns)
                self.event_stream.append_error(
                    error=verified.get("error", "Verification failed"),
                    traceback=verified.get("traceback", "")
                )

                if verified.get("should_replan"):
                    # Replanning needed
                    new_plan = await self._replan(
                        current_step,
                        verified["error"]
                    )
                    if new_plan:
                        # Update todo with new steps
                        for step in new_plan.get("new_steps", []):
                            self.todo_manager.add_step(
                                description=step["description"],
                                tools=step.get("tools", []),
                                after=current_step.number
                            )

                retries += 1
                if retries >= self.max_retries:
                    self.todo_manager.fail_step(
                        current_step.number,
                        verified.get("error", "Max retries exceeded")
                    )

    async def _execute_parallel(self, steps: list[dict], context: dict = None) -> int:
        """
        Execute steps with maximum parallelism.

        This is the Manus-style parallel execution pattern:
        - Analyze plan to find parallelizable groups
        - Execute groups sequentially
        - Within each group, execute steps in parallel

        Args:
            steps: Steps from planner with dependency hints
            context: Task context

        Returns:
            Number of parallel groups executed
        """
        # Reset parallel executor state
        self.parallel_executor.reset()

        # Build execution state
        state = {
            "task_id": self.task_id,
            "workspace": str(self.workspace),
            "context": context or {},
        }

        # Get event stream context
        event_context = self.event_stream.to_context()

        # Callback to update todo manager after each group
        def on_group_complete(group_idx: int, batch_result: ParallelBatchResult):
            logger.info(
                f"Group {group_idx + 1} complete: "
                f"{len(batch_result.results)} steps, "
                f"{len(batch_result.failed_steps)} failed, "
                f"{batch_result.total_time:.2f}s"
            )

            # Update todo manager with results
            for result in batch_result.results:
                if result.success:
                    self.todo_manager.complete_step(
                        result.step_number,
                        notes=result.observation[:200]
                    )
                else:
                    self.todo_manager.fail_step(
                        result.step_number,
                        result.error or result.observation[:200]
                    )

                # Log to event stream
                self.event_stream.append_action_observation(
                    tool=f"parallel_step_{result.step_number}",
                    params={"step": result.step_number},
                    result=result.observation,
                    success=result.success
                )

        # Execute all steps with parallelism
        batch_results = await self.parallel_executor.execute_all_parallel(
            steps=steps,
            state=state,
            event_context=event_context,
            on_group_complete=on_group_complete
        )

        return len(batch_results)

    def _create_workspace(self) -> Path:
        """Create isolated workspace for this task."""
        workspace = self.workspace_base / self.task_id
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    async def _plan(self, request: str, context: dict = None) -> Optional[dict]:
        """
        Create execution plan using Planner Agent.

        Returns dict with 'steps' key containing list of step dicts.
        """
        plan = await self.planner.create_plan(request, context)

        if plan:
            return {
                "analysis": plan.analysis,
                "steps": plan.steps,
                "complexity": plan.complexity,
                "requires_input": plan.requires_input
            }
        return None

    async def _select_action(self, step) -> Optional[Action]:
        """
        Select ONE action to execute.

        CRITICAL: Only one tool per iteration.
        """
        # Build current state
        state = {
            "task_id": self.task_id,
            "workspace": str(self.workspace),
            "completed_steps": self.todo_manager.get_progress()[0],
            "total_steps": self.todo_manager.get_progress()[1],
        }

        # Get recent context from event stream
        event_context = self.event_stream.to_context()

        # Convert step to dict format if needed
        step_dict = {
            "number": step.number,
            "description": step.description,
            "tools": step.tools,
            "expected_outcome": step.expected_outcome
        }

        # Use executor to select action
        action = await self.executor.select_action(
            current_step=step_dict,
            state=state,
            event_context=event_context
        )

        if action:
            return Action(
                tool=action.tool,
                params=action.params,
                expected_outcome=action.expected_outcome,
                step_number=action.step_number
            )
        return None

    async def _execute_action(self, action: Action) -> str:
        """
        Execute action in sandbox environment.

        Routes to appropriate node based on action type.
        """
        # Create executor action with proper category
        from .agents.executor import Action as ExecutorAction, ToolCategory

        tool_info = self.executor.tools.get(action.tool, {})
        category = tool_info.get("category", ToolCategory.FILE)

        executor_action = ExecutorAction(
            tool=action.tool,
            params=action.params,
            category=category,
            expected_outcome=action.expected_outcome,
            step_number=action.step_number
        )

        return await self.executor.execute(executor_action)

    async def _verify(self, action: Action, observation: str, step) -> dict:
        """
        Verify action result using Verifier Agent.

        Returns dict with:
        - success: bool
        - error: str (if failed)
        - should_replan: bool
        - notes: str
        """
        # Get expected outcome from step
        expected = step.expected_outcome if hasattr(step, 'expected_outcome') else ""

        action_dict = {"tool": action.tool, "params": action.params}
        result = await self.verifier.verify(
            action=action_dict,
            observation=observation,
            expected_outcome=expected
        )

        return {
            "success": result.success,
            "error": result.error if not result.success else "",
            "should_replan": not result.success and self.verifier.is_recoverable(result.error),
            "notes": result.notes,
            "traceback": getattr(result, 'traceback', "")
        }

    async def _replan(self, failed_step, error: str) -> Optional[dict]:
        """
        Create new plan to handle failure.

        Returns dict with 'new_steps' to add.
        """
        # Get current todo status
        plan_status = self.todo_manager.get_focus_context()

        # Convert step to dict
        failed_step_dict = {
            "number": failed_step.number,
            "description": failed_step.description,
            "tools": failed_step.tools,
            "expected_outcome": failed_step.expected_outcome
        }

        return await self.planner.replan(
            original_task=self.todo_manager.task_description,
            failed_step=failed_step_dict,
            error=error,
            plan_status=plan_status
        )

    def _generate_summary(self) -> str:
        """Generate human-readable summary of execution."""
        completed, total = self.todo_manager.get_progress()
        errors = self.event_stream.get_errors()

        if self.todo_manager.is_complete():
            return f"Task completed successfully. {completed}/{total} steps done."
        elif errors:
            return f"Task partially completed. {completed}/{total} steps. {len(errors)} errors encountered."
        else:
            return f"Task in progress. {completed}/{total} steps completed."

    def _collect_outputs(self) -> list[dict]:
        """Collect output files and artifacts."""
        outputs = []
        if self.workspace and self.workspace.exists():
            for file in self.workspace.iterdir():
                if file.is_file() and file.name != "events.jsonl":
                    outputs.append({
                        "type": "file",
                        "path": str(file),
                        "name": file.name
                    })
        return outputs


# Convenience function for simple usage
async def run_prometheus(
    task: str,
    context: dict = None,
    execution_mode: ExecutionMode = ExecutionMode.AUTO,
    max_parallelism: int = 10
) -> TaskResult:
    """
    Run a task through Prometheus agent loop.

    Args:
        task: Natural language task description
        context: Optional context dict
        execution_mode: SEQUENTIAL, PARALLEL, or AUTO
        max_parallelism: Max concurrent executions (default 10)

    Returns:
        TaskResult with execution details
    """
    loop = PrometheusAgentLoop(
        execution_mode=execution_mode,
        max_parallelism=max_parallelism
    )
    return await loop.execute_task(task, context)


async def run_prometheus_parallel(task: str, context: dict = None) -> TaskResult:
    """Run a task with forced parallel execution."""
    return await run_prometheus(
        task=task,
        context=context,
        execution_mode=ExecutionMode.PARALLEL
    )
