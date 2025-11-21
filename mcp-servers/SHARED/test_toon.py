#!/usr/bin/env python3
"""
Test TOON codec and utilities
"""

import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import toon_codec
import toon_utils


def test_basic_encoding():
    """Test basic TOON encoding/decoding"""
    print("=" * 60)
    print("TEST 1: Basic Encoding/Decoding")
    print("=" * 60)

    test_data = {
        "name": "Test Task",
        "id": 123,
        "status": "active",
        "tags": ["urgent", "backend"],
        "metadata": {
            "priority": 8,
            "assignee": "alice"
        }
    }

    print("\nOriginal data:")
    print(json.dumps(test_data, indent=2))

    # Encode
    toon_str = toon_codec.encode(test_data)
    print(f"\nTOON encoded ({len(toon_str)} chars):")
    print(toon_str)

    # Decode
    decoded = toon_codec.decode(toon_str)
    print("\nDecoded data:")
    print(json.dumps(decoded, indent=2))

    # Verify
    assert decoded == test_data, "Decode mismatch!"
    print("\n✓ Encoding/decoding successful!")

    return test_data, toon_str


def test_compression_ratio():
    """Test compression ratio calculation"""
    print("\n" + "=" * 60)
    print("TEST 2: Compression Ratio")
    print("=" * 60)

    task_queue = [
        {
            "id": i,
            "title": f"Task {i}",
            "description": f"Complete task number {i}",
            "status": "pending",
            "priority": 5,
            "assignee": f"user{i % 3}",
            "tags": ["backend", "api"]
        }
        for i in range(1, 21)  # 20 tasks
    ]

    stats = toon_codec.compression_ratio(task_queue)

    print(f"\nJSON size: {stats['json_size']} chars")
    print(f"TOON size: {stats['toon_size']} chars")
    print(f"Compression ratio: {stats['ratio']}x")
    print(f"Tokens saved: ~{stats['tokens_saved']} tokens")
    print(f"Reduction: {stats['reduction_percent']}%")

    print("\n✓ Compression analysis complete!")
    return stats


def test_mcp_response():
    """Test MCP response helper"""
    print("\n" + "=" * 60)
    print("TEST 3: MCP Response Helper")
    print("=" * 60)

    result_data = {
        "goals": [
            {"id": 1, "name": "Goal A", "status": "active"},
            {"id": 2, "name": "Goal B", "status": "completed"}
        ],
        "tasks": [
            {"id": 1, "goal_id": 1, "title": "Task 1"},
            {"id": 2, "goal_id": 1, "title": "Task 2"}
        ]
    }

    response = toon_utils.toon_response(
        data=result_data,
        metadata={"generated_at": "2025-11-20T12:00:00", "version": "1.0"}
    )

    print("\nMCP Response structure:")
    print(json.dumps(response, indent=2))

    print("\n✓ MCP response generation successful!")
    return response


def test_fallback_encoding():
    """Test fallback to JSON"""
    print("\n" + "=" * 60)
    print("TEST 4: Fallback Encoding")
    print("=" * 60)

    test_data = {"test": "data", "number": 42}

    # Test with fallback
    encoded = toon_utils.encode_with_fallback(test_data)
    print(f"\nEncoded with fallback ({len(encoded)} chars):")
    print(encoded)

    # Decode
    decoded = toon_utils.smart_decode(encoded)
    print("\nDecoded:")
    print(json.dumps(decoded, indent=2))

    assert decoded == test_data
    print("\n✓ Fallback encoding works!")


def test_batch_operations():
    """Test batch encode/decode"""
    print("\n" + "=" * 60)
    print("TEST 5: Batch Operations")
    print("=" * 60)

    items = [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"},
        {"id": 3, "name": "Item 3"}
    ]

    print(f"\nEncoding {len(items)} items...")
    encoded = toon_utils.batch_encode(items)

    print(f"Encoded {len(encoded)} TOON strings")
    for i, e in enumerate(encoded, 1):
        print(f"  {i}. {e}")

    print("\nDecoding...")
    decoded = toon_utils.batch_decode(encoded)

    assert decoded == items
    print("\n✓ Batch operations successful!")


def test_comparison():
    """Test encoding comparison"""
    print("\n" + "=" * 60)
    print("TEST 6: Encoding Comparison")
    print("=" * 60)

    data = {
        "tasks": [
            {
                "id": i,
                "title": f"Task {i}",
                "description": f"Description for task {i}",
                "status": "pending",
                "priority": i % 10,
                "tags": ["backend", "urgent"] if i % 2 == 0 else ["frontend"]
            }
            for i in range(1, 11)
        ]
    }

    comparison = toon_utils.compare_encodings(data)

    print("\nJSON Encoding:")
    print(f"  Compact: {comparison['json']['compact']} chars")
    print(f"  Pretty: {comparison['json']['pretty']} chars")
    print(f"  Sample: {comparison['json']['sample']}")

    print("\nTOON Encoding:")
    print(f"  Compact: {comparison['toon']['compact']} chars")
    print(f"  Pretty: {comparison['toon']['pretty']} chars")
    print(f"  Sample: {comparison['toon']['sample']}")

    print("\nCompression Stats:")
    print(f"  Ratio: {comparison['compression']['ratio']}x")
    print(f"  Reduction: {comparison['compression']['reduction_percent']}%")
    print(f"  Tokens saved: ~{comparison['compression']['tokens_saved']}")

    print(f"\n🏆 Winner: {comparison['winner']}")

    print("\n✓ Comparison complete!")


def test_payload_optimization():
    """Test payload optimization"""
    print("\n" + "=" * 60)
    print("TEST 7: Payload Optimization")
    print("=" * 60)

    # Small payload
    small_data = {"id": 1, "name": "Test"}
    small_result = toon_utils.optimize_mcp_payload(small_data, threshold=1000)

    print("\nSmall payload:")
    print(f"  Encoding: {small_result['encoding']}")
    print(f"  Size: {small_result['size']} chars")
    print(f"  Reason: {small_result['reason']}")

    # Large payload
    large_data = {
        "items": [
            {"id": i, "name": f"Item {i}", "description": f"Description {i}"}
            for i in range(100)
        ]
    }
    large_result = toon_utils.optimize_mcp_payload(large_data, threshold=1000)

    print("\nLarge payload:")
    print(f"  Encoding: {large_result['encoding']}")
    print(f"  TOON size: {large_result['size']} chars")
    print(f"  JSON size: {large_result['json_size']} chars")
    print(f"  Tokens saved: ~{large_result['tokens_saved']}")
    print(f"  Reduction: {large_result['reduction']}")
    print(f"  Reason: {large_result['reason']}")

    print("\n✓ Payload optimization complete!")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TOON CODEC & UTILITIES TEST SUITE")
    print("=" * 60)

    try:
        # Run tests
        test_basic_encoding()
        stats = test_compression_ratio()
        test_mcp_response()
        test_fallback_encoding()
        test_batch_operations()
        test_comparison()
        test_payload_optimization()

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("\n✓ All tests passed!")
        print(f"\nKey Findings:")
        print(f"  - TOON compression ratio: {stats['ratio']}x")
        print(f"  - Token savings: ~{stats['tokens_saved']} tokens")
        print(f"  - Size reduction: {stats['reduction_percent']}%")
        print("\nTOON utilities ready for production use!")

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
