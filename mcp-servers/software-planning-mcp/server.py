#!/usr/bin/env python3
"""
FastMCP Wrapper: software-planning-mcp
Auto-generated wrapper for original implementation
"""

import sys
import asyncio
from pathlib import Path
from fastmcp import FastMCP

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Initialize FastMCP server
mcp = FastMCP("software-planning-mcp")

# Import original server logic (if possible)
try:
    import server_original as original_server
    HAS_ORIGINAL = True
except ImportError:
    HAS_ORIGINAL = False

@mcp.tool()
async def process(**kwargs):
    """Main processing tool"""
    if HAS_ORIGINAL and hasattr(original_server, 'main'):
        try:
            result = original_server.main()
            return {"result": result, "status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "error"}
    return {"message": "FastMCP wrapper for software-planning-mcp", "status": "operational"}

@mcp.tool() 
async def status(**kwargs):
    """Get server status"""
    return {
        "server": "software-planning-mcp",
        "framework": "FastMCP",
        "status": "operational",
        "original_available": HAS_ORIGINAL
    }

if __name__ == "__main__":
    mcp.run()
