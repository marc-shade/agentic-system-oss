import asyncio
import sys
from pathlib import Path
import json

# Add mcp to path (assuming it's installed in the environment, but just in case)
# sys.path.insert(0, ...) 

# We'll test by importing the server module directly and calling the handlers
# This avoids the complexity of setting up stdio communication in a simple test script
sys.path.insert(0, str(Path("/home/marc/agentic-system/mcp-servers/security-auditor-mcp")))

from server import handle_list_tools, handle_call_tool

async def main():
    print("Testing Security Auditor MCP Server...")
    
    # 1. List Tools
    print("\n1. Listing Tools...")
    tools = await handle_list_tools()
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # 2. Test validate_change
    print("\n2. Testing validate_change...")
    result = await handle_call_tool("validate_change", {
        "code_before": "print('hello')",
        "code_after": "print('hello world')"
    })
    print(f"  Result: {result[0].text}")
    
    # 3. Test generate_patch (mock)
    print("\n3. Testing generate_patch...")
    result = await handle_call_tool("generate_patch", {
        "description": "SQL Injection",
        "file_path": "db.py",
        "suggested_fix": "Use parameterized queries"
    })
    print(f"  Result: {result[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
