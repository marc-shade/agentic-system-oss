#!/usr/bin/env python3
"""
Example usage of TOON utilities in MCP servers
"""

import sys
from pathlib import Path

# Add shared directory to path
sys.path.insert(0, str(Path(__file__).parent))

import toon_codec
import toon_utils


def example_basic_encoding():
    """Example 1: Basic encoding/decoding"""
    print("=" * 60)
    print("Example 1: Basic Encoding/Decoding")
    print("=" * 60)

    task = {
        "id": 1,
        "title": "Implement TOON support",
        "status": "completed",
        "priority": 9,
        "tags": ["enhancement", "performance"]
    }

    # Encode
    toon_str = toon_codec.encode(task)
    print(f"\nOriginal JSON: {len(str(task))} chars")
    print(f"TOON encoded: {len(toon_str)} chars")
    print(f"\nTOON output:\n{toon_str}")

    # Decode
    decoded = toon_codec.decode(toon_str)
    print(f"\nDecoded successfully: {decoded == task}")


def example_mcp_response():
    """Example 2: Creating MCP tool responses"""
    print("\n" + "=" * 60)
    print("Example 2: MCP Tool Response")
    print("=" * 60)

    # Simulate fetching data
    goals = [
        {"id": 1, "name": "Q1 Objectives", "status": "active"},
        {"id": 2, "name": "Q2 Objectives", "status": "planned"}
    ]

    tasks = [
        {"id": 1, "goal_id": 1, "title": "Task A", "status": "done"},
        {"id": 2, "goal_id": 1, "title": "Task B", "status": "in_progress"},
        {"id": 3, "goal_id": 2, "title": "Task C", "status": "pending"}
    ]

    # Create MCP response with TOON encoding
    response = toon_utils.mcp_tool_response(
        tool_name="list_all",
        result={"goals": goals, "tasks": tasks},
        format="toon",
        include_stats=True
    )

    print("\nMCP Response:")
    print(f"Content type: {response['content'][0]['type']}")
    print(f"Encoding: {response.get('_meta', {}).get('encoding', 'N/A')}")
    print(f"Compression: {response.get('_meta', {}).get('compression', 'N/A')}")
    print(f"\nTOON content:\n{response['content'][0]['text'][:200]}...")


def example_compression_comparison():
    """Example 3: Comparing compression ratios"""
    print("\n" + "=" * 60)
    print("Example 3: Compression Comparison")
    print("=" * 60)

    # Create test data
    test_data = {
        "tasks": [
            {
                "id": i,
                "title": f"Task {i}",
                "description": f"Complete task number {i}",
                "status": "pending" if i % 3 == 0 else "active",
                "priority": i % 10,
                "assignee": f"user{i % 5}",
                "tags": ["backend", "urgent"] if i % 2 == 0 else ["frontend"],
                "created_at": f"2025-11-{20 + (i % 10):02d}T10:00:00"
            }
            for i in range(1, 51)  # 50 tasks
        ]
    }

    comparison = toon_utils.compare_encodings(test_data)

    print("\nEncoding Comparison (50 tasks):")
    print(f"\nJSON Compact: {comparison['json']['compact']} chars")
    print(f"JSON Pretty:  {comparison['json']['pretty']} chars")
    print(f"TOON Compact: {comparison['toon']['compact']} chars")
    print(f"TOON Pretty:  {comparison['toon']['pretty']} chars")

    print(f"\nCompression Stats:")
    print(f"  Ratio: {comparison['compression']['ratio']}x")
    print(f"  Reduction: {comparison['compression']['reduction_percent']}%")
    print(f"  Tokens Saved: ~{comparison['compression']['tokens_saved']}")

    print(f"\n🏆 Winner: {comparison['winner']}")


def example_smart_payload_optimization():
    """Example 4: Smart payload optimization"""
    print("\n" + "=" * 60)
    print("Example 4: Smart Payload Optimization")
    print("=" * 60)

    # Small payload - should use JSON
    small_data = {"id": 1, "name": "Quick task"}
    small_result = toon_utils.optimize_mcp_payload(small_data, threshold=100)

    print("\nSmall Payload (< threshold):")
    print(f"  Encoding: {small_result['encoding']}")
    print(f"  Size: {small_result['size']} chars")
    print(f"  Reason: {small_result['reason']}")

    # Large payload - should use TOON
    large_data = {
        "items": [
            {"id": i, "name": f"Item {i}", "value": i * 100}
            for i in range(200)
        ]
    }
    large_result = toon_utils.optimize_mcp_payload(large_data, threshold=100)

    print("\nLarge Payload (> threshold):")
    print(f"  Encoding: {large_result['encoding']}")
    print(f"  TOON Size: {large_result['size']} chars")
    print(f"  JSON Size: {large_result['json_size']} chars")
    print(f"  Tokens Saved: ~{large_result['tokens_saved']}")
    print(f"  Reduction: {large_result['reduction']}")
    print(f"  Reason: {large_result['reason']}")


def example_batch_processing():
    """Example 5: Batch encoding/decoding"""
    print("\n" + "=" * 60)
    print("Example 5: Batch Processing")
    print("=" * 60)

    items = [
        {"id": 1, "type": "goal", "name": "Goal A"},
        {"id": 2, "type": "goal", "name": "Goal B"},
        {"id": 3, "type": "task", "name": "Task 1"},
        {"id": 4, "type": "task", "name": "Task 2"}
    ]

    print(f"\nEncoding {len(items)} items in batch...")
    encoded = toon_utils.batch_encode(items)

    print(f"Encoded {len(encoded)} TOON strings:")
    for i, toon_str in enumerate(encoded, 1):
        print(f"  {i}. {toon_str}")

    print(f"\nDecoding {len(encoded)} TOON strings...")
    decoded = toon_utils.batch_decode(encoded)

    print(f"Successfully decoded {len(decoded)} items")
    print(f"Round-trip successful: {decoded == items}")


def example_mcp_integration():
    """Example 6: Full MCP server integration pattern"""
    print("\n" + "=" * 60)
    print("Example 6: MCP Server Integration Pattern")
    print("=" * 60)

    # Simulated MCP tool handler
    def handle_list_tasks(arguments):
        """Example MCP tool handler using TOON"""
        # Fetch data (simulated)
        tasks = [
            {"id": i, "title": f"Task {i}", "status": "active"}
            for i in range(1, 21)
        ]

        # Create optimized response
        return toon_utils.mcp_tool_response(
            tool_name="list_tasks",
            result={"tasks": tasks, "total": len(tasks)},
            format="toon",
            include_stats=True
        )

    # Call the handler
    response = handle_list_tasks({})

    print("\nMCP Tool Response:")
    print(f"  Tool: {response.get('_meta', {}).get('tool', 'N/A')}")
    print(f"  Encoding: {response.get('_meta', {}).get('encoding', 'N/A')}")
    print(f"  Compression: {response.get('_meta', {}).get('compression', 'N/A')}")
    print(f"  Tokens Saved: {response.get('_meta', {}).get('tokens_saved', 'N/A')}")
    print(f"\nContent preview:\n{response['content'][0]['text'][:150]}...")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("TOON UTILITIES - USAGE EXAMPLES")
    print("=" * 60)

    example_basic_encoding()
    example_mcp_response()
    example_compression_comparison()
    example_smart_payload_optimization()
    example_batch_processing()
    example_mcp_integration()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
