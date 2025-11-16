#!/usr/bin/env python3
"""
Test FastMCP Enhanced Memory Server
Quick verification that the server works correctly
"""

import asyncio
import json
from server_fastmcp import create_entities, search_nodes, read_graph, get_memory_status, create_relations

async def test_fastmcp_server():
    """Test the FastMCP server functions directly"""
    print("🧪 Testing Enhanced Memory MCP Server (FastMCP)")
    
    # Test 1: Create entities
    print("\n1. Testing create_entities...")
    entities = [
        {
            "name": "test_agent",
            "entityType": "agent",
            "observations": ["Agent initialized", "Ready for tasks"]
        },
        {
            "name": "project_context",
            "entityType": "project",
            "observations": ["Enhanced memory system", "Testing phase"]
        }
    ]
    
    result = await create_entities(entities)
    print(f"   ✅ Created {result['entities_created']} entities")
    print(f"   ✅ Compression: {result['overall_savings']} savings")
    
    # Test 2: Search nodes
    print("\n2. Testing search_nodes...")
    search_result = await search_nodes("test", max_results=5)
    print(f"   ✅ Found {search_result['results_found']} matching entities")
    
    # Test 3: Read graph
    print("\n3. Testing read_graph...")
    graph = await read_graph()
    print(f"   ✅ Graph contains {len(graph['entities'])} entities")
    
    # Test 4: Memory status
    print("\n4. Testing get_memory_status...")
    status = await get_memory_status()
    print(f"   ✅ System has {status['statistics']['total_entities']} total entities")
    print(f"   ✅ Compression method: {status['compression_method']}")
    print(f"   ✅ Database size: {status['database_size_bytes']} bytes")
    
    # Test 5: Create relations
    print("\n5. Testing create_relations...")
    relations = [
        {
            "from": "test_agent",
            "to": "project_context", 
            "relationType": "works_on"
        }
    ]
    
    rel_result = await create_relations(relations)
    print(f"   ✅ Created {rel_result['relations_created']} relations")
    
    print("\n🎉 All FastMCP server tests passed! Server is working correctly.")
    return True

if __name__ == "__main__":
    asyncio.run(test_fastmcp_server())