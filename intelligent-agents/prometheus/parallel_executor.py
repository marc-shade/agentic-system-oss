"""
Parallel Executor - Multi-agent concurrent execution for Prometheus.

This is the key capability that Manus has: spawning multiple agents
to work on independent subtasks simultaneously.

Patterns:
- Identify parallelizable steps (no dependencies)
- Spawn executor instances per step
- Use asyncio.gather for concurrent execution
- Collect and merge results
- Handle failures gracefully (one failure doesn't kill all)

Integration:
- agent-runtime-mcp for persistent task tracking
- cluster-execution-mcp for distributed execution
- Event stream for coordination
"""

import asyncio
import logging
import time
import os
import json
from dataclasses import dataclass, field
from typing import Optional, Any, Callable
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if agent-runtime-mcp is available
AGENT_RUNTIME_AVAILABLE = False
try:
    import httpx
    AGENT_RUNTIME_AVAILABLE = True
except ImportError:
    logger.debug("httpx not available, agent-runtime-mcp integration disabled")


class ParallelStrategy(Enum):
    """How to parallelize execution."""
    ALL_AT_ONCE = "all"          # Run all parallel steps at once
    BATCHED = "batched"          # Run in batches of N
    DEPENDENCY_AWARE = "deps"    # Respect step dependencies


@dataclass
class ParallelStep:
    """A step that can be executed in parallel."""
    number: int
    description: str
    tools: list[str]
    expected_outcome: str = ""
    depends_on: list[int] = field(default_factory=list)
    group_id: int = 0  # Steps in same group can run in parallel


@dataclass
class ParallelResult:
    """Result from parallel execution."""
    step_number: int
    success: bool
    observation: str
    execution_time: float
    error: Optional[str] = None


@dataclass
class ParallelBatchResult:
    """Results from a batch of parallel executions."""
    results: list[ParallelResult]
    total_time: float
    all_success: bool
    failed_steps: list[int]


