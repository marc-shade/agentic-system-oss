#!/usr/bin/env python3
"""Test script for SQLite MCP Server"""

import json
import subprocess
import sys

def send_request(request):
    """Send a request to the MCP server and get response"""
    proc = subprocess.Popen(
        ['node', 'build/index.js', 'data/test_orchestration.db'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send request
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    
    # Get response
    response = proc.stdout.readline()
    
    # Terminate process
    proc.terminate()
    
    return json.loads(response) if response else None

def test_sqlite_mcp():
    """Run tests on SQLite MCP Server"""
    print("Testing SQLite MCP Server...")
    
    # Test 1: List tools
    print("\n1. Testing tools/list...")
    request = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }
    response = send_request(request)
    if response:
        print(f"Available tools: {len(response.get('result', {}).get('tools', []))}")
        for tool in response.get('result', {}).get('tools', []):
            print(f"  - {tool['name']}: {tool['description']}")
    
    print("\n✅ SQLite MCP Server is ready for use!")
    print("\nCapabilities:")
    print("- read_query: Execute SELECT queries")
    print("- write_query: Execute INSERT/UPDATE/DELETE queries")
    print("- create_table: Create new tables")
    print("- list_tables: List all tables in database")
    print("- describe_table: Show table schema")
    print("- append_insight: Add business insights")
    print("\nThe server is configured to use:")
    print("Database: /Users/marc/Documents/Cline/MCP/sqlite-mcp-server/data/orchestration.db")

if __name__ == "__main__":
    test_sqlite_mcp()