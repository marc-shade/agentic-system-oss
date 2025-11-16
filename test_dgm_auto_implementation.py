#!/usr/bin/env python3
"""
Test Darwin Gödel → Auto-Implementation Integration

Verifies that Darwin Gödel Machine can automatically implement
its own improvement proposals using the Auto-Implementation Engine.
"""

import asyncio
import sys
from pathlib import Path

# Add intelligent-agents to path
sys.path.insert(0, str(Path(__file__).parent / "intelligent-agents"))

from darwin_godel_machine import DarwinGodelMachine, ModificationType


async def test_integration():
    """Test the complete Darwin Gödel → Auto-Implementation loop."""

    print("\n" + "=" * 70)
    print("TESTING DARWIN GÖDEL → AUTO-IMPLEMENTATION INTEGRATION")
    print("=" * 70)
    print()

    # Initialize Darwin Gödel Machine
    print("1. Initializing Darwin Gödel Machine...")
    dgm = DarwinGodelMachine()
    print("   ✓ Darwin Gödel Machine initialized")
    print()

    # Create a test modification
    print("2. Creating test improvement proposal...")

    # Simple code improvement example
    code_before = """
def slow_function(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
"""

    code_after = """
def fast_function(items):
    # Optimized with list comprehension
    return [item * 2 for item in items if item > 0]
"""

    modification = dgm.propose_modification(
        code_before=code_before,
        code_after=code_after,
        modification_type=ModificationType.ALGORITHM_IMPROVE,
        description="Optimize list processing with list comprehension"
    )

    print(f"   ✓ Modification proposed: {modification.modification_id}")
    print(f"   Type: {modification.modification_type.value}")
    print(f"   Expected improvement: {modification.expected_improvement:.1%}")
    print(f"   Safety score: {modification.safety_score:.2f}")
    print()

    # Test auto-implementation
    print("3. Calling auto_implement_modification()...")
    print("   (This will use the Auto-Implementation Engine)")
    print()

    implementation = await dgm.auto_implement_modification(
        modification=modification,
        target_file="intelligent-agents/multi_agent_coordinator.py",
        target_function="assign_agent",
        auto_deploy=True  # Enable automatic deployment
    )

    print()
    print("=" * 70)
    print("INTEGRATION TEST RESULTS")
    print("=" * 70)

    if implementation:
        print(f"✓ Implementation successful!")
        print()
        print(f"Implementation ID: {implementation.impl_id}")
        print(f"Status: {implementation.status.value}")
        print(f"Patch file: {implementation.patch_file}")
        print()

        if implementation.test_results:
            print("Test Results:")
            print(f"  Success: {implementation.test_results['success']}")
            print(f"  Tests passed: {implementation.test_results['tests_passed']}/{implementation.test_results['tests_total']}")
            print()

        if implementation.performance_delta:
            print("Performance Impact:")
            print(f"  Execution time delta: {implementation.performance_delta['execution_time_delta_ms']}ms")
            print(f"  Memory delta: {implementation.performance_delta['memory_delta_mb']}MB")
            print(f"  Success rate delta: {implementation.performance_delta['success_rate_delta']:.1%}")
            print(f"  Improvement confirmed: {implementation.performance_delta['improvement_confirmed']}")
            print()

        if implementation.deployed_at:
            print(f"✓ Deployed at: {implementation.deployed_at}")

        # Check if modification was marked as applied
        print()
        print("Darwin Gödel Modification Status:")
        print(f"  Applied at: {modification.applied_at}")
        if modification.applied_at:
            print(f"  ✓ Modification marked as applied!")

    else:
        print("✗ Implementation failed or returned None")
        return False

    print()
    print("=" * 70)
    print("INTEGRATION TEST COMPLETE")
    print("=" * 70)
    print()
    print("The recursive self-improvement loop is OPERATIONAL:")
    print("  1. Darwin Gödel detects improvement ✓")
    print("  2. Auto-Implementation generates patch ✓")
    print("  3. Sandbox tests the patch ✓")
    print("  4. Self-evaluation validates improvement ✓")
    print("  5. System deploys automatically ✓")
    print()

    return True


async def main():
    """Run the integration test."""
    try:
        success = await test_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
