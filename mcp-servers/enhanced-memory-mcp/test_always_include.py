#!/usr/bin/env python3
"""Test always_include functionality"""

import sys
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

from memory_client import MemoryClient
import json

client = MemoryClient()

print("Testing search_nodes with always_include...")
print("="*60)

# Test search - should return user profile + search results
result = client.search_nodes_sync("code execution", limit=3)

print(f"\nSearch query: 'code execution'")
print(f"Total results: {result.get('count', 0)}")
print(f"Always-include count: {result.get('always_include_count', 0)}")
print(f"Search results count: {result.get('search_results_count', 0)}")
print()

if result.get('success'):
    for i, entity in enumerate(result.get('results', []), 1):
        print(f"{i}. {entity['name']}")
        print(f"   Type: {entity['entityType']}")
        print(f"   Source: {entity.get('source', 'unknown')}")
        print(f"   Always Include: {entity.get('always_include', False)}")
        print(f"   Observations: {len(entity.get('observations', []))} items")
        print()
else:
    print(f"ERROR: {result.get('error', 'Unknown error')}")

# Test with unrelated query - should still show user profile
print("\n" + "="*60)
print("Testing with unrelated query...")
print("="*60)

result2 = client.search_nodes_sync("temporal workflow", limit=3)

print(f"\nSearch query: 'temporal workflow'")
print(f"Total results: {result2.get('count', 0)}")
print(f"Always-include count: {result2.get('always_include_count', 0)}")
print()

if result2.get('success'):
    for i, entity in enumerate(result2.get('results', []), 1):
        print(f"{i}. {entity['name']}")
        print(f"   Source: {entity.get('source', 'unknown')}")
        print()
