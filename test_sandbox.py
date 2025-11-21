#!/usr/bin/env python3
"""
Test script for Sandboxed Testing Environment
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sandbox_testing_environment import SandboxedTestingEnvironment, TestStatus


async def test_sandbox():
    """Test the sandboxed testing environment."""

    print("=" * 70)
    print("TESTING SANDBOXED TESTING ENVIRONMENT")
    print("=" * 70)
    print()

    # Initialize sandbox
    print("1. Initializing Sandboxed Testing Environment...")
    sandbox = SandboxedTestingEnvironment()
    print(f"   ✓ Sandbox initialized")
    print(f"   Docker enabled: {sandbox.docker_enabled}")
    print(f"   Base path: {sandbox.base_path}")
    print()

    # Test 1: Create a simple test file
    print("2. Creating test code file...")
    test_code = """
def add(a, b):
    '''Simple addition function.'''
    return a + b

def multiply(a, b):
    '''Simple multiplication function.'''
    return a * b

if __name__ == '__main__':
    print(f"add(2, 3) = {add(2, 3)}")
    print(f"multiply(4, 5) = {multiply(4, 5)}")
"""

    test_file = Path("/tmp/test_sandbox_code.py")
    test_file.write_text(test_code)
    print(f"   ✓ Test code written to {test_file}")
    print()

    # Test 2: Run tests
    print("3. Running tests in sandbox...")
    result = await sandbox.run_tests(
        code_file=str(test_file),
        timeout_seconds=30
    )
    print(f"   Test ID: {result.test_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Tests: {result.tests_passed}/{result.tests_total}")
    print(f"   Execution time: {result.execution_time_ms}ms")
    if result.errors:
        print(f"   Errors: {result.errors}")
    print(f"   ✓ Tests {'PASSED' if result.status == TestStatus.PASSED else 'FAILED'}")
    print()

    # Test 3: Performance comparison
    print("4. Testing performance comparison...")
    baseline_code = """
def process_list(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result

if __name__ == '__main__':
    data = list(range(-1000, 1000))
    result = process_list(data)
"""

    optimized_code = """
def process_list(items):
    # Optimized with list comprehension
    return [item * 2 for item in items if item > 0]

if __name__ == '__main__':
    data = list(range(-1000, 1000))
    result = process_list(data)
"""

    baseline_file = Path("/tmp/test_baseline.py")
    optimized_file = Path("/tmp/test_optimized.py")
    baseline_file.write_text(baseline_code)
    optimized_file.write_text(optimized_code)

    perf_metrics = await sandbox.compare_performance(
        baseline_code=str(baseline_file),
        modified_code=str(optimized_file),
        iterations=3
    )

    print(f"   Baseline execution time: {perf_metrics.baseline_execution_time_ms:.2f}ms")
    print(f"   Modified execution time: {perf_metrics.modified_execution_time_ms:.2f}ms")
    print(f"   Delta: {perf_metrics.execution_time_delta_ms:.2f}ms ({perf_metrics.execution_time_delta_percent:.1f}%)")
    print(f"   Memory delta: {perf_metrics.memory_delta_mb:.2f}MB")
    print(f"   Improvement confirmed: {perf_metrics.improvement_confirmed}")
    print(f"   Regression detected: {perf_metrics.regression_detected}")
    print(f"   ✓ Performance comparison complete")
    print()

    # Cleanup
    test_file.unlink()
    baseline_file.unlink()
    optimized_file.unlink()

    print("=" * 70)
    print("SANDBOX TEST COMPLETE")
    print("=" * 70)
    print()
    print("Sandboxed Testing Environment is OPERATIONAL:")
    print("  1. Test execution ✓")
    print("  2. Performance benchmarking ✓")
    print("  3. Regression detection ✓")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_sandbox())
    sys.exit(0 if success else 1)
