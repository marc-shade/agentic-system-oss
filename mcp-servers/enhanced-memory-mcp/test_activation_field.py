#!/usr/bin/env python3
"""
Test Activation Field - Holographic Memory Implementation

Verifies that the activation field correctly:
1. Computes from query context
2. Spreads activation through associative network
3. Extracts primed concepts
4. Computes emotional context
5. Generates routing bias
6. Calculates confidence modifier
"""

import sys
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-activation-field")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def test_activation_field_import():
    """Test that activation field module imports correctly."""
    print("\n[TEST 1] Import activation field module...")
    try:
        from agi.activation_field import (
            ActivationField,
            ActivationState,
            get_activation_field,
            compute_activation_for_query,
            get_current_routing_bias,
            get_current_confidence_modifier
        )
        print("  PASS: All imports successful")
        return True
    except Exception as e:
        print(f"  FAIL: Import error: {e}")
        return False


def test_singleton_pattern():
    """Test that ActivationField uses singleton pattern."""
    print("\n[TEST 2] Singleton pattern...")
    try:
        from agi.activation_field import ActivationField, get_activation_field

        field1 = get_activation_field()
        field2 = get_activation_field()
        field3 = ActivationField()

        if field1 is field2 is field3:
            print("  PASS: Singleton pattern works correctly")
            return True
        else:
            print("  FAIL: Different instances created")
            return False
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        return False


def test_compute_activation_field():
    """Test computing activation field from query."""
    print("\n[TEST 3] Compute activation field...")
    try:
        from agi.activation_field import get_activation_field

        field = get_activation_field()

        # Compute with a sample query
        start = time.time()
        state = field.compute_from_context(
            query="How do I optimize memory performance in Python?",
            session_context={"task_type": "code_optimization"}
        )
        elapsed = (time.time() - start) * 1000

        print(f"  Computation time: {elapsed:.1f}ms")
        print(f"  Activated entities: {len(state.active_entity_ids)}")
        print(f"  Primed concepts: {state.primed_concepts}")
        print(f"  Confidence modifier: {state.confidence_modifier:.2f}")
        print(f"  Emotional context: {state.emotional_context}")
        print(f"  Routing bias: {state.routing_bias}")

        # Validate state structure
        assert hasattr(state, 'routing_bias'), "Missing routing_bias"
        assert hasattr(state, 'confidence_modifier'), "Missing confidence_modifier"
        assert hasattr(state, 'emotional_context'), "Missing emotional_context"
        assert hasattr(state, 'primed_concepts'), "Missing primed_concepts"
        assert isinstance(state.confidence_modifier, float), "confidence_modifier should be float"

        print("  PASS: Activation field computed successfully")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routing_recommendation():
    """Test routing recommendation based on activation."""
    print("\n[TEST 4] Routing recommendation...")
    try:
        from agi.activation_field import get_activation_field

        field = get_activation_field()

        # Compute for different contexts
        simple_state = field.compute_from_context(
            query="What time is it?",
            session_context={"task_type": "quick_question"},
            force_recompute=True
        )

        recommendation = field.get_routing_recommendation()
        print(f"  Simple query routing: {recommendation}")

        complex_state = field.compute_from_context(
            query="Design a distributed system architecture with fault tolerance and consistency guarantees",
            session_context={"task_type": "architecture"},
            force_recompute=True
        )

        recommendation = field.get_routing_recommendation()
        print(f"  Complex query routing: {recommendation}")

        # Recommendation should be one of the valid tiers
        valid_tiers = {"simple", "balanced", "complex", "local"}
        assert recommendation in valid_tiers, f"Invalid recommendation: {recommendation}"

        print("  PASS: Routing recommendation works")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_persistence():
    """Test that state persists across accesses."""
    print("\n[TEST 5] State persistence...")
    try:
        from agi.activation_field import get_activation_field

        field = get_activation_field()

        # Compute once
        state1 = field.compute_from_context("Test persistence query")

        # Get state again (should be cached)
        state2 = field.current_state

        if state1 is state2:
            print("  PASS: State persists correctly")
            return True
        else:
            print("  FAIL: State not persisting")
            return False
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        return False


