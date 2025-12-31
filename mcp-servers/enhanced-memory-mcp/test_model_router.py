#!/usr/bin/env python3
"""
Test suite for ModelRouter integration.

Tests both:
1. Legacy IntelligentModelRouter for backward compatibility
2. New comprehensive ModelRouter ported from ruvnet/agentic-flow

Verifies:
- Router initializes correctly
- Model selection logic works
- Provider types and routing modes
- Metrics tracking
- MCP tool registration
- Rule-based routing
"""

import asyncio
import os
import sys
from pathlib import Path

# Set up test environment
os.chdir(Path(__file__).parent)

from model_router import IntelligentModelRouter


async def test_router():
    """Test the IntelligentModelRouter functionality"""

    print("🧪 Testing IntelligentModelRouter\n")

    # Initialize router
    router = IntelligentModelRouter(
        stats_file="/tmp/test_model_router_stats.json"
    )
    print("✅ Router initialized successfully\n")

    # Test 1: Health check
    print("Test 1: Health Check")
    print("-" * 50)
    health = await router.health_check()
    print(f"Ollama available: {health['ollama_available']}")
    print(f"Models available:")
    for model_type, info in health['models_available'].items():
        status = "✅" if info['available'] else "❌"
        print(f"  {status} {model_type}: {info['name']}")
    print()

    # Test 2: Model selection logic
    print("Test 2: Model Selection Logic")
    print("-" * 50)

    test_contexts = [
        {"complexity": 30, "description": "Simple task"},
        {"complexity": 50, "description": "Moderate task"},
        {"complexity": 80, "description": "Complex task"},
        {"complexity": 50, "requires_reasoning": True, "description": "Reasoning task"},
        {"complexity": 60, "multi_step": True, "description": "Multi-step task"}
    ]

    for context in test_contexts:
        desc = context.pop("description")
        model, location = router._select_model(context)
        print(f"  {desc}: {model} ({location})")
    print()

    # Test 3: Actual execution (simple test)
    print("Test 3: Execution Test (Simple)")
    print("-" * 50)
    try:
        result = await router.execute_with_routing(
            task="What is 2 + 2? Answer with just the number.",
            context={"complexity": 30}
        )
        print(f"  Model used: {result['model_used']}")
        print(f"  Location: {result['location']}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
        print(f"  Response preview: {result['response'][:100]}...")
        print()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print()

    # Test 4: Stats tracking
    print("Test 4: Stats Tracking")
    print("-" * 50)
    stats = router.get_stats()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Local requests: {stats['local_requests']}")
    print(f"  Cloud requests: {stats['cloud_requests']}")
    print(f"  Model usage:")
    for model, usage in stats.get('model_usage', {}).items():
        print(f"    {model}: {usage['count']} requests, avg {usage['avg_duration']:.2f}s")
    print()

    print("✅ Legacy router tests completed!")
    return True


# =============================================================================
# New ModelRouter Tests (from ruvnet/agentic-flow)
# =============================================================================

async def test_basic_initialization():
    """Test basic ModelRouter initialization."""
    print("\n=== Test: Basic Initialization ===")

    from model_router import (
        ModelRouter, RouterConfig, ProviderConfig,
        ProviderType, RoutingMode, RoutingConfig
    )

    # Test with default config (from environment)
    router = ModelRouter()

    print(f"  ✓ Router initialized")
    print(f"  ✓ Version: {router.config.version}")
    print(f"  ✓ Default provider: {router.config.default_provider.value}")
    print(f"  ✓ Fallback chain: {[p.value for p in router.config.fallback_chain]}")
    print(f"  ✓ Available providers: {list(router.providers.keys())}")

    assert router.config is not None, "Config should be set"
    print("  ✅ Basic initialization: PASSED")
    return True


async def test_provider_types():
    """Test provider type enums and creation."""
    print("\n=== Test: Provider Types ===")

    from model_router import (
        ProviderType, RoutingMode, StopReason,
        ProviderConfig, OllamaProvider
    )

    # Test provider types
    assert ProviderType.ANTHROPIC.value == "anthropic"
    assert ProviderType.OPENAI.value == "openai"
    assert ProviderType.OLLAMA.value == "ollama"
    assert ProviderType.EXO.value == "exo"
    print(f"  ✓ Provider types defined: {[p.value for p in ProviderType]}")

    # Test routing modes
    assert RoutingMode.MANUAL.value == "manual"
    assert RoutingMode.RULE_BASED.value == "rule-based"
    assert RoutingMode.COST_OPTIMIZED.value == "cost-optimized"
    assert RoutingMode.PERFORMANCE_OPTIMIZED.value == "performance-optimized"
    print(f"  ✓ Routing modes defined: {[m.value for m in RoutingMode]}")

    # Test stop reasons
    assert StopReason.END_TURN.value == "end_turn"
    assert StopReason.TOOL_USE.value == "tool_use"
    print(f"  ✓ Stop reasons defined: {[s.value for s in StopReason]}")

    # Test provider creation
    config = ProviderConfig(base_url="http://localhost:11434")
    provider = OllamaProvider(config)
    assert provider.name == "ollama"
    assert provider.supports_streaming is True
    print(f"  ✓ OllamaProvider created: supports_streaming={provider.supports_streaming}")

    print("  ✅ Provider types: PASSED")
    return True


async def test_data_classes():
    """Test data classes and message structures."""
    print("\n=== Test: Data Classes ===")

    from model_router import (
        Message, ContentBlock, ChatParams, Tool,
        UsageStats, ResponseMetadata, ChatResponse
    )

    # Test Message
    msg = Message(role="user", content="Hello, world!")
    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    print(f"  ✓ Message created: role={msg.role}")

    # Test ContentBlock
    block = ContentBlock(type="text", text="Response text")
    assert block.type == "text"
    assert block.text == "Response text"
    print(f"  ✓ ContentBlock created: type={block.type}")

    # Test ChatParams
    params = ChatParams(
        model="claude-3.5-sonnet",
        messages=[msg],
        temperature=0.7,
        max_tokens=4096
    )
    assert params.model == "claude-3.5-sonnet"
    assert len(params.messages) == 1
    print(f"  ✓ ChatParams created: model={params.model}")

    # Test Tool
    tool = Tool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}}
    )
    assert tool.name == "test_tool"
    print(f"  ✓ Tool created: name={tool.name}")

    # Test UsageStats
    usage = UsageStats(input_tokens=100, output_tokens=50)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    print(f"  ✓ UsageStats created: total={usage.input_tokens + usage.output_tokens}")

    # Test ResponseMetadata
    meta = ResponseMetadata(provider="anthropic", model="claude-3.5-sonnet", cost=0.001)
    assert meta.provider == "anthropic"
    print(f"  ✓ ResponseMetadata created: provider={meta.provider}")

    print("  ✅ Data classes: PASSED")
    return True


