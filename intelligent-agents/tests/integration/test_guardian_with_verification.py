#!/usr/bin/env python3
"""
Integration tests for Enhanced System Health Guardian
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "enhanced_agents"))

from guardian_with_verification import EnhancedSystemHealthGuardian


async def test_guardian_initialization():
    """Test guardian initializes correctly"""
    print("🧪 Test: Guardian initialization")

    guardian = EnhancedSystemHealthGuardian(
        arduino_port="/dev/tty.usbmodem8344401",
        enable_verification=True
    )

    assert guardian.enable_verification is True
    assert guardian.verifier is not None
    assert guardian.cli_tool in ["gemini", "codex", "claude"]

    print("✅ Guardian initialized successfully")
    print(f"   - CLI tool: {guardian.cli_tool}")
    print(f"   - Verification enabled: {guardian.enable_verification}")
    print()


async def test_critical_decision_detection():
    """Test critical decision detection"""
    print("🧪 Test: Critical decision detection")

    guardian = EnhancedSystemHealthGuardian(
        arduino_port="/dev/tty.usbmodem8344401",
        enable_verification=True
    )

    # Create mock decision
    class MockDecision:
        def __init__(self, decision_text, confidence):
            self.decision = decision_text
            self.confidence = confidence
            self.tool_used = "gemini"
            self.reasoning = "Test reasoning"

    # Test restart decision (should be critical)
    restart_decision = MockDecision("Restart temporal service", 0.85)
    observations = {"cpu_percent": 95, "memory_percent": 92}

    is_critical = guardian._is_critical_decision(restart_decision, observations)
    assert is_critical is True
    print("✅ Restart decision correctly identified as critical")

    # Test non-critical decision
    status_decision = MockDecision("Check system status", 0.9)
    is_critical = guardian._is_critical_decision(status_decision, {})
    assert is_critical is False
    print("✅ Status check correctly identified as non-critical")
    print()


async def test_verification_stats():
    """Test verification statistics tracking"""
    print("🧪 Test: Verification statistics")

    guardian = EnhancedSystemHealthGuardian(
        arduino_port="/dev/tty.usbmodem8344401",
        enable_verification=True
    )

    stats = guardian.get_verification_stats()

    assert "total_verifications" in stats
    assert "passed" in stats
    assert "failed" in stats
    assert "prevented_errors" in stats
    assert "pass_rate" in stats

    print("✅ Verification statistics available")
    print(f"   - Total verifications: {stats['total_verifications']}")
    print(f"   - Pass rate: {stats['pass_rate']:.2%}")
    print()


async def test_enhanced_decision_making():
    """Test enhanced decision making with verification"""
    print("🧪 Test: Enhanced decision making")

    guardian = EnhancedSystemHealthGuardian(
        arduino_port="/dev/tty.usbmodem8344401",
        enable_verification=True
    )

    class MockDecision:
        def __init__(self):
            self.decision = "Perform routine health check"
            self.confidence = 0.95
            self.tool_used = "gemini"
            self.reasoning = "Regular monitoring task"

    decision = MockDecision()
    observations = {"system_stress": False}

    should_execute, reasoning = await guardian.enhanced_decision_making(
        decision, observations
    )

    # Non-critical decision should be approved without verification
    assert should_execute is True
    assert "non-critical" in reasoning.lower() or "approved" in reasoning.lower()

    print("✅ Non-critical decision approved without verification")
    print(f"   - Reasoning: {reasoning}")
    print()


async def test_guardian_stats_output():
    """Test guardian stats output"""
    print("🧪 Test: Guardian statistics output")

    guardian = EnhancedSystemHealthGuardian(
        arduino_port="/dev/tty.usbmodem8344401",
        enable_verification=True
    )

    stats = guardian.get_verification_stats()

    # All stats should be properly initialized
    assert stats["total_verifications"] == 0
    assert stats["passed"] == 0
    assert stats["failed"] == 0
    assert stats["pass_rate"] == 0.0

    print("✅ Statistics properly initialized")
    print()


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("🧪 ENHANCED SYSTEM HEALTH GUARDIAN INTEGRATION TESTS")
    print("=" * 60)
    print()

    tests = [
        test_guardian_initialization,
        test_critical_decision_detection,
        test_verification_stats,
        test_enhanced_decision_making,
        test_guardian_stats_output
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed += 1

    print("=" * 60)
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 TOTAL: {passed + failed}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