def test_state_serialization():
    """Test that state can be serialized to dict and back."""
    print("\n[TEST 6] State serialization...")
    try:
        from agi.activation_field import ActivationState

        # Create a state
        original = ActivationState(
            routing_bias={"simple": 0.1, "complex": 0.3},
            confidence_modifier=1.2,
            primed_concepts={"python", "optimization"},
            emotional_context={"valence": 0.5, "arousal": 0.3, "dominance": 0.6}
        )

        # Serialize
        data = original.to_dict()
        print(f"  Serialized: {data}")

        # Deserialize
        restored = ActivationState.from_dict(data)

        # Verify
        assert restored.routing_bias == original.routing_bias
        assert restored.confidence_modifier == original.confidence_modifier
        assert restored.primed_concepts == original.primed_concepts

        print("  PASS: Serialization works correctly")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clear_field():
    """Test clearing the activation field."""
    print("\n[TEST 7] Clear activation field...")
    try:
        from agi.activation_field import get_activation_field

        field = get_activation_field()

        # Compute something
        field.compute_from_context("Test clear query")
        assert field.current_state is not None, "State should exist"

        # Clear
        field.clear()
        assert field.current_state is None, "State should be None after clear"

        print("  PASS: Clear works correctly")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        return False


def test_convenience_functions():
    """Test convenience functions for hook integration."""
    print("\n[TEST 8] Convenience functions...")
    try:
        from agi.activation_field import (
            compute_activation_for_query,
            get_current_routing_bias,
            get_current_confidence_modifier
        )

        # Test compute function
        result = compute_activation_for_query("Test convenience function")
        assert isinstance(result, dict), "Should return dict"
        assert "routing_bias" in result, "Should have routing_bias"
        print(f"  compute_activation_for_query: OK (keys: {list(result.keys())})")

        # Test routing bias
        bias = get_current_routing_bias()
        assert isinstance(bias, dict), "Should return dict"
        print(f"  get_current_routing_bias: OK ({bias})")

        # Test confidence modifier
        modifier = get_current_confidence_modifier()
        assert isinstance(modifier, float), "Should return float"
        print(f"  get_current_confidence_modifier: OK ({modifier})")

        print("  PASS: All convenience functions work")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_tools_registration():
    """Test MCP tool registration."""
    print("\n[TEST 9] MCP tools registration...")
    try:
        # Create mock app
        class MockApp:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()

        from activation_field_tools import register_activation_field_tools
        register_activation_field_tools(mock_app)

        expected_tools = [
            "compute_activation_field",
            "get_activation_state",
            "get_routing_bias",
            "get_primed_concepts",
            "get_emotional_context",
            "clear_activation_field",
            "get_activation_field_stats"
        ]

        missing = [t for t in expected_tools if t not in mock_app.tools]
        if missing:
            print(f"  FAIL: Missing tools: {missing}")
            return False

        print(f"  Registered tools: {list(mock_app.tools.keys())}")
        print("  PASS: All MCP tools registered")
        return True
    except Exception as e:
        print(f"  FAIL: Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("ACTIVATION FIELD TEST SUITE")
    print("Holographic Memory Implementation - Phase 1")
    print("=" * 60)

    tests = [
        test_activation_field_import,
        test_singleton_pattern,
        test_compute_activation_field,
        test_routing_recommendation,
        test_state_persistence,
        test_state_serialization,
        test_clear_field,
        test_convenience_functions,
        test_mcp_tools_registration,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  FAIL: Unexpected error: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("\nALL TESTS PASSED - Phase 1 Implementation Complete")
        return 0
    else:
        print(f"\n{total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
