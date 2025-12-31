#!/usr/bin/env python3
"""
Test script for Project Prometheus components.

Run with: python3 test_prometheus.py
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test all imports work."""
    print("Testing imports...")

    try:
        from prometheus import (
            PrometheusAgentLoop,
            EventStream,
            Event,
            EventType,
            TodoManager
        )
        print("  Core imports OK")

        from prometheus.agents import (
            PlannerAgent,
            ExecutorAgent,
            VerifierAgent,
            KnowledgeAgent
        )
        print("  Agent imports OK")

        return True
    except ImportError as e:
        print(f"  Import failed: {e}")
        return False


def test_event_stream():
    """Test event stream functionality."""
    print("\nTesting EventStream...")

    from prometheus.event_stream import EventStream, Event, EventType

    stream = EventStream(max_tokens=1000)

    # Add events
    stream.append(Event.action("read", {"path": "/test.txt"}))
    stream.append(Event.observation("File contents here", success=True))
    stream.append(Event.error("Something went wrong", "Traceback..."))
    stream.append(Event.plan(["Step 1", "Step 2", "Step 3"]))

    assert len(stream) == 4, f"Expected 4 events, got {len(stream)}"
    print(f"  Added {len(stream)} events OK")

    # Test context formatting
    context = stream.to_context()
    assert "[ACTION]" in context
    assert "[OBSERVATION]" in context
    assert "[ERROR]" in context
    print("  Context formatting OK")

    # Test error retrieval
    errors = stream.get_errors()
    assert len(errors) == 1
    print("  Error retrieval OK")

    return True


def test_todo_manager():
    """Test todo manager functionality."""
    print("\nTesting TodoManager...")

    from prometheus.todo_manager import TodoManager, StepStatus

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        manager = TodoManager(workspace)

        # Initialize with steps
        steps = [
            {"description": "First step", "tools": ["read", "write"]},
            {"description": "Second step", "tools": ["bash"]},
            {"description": "Third step", "tools": ["notify"]}
        ]
        manager.initialize("Test task", steps)
        print("  Initialization OK")

        # Check file exists
        assert manager.todo_path.exists()
        print("  File creation OK")

        # Update steps
        manager.start_step(1)
        assert manager.steps[0].status == StepStatus.IN_PROGRESS
        print("  Start step OK")

        manager.complete_step(1, "Done!")
        assert manager.steps[0].status == StepStatus.COMPLETED
        print("  Complete step OK")

        # Check progress
        completed, total = manager.get_progress()
        assert completed == 1 and total == 3
        print(f"  Progress: {completed}/{total} OK")

        # Get focus context
        focus = manager.get_focus_context()
        assert "Current Focus" in focus
        print("  Focus context OK")

    return True


def test_agents():
    """Test agent instantiation."""
    print("\nTesting Agents...")

    from prometheus.agents import (
        PlannerAgent,
        ExecutorAgent,
        VerifierAgent,
        KnowledgeAgent
    )

    planner = PlannerAgent()
    print("  PlannerAgent OK")

    executor = ExecutorAgent(sandbox_node="macpro51")
    print("  ExecutorAgent OK")

    verifier = VerifierAgent()
    print("  VerifierAgent OK")

    knowledge = KnowledgeAgent()
    print("  KnowledgeAgent OK")

    return True


def test_verifier_patterns():
    """Test verifier pattern matching."""
    print("\nTesting Verifier patterns...")

    from prometheus.agents.verifier import VerifierAgent

    verifier = VerifierAgent()

    # Test error detection
    result = verifier._quick_verify("Error: File not found")
    assert not result.success
    print("  Error detection OK")

    # Test success detection
    result = verifier._quick_verify("File created successfully")
    assert result.success
    print("  Success detection OK")

    # Test ambiguous
    result = verifier._quick_verify("Processing complete")
    assert result.success
    print("  Ambiguous handling OK")

    return True


async def test_agent_loop():
    """Test agent loop instantiation."""
    print("\nTesting PrometheusAgentLoop...")

    from prometheus.agent_loop import PrometheusAgentLoop

    loop = PrometheusAgentLoop(
        max_iterations=10,
        sandbox_node="macpro51"
    )
    print("  Instantiation OK")

    # Test workspace creation
    loop.task_id = "test_001"
    workspace = loop._create_workspace()
    assert workspace.exists()
    print(f"  Workspace created: {workspace}")

    # Cleanup
    import shutil
    shutil.rmtree(workspace)

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Project Prometheus - Component Tests")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("EventStream", test_event_stream),
        ("TodoManager", test_todo_manager),
        ("Agents", test_agents),
        ("Verifier Patterns", test_verifier_patterns),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAILED: {name} - {e}")

    # Run async tests
    async def run_async_tests():
        return await test_agent_loop()

    try:
        if asyncio.run(run_async_tests()):
            passed += 1
        else:
            failed += 1
    except Exception as e:
        failed += 1
        print(f"  FAILED: AgentLoop - {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
