#!/usr/bin/env python3
"""
Quality Gates Rejection Demo
============================

Demonstrates that quality gates correctly reject bad modifications
and prevent them from being deployed.
"""

import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from quality_gates import QualityGateSystem


async def demo_rejection():
    """Demonstrate quality gate rejection of bad code."""

    print("\n" + "=" * 70)
    print("QUALITY GATES REJECTION DEMONSTRATION")
    print("=" * 70)
    print()

    gates = QualityGateSystem(strict_mode=True)

    # Bad modification: Security vulnerability
    bad_code = '''
import pickle
import subprocess

def load_user_data(filename):
    """Load user data from file."""
    # SECURITY ISSUE: Using pickle on untrusted data
    with open(filename, 'rb') as f:
        return pickle.load(f)

def execute_user_command(cmd):
    """Execute command from user."""
    # SECURITY ISSUE: Shell injection vulnerability
    subprocess.call(cmd, shell=True)

def process_data():
    """Process data."""
    data = load_user_data('/tmp/user_data.pkl')
    execute_user_command(data.get('command', 'ls'))
    return data
'''

    print("BAD MODIFICATION DETECTED:")
    print("-" * 70)
    print("Code with security vulnerabilities:")
    print("  - Using pickle.load() on untrusted data")
    print("  - Using subprocess.call() with shell=True")
    print()

    print("Running quality gates...")
    print()

    passed, report = await gates.check_all_gates(bad_code, "vulnerable_code.py")

    print("=" * 70)
    print("QUALITY GATE RESULTS")
    print("=" * 70)
    print()

    print(f"Overall Result: {'✓ APPROVED' if passed else '✗ REJECTED'}")
    print(f"Overall Score: {report.overall_score:.2f}/1.00")
    print()

    print("Individual Gates:")
    print("-" * 70)

    gates_to_check = [
        ('Syntax Check', report.syntax_result),
        ('Type Check', report.types_result),
        ('Security Scan', report.security_result),
        ('Complexity Check', report.complexity_result),
        ('Style Check', report.style_result)
    ]

    for name, result in gates_to_check:
        if result:
            status_icon = "✓" if result.status.value == "pass" else "✗"
            print(f"{status_icon} {name:20s}: {result.status.value.upper():8s} (score: {result.score:.2f})")
            if result.message:
                print(f"  └─ {result.message}")

    print()

    if report.critical_failures:
        print("CRITICAL FAILURES:")
        for failure in report.critical_failures:
            print(f"  ✗ {failure}")
        print()

    if report.high_failures:
        print("HIGH SEVERITY FAILURES:")
        for failure in report.high_failures:
            print(f"  ⚠ {failure}")
        print()

    print("=" * 70)
    print("DECISION")
    print("=" * 70)
    print()
    print(f"Reasoning: {report.reasoning}")
    print()

    if not passed:
        print("ACTION: Modification REJECTED and ROLLED BACK")
        print()
        print("✓ Quality gates prevented deployment of vulnerable code!")
        print("✓ System protected from security issues")
        print("✓ No testing resources wasted on bad code")
    else:
        print("⚠ WARNING: This modification should have been rejected!")

    print()
    print("=" * 70)
    print()

    return not passed  # Success if rejected


async def main():
    """Run the demonstration."""
    success = await demo_rejection()

    if success:
        print("✓ DEMONSTRATION SUCCESSFUL")
        print()
        print("Key Takeaways:")
        print("  1. Quality gates catch security issues before deployment")
        print("  2. Bad modifications are rejected in ~1 second")
        print("  3. Detailed reports explain why code was rejected")
        print("  4. System prevents testing of obviously bad code")
        print()
        return 0
    else:
        print("✗ DEMONSTRATION FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
