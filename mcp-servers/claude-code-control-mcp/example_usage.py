#!/usr/bin/env python3
"""
Example usage of Claude Code Control MCP components
Demonstrates how to use the executor directly for programmatic task execution
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from executor import TaskExecutor
from file_tracker import FileTracker


async def example_create_simple_script():
    """Example 1: Create a simple Python script"""
    print("\n" + "="*60)
    print("Example 1: Create Simple Script")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)

        result = await executor.execute_task(
            task_description="Create a Python script called greet.py that takes a name as command line argument and prints 'Hello, {name}!'",
            working_directory=tmpdir,
            max_iterations=10
        )

        print(f"\n✓ Task completed in {result['iterations']} iterations")
        print(f"  Duration: {result['duration_seconds']:.2f} seconds")
        print(f"  Success: {result['success']}")

        if result['success']:
            print(f"\nFile changes:")
            print(f"  Created: {result['file_changes']['files_created']}")
            print(f"  Modified: {result['file_changes']['files_modified']}")

            # Show the created file
            script_path = Path(tmpdir) / "greet.py"
            if script_path.exists():
                print(f"\nCreated script content:")
                print("-" * 60)
                print(script_path.read_text())
                print("-" * 60)


async def example_refactor_code():
    """Example 2: Refactor existing code"""
    print("\n" + "="*60)
    print("Example 2: Refactor Existing Code")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create initial code
        initial_code = '''
def calculate(x, y, op):
    if op == 'add':
        return x + y
    elif op == 'subtract':
        return x - y
    elif op == 'multiply':
        return x * y
    elif op == 'divide':
        return x / y
'''
        code_file = Path(tmpdir) / "calculator.py"
        code_file.write_text(initial_code)

        executor = TaskExecutor(api_key)

        result = await executor.execute_task(
            task_description=(
                "Refactor calculator.py to use a dictionary mapping for operations "
                "instead of if/elif chains. Add type hints and docstrings."
            ),
            working_directory=tmpdir,
            context_files=["calculator.py"],
            max_iterations=10
        )

        print(f"\n✓ Task completed in {result['iterations']} iterations")

        if result['success']:
            print(f"\nRefactored code:")
            print("-" * 60)
            print(code_file.read_text())
            print("-" * 60)


async def example_create_with_tests():
    """Example 3: Create code with tests"""
    print("\n" + "="*60)
    print("Example 3: Create Code with Tests")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)

        result = await executor.execute_task(
            task_description=(
                "Create a Python module fibonacci.py with a function to calculate "
                "fibonacci numbers. Then create test_fibonacci.py with comprehensive "
                "unit tests using pytest. Finally, run the tests to verify they pass."
            ),
            working_directory=tmpdir,
            max_iterations=20
        )

        print(f"\n✓ Task completed in {result['iterations']} iterations")

        if result['success']:
            print(f"\nFiles created:")
            for file in result['file_changes']['files_created']:
                print(f"  - {file}")

            print(f"\nTool uses:")
            for tool in result['tool_uses']:
                print(f"  - {tool['tool']}: {str(tool['input'])[:60]}...")

            # Show the test results if tests were run
            test_runs = [
                tool for tool in result['tool_uses']
                if tool['tool'] == 'run_command' and 'pytest' in tool['input'].get('command', '')
            ]
            if test_runs:
                print(f"\nTest execution:")
                for test in test_runs:
                    print(f"  Command: {test['input']['command']}")
                    print(f"  Result: {test['result'][:200]}...")


async def example_file_tracking():
    """Example 4: Demonstrate file tracking"""
    print("\n" + "="*60)
    print("Example 4: File Change Tracking")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = FileTracker(tmpdir)

        # Create some files
        file1 = Path(tmpdir) / "file1.txt"
        file1.write_text("Original content 1")
        tracker.track_file("file1.txt")

        file2 = Path(tmpdir) / "file2.txt"
        file2.write_text("Original content 2")
        tracker.track_file("file2.txt")

        print("✓ Created and tracked 2 files")

        # Modify files
        file1.write_text("Modified content 1")
        file2.write_text("Modified content 2 - much longer!")

        # Create new file
        file3 = Path(tmpdir) / "file3.txt"
        file3.write_text("New file content")

        print("✓ Modified existing files and created new file")

        # Check changes
        changes = tracker.check_changes()
        summary = tracker.get_summary()

        print(f"\n✓ Detected changes:")
        print(f"  Total changes: {summary['total_changes']}")
        print(f"  Files created: {len(summary['files_created'])}")
        print(f"  Files modified: {len(summary['files_modified'])}")

        print(f"\nDetailed changes:")
        for change in summary['detailed_changes']:
            print(f"  - {change['action']}: {change['path']}")
            if change['size_change']:
                print(f"    Size change: {change['size_change']:+d} bytes")


async def example_batch_operations():
    """Example 5: Batch file operations"""
    print("\n" + "="*60)
    print("Example 5: Batch Operations")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        executor = TaskExecutor(api_key)

        result = await executor.execute_task(
            task_description=(
                "Create a simple Python package structure with:\n"
                "1. __init__.py with package metadata\n"
                "2. utils.py with helper functions\n"
                "3. main.py with a main entry point\n"
                "4. requirements.txt with dependencies\n"
                "5. README.md with usage instructions"
            ),
            working_directory=tmpdir,
            max_iterations=15
        )

        print(f"\n✓ Task completed in {result['iterations']} iterations")

        if result['success']:
            print(f"\nPackage structure created:")
            for file in result['file_changes']['files_created']:
                print(f"  - {file}")

            # List all files
            print(f"\nDirectory contents:")
            for path in Path(tmpdir).rglob('*'):
                if path.is_file():
                    rel_path = path.relative_to(tmpdir)
                    size = path.stat().st_size
                    print(f"  {rel_path} ({size} bytes)")


async def main():
    """Run all examples"""
    print("="*60)
    print("Claude Code Control MCP - Usage Examples")
    print("="*60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠ Warning: ANTHROPIC_API_KEY not set")
        print("Some examples will be skipped.")
        print("\nTo run all examples, set your API key:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")

    # Run examples
    await example_file_tracking()  # No API key needed

    if api_key:
        await example_create_simple_script()
        await example_refactor_code()
        await example_create_with_tests()
        await example_batch_operations()
    else:
        print("\n⚠ Skipping API-dependent examples")

    print("\n" + "="*60)
    print("✓ All examples completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