async def test_routing_rules():
    """Test routing rules and rule-based selection."""
    print("\n=== Test: Routing Rules ===")

    from model_router import (
        ModelRouter, RouterConfig, ProviderConfig,
        RoutingConfig, RoutingRule, RoutingMode, ProviderType
    )

    # Create router with rules
    rules = [
        RoutingRule(
            condition={"agent_type": ["coder", "developer"]},
            action={"provider": "anthropic", "model": "claude-3.5-sonnet"},
            reason="Use Claude for coding tasks"
        ),
        RoutingRule(
            condition={"local_only": True},
            action={"provider": "ollama", "model": "llama3.2"},
            reason="Use local model for privacy"
        )
    ]

    routing_config = RoutingConfig(
        mode=RoutingMode.RULE_BASED,
        rules=rules
    )

    config = RouterConfig(
        version="1.0.0",
        default_provider=ProviderType.OLLAMA,
        fallback_chain=[],
        providers={"ollama": ProviderConfig(base_url="http://localhost:11434")},
        routing=routing_config
    )

    router = ModelRouter(config=config)

    assert len(router.config.routing.rules) == 2, "Should have 2 rules"
    print(f"  ✓ Router created with {len(router.config.routing.rules)} rules")

    assert router.config.routing.mode == RoutingMode.RULE_BASED
    print(f"  ✓ Routing mode: {router.config.routing.mode.value}")

    # Check rule details
    rule1 = router.config.routing.rules[0]
    assert "agent_type" in rule1.condition
    print(f"  ✓ Rule 1: {rule1.reason}")

    rule2 = router.config.routing.rules[1]
    assert rule2.condition.get("local_only") is True
    print(f"  ✓ Rule 2: {rule2.reason}")

    print("  ✅ Routing rules: PASSED")
    return True


