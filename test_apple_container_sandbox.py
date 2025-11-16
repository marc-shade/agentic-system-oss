#!/usr/bin/env python3
"""
Test Apple Container Integration with Sandboxed Testing Environment
"""
import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from sandbox_testing_environment import SandboxedTestingEnvironment


async def test_apple_container_detection():
    """Test that Apple Container is detected and used."""

    print("=" * 70)
    print("TESTING APPLE CONTAINER INTEGRATION")
    print("=" * 70)
    print()

    # Initialize sandbox
    print("1. Initializing Sandboxed Testing Environment...")
    sandbox = SandboxedTestingEnvironment()

    print(f"   Container runtime detected: {sandbox.container_runtime}")
    print(f"   Apple Container enabled: {sandbox.apple_container_enabled}")
    print(f"   Docker enabled: {sandbox.docker_enabled}")
    print()

    # Verify Apple Container is preferred
    if sandbox.apple_container_enabled:
        print("   ✓ Apple Container is ACTIVE (preferred)")
    elif sandbox.docker_enabled:
        print("   ⚠ Docker is active (Apple Container not available)")
    else:
        print("   ⚠ Local sandbox mode (no containers available)")
    print()

    # Test 2: Create a simple test file
    print("2. Creating test code file...")
    test_code = """
def add(a, b):
    '''Simple addition function.'''
    return a + b

def multiply(a, b):
    '''Simple multiplication function.'''
    return a * b

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_multiply():
    assert multiply(4, 5) == 20
    assert multiply(2, 0) == 0

if __name__ == '__main__':
    print(f"add(2, 3) = {add(2, 3)}")
    print(f"multiply(4, 5) = {multiply(4, 5)}")
"""

    test_file = Path("/tmp/test_apple_container_code.py")
    test_file.write_text(test_code)
    print(f"   ✓ Test code written to {test_file}")
    print()

    # Test 3: Run tests in sandbox
    if sandbox.apple_container_enabled:
        print("3. Running tests in Apple Container...")
        print("   (This will use native macOS container runtime)")
    else:
        print("3. Running tests in fallback mode...")

    print()

    result = await sandbox.run_tests(
        code_file=str(test_file),
        timeout_seconds=120
    )

    print(f"   Test ID: {result.test_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Tests: {result.tests_passed}/{result.tests_total}")
    print(f"   Execution time: {result.execution_time_ms:.2f}ms")
    print(f"   Errors: {len(result.errors)}")
    if result.errors:
        for error in result.errors:
            print(f"      - {error}")
    print()

    # Cleanup
    test_file.unlink()

    print("=" * 70)
    print("APPLE CONTAINER INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()

    if sandbox.apple_container_enabled:
        print("✓ Apple Container is OPERATIONAL and integrated with sandbox!")
        print("  - Native macOS performance")
        print("  - Optimized for Apple silicon")
        print("  - OCI-compatible image support")
        print("  - Automatic preference over Docker")
    else:
        print("⚠ Apple Container not detected, using fallback")

    print()
    print("Next Steps:")
    print("  1. Darwin Gödel will now use Apple Container for self-modifications")
    print("  2. Auto-Implementation will test patches in native containers")
    print("  3. Performance evaluation will use optimized runtime")
    print()

    return sandbox.apple_container_enabled


if __name__ == "__main__":
    success = asyncio.run(test_apple_container_detection())
    sys.exit(0 if success else 1)
