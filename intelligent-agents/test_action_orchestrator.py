#!/usr/bin/env python3
"""
Test Action Orchestrator - Comprehensive Testing
================================================

Tests all intent types and execution scenarios:
1. COMMAND: File operations, bash execution
2. QUERY: Information retrieval
3. CONVERSATION: Natural language responses
4. META: System control and status

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 test_action_orchestrator.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from action_orchestrator import (
    ActionOrchestrator,
    Intent,
    IntentType,
    ActionStatus
)


async def test_command_intent():
    """Test COMMAND intent - file creation"""
    print("\n" + "=" * 60)
    print("TEST 1: COMMAND Intent - Create Python File")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path(tempfile.gettempdir())
    )

    intent = Intent(
        type=IntentType.COMMAND,
        text="Create a Python file called test_hello.py that prints 'Hello from voice command!'",
        entities={"file_name": "test_hello.py"},
        confidence=0.95
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Steps executed: {len(result.steps)}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"✓ Tokens used: {result.tokens_used}")
    print(f"\nOutput:\n{result.output}")
    print(f"\nSummary:\n{result.summary}")

    # Verify file was created
    test_file = Path(tempfile.gettempdir()) / "test_hello.py"
    if test_file.exists():
        print(f"\n✓ File verified: {test_file}")
        print(f"Content:\n{test_file.read_text()}")
    else:
        print(f"\n✗ File not found: {test_file}")

    return result


async def test_query_intent():
    """Test QUERY intent - information retrieval"""
    print("\n" + "=" * 60)
    print("TEST 2: QUERY Intent - List Files")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.QUERY,
        text="What Python files are in the current directory?",
        entities={"file_type": "python"},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Steps executed: {len(result.steps)}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"✓ Tokens used: {result.tokens_used}")
    print(f"\nOutput:\n{result.output}")

    return result


async def test_conversation_intent():
    """Test CONVERSATION intent - natural language"""
    print("\n" + "=" * 60)
    print("TEST 3: CONVERSATION Intent - Greeting")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.CONVERSATION,
        text="Hello! How are you doing today?",
        entities={},
        confidence=0.85
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"✓ Tokens used: {result.tokens_used}")
    print(f"\nResponse:\n{result.output}")

    return result


async def test_meta_intent():
    """Test META intent - system status"""
    print("\n" + "=" * 60)
    print("TEST 4: META Intent - System Status")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.META,
        text="What is the current system status?",
        entities={},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"\nStatus:\n{result.output}")

    return result


async def test_bash_execution():
    """Test bash command execution"""
    print("\n" + "=" * 60)
    print("TEST 5: COMMAND Intent - Bash Execution")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.COMMAND,
        text="Run the command 'echo Hello from bash' and show me the output",
        entities={},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Steps executed: {len(result.steps)}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"\nOutput:\n{result.output}")

    return result


async def test_file_search():
    """Test grep/search functionality"""
    print("\n" + "=" * 60)
    print("TEST 6: QUERY Intent - Search Files")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.QUERY,
        text="Search for the word 'orchestrator' in Python files",
        entities={"search_term": "orchestrator"},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"\nSearch results:\n{result.output[:500]}...")

    return result


async def test_error_handling():
    """Test error handling with invalid command"""
    print("\n" + "=" * 60)
    print("TEST 7: Error Handling - Invalid File Operation")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path.cwd()
    )

    intent = Intent(
        type=IntentType.COMMAND,
        text="Read a file that doesn't exist called nonexistent_file_12345.txt",
        entities={"file_path": "nonexistent_file_12345.txt"},
        confidence=0.9
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Errors captured: {len(result.errors)}")
    print(f"\nErrors:\n{result.errors}")
    print(f"\nSummary:\n{result.summary}")

    return result


async def test_multi_step_command():
    """Test complex multi-step command"""
    print("\n" + "=" * 60)
    print("TEST 8: COMMAND Intent - Multi-Step Execution")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path(tempfile.gettempdir())
    )

    intent = Intent(
        type=IntentType.COMMAND,
        text="Create a Python file called math_ops.py with functions for add, subtract, multiply, and divide",
        entities={"file_name": "math_ops.py", "operations": ["add", "subtract", "multiply", "divide"]},
        confidence=0.95
    )

    result = await orchestrator.execute_intent(intent)

    print(f"✓ Success: {result.success}")
    print(f"✓ Steps executed: {len(result.steps)}")
    print(f"✓ Duration: {result.total_duration_ms}ms")
    print(f"✓ Tokens used: {result.tokens_used}")

    # Show step details
    print("\nExecution Steps:")
    for step in result.steps:
        status_icon = "✓" if step.status == ActionStatus.SUCCESS else "✗"
        print(f"  {status_icon} Step {step.step_number}: {step.description} ({step.duration_ms}ms)")

    print(f"\nOutput:\n{result.output}")

    # Verify file
    test_file = Path(tempfile.gettempdir()) / "math_ops.py"
    if test_file.exists():
        print(f"\n✓ File verified: {test_file}")
        content = test_file.read_text()
        print(f"Content preview (first 300 chars):\n{content[:300]}...")
    else:
        print(f"\n✗ File not found: {test_file}")

    return result


async def test_context_awareness():
    """Test context awareness across multiple intents"""
    print("\n" + "=" * 60)
    print("TEST 9: Context Awareness - Multiple Intents")
    print("=" * 60)

    orchestrator = ActionOrchestrator(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        working_dir=Path(tempfile.gettempdir())
    )

    # First intent: Create a file
    intent1 = Intent(
        type=IntentType.COMMAND,
        text="Create a file called test_context.txt with the content 'Context test'",
        entities={"file_name": "test_context.txt"},
        confidence=0.9
    )

    result1 = await orchestrator.execute_intent(intent1)
    print(f"✓ Intent 1 - Success: {result1.success}")

    # Second intent: Ask about recent actions
    intent2 = Intent(
        type=IntentType.META,
        text="What did you just do?",
        entities={},
        confidence=0.9
    )

    result2 = await orchestrator.execute_intent(intent2)
    print(f"✓ Intent 2 - Success: {result2.success}")
    print(f"\nContext response:\n{result2.output}")

    # Third intent: Query about the file
    intent3 = Intent(
        type=IntentType.QUERY,
        text="What files did we create?",
        entities={},
        confidence=0.9
    )

    result3 = await orchestrator.execute_intent(intent3)
    print(f"✓ Intent 3 - Success: {result3.success}")
    print(f"\nFile query response:\n{result3.output}")

    return result1, result2, result3


async def run_all_tests():
    """Run comprehensive test suite"""
    print("=" * 60)
    print("ACTION ORCHESTRATOR COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n✗ ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='sk-ant-...'")
        return

    print(f"\n✓ API key found: {api_key[:20]}...")

    # Run tests
    try:
        results = []

        results.append(await test_command_intent())
        results.append(await test_query_intent())
        results.append(await test_conversation_intent())
        results.append(await test_meta_intent())
        results.append(await test_bash_execution())
        results.append(await test_file_search())
        results.append(await test_error_handling())
        results.append(await test_multi_step_command())
        context_results = await test_context_awareness()
        results.extend(context_results)

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        # Flatten results (context_results is a tuple)
        flat_results = []
        for r in results:
            if isinstance(r, tuple):
                flat_results.extend(r)
            else:
                flat_results.append(r)

        total_tests = len(flat_results)
        passed = sum(1 for r in flat_results if r.success)
        failed = total_tests - passed

        total_duration = sum(r.total_duration_ms for r in flat_results)
        total_tokens = {
            "input": sum(r.tokens_used.get("input", 0) for r in flat_results),
            "output": sum(r.tokens_used.get("output", 0) for r in flat_results)
        }
        total_steps = sum(len(r.steps) for r in flat_results)

        print(f"\nTests Run: {total_tests}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"\nTotal Duration: {total_duration}ms ({total_duration/1000:.2f}s)")
        print(f"Total Steps: {total_steps}")
        print(f"Total Tokens: {total_tokens['input']} input, {total_tokens['output']} output")
        print(f"              {total_tokens['input'] + total_tokens['output']} total")

        if passed == total_tests:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) failed")

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