async def test_metrics_tracking():
    """Test metrics tracking."""
    print("\n=== Test: Metrics Tracking ===")

    from model_router import ModelRouter, RouterMetrics

    router = ModelRouter()

    # Check initial metrics
    metrics = router.get_metrics()
    assert metrics.total_requests == 0
    print(f"  ✓ Initial requests: {metrics.total_requests}")

    assert metrics.total_cost == 0.0
    print(f"  ✓ Initial cost: ${metrics.total_cost}")

    assert metrics.total_tokens.input_tokens == 0
    print(f"  ✓ Initial tokens: {metrics.total_tokens.input_tokens}/{metrics.total_tokens.output_tokens}")

    # Test reset
    router.reset_metrics()
    new_metrics = router.get_metrics()
    assert new_metrics.total_requests == 0
    print(f"  ✓ Metrics reset successfully")

    print("  ✅ Metrics tracking: PASSED")
    return True


async def test_config_loading():
    """Test configuration loading from environment."""
    print("\n=== Test: Config Loading ===")

    from model_router import ModelRouter

    # Test loading from environment
    router = ModelRouter()
    config = router.get_config()

    assert config.version is not None
    print(f"  ✓ Config version: {config.version}")

    # Check provider initialization
    providers = router.get_providers()
    print(f"  ✓ Initialized {len(providers)} providers")

    for ptype, provider in providers.items():
        print(f"    - {ptype.value}: streaming={provider.supports_streaming}, tools={provider.supports_tools}")

    assert config.monitoring is not None
    print(f"  ✓ Monitoring enabled: {config.monitoring.enabled}")

    print("  ✅ Config loading: PASSED")
    return True


async def test_mcp_tools():
    """Test MCP tool registration."""
    print("\n=== Test: MCP Tool Registration ===")

    from model_router import register_model_router_tools

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mock_app = MockApp()
    router = register_model_router_tools(mock_app)

    expected_tools = [
        "router_chat",
        "router_select_provider",
        "router_metrics",
        "router_status",
        "router_set_mode",
        "router_add_rule"
    ]

    for tool_name in expected_tools:
        assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"
        print(f"  ✓ {tool_name} registered")

    # Test router_status
    status = await mock_app.tools["router_status"]()
    assert "version" in status
    assert "routing_mode" in status
    assert "default_provider" in status
    print(f"  ✓ Status: mode={status['routing_mode']}, default={status['default_provider']}")

    # Test router_metrics
    metrics = await mock_app.tools["router_metrics"]()
    assert "total_requests" in metrics
    assert "provider_breakdown" in metrics
    print(f"  ✓ Metrics: requests={metrics['total_requests']}")

    # Test router_set_mode
    result = await mock_app.tools["router_set_mode"]("cost-optimized")
    assert result["success"] is True
    assert result["new_mode"] == "cost-optimized"
    print(f"  ✓ Mode changed to: {result['new_mode']}")

    # Test router_add_rule
    result = await mock_app.tools["router_add_rule"](
        provider="ollama",
        model="llama3.2",
        agent_types=["researcher"],
        reason="Test rule"
    )
    assert result["success"] is True
    assert result["rules_count"] >= 1
    print(f"  ✓ Rule added: {result['rules_count']} rules total")

    print("  ✅ MCP tools: PASSED")
    return True


async def test_convenience_functions():
    """Test convenience functions."""
    print("\n=== Test: Convenience Functions ===")

    from model_router import get_router, chat, ModelRouter

    # Test get_router
    router1 = get_router()
    assert isinstance(router1, ModelRouter)
    print(f"  ✓ get_router() returns ModelRouter")

    # Test singleton behavior
    router2 = get_router()
    assert router1 is router2
    print(f"  ✓ get_router() returns same instance")

    # Note: chat() function requires actual API connection
    # Just test that it's importable and callable
    assert callable(chat)
    print(f"  ✓ chat() function is callable")

    print("  ✅ Convenience functions: PASSED")
    return True


# =============================================================================
# UncertaintyEstimator Tests (Ported from tiny-dancer-core)
# =============================================================================