class ParallelExecutor:
    """
    Executes multiple steps in parallel using async workers.

    This is the Manus-style parallel agent execution pattern:
    - Analyze plan to find parallelizable steps
    - Spawn concurrent executors
    - Collect results
    - Continue to next parallel batch
    """

    # Maximum concurrent executions (like Claude Code's limit of 10)
    MAX_PARALLELISM = 10

    def __init__(
        self,
        executor_factory: Callable,
        max_parallelism: int = None,
        strategy: ParallelStrategy = ParallelStrategy.DEPENDENCY_AWARE
    ):
        """
        Initialize parallel executor.

        Args:
            executor_factory: Function that creates ExecutorAgent instances
            max_parallelism: Max concurrent executions (default: 10)
            strategy: How to determine parallel execution
        """
        self.executor_factory = executor_factory
        self.max_parallelism = max_parallelism or self.MAX_PARALLELISM
        self.strategy = strategy

        # Track execution state
        self.active_executors: dict[int, Any] = {}
        self.completed_steps: set[int] = set()
        self.failed_steps: set[int] = set()

    def analyze_parallelism(self, steps: list[dict]) -> list[list[ParallelStep]]:
        """
        Analyze steps to find parallelizable groups.

        Returns list of groups, where steps in each group can run in parallel.
        Groups must be executed sequentially (group 2 after group 1, etc.)

        Args:
            steps: List of step dicts from planner

        Returns:
            List of parallel groups
        """
        if not steps:
            return []

        # Convert to ParallelStep objects
        parallel_steps = []
        for step in steps:
            ps = ParallelStep(
                number=step.get("number", len(parallel_steps) + 1),
                description=step.get("description", ""),
                tools=step.get("tools", []),
                expected_outcome=step.get("expected_outcome", ""),
                depends_on=step.get("depends_on", [])
            )
            parallel_steps.append(ps)

        if self.strategy == ParallelStrategy.ALL_AT_ONCE:
            # All steps in one group (dangerous for dependent steps)
            return [parallel_steps]

        elif self.strategy == ParallelStrategy.BATCHED:
            # Simple batching by max_parallelism
            groups = []
            for i in range(0, len(parallel_steps), self.max_parallelism):
                groups.append(parallel_steps[i:i + self.max_parallelism])
            return groups

        else:  # DEPENDENCY_AWARE (default)
            return self._group_by_dependencies(parallel_steps)

    def _group_by_dependencies(self, steps: list[ParallelStep]) -> list[list[ParallelStep]]:
        """
        Group steps by dependencies for optimal parallel execution.

        Steps with no dependencies (or whose dependencies are met) form a group.
        """
        groups = []
        remaining = steps.copy()
        completed_numbers = set()

        while remaining:
            # Find steps whose dependencies are all completed
            ready = []
            not_ready = []

            for step in remaining:
                deps_met = all(d in completed_numbers for d in step.depends_on)
                if deps_met:
                    ready.append(step)
                else:
                    not_ready.append(step)

            if not ready:
                # No steps ready - circular dependency or bug
                # Fall back to sequential
                logger.warning("No ready steps found, falling back to sequential")
                groups.append(not_ready)
                break

            # Limit group size to max_parallelism
            if len(ready) > self.max_parallelism:
                # Split into batches
                for i in range(0, len(ready), self.max_parallelism):
                    batch = ready[i:i + self.max_parallelism]
                    groups.append(batch)
                    completed_numbers.update(s.number for s in batch)
            else:
                groups.append(ready)
                completed_numbers.update(s.number for s in ready)

            remaining = not_ready

        return groups

    async def execute_parallel_group(
        self,
        steps: list[ParallelStep],
        state: dict,
        event_context: str = ""
    ) -> ParallelBatchResult:
        """
        Execute a group of steps in parallel.

        Args:
            steps: Steps to execute concurrently
            state: Current execution state
            event_context: Context from event stream

        Returns:
            ParallelBatchResult with all results
        """
        if not steps:
            return ParallelBatchResult(
                results=[],
                total_time=0.0,
                all_success=True,
                failed_steps=[]
            )

        start_time = time.time()
        logger.info(f"Executing {len(steps)} steps in parallel")

        # Create tasks for concurrent execution
        tasks = []
        for step in steps:
            task = asyncio.create_task(
                self._execute_single_step(step, state, event_context)
            )
            tasks.append((step.number, task))

        # Wait for all to complete (with individual error handling)
        results = []
        failed = []

        for step_num, task in tasks:
            try:
                result = await task
                results.append(result)
                if result.success:
                    self.completed_steps.add(step_num)
                else:
                    self.failed_steps.add(step_num)
                    failed.append(step_num)
            except Exception as e:
                logger.error(f"Step {step_num} raised exception: {e}")
                results.append(ParallelResult(
                    step_number=step_num,
                    success=False,
                    observation=f"Exception: {str(e)}",
                    execution_time=0.0,
                    error=str(e)
                ))
                self.failed_steps.add(step_num)
                failed.append(step_num)

        total_time = time.time() - start_time

        return ParallelBatchResult(
            results=results,
            total_time=total_time,
            all_success=len(failed) == 0,
            failed_steps=failed
        )

    async def _execute_single_step(
        self,
        step: ParallelStep,
        state: dict,
        event_context: str
    ) -> ParallelResult:
        """
        Execute a single step using a dedicated executor.

        Each parallel step gets its own executor instance.
        """
        start_time = time.time()

        # Create fresh executor for this step
        executor = self.executor_factory()
        self.active_executors[step.number] = executor

        try:
            # Convert step to dict for executor
            step_dict = {
                "number": step.number,
                "description": step.description,
                "tools": step.tools,
                "expected_outcome": step.expected_outcome
            }

            # Select action
            action = await executor.select_action(
                current_step=step_dict,
                state=state,
                event_context=event_context
            )

            if not action:
                return ParallelResult(
                    step_number=step.number,
                    success=False,
                    observation="Could not determine action",
                    execution_time=time.time() - start_time,
                    error="No action selected"
                )

            # Execute action
            observation = await executor.execute(action)

            # Determine success
            success = "error" not in observation.lower()

            return ParallelResult(
                step_number=step.number,
                success=success,
                observation=observation,
                execution_time=time.time() - start_time,
                error=None if success else observation
            )

        except Exception as e:
            logger.exception(f"Step {step.number} execution failed")
            return ParallelResult(
                step_number=step.number,
                success=False,
                observation=f"Exception: {str(e)}",
                execution_time=time.time() - start_time,
                error=str(e)
            )

        finally:
            # Cleanup
            del self.active_executors[step.number]

    async def execute_all_parallel(
        self,
        steps: list[dict],
        state: dict,
        event_context: str = "",
        on_group_complete: Callable = None
    ) -> list[ParallelBatchResult]:
        """
        Execute all steps with maximum parallelism.

        This is the main entry point for parallel execution.

        Args:
            steps: All steps from planner
            state: Execution state
            event_context: Context from events
            on_group_complete: Callback after each group finishes

        Returns:
            List of batch results
        """
        # Analyze parallelism
        groups = self.analyze_parallelism(steps)

        logger.info(f"Parallel execution: {len(steps)} steps in {len(groups)} groups")
        for i, group in enumerate(groups):
            logger.info(f"  Group {i+1}: {len(group)} steps (numbers: {[s.number for s in group]})")

        # Execute groups sequentially, steps within group in parallel
        all_results = []

        for group_idx, group in enumerate(groups):
            logger.info(f"Executing group {group_idx + 1}/{len(groups)}")

            # Update state with completed steps
            state["completed_steps"] = list(self.completed_steps)

            # Execute group in parallel
            batch_result = await self.execute_parallel_group(
                steps=group,
                state=state,
                event_context=event_context
            )

            all_results.append(batch_result)

            # Callback
            if on_group_complete:
                on_group_complete(group_idx, batch_result)

            # Check for failures that should stop execution
            if batch_result.failed_steps:
                critical_failures = self._check_critical_failures(
                    batch_result.failed_steps,
                    groups[group_idx + 1:] if group_idx + 1 < len(groups) else []
                )
                if critical_failures:
                    logger.warning(f"Critical failures detected, stopping parallel execution")
                    break

        return all_results

    def _check_critical_failures(
        self,
        failed_steps: list[int],
        remaining_groups: list[list[ParallelStep]]
    ) -> bool:
        """
        Check if failed steps are critical (block remaining work).

        Returns True if execution should stop.
        """
        if not remaining_groups:
            return False

        # Check if any remaining step depends on a failed step
        for group in remaining_groups:
            for step in group:
                for dep in step.depends_on:
                    if dep in failed_steps:
                        logger.warning(
                            f"Step {step.number} depends on failed step {dep}"
                        )
                        return True

        return False

    def reset(self):
        """Reset state for new task."""
        self.active_executors.clear()
        self.completed_steps.clear()
        self.failed_steps.clear()


