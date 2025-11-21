#!/usr/bin/env python3
"""
MCP Server Implementation for Enhanced Router
Production-ready server that integrates with Claude Desktop
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_mcp_router import EnhancedMCPRouter
from oauth_integration_layer import OAuthManager, integrate_oauth_with_router
from integrate_enhanced_router import MCPRouterIntegration, MCPRouterServer

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("Warning: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)

# FastMCP compatibility
try:
    from fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False


class EnhancedRouterMCPServer:
    """MCP Server for Enhanced Router"""

    def __init__(self):
        self.integration = MCPRouterIntegration()
        self.server = Server("enhanced-mcp-router")

        # Migrate legacy mappings on startup
        self.integration.migrate_legacy_mappings()

        # Setup handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools based on session context"""
            # For now, return a static tool list
            # In production, this would be dynamic based on session
            return [
                Tool(
                    name="route_request",
                    description="Route a request to optimal MCP tools with progressive discovery",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task": {
                                "type": "string",
                                "description": "Task description to route"
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier for context"
                            },
                            "requirements": {
                                "type": "object",
                                "description": "Optional requirements"
                            }
                        },
                        "required": ["task"]
                    }
                ),
                Tool(
                    name="get_session_summary",
                    description="Get progress summary for a session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                Tool(
                    name="record_execution",
                    description="Record tool execution result",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session identifier"
                            },
                            "tool": {
                                "type": "string",
                                "description": "Tool name"
                            },
                            "success": {
                                "type": "boolean",
                                "description": "Whether execution was successful"
                            }
                        },
                        "required": ["session_id", "tool", "success"]
                    }
                ),
                Tool(
                    name="check_oauth_status",
                    description="Check OAuth authentication status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "provider": {
                                "type": "string",
                                "description": "OAuth provider name"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_integration_status",
                    description="Get current integration status",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list:
            """Handle tool calls"""

            if name == "route_request":
                # Route request through enhanced router
                result = await self.integration.route_request({
                    "session_id": arguments.get("session_id", "default"),
                    "task": arguments.get("task", ""),
                    "requirements": arguments.get("requirements", {}),
                    "method": "tools.route"
                })

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            elif name == "get_session_summary":
                # Get session summary
                session_id = arguments.get("session_id", "default")
                summary = self.integration.enhanced_router.get_session_summary(session_id)

                return [TextContent(
                    type="text",
                    text=json.dumps(summary, indent=2)
                )]

            elif name == "record_execution":
                # Record execution result
                self.integration.record_execution(
                    arguments.get("session_id"),
                    arguments.get("tool"),
                    arguments.get("success", False)
                )

                return [TextContent(
                    type="text",
                    text="Execution recorded successfully"
                )]

            elif name == "check_oauth_status":
                # Check OAuth status
                provider = arguments.get("provider")
                if provider:
                    status = {
                        "provider": provider,
                        "authenticated": self.integration.oauth_manager.is_authenticated(provider)
                    }
                else:
                    status = {
                        "authenticated_providers": self.integration.oauth_manager.get_authenticated_providers()
                    }

                return [TextContent(
                    type="text",
                    text=json.dumps(status, indent=2)
                )]

            elif name == "get_integration_status":
                # Get integration status
                status = self.integration.get_integration_status()

                return [TextContent(
                    type="text",
                    text=json.dumps(status, indent=2)
                )]

            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]

    async def run(self):
        """Run the MCP server"""
        from mcp.server.models import ServerCapabilities

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="enhanced-mcp-router",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools={}
                    )
                )
            )


def create_fastmcp_server():
    """Create FastMCP compatible server"""
    if not HAS_FASTMCP:
        return None

    mcp = FastMCP("enhanced-mcp-router")
    integration = MCPRouterIntegration()
    integration.migrate_legacy_mappings()

    @mcp.tool()
    async def route_request(task: str, session_id: str = "default",
                           requirements: Optional[Dict] = None) -> Dict[str, Any]:
        """Route a request to optimal MCP tools"""
        result = await integration.route_request({
            "session_id": session_id,
            "task": task,
            "requirements": requirements or {},
            "method": "tools.route"
        })
        return result

    @mcp.tool()
    async def get_session_summary(session_id: str = "default") -> Dict[str, Any]:
        """Get session progress summary"""
        return integration.enhanced_router.get_session_summary(session_id)

    @mcp.tool()
    async def record_execution(session_id: str, tool: str, success: bool) -> str:
        """Record tool execution result"""
        integration.record_execution(session_id, tool, success)
        return "Execution recorded successfully"

    @mcp.tool()
    async def check_oauth_status(provider: Optional[str] = None) -> Dict[str, Any]:
        """Check OAuth authentication status"""
        if provider:
            return {
                "provider": provider,
                "authenticated": integration.oauth_manager.is_authenticated(provider)
            }
        else:
            return {
                "authenticated_providers": integration.oauth_manager.get_authenticated_providers()
            }

    @mcp.tool()
    async def get_integration_status() -> Dict[str, Any]:
        """Get current integration status"""
        return integration.get_integration_status()

    return mcp


async def main():
    """Main entry point"""
    mode = os.getenv("ROUTER_MODE", "enhanced")

    if mode == "fastmcp" and HAS_FASTMCP:
        # Run as FastMCP server
        server = create_fastmcp_server()
        if server:
            server.run()
    elif HAS_MCP:
        # Run as standard MCP server
        server = EnhancedRouterMCPServer()
        await server.run()
    else:
        # Fallback mode
        print("No MCP framework available. Running in test mode...", file=sys.stderr)

        # Test the integration
        integration = MCPRouterIntegration()
        integration.migrate_legacy_mappings()

        test_result = await integration.route_request({
            "session_id": "test",
            "task": "Test routing",
            "method": "tools.route"
        })

        print(json.dumps(test_result, indent=2))


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("GITHUB_CLIENT_ID"):
        print("Note: OAuth providers not configured. Set GITHUB_CLIENT_ID, etc. for OAuth support",
              file=sys.stderr)

    # Run server
    asyncio.run(main())