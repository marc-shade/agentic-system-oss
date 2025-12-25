#!/usr/bin/env python3
"""
Test suite for Strange Loops Detector integration.

Tests both:
1. Core StrangeLoopsDetector class functionality
2. MCP tool registration and operation

Verifies:
- Circular reasoning detection via DFS
- Contradiction detection via keyword matching
- Causal chain validation
- Recursive pattern detection
- MCP tool registration
"""

import asyncio
import os
import sys
from pathlib import Path

# Set up test environment
os.chdir(Path(__file__).parent)

from strange_loops import (
    StrangeLoopsDetector, PatternType, Severity,
    CausalChain, CausalNode, CausalEdge, EdgeType,
    LogicalPattern, ValidationResult, RecursivePattern,
    register_strange_loops_tools
)


async def test_basic_initialization():
    """Test basic detector initialization."""
    print("\n=== Test: Basic Initialization ===")

    detector = StrangeLoopsDetector()

    assert detector.detection_count == 0
    print("  Detection count: 0")

    assert len(detector.detected_patterns) == 0
    print("  Detected patterns: []")

    stats = detector.get_stats()
    assert stats["total_detections"] == 0
    assert stats["pattern_count"] == 0
    print(f"  Stats: {stats['total_detections']} detections")

    print("  Detector initialized successfully")
    return True


async def test_circular_reasoning_simple():
    """Test simple circular reasoning detection."""
    print("\n=== Test: Simple Circular Reasoning ===")

    detector = StrangeLoopsDetector()

    # Simple 3-node cycle: A -> B -> C -> A
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"]
    }

    patterns = detector.detect_circular_reasoning(graph)

    assert len(patterns) >= 1, "Should detect at least one cycle"
    print(f"  Detected {len(patterns)} circular pattern(s)")

    # Check the pattern
    pattern = patterns[0]
    assert pattern.type == PatternType.CIRCULAR
    print(f"  Pattern type: {pattern.type.value}")

    assert len(pattern.affected_nodes) >= 3
    print(f"  Affected nodes: {pattern.affected_nodes}")

    # Should be high severity for 3-node cycle
    assert pattern.severity in [Severity.HIGH, Severity.CRITICAL]
    print(f"  Severity: {pattern.severity.value}")

    print("  Simple circular reasoning: PASSED")
    return True


async def test_circular_reasoning_multiple():
    """Test detection of multiple cycles."""
    print("\n=== Test: Multiple Cycles ===")

    detector = StrangeLoopsDetector()

    # Graph with multiple independent cycles
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],  # Cycle 1: A->B->C->A
        "D": ["E"],
        "E": ["D"],  # Cycle 2: D->E->D
        "X": ["Y"],
        "Y": ["Z"]   # No cycle here
    }

    patterns = detector.detect_circular_reasoning(graph)

    assert len(patterns) >= 2, "Should detect at least 2 cycles"
    print(f"  Detected {len(patterns)} circular patterns")

    # Stats should reflect detections
    stats = detector.get_stats()
    assert stats["operations"]["circular_detections"] >= 2
    print(f"  Circular detections in stats: {stats['operations']['circular_detections']}")

    print("  Multiple cycles: PASSED")
    return True


async def test_self_reference_cycle():
    """Test detection of self-reference (node pointing to itself)."""
    print("\n=== Test: Self-Reference Cycle ===")

    detector = StrangeLoopsDetector()

    # Self-reference: A -> A
    graph = {
        "A": ["A"],
        "B": ["C"],
        "C": []
    }

    patterns = detector.detect_circular_reasoning(graph)

    assert len(patterns) >= 1
    print(f"  Detected {len(patterns)} pattern(s)")

    # Self-reference should be critical severity
    self_ref_patterns = [p for p in patterns if len(p.affected_nodes) <= 2]
    if self_ref_patterns:
        assert self_ref_patterns[0].severity == Severity.CRITICAL
        print(f"  Self-reference severity: CRITICAL")

    print("  Self-reference cycle: PASSED")
    return True


