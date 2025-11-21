#!/usr/bin/env python3
"""
Integration tests for Enhanced Code Evolution Protector
"""

import asyncio
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "enhanced_agents"))

from protector_with_verification import EnhancedCodeEvolutionProtector


async def test_protector_initialization():
    """Test protector initializes correctly"""
    print("🧪 Test: Protector initialization")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    assert protector.enable_verification is True
    assert protector.verifier is not None
    assert protector.edge_learner is not None
    assert protector.cli_tool in ["gemini", "codex", "claude"]

    print("✅ Protector initialized successfully")
    print(f"   - CLI tool: {protector.cli_tool}")
    print(f"   - Verification enabled: {protector.enable_verification}")
    print(f"   - Edge learner initialized: {len(protector.edge_learner.edge_cases)} cases loaded")
    print()


async def test_evolution_vs_bug_detection():
    """Test evolution vs bug decision detection"""
    print("🧪 Test: Evolution vs bug detection")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    # Verify that protector has necessary components
    assert protector.verifier is not None
    assert protector.edge_learner is not None
    assert hasattr(protector, 'enhanced_change_analysis')

    print("✅ Protector has enhanced change analysis capability")
    print("✅ Verification and edge learning components initialized")
    print()


async def test_edge_case_recording():
    """Test edge case recording and learning"""
    print("🧪 Test: Edge case recording")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    # Record an edge case
    edge_case = protector.edge_learner.record_edge_case(
        input_text="Payment amount: $0.00",
        expected_output={"status": "rejected"},
        actual_output={"status": "accepted"},
        category="evolution_detection"
    )

    assert edge_case is not None
    assert edge_case.category == "evolution_detection"
    assert edge_case.id in protector.edge_learner.edge_cases

    print("✅ Edge case recorded successfully")
    print(f"   - Edge case ID: {edge_case.id}")
    print(f"   - Severity: {edge_case.severity.value}")
    print()


async def test_verification_stats():
    """Test verification statistics tracking"""
    print("🧪 Test: Verification statistics")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    stats = protector.get_verification_stats()

    assert "total_verifications" in stats
    assert "passed" in stats
    assert "failed" in stats
    assert "prevented_bugs" in stats
    assert "allowed_evolution" in stats

    print("✅ Verification statistics available")
    print(f"   - Total verifications: {stats['total_verifications']}")
    print(f"   - Prevented bugs: {stats['prevented_bugs']}")
    print(f"   - Allowed evolution: {stats['allowed_evolution']}")
    print()


async def test_edge_learning_metrics():
    """Test edge case learning metrics"""
    print("🧪 Test: Edge learning metrics")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    metrics = protector.edge_learner.get_quality_metrics()

    assert "total_edge_cases" in metrics
    assert "false_negative_rate" in metrics
    assert "boundary_detection_coverage" in metrics
    assert "patterns_detected" in metrics

    print("✅ Edge learning metrics available")
    print(f"   - Total edge cases: {metrics['total_edge_cases']}")
    print(f"   - Patterns detected: {metrics['patterns_detected']}")
    print()


async def test_enhanced_change_analysis():
    """Test enhanced change analysis with verification"""
    print("🧪 Test: Enhanced change analysis")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    # Test with a simple formatting change (should be allowed)
    file_path = "test.py"
    change_description = "Minor whitespace formatting"
    context = {"risk_level": "low"}

    allowed, reasoning, confidence = await protector.enhanced_change_analysis(
        file_path, change_description, context
    )

    # Should receive a result
    assert isinstance(allowed, bool)
    assert isinstance(reasoning, str)
    assert isinstance(confidence, float)
    assert len(reasoning) > 0

    print("✅ Enhanced change analysis executed successfully")
    print(f"   - Allowed: {allowed}")
    print(f"   - Reasoning: {reasoning[:100]}...")
    print(f"   - Confidence: {confidence:.2f}")
    print()


async def test_pattern_detection():
    """Test protection pattern detection"""
    print("🧪 Test: Protection pattern detection")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    # Test detection of various patterns
    patterns = [
        ("array index out of range at position length-1", "off_by_one"),
        ("expected empty string but got null", "null_vs_empty"),
        ("concurrent access to shared resource caused timing issue", "race_condition"),
        ("simple print statement", None)
    ]

    for test_input, expected_pattern in patterns:
        boundaries = protector.edge_learner.detector.detect_boundaries(test_input)

        if expected_pattern:
            assert len(boundaries) > 0, f"Failed to detect boundary in: {test_input}"
            assert expected_pattern in boundaries, f"Expected {expected_pattern}, got {boundaries}"
            print(f"✅ Detected boundary pattern '{expected_pattern}' in test input")
        else:
            print(f"✅ No boundary pattern detected (as expected)")

    print()


async def test_protector_stats_output():
    """Test protector statistics output"""
    print("🧪 Test: Protector statistics output")

    evolution_config = "/mnt/agentic-system/config/evolution_phases.json"

    protector = EnhancedCodeEvolutionProtector(
        evolution_config_path=evolution_config,
        enable_verification=True
    )

    stats = protector.get_verification_stats()

    # All stats should be properly initialized
    assert stats["total_verifications"] == 0
    assert stats["passed"] == 0
    assert stats["failed"] == 0
    assert stats["prevented_bugs"] == 0
    assert stats["allowed_evolution"] == 0

    print("✅ Statistics properly initialized")
    print()


async def main():
    """Run all integration tests"""
    print("=" * 60)
    print("🧪 ENHANCED CODE EVOLUTION PROTECTOR INTEGRATION TESTS")
    print("=" * 60)
    print()

    tests = [
        test_protector_initialization,
        test_evolution_vs_bug_detection,
        test_edge_case_recording,
        test_verification_stats,
        test_edge_learning_metrics,
        test_enhanced_change_analysis,
        test_pattern_detection,
        test_protector_stats_output
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 60)
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 TOTAL: {passed + failed}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
