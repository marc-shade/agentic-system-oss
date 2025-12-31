#!/usr/bin/env python3
"""
Test script for Prometheus parallel execution.

Tests:
1. Dependency analysis and grouping
2. Parallel vs sequential execution
3. Error handling in parallel context
4. Performance comparison
"""

import asyncio
import time
import logging
from parallel_executor import (
    ParallelExecutor,
    ParallelStrategy,
    ParallelStep,
    ParallelResult,
    add_dependency_hints,
    identify_parallel_steps
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mock executor for testing
class MockExecutor:
    """Mock executor that simulates tool execution."""

    def __init__(self, delay: float = 0.1, fail_steps: list = None):
        self.delay = delay
        self.fail_steps = fail_steps or []
        self.executions = []

    async def select_action(self, current_step: dict, state: dict, event_context: str):
        """Return a mock action for the step."""
        from dataclasses import dataclass

        @dataclass
        class MockAction:
            tool: str
            params: dict
            expected_outcome: str
            step_number: int

        return MockAction(
            tool="mock_tool",
            params={"step": current_step["number"]},
            expected_outcome=current_step.get("expected_outcome", ""),
            step_number=current_step["number"]
        )

    async def execute(self, action):
        """Simulate execution with delay."""
        await asyncio.sleep(self.delay)

        step_num = action.step_number
        self.executions.append({
            "step": step_num,
            "time": time.time()
        })

        if step_num in self.fail_steps:
            return f"error: Step {step_num} failed intentionally"

        return f"Success: Completed step {step_num}"


def test_dependency_analysis():
    """Test that dependency analysis correctly groups steps."""
    print("\n" + "="*60)
    print("TEST 1: Dependency Analysis")
    print("="*60)

    steps = [
        {"number": 1, "description": "Read file A", "tools": ["read"], "depends_on": []},
        {"number": 2, "description": "Read file B", "tools": ["read"], "depends_on": []},
        {"number": 3, "description": "Read file C", "tools": ["read"], "depends_on": []},
        {"number": 4, "description": "Merge A and B", "tools": ["write"], "depends_on": [1, 2]},
        {"number": 5, "description": "Process C", "tools": ["bash"], "depends_on": [3]},
        {"number": 6, "description": "Final combine", "tools": ["write"], "depends_on": [4, 5]},
    ]

    executor = ParallelExecutor(
        executor_factory=lambda: MockExecutor(),
        max_parallelism=10,
        strategy=ParallelStrategy.DEPENDENCY_AWARE
    )

    groups = executor.analyze_parallelism(steps)

    print(f"\nInput: {len(steps)} steps")
    print(f"Output: {len(groups)} groups")

    for i, group in enumerate(groups):
        step_nums = [s.number for s in group]
        print(f"  Group {i+1}: Steps {step_nums}")

    # Expected: Group 1: [1,2,3], Group 2: [4,5], Group 3: [6]
    assert len(groups) == 3, f"Expected 3 groups, got {len(groups)}"
    assert len(groups[0]) == 3, f"First group should have 3 steps (independent reads)"
    assert len(groups[1]) == 2, f"Second group should have 2 steps (4,5)"
    assert len(groups[2]) == 1, f"Third group should have 1 step (6)"

    print("\n[PASS] Dependency analysis working correctly")


async def test_parallel_execution():
    """Test that parallel execution actually runs concurrently."""
    print("\n" + "="*60)
    print("TEST 2: Parallel Execution Performance")
    print("="*60)

    steps = [
        {"number": 1, "description": "Task A", "tools": ["read"], "depends_on": []},
        {"number": 2, "description": "Task B", "tools": ["read"], "depends_on": []},
        {"number": 3, "description": "Task C", "tools": ["read"], "depends_on": []},
        {"number": 4, "description": "Task D", "tools": ["read"], "depends_on": []},
    ]

    delay = 0.2  # 200ms per step
    mock_exec = MockExecutor(delay=delay)

    executor = ParallelExecutor(
        executor_factory=lambda: MockExecutor(delay=delay),
        max_parallelism=10,
        strategy=ParallelStrategy.ALL_AT_ONCE
    )

    state = {"task_id": "test", "workspace": "/tmp"}

    start = time.time()
    results = await executor.execute_all_parallel(
        steps=steps,
        state=state,
        event_context=""
    )
    elapsed = time.time() - start

    print(f"\n4 steps @ {delay}s each")
    print(f"Sequential time would be: {4 * delay:.2f}s")
    print(f"Actual parallel time: {elapsed:.2f}s")
    print(f"Speedup: {(4 * delay) / elapsed:.1f}x")

    # Should be significantly faster than sequential
    assert elapsed < 4 * delay * 0.6, f"Parallel should be at least 40% faster"

    # All should succeed
    assert len(results) == 1  # One batch (ALL_AT_ONCE)
    assert results[0].all_success, "All steps should succeed"

    print("\n[PASS] Parallel execution is working")


async def test_error_handling():
    """Test that errors in one step don't crash others."""
    print("\n" + "="*60)
    print("TEST 3: Error Handling in Parallel Context")
    print("="*60)

    steps = [
        {"number": 1, "description": "Good step 1", "tools": ["read"], "depends_on": []},
        {"number": 2, "description": "Bad step (will fail)", "tools": ["read"], "depends_on": []},
        {"number": 3, "description": "Good step 3", "tools": ["read"], "depends_on": []},
    ]

    executor = ParallelExecutor(
        executor_factory=lambda: MockExecutor(delay=0.1, fail_steps=[2]),
        max_parallelism=10,
        strategy=ParallelStrategy.ALL_AT_ONCE
    )

    state = {"task_id": "test", "workspace": "/tmp"}

    results = await executor.execute_all_parallel(
        steps=steps,
        state=state,
        event_context=""
    )

    batch = results[0]
    print(f"\nResults:")
    for r in batch.results:
        status = "SUCCESS" if r.success else "FAILED"
        print(f"  Step {r.step_number}: {status}")

    # Step 2 should fail, others should succeed
    assert not batch.all_success, "Not all should succeed (step 2 fails)"
    assert 2 in batch.failed_steps, "Step 2 should be in failed list"

    # Other steps should have succeeded
    successes = [r for r in batch.results if r.success]
    assert len(successes) == 2, "Two steps should succeed"

    print("\n[PASS] Error isolation working correctly")


async def test_dependency_blocking():
    """Test that dependent steps are blocked when dependencies fail."""
    print("\n" + "="*60)
    print("TEST 4: Dependency Blocking on Failure")
    print("="*60)

    steps = [
        {"number": 1, "description": "Base step (will fail)", "tools": ["read"], "depends_on": []},
        {"number": 2, "description": "Depends on 1", "tools": ["write"], "depends_on": [1]},
        {"number": 3, "description": "Independent", "tools": ["read"], "depends_on": []},
    ]

    executor = ParallelExecutor(
        executor_factory=lambda: MockExecutor(delay=0.1, fail_steps=[1]),
        max_parallelism=10,
        strategy=ParallelStrategy.DEPENDENCY_AWARE
    )

    state = {"task_id": "test", "workspace": "/tmp"}

    results = await executor.execute_all_parallel(
        steps=steps,
        state=state,
        event_context=""
    )

    print(f"\nExecuted {len(results)} group(s)")
    for i, batch in enumerate(results):
        print(f"  Group {i+1}: {len(batch.results)} results, failed: {batch.failed_steps}")

    # First group should have steps 1 and 3
    # Step 1 fails, step 3 succeeds
    # Step 2 should be blocked (depends on failed step 1)

    assert len(results) == 1, "Should stop after first group due to critical failure"

    print("\n[PASS] Dependency blocking working correctly")


def test_identify_parallel_steps():
    """Test the helper function for identifying parallelizable steps."""
    print("\n" + "="*60)
    print("TEST 5: Identify Parallel Steps Helper")
    print("="*60)

    steps = [
        {"number": 1, "description": "Read file", "tools": ["read"]},
        {"number": 2, "description": "Search web", "tools": ["web_search"]},
        {"number": 3, "description": "Write output", "tools": ["write"]},
        {"number": 4, "description": "Run command", "tools": ["bash"]},
        {"number": 5, "description": "Grep files", "tools": ["grep"]},
    ]

    parallel, sequential = identify_parallel_steps(steps)

    print(f"\nParallel (read-only): {[s['number'] for s in parallel]}")
    print(f"Sequential (writes): {[s['number'] for s in sequential]}")

    # Read, web_search, grep are read-only
    assert len(parallel) == 3, f"Expected 3 parallel steps, got {len(parallel)}"
    # Write, bash are not read-only
    assert len(sequential) == 2, f"Expected 2 sequential steps, got {len(sequential)}"

    print("\n[PASS] Parallel step identification working")


def test_add_dependency_hints():
    """Test automatic dependency hint addition."""
    print("\n" + "="*60)
    print("TEST 6: Automatic Dependency Hints")
    print("="*60)

    steps = [
        {"number": 1, "description": "Create config.json", "tools": ["write"]},
        {"number": 2, "description": "Read config.json created above", "tools": ["read"]},
        {"number": 3, "description": "Independent task", "tools": ["bash"]},
        {"number": 4, "description": "Use previous step output", "tools": ["write"]},
    ]

    enhanced = add_dependency_hints(steps)

    print("\nDependency hints added:")
    for s in enhanced:
        deps = s.get("depends_on", [])
        print(f"  Step {s['number']}: depends_on={deps}")

    # Step 2 mentions config.json and "above" - should depend on 1
    # Step 4 mentions "previous" - should depend on 3

    assert 1 in enhanced[1].get("depends_on", []), "Step 2 should depend on 1 (mentions config.json)"

    print("\n[PASS] Dependency hints working")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PROMETHEUS PARALLEL EXECUTION TESTS")
    print("="*60)

    try:
        # Synchronous tests
        test_dependency_analysis()
        test_identify_parallel_steps()
        test_add_dependency_hints()

        # Async tests
        await test_parallel_execution()
        await test_error_handling()
        await test_dependency_blocking()

        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)

    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