async def test_contradiction_detection():
    """Test contradiction detection via keyword matching."""
    print("\n=== Test: Contradiction Detection ===")

    detector = StrangeLoopsDetector()

    statements = [
        "The system always runs at midnight",
        "The system never runs at midnight",
        "Temperature will increase steadily",
        "Temperature will decrease over time"
    ]

    patterns = detector.detect_contradictions(statements)

    assert len(patterns) >= 2, "Should detect at least 2 contradictions"
    print(f"  Detected {len(patterns)} contradiction(s)")

    for p in patterns:
        assert p.type == PatternType.CONTRADICTION
        assert p.severity == Severity.HIGH
        print(f"  - {p.description}")

    # Check stats
    stats = detector.get_stats()
    assert stats["operations"]["contradiction_detections"] >= 2
    print(f"  Contradiction detections in stats: {stats['operations']['contradiction_detections']}")

    print("  Contradiction detection: PASSED")
    return True


async def test_no_contradictions():
    """Test that consistent statements don't trigger false positives."""
    print("\n=== Test: No False Contradictions ===")

    detector = StrangeLoopsDetector()

    statements = [
        "The system runs efficiently",
        "Performance is optimized",
        "Memory usage is low",
        "CPU utilization is balanced"
    ]

    patterns = detector.detect_contradictions(statements)

    assert len(patterns) == 0, "Should not detect contradictions in consistent statements"
    print(f"  Detected {len(patterns)} contradictions (expected 0)")

    print("  No false contradictions: PASSED")
    return True


async def test_causal_chain_valid():
    """Test validation of a valid causal chain."""
    print("\n=== Test: Valid Causal Chain ===")

    detector = StrangeLoopsDetector()

    chain = CausalChain(
        id="valid_chain",
        nodes=[
            CausalNode("A", "Rain falls", 0.9),
            CausalNode("B", "Ground is wet", 0.95),
            CausalNode("C", "Plants grow", 0.85)
        ],
        edges=[
            CausalEdge("A", "B", 0.9, EdgeType.CAUSES),
            CausalEdge("B", "C", 0.8, EdgeType.CAUSES)
        ]
    )

    result = detector.validate_causal_chain(chain)

    assert result.is_valid, "Chain should be valid"
    print(f"  Chain valid: {result.is_valid}")

    assert len(result.cycles) == 0
    print(f"  Cycles: {len(result.cycles)}")

    assert len(result.weak_links) == 0
    print(f"  Weak links: {len(result.weak_links)}")

    assert len(result.contradictions) == 0
    print(f"  Contradictions: {len(result.contradictions)}")

    print("  Valid causal chain: PASSED")
    return True


async def test_causal_chain_with_cycle():
    """Test detection of cycle in causal chain."""
    print("\n=== Test: Causal Chain with Cycle ===")

    detector = StrangeLoopsDetector()

    chain = CausalChain(
        id="cyclic_chain",
        nodes=[
            CausalNode("A", "Event A occurs", 0.9),
            CausalNode("B", "Event B follows", 0.9),
            CausalNode("C", "Event C happens", 0.9)
        ],
        edges=[
            CausalEdge("A", "B", 0.9),
            CausalEdge("B", "C", 0.9),
            CausalEdge("C", "A", 0.9)  # Creates cycle!
        ]
    )

    result = detector.validate_causal_chain(chain)

    assert not result.is_valid, "Chain with cycle should be invalid"
    print(f"  Chain valid: {result.is_valid}")

    assert len(result.cycles) >= 1
    print(f"  Cycles detected: {result.cycles}")

    print("  Causal chain with cycle: PASSED")
    return True


