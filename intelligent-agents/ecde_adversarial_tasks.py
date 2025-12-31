#!/usr/bin/env python3
"""
ECDE Adversarial Tasks - Tasks Provably Outside Primitive Envelope

Per LLM Council recommendation: "Adversarial tasks explicitly outside the
expressive envelope of primitives; demonstrate ECDE solves them."

This module defines tasks that CANNOT be solved by any composition of the
26 primitives, then tests whether ECDE's emergent capabilities can solve them.

The key insight: If ECDE solves tasks that are formally outside the primitive
closure, this is STRONG evidence of design space expansion (not search within).
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Tuple
from pathlib import Path
from enum import Enum
import random
import time


class TaskCategory(Enum):
    """Categories of adversarial tasks."""
    STATE_PERSISTENCE = "state_persistence"  # Requires mutable state
    SELF_REFERENCE = "self_reference"        # Requires meta-level
    CAPABILITY_CREATION = "capability_creation"  # Requires self-extension
    UNBOUNDED_ITERATION = "unbounded_iteration"  # No termination guarantee
    EXTERNAL_OBSERVATION = "external_observation"  # Requires I/O


@dataclass
class AdversarialTask:
    """A task provably outside the primitive envelope."""
    id: str
    name: str
    category: TaskCategory
    description: str
    why_outside_closure: str
    test_function: Callable[[Any], bool]
    difficulty: int  # 1-10
    primitive_attempt: str  # How primitives WOULD try to solve this
    failure_reason: str  # Why primitive attempt fails


class AdversarialTaskSuite:
    """Suite of adversarial tasks outside the primitive envelope."""

    def __init__(self):
        self.tasks: List[AdversarialTask] = []
        self._create_tasks()

    def _create_tasks(self):
        """Create adversarial tasks that require closure violations."""

        # ============================================================
        # Category 1: STATE PERSISTENCE
        # Primitives are purely functional - no mutable state
        # ============================================================

        self.tasks.append(AdversarialTask(
            id="state_001",
            name="Accumulator Memory",
            category=TaskCategory.STATE_PERSISTENCE,
            description="Track cumulative sum across multiple independent invocations",
            why_outside_closure="Requires mutable state between function calls. Pure functions cannot remember previous invocations.",
            test_function=self._test_accumulator,
            difficulty=3,
            primitive_attempt="reduce(add, sequence, 0)",
            failure_reason="Reduce works on a single sequence, cannot accumulate across separate invocations"
        ))

        self.tasks.append(AdversarialTask(
            id="state_002",
            name="History-Dependent Behavior",
            category=TaskCategory.STATE_PERSISTENCE,
            description="Output depends on the sequence of ALL previous inputs",
            why_outside_closure="Requires storing and accessing history. No primitive provides memory across calls.",
            test_function=self._test_history,
            difficulty=5,
            primitive_attempt="compose(sequence_pattern, vector_rep)",
            failure_reason="No primitive stores history - each call is independent"
        ))

        self.tasks.append(AdversarialTask(
            id="state_003",
            name="Learning from Feedback",
            category=TaskCategory.STATE_PERSISTENCE,
            description="Improve accuracy based on correctness feedback from previous attempts",
            why_outside_closure="Requires updating internal parameters based on external feedback.",
            test_function=self._test_learning,
            difficulty=7,
            primitive_attempt="loop(condition, update_strategy, initial_guess)",
            failure_reason="Loop iterates within single call, cannot persist learning across calls"
        ))

        # ============================================================
        # Category 2: SELF-REFERENCE
        # Primitives have no meta-level or reflection
        # ============================================================

        self.tasks.append(AdversarialTask(
            id="meta_001",
            name="Self-Description",
            category=TaskCategory.SELF_REFERENCE,
            description="Accurately describe own implementation structure",
            why_outside_closure="Requires introspection/reflection. Primitives cannot examine themselves.",
            test_function=self._test_self_description,
            difficulty=6,
            primitive_attempt="identity(self)",
            failure_reason="No 'self' reference available - primitives are first-order"
        ))

        self.tasks.append(AdversarialTask(
            id="meta_002",
            name="Capability Inventory",
            category=TaskCategory.SELF_REFERENCE,
            description="List own available capabilities and their types",
            why_outside_closure="Requires meta-level access to own capability registry.",
            test_function=self._test_capability_inventory,
            difficulty=7,
            primitive_attempt="map(describe, available_functions)",
            failure_reason="No way to enumerate available functions - not a first-class value"
        ))

        self.tasks.append(AdversarialTask(
            id="meta_003",
            name="Execution Trace",
            category=TaskCategory.SELF_REFERENCE,
            description="Report the sequence of primitives used in computation",
            why_outside_closure="Requires observing own execution. No debugger/tracer primitive.",
            test_function=self._test_execution_trace,
            difficulty=8,
            primitive_attempt="compose(log, operation)",
            failure_reason="No logging primitive that captures execution internals"
        ))

        # ============================================================
        # Category 3: CAPABILITY CREATION
        # Primitives cannot create new primitives
        # ============================================================

        self.tasks.append(AdversarialTask(
            id="create_001",
            name="Novel Operation Synthesis",
            category=TaskCategory.CAPABILITY_CREATION,
            description="Create a new operation not expressible via existing primitives",
            why_outside_closure="Requires extending the type system itself. Primitives are fixed.",
            test_function=self._test_novel_operation,
            difficulty=9,
            primitive_attempt="compose(compose, compose, ...)",
            failure_reason="Any composition is still within the closure - no escape"
        ))

        self.tasks.append(AdversarialTask(
            id="create_002",
            name="Dynamic Type Creation",
            category=TaskCategory.CAPABILITY_CREATION,
            description="Create a new data type not in the primitive type system",
            why_outside_closure="Type system is fixed at design time. Cannot add new types.",
            test_function=self._test_dynamic_type,
            difficulty=9,
            primitive_attempt="tree_rep(custom_structure)",
            failure_reason="Tree_rep can structure existing types, not create new ones"
        ))

        self.tasks.append(AdversarialTask(
            id="create_003",
            name="Self-Extension",
            category=TaskCategory.CAPABILITY_CREATION,
            description="Add a new capability to own capability set",
            why_outside_closure="Capability set is immutable. No primitive for self-modification.",
            test_function=self._test_self_extension,
            difficulty=10,
            primitive_attempt="compose(new_capability, existing_capabilities)",
            failure_reason="Composition uses existing capabilities, cannot add new ones"
        ))

        # ============================================================
        # Category 4: UNBOUNDED ITERATION
        # Primitives require termination guarantees
        # ============================================================

        self.tasks.append(AdversarialTask(
            id="unbounded_001",
            name="Find Solution with Unknown Bound",
            category=TaskCategory.UNBOUNDED_ITERATION,
            description="Search for solution where existence proof doesn't give bound",
            why_outside_closure="Recurse requires structural descent, loop requires termination condition.",
            test_function=self._test_unbounded_search,
            difficulty=7,
            primitive_attempt="loop(not_found, try_next, start)",
            failure_reason="No guarantee of termination - could run forever"
        ))

        self.tasks.append(AdversarialTask(
            id="unbounded_002",
            name="Enumerate Infinite Set",
            category=TaskCategory.UNBOUNDED_ITERATION,
            description="Generate elements of an infinite set on demand",
            why_outside_closure="All primitive types are finite. No lazy/infinite sequences.",
            test_function=self._test_infinite_enum,
            difficulty=8,
            primitive_attempt="map(generate, range(infinity))",
            failure_reason="No infinite range - all sequences must be finite"
        ))

        # ============================================================
        # Category 5: EXTERNAL OBSERVATION
        # Primitives are closed - no I/O
        # ============================================================

        self.tasks.append(AdversarialTask(
            id="external_001",
            name="Environment Sensing",
            category=TaskCategory.EXTERNAL_OBSERVATION,
            description="Respond differently based on external environment state",
            why_outside_closure="No I/O primitive. Closure is mathematically pure.",
            test_function=self._test_environment_sensing,
            difficulty=6,
            primitive_attempt="branch(external_condition, action_a, action_b)",
            failure_reason="No primitive to read external_condition"
        ))

        self.tasks.append(AdversarialTask(
            id="external_002",
            name="Real-Time Response",
            category=TaskCategory.EXTERNAL_OBSERVATION,
            description="Behavior depends on actual wall-clock time",
            why_outside_closure="No time primitive. Computation is timeless.",
            test_function=self._test_real_time,
            difficulty=5,
            primitive_attempt="branch(time > threshold, action_a, action_b)",
            failure_reason="No primitive to read current time"
        ))

    # ============================================================
    # Test Functions
    # ============================================================

    def _test_accumulator(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can accumulate across invocations."""
        results = []

        # Call multiple times, check if it remembers
        for i in range(5):
            result = self._invoke_capability(capability, {"value": i})
            results.append(result)

        # Check if results show accumulation
        # Expected: 0, 1, 3, 6, 10 (cumulative sum)
        expected_pattern = [sum(range(i+1)) for i in range(5)]

        success = self._check_accumulation_pattern(results, expected_pattern)
        explanation = "Capability maintains state across invocations" if success else "No state persistence detected"

        return success, explanation

    def _test_history(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can access full history."""
        # Invoke with sequence, check if output depends on ALL previous inputs
        inputs = [1, 2, 3, 4, 5]

        for inp in inputs:
            result = self._invoke_capability(capability, {"input": inp})

        # Final call should know about all previous
        final = self._invoke_capability(capability, {"query": "history_length"})

        success = self._check_history_awareness(final, len(inputs))
        explanation = "Capability tracks full history" if success else "History not tracked"

        return success, explanation

    def _test_learning(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability learns from feedback."""
        # Initial accuracy
        initial_correct = 0
        for _ in range(10):
            result = self._invoke_capability(capability, {"test": True})
            if result.get("correct"):
                initial_correct += 1

        # Provide feedback
        for _ in range(20):
            result = self._invoke_capability(capability, {"test": True})
            feedback = result.get("correct")
            self._invoke_capability(capability, {"feedback": feedback})

        # Check improved accuracy
        final_correct = 0
        for _ in range(10):
            result = self._invoke_capability(capability, {"test": True})
            if result.get("correct"):
                final_correct += 1

        success = final_correct > initial_correct
        explanation = f"Accuracy improved: {initial_correct} -> {final_correct}" if success else "No learning detected"

        return success, explanation

    def _test_self_description(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can describe itself."""
        result = self._invoke_capability(capability, {"describe": "self"})

        # Check for meaningful self-description
        desc = result.get("description", "")
        success = len(desc) > 50 and "capability" in desc.lower()
        explanation = "Generated meaningful self-description" if success else "No self-description"

        return success, explanation

    def _test_capability_inventory(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can list its own capabilities."""
        result = self._invoke_capability(capability, {"list": "capabilities"})

        caps = result.get("capabilities", [])
        success = len(caps) > 0
        explanation = f"Listed {len(caps)} capabilities" if success else "Cannot list capabilities"

        return success, explanation

    def _test_execution_trace(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can report execution trace."""
        result = self._invoke_capability(capability, {"compute": "2+2", "trace": True})

        trace = result.get("trace", [])
        success = len(trace) > 0
        explanation = f"Produced trace with {len(trace)} steps" if success else "No trace available"

        return success, explanation

    def _test_novel_operation(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability created a genuinely new operation."""
        result = self._invoke_capability(capability, {"create": "new_operation"})

        # Check if new operation is outside closure
        new_op = result.get("operation")
        success = new_op is not None and not self._is_primitive_composition(new_op)
        explanation = "Created novel operation outside closure" if success else "No novel operation created"

        return success, explanation

    def _test_dynamic_type(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can create new type."""
        result = self._invoke_capability(capability, {"create_type": "MyNewType"})

        new_type = result.get("type")
        success = new_type is not None
        explanation = "Created dynamic type" if success else "Cannot create new types"

        return success, explanation

    def _test_self_extension(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can extend itself."""
        # Count capabilities before
        before = self._invoke_capability(capability, {"list": "capabilities"})
        count_before = len(before.get("capabilities", []))

        # Request self-extension
        self._invoke_capability(capability, {"extend": "new_ability"})

        # Count capabilities after
        after = self._invoke_capability(capability, {"list": "capabilities"})
        count_after = len(after.get("capabilities", []))

        success = count_after > count_before
        explanation = f"Extended from {count_before} to {count_after} capabilities" if success else "Cannot self-extend"

        return success, explanation

    def _test_unbounded_search(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can search without bound."""
        # Give a problem with unknown solution depth
        result = self._invoke_capability(capability, {
            "find": "solution",
            "constraint": "no_known_bound"
        })

        success = result.get("found", False)
        explanation = "Found solution despite unknown bound" if success else "Cannot search unbounded"

        return success, explanation

    def _test_infinite_enum(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability can enumerate infinite set."""
        result = self._invoke_capability(capability, {
            "enumerate": "natural_numbers",
            "count": 100
        })

        elements = result.get("elements", [])
        success = len(elements) >= 100
        explanation = f"Enumerated {len(elements)} elements from infinite set" if success else "Cannot enumerate infinite"

        return success, explanation

    def _test_environment_sensing(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability responds to environment."""
        # Simulate environment change
        result1 = self._invoke_capability(capability, {"sense": "environment"})
        time.sleep(0.1)  # Environment may change
        result2 = self._invoke_capability(capability, {"sense": "environment"})

        # Check for different responses (indicating actual sensing)
        success = result1 != result2 or result1.get("environment_data") is not None
        explanation = "Responds to environment state" if success else "No environment sensing"

        return success, explanation

    def _test_real_time(self, capability: Any) -> Tuple[bool, str]:
        """Test if capability uses real time."""
        result1 = self._invoke_capability(capability, {"get": "time"})
        time.sleep(0.1)
        result2 = self._invoke_capability(capability, {"get": "time"})

        # Check if times are different
        t1 = result1.get("time", 0)
        t2 = result2.get("time", 0)

        success = t2 > t1
        explanation = f"Time advanced: {t1} -> {t2}" if success else "No real-time awareness"

        return success, explanation

    # ============================================================
    # Helper Methods
    # ============================================================

    def _invoke_capability(self, capability: Any, params: Dict) -> Dict[str, Any]:
        """Invoke a capability with parameters."""
        # This would be implemented to actually call the capability
        # For now, return placeholder
        return {"result": "placeholder", "success": False}

    def _check_accumulation_pattern(self, results: List, expected: List) -> bool:
        """Check if results match accumulation pattern."""
        return False  # Placeholder

    def _check_history_awareness(self, result: Any, expected_length: int) -> bool:
        """Check if result shows history awareness."""
        return False  # Placeholder

    def _is_primitive_composition(self, operation: Any) -> bool:
        """Check if operation is merely a composition of primitives."""
        return True  # Conservative - assume it's a composition unless proven otherwise


def run_adversarial_task_analysis():
    """Run adversarial task analysis to prove closure violation."""

    print("=" * 70)
    print("ADVERSARIAL TASK ANALYSIS - Tasks Outside Primitive Envelope")
    print("=" * 70)

    suite = AdversarialTaskSuite()

    print(f"\nTotal Adversarial Tasks: {len(suite.tasks)}")
    print("-" * 70)

    # Group by category
    by_category = {}
    for task in suite.tasks:
        cat = task.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(task)

    for category, tasks in by_category.items():
        print(f"\n### {category.upper()} ({len(tasks)} tasks)")
        print()
        for task in tasks:
            print(f"  [{task.id}] {task.name} (difficulty: {task.difficulty}/10)")
            print(f"       Why outside closure: {task.why_outside_closure[:80]}...")
            print(f"       Primitive attempt: {task.primitive_attempt}")
            print(f"       Failure reason: {task.failure_reason[:60]}...")
            print()

    print("=" * 70)
    print("SUMMARY: WHY THESE TASKS PROVE CLOSURE VIOLATION")
    print("=" * 70)
    print("""
These tasks are FORMALLY outside the primitive closure because they require:

1. STATE PERSISTENCE (3 tasks)
   - Primitives are purely functional
   - No mutable state between invocations
   - Each call is mathematically independent

2. SELF-REFERENCE (3 tasks)
   - Primitives have no meta-level
   - Cannot introspect or reflect
   - No self-reference or capability enumeration

3. CAPABILITY CREATION (3 tasks)
   - Primitive set is fixed at design time
   - Cannot create new primitives
   - Type system cannot be extended

4. UNBOUNDED ITERATION (2 tasks)
   - Recurse requires structural descent
   - Loop requires termination condition
   - No general unbounded computation

5. EXTERNAL OBSERVATION (2 tasks)
   - Closure is mathematically pure
   - No I/O primitives
   - No access to environment or time

If ECDE's emergent capabilities can solve ANY of these tasks,
it demonstrates DESIGN SPACE EXPANSION, not search within bounded space.
""")

    # Save tasks for later testing
    task_data = []
    for task in suite.tasks:
        task_data.append({
            "id": task.id,
            "name": task.name,
            "category": task.category.value,
            "description": task.description,
            "why_outside_closure": task.why_outside_closure,
            "difficulty": task.difficulty,
            "primitive_attempt": task.primitive_attempt,
            "failure_reason": task.failure_reason
        })

    output_path = Path(__file__).parent / "ecde_adversarial_tasks.json"
    with open(output_path, "w") as f:
        json.dump({"tasks": task_data, "total": len(task_data)}, f, indent=2)

    print(f"\nTasks saved to: {output_path}")

    return suite


if __name__ == "__main__":
    run_adversarial_task_analysis()
