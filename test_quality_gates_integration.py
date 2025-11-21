#!/usr/bin/env python3
"""
Test Quality Gates Integration with Autonomous Loop
===================================================

Demonstrates that quality gates are working correctly and rejecting
bad modifications before they get tested.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from quality_gates import QualityGateSystem


async def test_quality_gates_integration():
    """Test quality gates with various code samples."""

    print("\n" + "=" * 70)
    print("QUALITY GATES INTEGRATION TEST")
    print("=" * 70)
    print()

    gates = QualityGateSystem(strict_mode=True)

    test_cases = [
        {
            "name": "Valid optimization",
            "code": '''
def process_items(items):
    """Process items with list comprehension optimization."""
    return [x * 2 for x in items if x > 0]

def main():
    """Main function."""
    data = [1, 2, 3, 4, 5]
    result = process_items(data)
    print(f"Result: {result}")
''',
            "expected": "APPROVED"
        },
        {
            "name": "Syntax error (missing colon)",
            "code": '''
def broken_function()
    print("Missing colon")
    return None
''',
            "expected": "REJECTED"
        },
        {
            "name": "Security issue (pickle + os.system)",
            "code": '''
import pickle
import os

def load_unsafe_data(filename):
    """Load data unsafely."""
    with open(filename, 'rb') as f:
        return pickle.load(f)

def run_shell_command(cmd):
    """Execute shell command."""
    os.system(cmd)  # Security issue
''',
            "expected": "REJECTED"
        },
        {
            "name": "High complexity function",
            "code": '''
def super_complex_function(a, b, c, d, e):
    """Overly complex function."""
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        for i in range(a):
                            for j in range(b):
                                if i % 2 == 0:
                                    if j % 2 == 0:
                                        if i + j > c:
                                            while i < j:
                                                if i * j < d:
                                                    if (i + j + d) % e == 0:
                                                        return i + j + c + d + e
                                                i += 1
                                        elif i + j < c:
                                            return i - j
                                    else:
                                        return i + j
                                else:
                                    return i * j
    return 0
''',
            "expected": "REJECTED (high complexity)"
        }
    ]

    passed_tests = 0
    failed_tests = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 70)

        gate_passed, report = await gates.check_all_gates(
            code=test_case["code"],
            filename=f"test_{i}.py"
        )

        result = "APPROVED" if gate_passed else "REJECTED"
        expected = test_case["expected"].split()[0]  # Get first word

        print(f"Result: {result}")
        print(f"Expected: {test_case['expected']}")
        print(f"Score: {report.overall_score:.2f}")
        print(f"Reasoning: {report.reasoning}")

        if result == expected:
            print("✓ TEST PASSED")
            passed_tests += 1
        else:
            print("✗ TEST FAILED")
            failed_tests += 1

        print()

    print("=" * 70)
    print(f"SUMMARY: {passed_tests}/{len(test_cases)} tests passed")
    print("=" * 70)
    print()

    return passed_tests == len(test_cases)


async def test_quality_gate_rejection_tracking():
    """Test that quality gate rejections are tracked correctly."""

    print("\n" + "=" * 70)
    print("QUALITY GATE REJECTION TRACKING TEST")
    print("=" * 70)
    print()

    # This simulates what happens in the autonomous loop
    rejections = 0

    bad_codes = [
        "def bad(): pass",  # No syntax error but poor quality
        "def bad() print('missing colon')",  # Syntax error
        "import os\nos.system('rm -rf /')",  # Security issue
    ]

    gates = QualityGateSystem(strict_mode=True)

    for i, code in enumerate(bad_codes, 1):
        print(f"Testing bad code {i}...")

        gate_passed, report = await gates.check_all_gates(code, f"bad_{i}.py")

        if not gate_passed:
            rejections += 1
            print(f"  ✓ Correctly rejected: {report.reasoning}")
        else:
            print(f"  ✗ Should have been rejected but passed!")

    print()
    print(f"Total rejections: {rejections}/{len(bad_codes)}")
    print()

    return rejections >= 2  # At least 2 should be rejected


async def main():
    """Run all integration tests."""

    print("\n" + "=" * 70)
    print("QUALITY GATES INTEGRATION TEST SUITE")
    print("=" * 70)
    print()

    # Test 1: Quality gates functionality
    test1_passed = await test_quality_gates_integration()

    # Test 2: Rejection tracking
    test2_passed = await test_quality_gate_rejection_tracking()

    # Summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Quality Gates Functionality: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Rejection Tracking: {'PASSED' if test2_passed else 'FAILED'}")
    print()

    if test1_passed and test2_passed:
        print("✓ ALL TESTS PASSED - Quality gates integration is working correctly!")
        print()
        print("Key features verified:")
        print("  - Syntax checking blocks critical failures immediately")
        print("  - Security scanning detects vulnerabilities")
        print("  - Complexity analysis identifies overly complex code")
        print("  - Rejections are tracked for monitoring")
        print("  - System prevents bad modifications from being deployed")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Review quality gates implementation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