async def test_causal_chain_weak_links():
    """Test detection of weak links in causal chain."""
    print("\n=== Test: Causal Chain Weak Links ===")

    detector = StrangeLoopsDetector()

    chain = CausalChain(
        id="weak_chain",
        nodes=[
            CausalNode("A", "Strong start", 0.9),
            CausalNode("B", "Weak middle", 0.5),
            CausalNode("C", "Strong end", 0.9)
        ],
        edges=[
            CausalEdge("A", "B", 0.3),  # Weak!
            CausalEdge("B", "C", 0.2)   # Also weak!
        ]
    )

    result = detector.validate_causal_chain(chain)

    assert not result.is_valid, "Chain with weak links should be invalid"
    print(f"  Chain valid: {result.is_valid}")

    assert len(result.weak_links) >= 2
    print(f"  Weak links: {len(result.weak_links)}")

    print("  Causal chain weak links: PASSED")
    return True


async def test_recursive_pattern_detection():
    """Test recursive pattern detection in nested structures."""
    print("\n=== Test: Recursive Pattern Detection ===")

    detector = StrangeLoopsDetector()

    # Create structure with self-reference
    structure = {
        "name": "root",
        "data": {"value": 42},
        "children": []
    }
    # Add self-reference
    structure["children"].append({"name": "child", "parent": structure})

    patterns = detector.detect_recursive_patterns(structure)

    assert len(patterns) >= 1, "Should detect self-reference"
    print(f"  Detected {len(patterns)} recursive pattern(s)")

    if patterns:
        print(f"  Pattern depth: {patterns[0].depth}")
        print(f"  Pattern type: {patterns[0].pattern_type}")

    print("  Recursive pattern detection: PASSED")
    return True


async def test_no_recursive_patterns():
    """Test that normal structures don't trigger false positives."""
    print("\n=== Test: No False Recursive Patterns ===")

    detector = StrangeLoopsDetector()

    # Normal tree structure (no self-references)
    structure = {
        "name": "root",
        "children": [
            {"name": "child1", "value": 1},
            {"name": "child2", "value": 2},
            {"name": "child3", "children": [
                {"name": "grandchild1"}
            ]}
        ]
    }

    patterns = detector.detect_recursive_patterns(structure)

    assert len(patterns) == 0, "Normal tree should not have recursive patterns"
    print(f"  Detected {len(patterns)} patterns (expected 0)")

    print("  No false recursive patterns: PASSED")
    return True


async def test_pattern_filtering():
    """Test filtering patterns by type and severity."""
    print("\n=== Test: Pattern Filtering ===")

    detector = StrangeLoopsDetector()

    # Generate various patterns
    detector.detect_circular_reasoning({
        "A": ["B"], "B": ["A"]
    })

    detector.detect_contradictions([
        "Always true",
        "Never true"
    ])

    # Get all patterns
    all_patterns = detector.get_all_patterns()
    print(f"  Total patterns: {len(all_patterns)}")

    # Filter by type
    circular = detector.get_patterns_by_type(PatternType.CIRCULAR)
    print(f"  Circular patterns: {len(circular)}")

    contradictions = detector.get_patterns_by_type(PatternType.CONTRADICTION)
    print(f"  Contradiction patterns: {len(contradictions)}")

    # Filter by severity
    high_severity = detector.get_patterns_by_severity(Severity.HIGH)
    print(f"  High severity patterns: {len(high_severity)}")

    assert len(all_patterns) >= 2
    assert len(circular) >= 1
    assert len(contradictions) >= 1

    print("  Pattern filtering: PASSED")
    return True


async def test_statistics():
    """Test comprehensive statistics tracking."""
    print("\n=== Test: Statistics Tracking ===")

    detector = StrangeLoopsDetector()

    # Generate patterns
    detector.detect_circular_reasoning({"A": ["B"], "B": ["A"]})
    detector.detect_contradictions(["Must do X", "Cannot do X"])

    chain = CausalChain(
        id="test",
        nodes=[CausalNode("A", "Test", 0.9)],
        edges=[]
    )
    detector.validate_causal_chain(chain)

    stats = detector.get_stats()

    assert stats["total_detections"] >= 2
    print(f"  Total detections: {stats['total_detections']}")

    assert stats["operations"]["circular_detections"] >= 1
    print(f"  Circular: {stats['operations']['circular_detections']}")

    assert stats["operations"]["contradiction_detections"] >= 1
    print(f"  Contradictions: {stats['operations']['contradiction_detections']}")

    assert stats["operations"]["causal_validations"] >= 1
    print(f"  Causal validations: {stats['operations']['causal_validations']}")

    print(f"  By severity: {stats['by_severity']}")
    print(f"  By type: {stats['by_type']}")

    print("  Statistics tracking: PASSED")
    return True