class AgentRuntimeIntegration:
    """
    Integration with agent-runtime-mcp for persistent task tracking.

    This enables:
    - Creating goals from task descriptions
    - Tracking step progress across sessions
    - Persisting execution state
    """

    RUNTIME_PORT = 8102  # Default agent-runtime-mcp port

    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://localhost:{self.RUNTIME_PORT}"
        self._goal_id: Optional[int] = None
        self._task_ids: dict[int, int] = {}  # step_number -> task_id

    async def create_goal_from_task(
        self,
        task_description: str,
        steps: list[dict]
    ) -> Optional[int]:
        """
        Create a persistent goal from task and steps.

        Returns goal_id if successful.
        """
        if not AGENT_RUNTIME_AVAILABLE:
            logger.debug("agent-runtime-mcp not available")
            return None

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Create goal
                response = await client.post(
                    f"{self.base_url}/goals",
                    json={
                        "name": task_description[:50],
                        "description": task_description,
                        "metadata": {
                            "source": "prometheus",
                            "step_count": len(steps)
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    self._goal_id = data.get("goalId")
                    logger.info(f"Created goal {self._goal_id} in agent-runtime")

                    # Create tasks for each step
                    for step in steps:
                        task_response = await client.post(
                            f"{self.base_url}/tasks",
                            json={
                                "title": step.get("description", "")[:100],
                                "description": json.dumps(step),
                                "goal_id": self._goal_id,
                                "priority": 5
                            }
                        )
                        if task_response.status_code == 200:
                            task_data = task_response.json()
                            self._task_ids[step.get("number", 0)] = task_data.get("taskId")

                    return self._goal_id

        except Exception as e:
            logger.warning(f"Failed to create goal in agent-runtime: {e}")

        return None

    async def update_step_status(
        self,
        step_number: int,
        status: str,
        result: str = ""
    ) -> bool:
        """
        Update step/task status in agent-runtime.

        Args:
            step_number: Step number to update
            status: "pending", "in_progress", "completed", "failed"
            result: Result or error message
        """
        if not AGENT_RUNTIME_AVAILABLE or step_number not in self._task_ids:
            return False

        task_id = self._task_ids[step_number]

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.patch(
                    f"{self.base_url}/tasks/{task_id}",
                    json={
                        "status": status,
                        "result": result[:500] if result else None
                    }
                )
                return response.status_code == 200

        except Exception as e:
            logger.debug(f"Failed to update task status: {e}")
            return False

    async def get_goal_progress(self) -> Optional[dict]:
        """Get current goal progress from agent-runtime."""
        if not AGENT_RUNTIME_AVAILABLE or not self._goal_id:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/goals/{self._goal_id}")
                if response.status_code == 200:
                    return response.json()
        except Exception:
            pass

        return None


def identify_parallel_steps(steps: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Utility to identify which steps can run in parallel vs sequential.

    Simple heuristic: steps that don't reference output of previous steps
    and use read-only tools can be parallelized.

    Args:
        steps: Steps from planner

    Returns:
        (parallel_steps, sequential_steps)
    """
    READ_ONLY_TOOLS = {"read", "glob", "grep", "web_search", "memory_search", "browser_view"}

    parallel = []
    sequential = []

    for step in steps:
        tools = set(step.get("tools", []))

        # Check if step uses only read-only tools
        if tools and tools.issubset(READ_ONLY_TOOLS):
            parallel.append(step)
        else:
            sequential.append(step)

    return parallel, sequential


def add_dependency_hints(steps: list[dict]) -> list[dict]:
    """
    Add dependency hints to steps based on descriptions.

    Simple heuristic: if step mentions "previous", "above", or
    specific file from earlier step, it has a dependency.

    Args:
        steps: Steps from planner

    Returns:
        Steps with depends_on field populated
    """
    enhanced = []
    files_created = {}  # step_number -> files mentioned

    dependency_keywords = ["previous", "above", "created", "from step"]

    for i, step in enumerate(steps):
        step = step.copy()
        step["depends_on"] = step.get("depends_on", [])

        desc_lower = step.get("description", "").lower()

        # Check for explicit dependency keywords
        for keyword in dependency_keywords:
            if keyword in desc_lower and i > 0:
                # Depends on previous step
                step["depends_on"].append(i)  # Previous step number

        # Check for file references
        for prev_num, files in files_created.items():
            for f in files:
                if f.lower() in desc_lower:
                    step["depends_on"].append(prev_num)

        # Track files this step might create
        if any(t in step.get("tools", []) for t in ["write", "bash"]):
            # Extract potential file names from description
            # Simple heuristic: look for paths or common extensions
            words = step.get("description", "").split()
            files = [w for w in words if "/" in w or w.endswith((".py", ".js", ".html", ".css", ".json"))]
            if files:
                files_created[step.get("number", i + 1)] = files

        enhanced.append(step)

    return enhanced
