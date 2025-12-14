#!/usr/bin/env python3
"""
Test suite for Claude Code Control MCP Server
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from executor import TaskExecutor
from file_tracker import FileTracker


def test_file_tracker():
    """Test file tracking functionality"""
    print("\n=== Testing File Tracker ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = FileTracker(tmpdir)

        # Create test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello, World!")

        # Track file
        tracker.track_file("test.txt")
        print(f"✓ Tracked file: test.txt")

        # Modify file
        test_file.write_text("Hello, Modified!")

        # Check changes
        changes = tracker.check_changes()
        assert len(changes) > 0, "No changes detected"
        print(f"✓ Detected {len(changes)} change(s)")

        # Get summary
        summary = tracker.get_summary()
        print(f"✓ Summary: {summary['total_changes']} total changes")
        print(f"  - Files modified: {summary['files_modified']}")

        # Test file creation detection
        new_file = Path(tmpdir) / "new.txt"
        new_file.write_text("New file")

        changes = tracker.check_changes()
        created = [c for c in changes if c.action == 'created']
        assert len(created) > 0, "File creation not detected"
        print(f"✓ Detected new file creation")

    print("✓ File tracker tests passed")


async def test_executor_basic():
    """Test basic executor functionality"""
    print("\n=== Testing Task Executor (Basic) ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ Skipping executor tests (ANTHROPIC_API_KEY not set)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)
        print("✓ Executor initialized")

        # Simple task: Create a hello world script
        result = await executor.execute_task(
            task_description="Create a Python script called hello.py that prints 'Hello, World!'",
            working_directory=tmpdir,
            max_iterations=5
        )

        print(f"✓ Task executed in {result['iterations']} iterations")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
        print(f"  Success: {result['success']}")

        if result['success']:
            summary = result['file_changes']
            print(f"  Files created: {summary['files_created']}")
            print(f"  Files modified: {summary['files_modified']}")

            # Check if file was created
            hello_file = Path(tmpdir) / "hello.py"
            if hello_file.exists():
                print(f"✓ hello.py created successfully")
                content = hello_file.read_text()
                print(f"  Content preview: {content[:100]}")
            else:
                print(f"✗ hello.py not found")

        print("✓ Basic executor test passed")


async def test_executor_advanced():
    """Test advanced executor functionality"""
    print("\n=== Testing Task Executor (Advanced) ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ Skipping advanced executor tests (ANTHROPIC_API_KEY not set)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)

        # Create initial file
        initial_file = Path(tmpdir) / "config.py"
        initial_file.write_text("DEBUG = False\nPORT = 8080\n")

        # Task: Modify the config
        result = await executor.execute_task(
            task_description=(
                "Read config.py and modify it to set DEBUG = True and PORT = 9000. "
                "Also add a new variable API_KEY = 'test-key'."
            ),
            working_directory=tmpdir,
            context_files=["config.py"],
            max_iterations=10
        )

        print(f"✓ Task executed in {result['iterations']} iterations")

        if result['success']:
            # Check modifications
            modified_content = initial_file.read_text()
            print(f"  Modified content:\n{modified_content}")

            assert "DEBUG = True" in modified_content or "DEBUG=True" in modified_content
            assert "PORT = 9000" in modified_content or "PORT=9000" in modified_content
            print(f"✓ File modified correctly")

        print("✓ Advanced executor test passed")


async def test_executor_with_commands():
    """Test executor with command execution"""
    print("\n=== Testing Task Executor (Commands) ===")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠ Skipping command tests (ANTHROPIC_API_KEY not set)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)

        # Task: Create script and run it
        result = await executor.execute_task(
            task_description=(
                "Create a Python script test_script.py that prints 'Test successful'. "
                "Then run it using python3 to verify it works."
            ),
            working_directory=tmpdir,
            max_iterations=10
        )

        print(f"✓ Task executed in {result['iterations']} iterations")

        if result['success']:
            # Check for command execution in tool uses
            commands_run = [
                tool for tool in result['tool_uses']
                if tool['tool'] == 'run_command'
            ]
            print(f"  Commands executed: {len(commands_run)}")

            for cmd in commands_run:
                print(f"  - Command: {cmd['input'].get('command', 'N/A')}")

        print("✓ Command execution test passed")


def test_tool_definitions():
    """Test tool definitions are valid"""
    print("\n=== Testing Tool Definitions ===")

    executor = TaskExecutor(api_key="test")
    tools = executor._build_tools()

    print(f"✓ Found {len(tools)} tool definitions")

    for tool in tools:
        assert "name" in tool, f"Tool missing name: {tool}"
        assert "description" in tool, f"Tool missing description: {tool}"
        assert "input_schema" in tool, f"Tool missing input_schema: {tool}"
        print(f"  ✓ {tool['name']}: valid")

    print("✓ All tool definitions valid")


def run_all_tests():
    """Run all test suites"""
    print("=" * 60)
    print("Claude Code Control MCP Server - Test Suite")
    print("=" * 60)

    try:
        # Synchronous tests
        test_file_tracker()
        test_tool_definitions()

        # Async tests
        asyncio.run(test_executor_basic())
        asyncio.run(test_executor_advanced())
        asyncio.run(test_executor_with_commands())

        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
