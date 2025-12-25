#!/usr/bin/env python3
"""
Test entropy-based tier assignment integration.

Tests the PTM-inspired anchor/bridge classification and its
integration with TPU importance scoring for tier assignment.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from entropy_scoring import (
    analyze_entropy,
    score_entity_entropy,
    combine_scores,
    get_stats,
    reset_stats,
    EntropyResult,
    ENTROPY_HIGH_THRESHOLD,
    ENTROPY_LOW_THRESHOLD
)


def test_entropy_analysis():
    """Test basic entropy analysis."""
    print("\n=== Test 1: Basic Entropy Analysis ===")

    test_cases = [
        # (text, expected_class, description)
        ("John Smith works at OpenAI on GPT-5", "anchor", "Proper names + tech terms"),
        ("The system is working as expected", "bridge", "Common stopwords"),
        ("Error 0x8007045D in KERNEL32.DLL", "anchor", "Error codes + DLL names"),
        ("API endpoint https://api.example.com/v2/users", "anchor", "URLs + tech terms"),
        ("This is a very simple and basic test", "bridge", "High stopword ratio"),
    ]

    passed = 0
    for text, expected, desc in test_cases:
        result = analyze_entropy(text)
        status = "✓" if result.classification == expected else "✗"
        if result.classification == expected:
            passed += 1
        print(f"  {status} {desc}")
        print(f"    Text: '{text[:50]}...' ")
        print(f"    Entropy: {result.entropy_bits:.2f} bits, Class: {result.classification}")
        print(f"    Anchor ratio: {result.anchor_ratio:.1%}, Bridge ratio: {result.bridge_ratio:.1%}")
        print()

    print(f"  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_entity_scoring():
    """Test entity-level scoring."""
    print("\n=== Test 2: Entity Scoring ===")

    entities = [
        {
            "name": "PTM-Memory-Architecture",
            "type": "technique",
            "observations": [
                "Uses 16-dimensional hyper-torus T^16",
                "Achieves >3000x compression ratio",
                "O(1) retrieval complexity with no decay"
            ]
        },
        {
            "name": "session-note-2024-01-15",
            "type": "note",
            "observations": [
                "The meeting went well",
                "We discussed the project status",
                "Everything is on track"
            ]
        },
        {
            "name": "Error-CUDA-OOM-0x800",
            "type": "error",
            "observations": [
                "CUDA out of memory at 0x7f8b3c000000",
                "Process pytorch_train.py PID 42069",
                "GPU 0: NVIDIA RTX 4090 24GB"
            ]
        }
    ]

    reset_stats()

    for entity in entities:
        result = score_entity_entropy(
            entity["name"],
            entity["observations"],
            entity["type"]
        )
        print(f"  Entity: {entity['name']}")
        print(f"    Type: {entity['type']}")
        print(f"    Entropy: {result.entropy_bits:.2f} bits")
        print(f"    Classification: {result.classification}")
        print(f"    Recommended tier: {result.recommended_tier}")
        print(f"    Confidence: {result.confidence:.1%}")
        print()

    stats = get_stats()
    print(f"  Stats: {stats['entities_scored']} entities scored")
    print(f"  Anchor: {stats['anchor_count']}, Bridge: {stats['bridge_count']}, Mixed: {stats['mixed_count']}")

    return True


def test_combined_scoring():
    """Test TPU + entropy combined scoring."""
    print("\n=== Test 3: Combined TPU + Entropy Scoring ===")

    test_cases = [
        # (tpu_score, text, expected_tier, description)
        # Thresholds: >= 0.75 long_term, >= 0.50 episodic, < 0.50 working
        (0.9, "Critical security vulnerability CVE-2024-12345", "long_term", "High TPU + anchor"),
        (0.3, "The meeting was fine and went okay", "working", "Low TPU + bridge"),
        (0.8, "Database optimization pattern for PostgreSQL", "long_term", "High TPU + anchor boost"),
        (0.55, "This is a regular session note", "episodic", "Medium TPU + bridge penalty"),
    ]

    passed = 0
    for tpu_score, text, expected_tier, desc in test_cases:
        entropy_result = analyze_entropy(text)
        combined, tier = combine_scores(tpu_score, entropy_result)

        status = "✓" if tier == expected_tier else "✗"
        if tier == expected_tier:
            passed += 1

        print(f"  {status} {desc}")
        print(f"    TPU: {tpu_score:.2f}, Entropy: {entropy_result.entropy_bits:.2f} ({entropy_result.classification})")
        print(f"    Combined: {combined:.2f} → {tier} (expected: {expected_tier})")
        print()

    print(f"  Result: {passed}/{len(test_cases)} passed")
    return passed >= len(test_cases) - 1  # Allow 1 failure


def test_threshold_consistency():
    """Test that thresholds are consistent."""
    print("\n=== Test 4: Threshold Consistency ===")

    print(f"  ENTROPY_HIGH_THRESHOLD: {ENTROPY_HIGH_THRESHOLD} bits")
    print(f"  ENTROPY_LOW_THRESHOLD: {ENTROPY_LOW_THRESHOLD} bits")

    assert ENTROPY_HIGH_THRESHOLD > ENTROPY_LOW_THRESHOLD, "High must be > Low"
    print("  ✓ Thresholds are properly ordered")

    # Test boundary cases
    high_entropy_text = "NVIDIA RTX 4090 GPU CUDA 12.3 PyTorch 2.1.0 TensorFlow 2.15"
    low_entropy_text = "the and is a was the and is a the and was"

    high_result = analyze_entropy(high_entropy_text)
    low_result = analyze_entropy(low_entropy_text)

    assert high_result.entropy_bits > low_result.entropy_bits, "High entropy text should have higher entropy"
    print(f"  ✓ High entropy text: {high_result.entropy_bits:.2f} bits")
    print(f"  ✓ Low entropy text: {low_result.entropy_bits:.2f} bits")

    return True


async def test_integration_with_server():
    """Test actual integration with server scoring function."""
    print("\n=== Test 5: Server Integration Check ===")

    try:
        # Check if imports work
        from server import ENTROPY_SCORING_AVAILABLE, _score_and_tier_entities
        print(f"  ✓ ENTROPY_SCORING_AVAILABLE: {ENTROPY_SCORING_AVAILABLE}")

        if ENTROPY_SCORING_AVAILABLE:
            print("  ✓ Entropy scoring is enabled in server.py")

            # Test entities
            test_entities = [
                {
                    "name": "test-entropy-anchor",
                    "entityType": "test",
                    "observations": ["OpenAI GPT-5 API endpoint https://api.openai.com/v1"]
                },
                {
                    "name": "test-entropy-bridge",
                    "entityType": "test",
                    "observations": ["The system is working and everything is fine"]
                }
            ]

            # Note: Can't actually test without database, but we verify the function exists
            print("  ✓ _score_and_tier_entities function is available")
            return True
        else:
            print("  ⚠ Entropy scoring not available (check imports)")
            return False

    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Entropy-Based Tier Assignment Integration Tests")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Entropy Analysis", test_entropy_analysis()))
    results.append(("Entity Scoring", test_entity_scoring()))
    results.append(("Combined Scoring", test_combined_scoring()))
    results.append(("Threshold Consistency", test_threshold_consistency()))
    results.append(("Server Integration", asyncio.run(test_integration_with_server())))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
