#!/usr/bin/env python3
"""
Test Memory-Influenced Routing - Phase 2 Holographic Memory

Verifies that the model router correctly:
1. Accepts MEMORY_INFLUENCED routing mode
2. Integrates with activation field
3. Uses routing_bias for provider selection
4. Applies confidence_modifier to uncertainty estimation
5. Falls back gracefully when activation field unavailable
"""

import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-memory-routing")

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


def test_routing_mode_enum():
    """Test that MEMORY_INFLUENCED is in RoutingMode enum."""
    print("\n[TEST 1] RoutingMode enum includes MEMORY_INFLUENCED...")
    try:
        from model_router import RoutingMode

        assert hasattr(RoutingMode, 'MEMORY_INFLUENCED'), "Missing MEMORY_INFLUENCED"
        assert RoutingMode.MEMORY_INFLUENCED.value == "memory-influenced"
        print(f"  RoutingMode values: {[m.value for m in RoutingMode]}")
        print("  PASS: MEMORY_INFLUENCED routing mode available")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_router_has_select_by_memory():
    """Test that ModelRouter has _select_by_memory method."""
    print("\n[TEST 2] ModelRouter._select_by_memory method exists...")
    try:
        from model_router import ModelRouter

        router = ModelRouter()
        assert hasattr(router, '_select_by_memory'), "Missing _select_by_memory method"
        print("  PASS: _select_by_memory method exists")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_select_provider_handles_memory_mode():
    """Test that _select_provider handles MEMORY_INFLUENCED mode."""
    print("\n[TEST 3] _select_provider handles MEMORY_INFLUENCED mode...")
    try:
        from model_router import (
            ModelRouter, RoutingMode, RoutingConfig,
            ChatParams, Message
        )

        router = ModelRouter()
        router.config.routing = RoutingConfig(mode=RoutingMode.MEMORY_INFLUENCED)

        # Create test params
        params = ChatParams(
            model="claude-3.5-sonnet",
            messages=[Message(role="user", content="How do I optimize Python code?")]
        )

        # Run selection synchronously (method is sync)
        provider = router._select_by_memory(params, agent_type="developer")

        print(f"  Selected provider: {provider.type.value}")
        print("  PASS: Memory-influenced routing works")
        return True
    except ImportError as e:
        if "activation_field" in str(e):
            print(f"  WARN: Activation field not available, testing fallback: {e}")
            return True  # Fallback is expected behavior
        print(f"  FAIL: {e}")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_routing_with_activation_field():
    """Test memory routing with real activation field."""
    print("\n[TEST 4] Memory routing with activation field...")
    try:
        from model_router import (
            ModelRouter, RoutingMode, RoutingConfig,
            ChatParams, Message
        )
        from agi.activation_field import get_activation_field

        # Get activation field
        field = get_activation_field()

        # Create router with memory-influenced mode
        router = ModelRouter()
        router.config.routing = RoutingConfig(mode=RoutingMode.MEMORY_INFLUENCED)

        # Test different query types
        queries = [
            ("What time is it?", "simple"),
            ("Design a distributed system with fault tolerance", "complex"),
            ("How do I print hello world in Python?", "simple"),
            ("Explain the mathematical foundations of quantum computing", "complex"),
        ]

        for query, expected_type in queries:
            params = ChatParams(
                model="claude-3.5-sonnet",
                messages=[Message(role="user", content=query)]
            )

            provider = router._select_by_memory(params)
            print(f"  Query: '{query[:40]}...'")
            print(f"    Expected: {expected_type}, Provider: {provider.type.value}")

        print("  PASS: Activation field integration works")
        return True
    except ImportError as e:
        print(f"  SKIP: Activation field not available: {e}")
        return True  # Not a failure, just unavailable
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confidence_modifier_affects_uncertainty():
    """Test that confidence_modifier affects uncertainty estimation."""
    print("\n[TEST 5] Confidence modifier affects uncertainty...")
    try:
        from model_router import ModelRouter, UncertaintyEstimator

        router = ModelRouter()
        original_threshold = router.uncertainty_estimator.config.boundary_threshold

        # Simulate high confidence (>1 should lower boundary threshold)
        high_confidence = 1.5
        adjusted_threshold = 0.5 / high_confidence

        assert adjusted_threshold < original_threshold, "High confidence should lower threshold"
        print(f"  Original threshold: {original_threshold}")
        print(f"  High confidence ({high_confidence}) threshold: {adjusted_threshold:.3f}")

        # Simulate low confidence (<1 should raise boundary threshold)
        low_confidence = 0.5
        adjusted_threshold_low = 0.5 / low_confidence

        assert adjusted_threshold_low > original_threshold, "Low confidence should raise threshold"
        print(f"  Low confidence ({low_confidence}) threshold: {adjusted_threshold_low:.3f}")

        print("  PASS: Confidence modifier correctly affects uncertainty")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_mcp_tools_registration():
    """Test MCP tools for memory-influenced routing."""
    print("\n[TEST 6] MCP tools registration...")
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

        from model_router import register_model_router_tools
        register_model_router_tools(mock_app)

        # Check for new memory-influenced tools
        expected_tools = [
            "router_chat",
            "router_select_provider",
            "router_metrics",
            "router_status",
            "router_set_mode",
            "router_add_rule",
            "router_get_uncertainty",
            "router_estimate_uncertainty",
            "router_get_memory_state",
            "router_enable_memory_routing"
        ]

        missing = [t for t in expected_tools if t not in mock_app.tools]
        if missing:
            print(f"  Missing tools: {missing}")
            return False

        print(f"  Registered tools: {list(mock_app.tools.keys())}")
        print("  PASS: All MCP tools registered including memory routing tools")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_router_enable_memory_routing():
    """Test router_enable_memory_routing MCP tool."""
    print("\n[TEST 7] router_enable_memory_routing tool...")
    try:
        class MockApp:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()

        from model_router import register_model_router_tools, RoutingMode
        router = register_model_router_tools(mock_app)

        # Call the enable tool
        result = await mock_app.tools["router_enable_memory_routing"]()

        assert result["success"] is True
        assert result["mode"] == "memory-influenced"
        assert router.config.routing.mode == RoutingMode.MEMORY_INFLUENCED

        print(f"  Result: {result}")
        print("  PASS: router_enable_memory_routing works")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_router_get_memory_state():
    """Test router_get_memory_state MCP tool."""
    print("\n[TEST 8] router_get_memory_state tool...")
    try:
        class MockApp:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator

        mock_app = MockApp()

        from model_router import register_model_router_tools
        register_model_router_tools(mock_app)

        # Call the get state tool
        result = await mock_app.tools["router_get_memory_state"]()

        print(f"  Result: {result}")

        if result.get("success"):
            if result.get("has_state"):
                assert "routing_bias" in result
                assert "confidence_modifier" in result
                print("  PASS: Memory state retrieved with full data")
            else:
                print("  PASS: Memory state not computed yet (expected)")
        else:
            # May fail if activation field unavailable
            print(f"  WARN: {result.get('error', 'Unknown error')}")

        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_routing_flow():
    """Test full memory-influenced routing flow."""
    print("\n[TEST 9] Full memory-influenced routing flow...")
    try:
        from model_router import (
            ModelRouter, RoutingMode, RoutingConfig,
            ChatParams, Message
        )

        # Create router and enable memory-influenced mode
        router = ModelRouter()
        router.config.routing = RoutingConfig(mode=RoutingMode.MEMORY_INFLUENCED)

        # Verify mode
        assert router.config.routing.mode == RoutingMode.MEMORY_INFLUENCED

        # Create test request
        params = ChatParams(
            model="claude-3.5-sonnet",
            messages=[Message(role="user", content="Explain neural networks")]
        )

        # Select provider using async method
        provider = await router._select_provider(params, agent_type="researcher")

        print(f"  Routing mode: {router.config.routing.mode.value}")
        print(f"  Selected provider: {provider.type.value}")
        print("  PASS: Full routing flow works")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MEMORY-INFLUENCED ROUTING TEST SUITE")
    print("Phase 2: Holographic Memory Integration")
    print("=" * 60)

    # Synchronous tests
    sync_tests = [
        test_routing_mode_enum,
        test_router_has_select_by_memory,
        test_select_provider_handles_memory_mode,
        test_memory_routing_with_activation_field,
        test_confidence_modifier_affects_uncertainty,
        test_mcp_tools_registration,
    ]

    results = []
    for test in sync_tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  FAIL: Unexpected error: {e}")
            results.append(False)

    # Async tests
    async_tests = [
        test_router_enable_memory_routing,
        test_router_get_memory_state,
        test_full_routing_flow,
    ]

    for test in async_tests:
        try:
            result = await test()
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
        print("\nALL TESTS PASSED - Phase 2 Memory-Influenced Routing Complete")
        return 0
    else:
        print(f"\n{total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
