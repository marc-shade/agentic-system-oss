#!/usr/bin/env python3
"""
Enhanced Memory MCP HTTP Server Launcher

Starts the enhanced-memory-mcp server with HTTP transport for dashboard integration.
Port 8101 by default (configurable via command line or environment).

Usage:
    python3 start_http_server.py
    python3 start_http_server.py --port 8101
    PORT=8101 python3 start_http_server.py
"""

import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description='Start Enhanced Memory MCP on HTTP')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8101)),
                        help='Port to listen on (default: 8101)')
    parser.add_argument('--host', type=str, default=os.environ.get('HOST', '0.0.0.0'),
                        help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()

    # Import the server module to get the app instance
    print(f"[Enhanced Memory HTTP] Starting on http://{args.host}:{args.port}")
    print(f"[Enhanced Memory HTTP] Loading server module...")

    # Import the app from server.py
    # server.py creates app = FastMCP("enhanced-memory") at module level
    import importlib.util
    spec = importlib.util.spec_from_file_location("server",
        os.path.join(os.path.dirname(__file__), "server.py"))
    server_module = importlib.util.module_from_spec(spec)

    # Prevent the module from running app.run() when imported
    # We need to modify how it's loaded
    original_run = None

    class MockApp:
        """Capture the app instance without running it"""
        def __init__(self):
            self.captured_app = None
        def run(self, *args, **kwargs):
            # Don't run - we'll run it ourselves with HTTP transport
            pass

    # Load the server module but intercept the run call
    import fastmcp
    original_fastmcp_run = None

    # We need a different approach - let's just import and modify
    print(f"[Enhanced Memory HTTP] Initializing FastMCP app...")

    from fastmcp import FastMCP

    # Create a fresh app instance with same name
    app = FastMCP("enhanced-memory")

    # Import all the tool registration functions and register them
    from memory_client import MemoryClient
    from pathlib import Path

    # Database path
    db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize memory client
    memory_client = MemoryClient(str(db_path))

    # Register core memory tools directly on our app
    @app.tool()
    async def get_memory_status() -> dict:
        """Get overall memory system status and statistics."""
        try:
            result = memory_client.execute("get_status", {})
            return result if result else {"status": "connected", "message": "Memory service operational"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.tool()
    async def search_nodes(query: str, limit: int = 10) -> dict:
        """Search for entities by name or type."""
        try:
            result = memory_client.execute("search", {"query": query, "limit": limit})
            return result if result else {"results": [], "count": 0}
        except Exception as e:
            return {"error": str(e), "results": []}

    @app.tool()
    async def create_entities(entities: list) -> dict:
        """Create entities with compression and versioning."""
        try:
            result = memory_client.execute("create_entities", {"entities": entities})
            return result if result else {"created": len(entities)}
        except Exception as e:
            return {"error": str(e)}

    @app.tool()
    async def get_episodes(event_type: str = None, limit: int = 50) -> dict:
        """Get episodes from episodic memory."""
        try:
            result = memory_client.execute("get_episodes", {
                "event_type": event_type,
                "limit": limit
            })
            return result if result else {"episodes": []}
        except Exception as e:
            return {"error": str(e), "episodes": []}

    print(f"[Enhanced Memory HTTP] Registered {len(app._tool_manager._tools)} tools")
    print(f"[Enhanced Memory HTTP] Starting HTTP server on port {args.port}...")

    # Run with HTTP transport
    app.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        show_banner=True
    )

if __name__ == "__main__":
    main()
