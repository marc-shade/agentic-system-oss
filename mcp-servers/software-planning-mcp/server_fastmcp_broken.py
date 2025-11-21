#!/usr/bin/env python3
"""
Software Planning MCP Server - Simple entry point
"""
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Import FastMCP directly
from fastmcp import FastMCP
from tools import project_tools

# Create simple server with just project tools
mcp = FastMCP("software-planning-mcp")

# Register basic project tools
mcp.tool()(project_tools.create_project)
mcp.tool()(project_tools.breakdown_project)
mcp.tool()(project_tools.create_task)
mcp.tool()(project_tools.define_approaches)
mcp.tool()(project_tools.list_projects)
mcp.tool()(project_tools.get_status)
mcp.tool()(project_tools.suggest_team)
mcp.tool()(project_tools.gen_exec_plan)

if __name__ == "__main__":
    mcp.run()