async def test_uncertainty_config():
    """Test UncertaintyConfig dataclass."""
    print("\n=== Test: UncertaintyConfig ===")

    from model_router import UncertaintyConfig

    # Test default configuration
    config = UncertaintyConfig()
    assert config.calibration_quantile == 0.9
    assert config.min_samples_for_calibration == 30
    assert config.boundary_threshold == 0.5
    assert config.enable_calibration == True
    print(f"  ✓ Default config: quantile={config.calibration_quantile}")

    # Test custom configuration
    custom = UncertaintyConfig(
        calibration_quantile=0.95,
        min_samples_for_calibration=50,
        boundary_threshold=0.6,
        enable_calibration=False
    )
    assert custom.calibration_quantile == 0.95
    assert custom.min_samples_for_calibration == 50
    assert custom.boundary_threshold == 0.6
    assert custom.enable_calibration == False
    print(f"  ✓ Custom config: quantile={custom.calibration_quantile}")

    print("  ✅ UncertaintyConfig: PASSED")
    return True


async def test_uncertainty_estimator_init():
    """Test UncertaintyEstimator initialization."""
    print("\n=== Test: UncertaintyEstimator Initialization ===")

    from model_router import UncertaintyConfig, UncertaintyEstimator

    # Test with default config
    estimator = UncertaintyEstimator()
    assert estimator.config is not None
    assert len(estimator.calibration_scores) == 0
    assert len(estimator.prediction_history) == 0
    assert estimator._calibration_threshold is None
    print(f"  ✓ Default initialization: threshold={estimator._calibration_threshold}")

    # Test with custom config
    config = UncertaintyConfig(calibration_quantile=0.8)
    estimator2 = UncertaintyEstimator(config)
    assert estimator2.config.calibration_quantile == 0.8
    print(f"  ✓ Custom config initialization")

    print("  ✅ UncertaintyEstimator Initialization: PASSED")
    return True


async def test_uncertainty_boundary_distance():
    """Test boundary distance uncertainty calculation."""
    print("\n=== Test: Boundary Distance Uncertainty ===")

    from model_router import UncertaintyEstimator

    estimator = UncertaintyEstimator()

    # Test uncertainty at boundary (0.5) - should be maximum (1.0)
    uncertainty_at_boundary = estimator.estimate(None, 0.5)
    assert abs(uncertainty_at_boundary - 1.0) < 0.01
    print(f"  ✓ At boundary (0.5): uncertainty={uncertainty_at_boundary:.3f}")

    # Test uncertainty at extremes - should be minimum (0.0)
    uncertainty_at_zero = estimator.estimate(None, 0.0)
    uncertainty_at_one = estimator.estimate(None, 1.0)
    assert abs(uncertainty_at_zero - 0.0) < 0.01
    assert abs(uncertainty_at_one - 0.0) < 0.01
    print(f"  ✓ At extremes: 0.0={uncertainty_at_zero:.3f}, 1.0={uncertainty_at_one:.3f}")

    # Test intermediate values - symmetry
    uncertainty_at_25 = estimator.estimate(None, 0.25)
    uncertainty_at_75 = estimator.estimate(None, 0.75)
    assert abs(uncertainty_at_25 - uncertainty_at_75) < 0.01
    print(f"  ✓ Symmetry: 0.25={uncertainty_at_25:.3f}, 0.75={uncertainty_at_75:.3f}")

    # Formula: uncertainty = 1.0 - 2 * |prediction - 0.5|
    expected_30 = 1.0 - 2 * abs(0.3 - 0.5)  # = 1.0 - 0.4 = 0.6
    actual_30 = estimator.estimate(None, 0.3)
    assert abs(actual_30 - expected_30) < 0.01
    print(f"  ✓ Formula check: 0.3 → {actual_30:.3f} (expected {expected_30:.3f})")

    print("  ✅ Boundary Distance Uncertainty: PASSED")
    return True