async def test_clear_and_reset():
    """Test clearing patterns and resetting stats."""
    print("\n=== Test: Clear and Reset ===")

    detector = StrangeLoopsDetector()

    # Generate some patterns
    detector.detect_circular_reasoning({"A": ["A"]})
    detector.detect_contradictions(["Yes", "No"])

    # Verify we have patterns
    assert len(detector.detected_patterns) > 0
    assert detector.detection_count > 0
    print(f"  Before clear: {len(detector.detected_patterns)} patterns")

    # Clear patterns
    detector.clear_patterns()
    assert len(detector.detected_patterns) == 0
    assert detector.detection_count == 0
    print(f"  After clear: {len(detector.detected_patterns)} patterns")

    # Stats should still exist
    stats = detector.get_stats()
    assert stats["operations"]["circular_detections"] > 0
    print(f"  Stats before reset: {stats['operations']}")

    # Reset stats
    detector.reset_stats()
    stats = detector.get_stats()
    assert stats["operations"]["circular_detections"] == 0
    print(f"  Stats after reset: {stats['operations']}")

    print("  Clear and reset: PASSED")
    return True


async def test_mcp_tool_registration():
    """Test MCP tool registration."""
    print("\n=== Test: MCP Tool Registration ===")

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mock_app = MockApp()
    detector = register_strange_loops_tools(mock_app)

    expected_tools = [
        "sl_detect_circular",
        "sl_detect_contradictions",
        "sl_validate_chain",
        "sl_detect_recursive",
        "sl_get_patterns",
        "sl_status",
        "sl_clear"
    ]

    for tool_name in expected_tools:
        assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"
        print(f"  Registered: {tool_name}")

    assert isinstance(detector, StrangeLoopsDetector)
    print(f"  Returned detector: StrangeLoopsDetector")

    print("  MCP tool registration: PASSED")
    return True


async def test_mcp_tools_execution():
    """Test MCP tool execution."""
    print("\n=== Test: MCP Tool Execution ===")

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mock_app = MockApp()
    register_strange_loops_tools(mock_app)

    # Test sl_detect_circular
    result = await mock_app.tools["sl_detect_circular"]({"A": ["B"], "B": ["A"]})
    assert result["patterns_found"] >= 1
    print(f"  sl_detect_circular: {result['patterns_found']} patterns")

    # Test sl_detect_contradictions
    result = await mock_app.tools["sl_detect_contradictions"]([
        "Always enabled",
        "Never enabled"
    ])
    assert result["patterns_found"] >= 1
    print(f"  sl_detect_contradictions: {result['patterns_found']} patterns")

    # Test sl_validate_chain
    result = await mock_app.tools["sl_validate_chain"](
        chain_id="test",
        nodes=[
            {"id": "A", "statement": "Test A", "confidence": 0.9},
            {"id": "B", "statement": "Test B", "confidence": 0.9}
        ],
        edges=[
            {"from": "A", "to": "B", "strength": 0.8, "type": "causes"}
        ]
    )
    assert "is_valid" in result
    print(f"  sl_validate_chain: valid={result['is_valid']}")

    # Test sl_status
    result = await mock_app.tools["sl_status"]()
    assert result["detector"] == "StrangeLoopsDetector"
    assert "statistics" in result
    print(f"  sl_status: {result['statistics']['total_detections']} total detections")

    # Test sl_get_patterns
    result = await mock_app.tools["sl_get_patterns"]()
    assert "patterns" in result
    print(f"  sl_get_patterns: {result['pattern_count']} patterns")

    # Test sl_clear
    result = await mock_app.tools["sl_clear"]()
    assert result["cleared"] is True
    print(f"  sl_clear: cleared={result['cleared']}")

    print("  MCP tool execution: PASSED")
    return True