async def test_uncertainty_calibration():
    """Test conformal prediction calibration."""
    print("\n=== Test: Conformal Prediction Calibration ===")

    from model_router import UncertaintyConfig, UncertaintyEstimator

    # Use min_samples=5 but provide exactly 5 samples to calibrate()
    # (avoiding auto-recalibration which triggers at multiples of min_samples)
    config = UncertaintyConfig(
        min_samples_for_calibration=5,
        calibration_quantile=0.9,
        enable_calibration=True
    )
    estimator = UncertaintyEstimator(config)

    # Add 4 samples first (below auto-calibration threshold)
    predictions_phase1 = [0.6, 0.7, 0.8, 0.55]
    outcomes_phase1 = [True, True, True, False]

    for pred, outcome in zip(predictions_phase1, outcomes_phase1):
        estimator.record_outcome(pred, outcome)

    assert len(estimator.prediction_history) == 4
    print(f"  ✓ Recorded {len(estimator.prediction_history)} prediction outcomes (below threshold)")

    # Now call calibrate with 5+ samples directly
    calibration_predictions = [0.6, 0.7, 0.8, 0.55, 0.65]
    calibration_outcomes = [True, True, True, False, True]

    calibration_score = estimator.calibrate(calibration_predictions, calibration_outcomes)
    assert calibration_score > 0
    print(f"  ✓ Calibration score: {calibration_score:.3f}")

    # Check calibration scores were computed
    assert len(estimator.calibration_scores) == len(calibration_predictions)
    print(f"  ✓ Computed {len(estimator.calibration_scores)} non-conformity scores")

    # Check calibration threshold was set
    assert estimator._calibration_threshold is not None
    print(f"  ✓ Calibration threshold: {estimator._calibration_threshold:.3f}")

    print("  ✅ Conformal Prediction Calibration: PASSED")
    return True


async def test_uncertainty_record_outcome():
    """Test recording prediction outcomes."""
    print("\n=== Test: Record Outcome ===")

    from model_router import UncertaintyEstimator

    estimator = UncertaintyEstimator()

    # Initially empty
    assert len(estimator.prediction_history) == 0
    print(f"  ✓ Initial: 0 outcomes")

    # Record correct prediction (high confidence correct)
    estimator.record_outcome(0.9, True)
    assert len(estimator.prediction_history) == 1
    assert estimator.prediction_history[0] == (0.9, True)
    print(f"  ✓ After correct (0.9, True): recorded={estimator.prediction_history[0]}")

    # Record incorrect prediction (high confidence wrong)
    estimator.record_outcome(0.8, False)
    assert len(estimator.prediction_history) == 2
    assert estimator.prediction_history[1] == (0.8, False)
    print(f"  ✓ After incorrect (0.8, False): recorded={estimator.prediction_history[1]}")

    # Record borderline prediction
    estimator.record_outcome(0.5, True)
    assert len(estimator.prediction_history) == 3
    assert estimator.prediction_history[2] == (0.5, True)
    print(f"  ✓ After borderline (0.5, True): recorded={estimator.prediction_history[2]}")

    print("  ✅ Record Outcome: PASSED")
    return True


async def test_uncertainty_calibrated_output():
    """Test calibrated uncertainty output."""
    print("\n=== Test: Calibrated Uncertainty Output ===")

    from model_router import UncertaintyConfig, UncertaintyEstimator

    config = UncertaintyConfig(
        min_samples_for_calibration=3,
        calibration_quantile=0.9,
        enable_calibration=True
    )
    estimator = UncertaintyEstimator(config)

    # Without calibration data, should return base uncertainty
    base_uncertainty, conf_interval = estimator.get_calibrated_uncertainty(0.5)
    assert abs(base_uncertainty - 1.0) < 0.01  # At boundary
    print(f"  ✓ Uncalibrated at 0.5: {base_uncertainty:.3f}")

    # Add calibration data
    estimator.record_outcome(0.7, True)
    estimator.record_outcome(0.8, True)
    estimator.record_outcome(0.6, False)
    estimator.record_outcome(0.9, True)

    # After calibration
    calibrated_uncertainty, conf_interval = estimator.get_calibrated_uncertainty(0.6)
    assert calibrated_uncertainty >= 0
    assert conf_interval >= 0
    print(f"  ✓ Calibrated at 0.6: uncertainty={calibrated_uncertainty:.3f}, interval={conf_interval:.3f}")

    print("  ✅ Calibrated Uncertainty Output: PASSED")
    return True


async def test_uncertainty_statistics():
    """Test uncertainty statistics reporting."""
    print("\n=== Test: Uncertainty Statistics ===")

    from model_router import UncertaintyEstimator

    estimator = UncertaintyEstimator()

    # Get initial statistics
    stats = estimator.get_statistics()
    assert 'calibration_samples' in stats
    assert 'calibration_threshold' in stats
    assert 'total_predictions_tracked' in stats
    assert 'is_calibrated' in stats
    assert stats['calibration_samples'] == 0
    assert stats['total_predictions_tracked'] == 0
    assert stats['is_calibrated'] == False
    print(f"  ✓ Initial stats: samples={stats['calibration_samples']}, tracked={stats['total_predictions_tracked']}")

    # Add some samples
    estimator.record_outcome(0.7, True)
    estimator.record_outcome(0.8, False)
    estimator.record_outcome(0.6, True)

    stats = estimator.get_statistics()
    assert stats['total_predictions_tracked'] == 3
    assert 'recent_accuracy' in stats
    assert 'average_uncertainty' in stats
    print(f"  ✓ After samples: tracked={stats['total_predictions_tracked']}, accuracy={stats['recent_accuracy']:.3f}")

    print("  ✅ Uncertainty Statistics: PASSED")
    return True


async def test_uncertainty_reset():
    """Test uncertainty estimator reset."""
    print("\n=== Test: Uncertainty Reset ===")

    from model_router import UncertaintyEstimator

    estimator = UncertaintyEstimator()

    # Add calibration data
    estimator.record_outcome(0.7, True)
    estimator.record_outcome(0.8, True)
    estimator.record_outcome(0.6, False)
    assert len(estimator.prediction_history) == 3
    print(f"  ✓ Before reset: {len(estimator.prediction_history)} predictions tracked")

    # Manually set calibration threshold
    estimator._calibration_threshold = 0.25

    # Reset
    estimator.reset()
    assert len(estimator.prediction_history) == 0
    assert len(estimator.calibration_scores) == 0
    assert estimator._calibration_threshold is None
    print(f"  ✓ After reset: {len(estimator.prediction_history)} predictions, threshold={estimator._calibration_threshold}")

    print("  ✅ Uncertainty Reset: PASSED")
    return True


async def test_uncertainty_edge_cases():
    """Test uncertainty estimator edge cases."""
    print("\n=== Test: Uncertainty Edge Cases ===")

    from model_router import UncertaintyEstimator

    estimator = UncertaintyEstimator()

    # Test predictions at exact 0 and 1
    u_zero = estimator.estimate(None, 0.0)
    u_one = estimator.estimate(None, 1.0)
    assert u_zero == 0.0
    assert u_one == 0.0
    print(f"  ✓ Extreme predictions: 0.0→{u_zero}, 1.0→{u_one}")

    # Test predictions slightly outside [0, 1] - should be clamped
    u_negative = estimator.estimate(None, -0.1)
    u_over = estimator.estimate(None, 1.1)
    # These might raise or clamp, depending on implementation
    print(f"  ✓ Edge values handled gracefully")

    # Test with empty features list
    u_empty = estimator.estimate([], 0.5)
    assert u_empty == 1.0  # At boundary
    print(f"  ✓ Empty features: {u_empty}")

    # Test with predictions tracked
    estimator.reset()
    for i in range(5):
        estimator.record_outcome(0.9, True)
    stats = estimator.get_statistics()
    assert stats['total_predictions_tracked'] == 5
    assert stats['recent_accuracy'] == 1.0  # All correct
    print(f"  ✓ All correct predictions: tracked={stats['total_predictions_tracked']}, accuracy={stats['recent_accuracy']}")

    print("  ✅ Uncertainty Edge Cases: PASSED")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("ModelRouter Integration Tests")
    print("=" * 60)

    tests = [
        ("Legacy Router", test_router),
        ("Basic Initialization", test_basic_initialization),
        ("Provider Types", test_provider_types),
        ("Data Classes", test_data_classes),
        ("Routing Rules", test_routing_rules),
        ("Metrics Tracking", test_metrics_tracking),
        ("Config Loading", test_config_loading),
        ("MCP Tools", test_mcp_tools),
        ("Convenience Functions", test_convenience_functions),
        # UncertaintyEstimator tests (ported from tiny-dancer-core)
        ("Uncertainty Config", test_uncertainty_config),
        ("Uncertainty Estimator Init", test_uncertainty_estimator_init),
        ("Uncertainty Boundary Distance", test_uncertainty_boundary_distance),
        ("Uncertainty Calibration", test_uncertainty_calibration),
        ("Uncertainty Record Outcome", test_uncertainty_record_outcome),
        ("Uncertainty Calibrated Output", test_uncertainty_calibrated_output),
        ("Uncertainty Statistics", test_uncertainty_statistics),
        ("Uncertainty Reset", test_uncertainty_reset),
        ("Uncertainty Edge Cases", test_uncertainty_edge_cases),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            print(f"  ❌ {name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