async def test_edge_types():
    """Test different edge types in causal chains."""
    print("\n=== Test: Edge Types ===")

    detector = StrangeLoopsDetector()

    chain = CausalChain(
        id="multi_edge",
        nodes=[
            CausalNode("A", "Cause A", 0.9),
            CausalNode("B", "Effect B", 0.9),
            CausalNode("C", "Related C", 0.9),
            CausalNode("D", "Dependent D", 0.9)
        ],
        edges=[
            CausalEdge("A", "B", 0.9, EdgeType.CAUSES),
            CausalEdge("B", "C", 0.8, EdgeType.IMPLIES),
            CausalEdge("C", "D", 0.7, EdgeType.CORRELATES)
        ]
    )

    result = detector.validate_causal_chain(chain)

    assert result.is_valid
    print(f"  Chain valid: {result.is_valid}")

    # Verify edge types preserved
    assert chain.edges[0].edge_type == EdgeType.CAUSES
    assert chain.edges[1].edge_type == EdgeType.IMPLIES
    assert chain.edges[2].edge_type == EdgeType.CORRELATES
    print(f"  Edge types preserved: causes, implies, correlates")

    print("  Edge types: PASSED")
    return True


async def test_serialization():
    """Test pattern serialization to dict."""
    print("\n=== Test: Serialization ===")

    detector = StrangeLoopsDetector()

    # Create a pattern
    detector.detect_circular_reasoning({"A": ["B"], "B": ["A"]})

    patterns = detector.get_all_patterns()
    assert len(patterns) >= 1

    # Serialize
    pattern_dict = patterns[0].to_dict()

    assert "id" in pattern_dict
    assert "type" in pattern_dict
    assert "description" in pattern_dict
    assert "severity" in pattern_dict
    assert "affected_nodes" in pattern_dict
    assert "evidence" in pattern_dict
    assert "detected_at" in pattern_dict

    print(f"  Pattern ID: {pattern_dict['id'][:16]}...")
    print(f"  Type: {pattern_dict['type']}")
    print(f"  Severity: {pattern_dict['severity']}")

    # Test chain serialization
    chain = CausalChain(
        id="test",
        nodes=[CausalNode("A", "Test", 0.9)],
        edges=[CausalEdge("A", "B", 0.8)]
    )
    chain_dict = chain.to_dict()

    assert "nodes" in chain_dict
    assert "edges" in chain_dict
    print(f"  Chain serialization: OK")

    print("  Serialization: PASSED")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Strange Loops Detector - Integration Tests")
    print("=" * 60)

    tests = [
        ("Basic Initialization", test_basic_initialization),
        ("Simple Circular Reasoning", test_circular_reasoning_simple),
        ("Multiple Cycles", test_circular_reasoning_multiple),
        ("Self-Reference Cycle", test_self_reference_cycle),
        ("Contradiction Detection", test_contradiction_detection),
        ("No False Contradictions", test_no_contradictions),
        ("Valid Causal Chain", test_causal_chain_valid),
        ("Causal Chain with Cycle", test_causal_chain_with_cycle),
        ("Causal Chain Weak Links", test_causal_chain_weak_links),
        ("Recursive Pattern Detection", test_recursive_pattern_detection),
        ("No False Recursive", test_no_recursive_patterns),
        ("Pattern Filtering", test_pattern_filtering),
        ("Statistics Tracking", test_statistics),
        ("Clear and Reset", test_clear_and_reset),
        ("MCP Tool Registration", test_mcp_tool_registration),
        ("MCP Tool Execution", test_mcp_tools_execution),
        ("Edge Types", test_edge_types),
        ("Serialization", test_serialization),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
            print(f"  PASSED")
        except Exception as e:
            print(f"  FAILED - {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
