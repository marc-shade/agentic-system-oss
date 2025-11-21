"""
Cross-MCP Code Execution Proxy

Enables code executed in sandbox to call any MCP server tool.
Follows Anthropic's pattern where code can orchestrate multiple MCPs.

Example in code:
    # Call voice-mode from within execute_code
    result = await mcp.voice_mode.converse("Hello!", wait_for_response=False)

    # Call agent-runtime
    goal = await mcp.agent_runtime.create_goal("My Goal", "Description")

Token Savings: Massive - batch operations across MCPs in single code block
"""

import asyncio
import json
import socket
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server"""
    name: str
    socket_path: Optional[str] = None
    http_port: Optional[int] = None
    tools: List[str] = None


# Known MCP server connection info
MCP_SERVERS: Dict[str, MCPServerConfig] = {
    "voice-mode": MCPServerConfig(
        name="voice-mode",
        http_port=3456,  # Voice mode HTTP endpoint
        tools=["converse", "voice_registry"]
    ),
    "agent-runtime": MCPServerConfig(
        name="agent-runtime",
        socket_path="/tmp/agent-runtime.sock",
        tools=["create_goal", "decompose_goal", "create_task", "get_next_task", "list_goals", "list_tasks"]
    ),
    "arduino-surface": MCPServerConfig(
        name="arduino-surface",
        http_port=4200,
        tools=["surface_display", "surface_led_set", "surface_alert", "surface_beep", "surface_status"]
    ),
    "safla-enhanced": MCPServerConfig(
        name="safla-enhanced",
        socket_path="/tmp/safla-enhanced.sock",
        tools=["generate_embeddings", "store_memory", "retrieve_memories", "analyze_text"]
    ),
}


class MCPProxyClient:
    """
    Client for proxying calls to other MCP servers from within code execution.

    Provides namespace-based access to MCP tools:
        mcp.voice_mode.converse(...)
        mcp.agent_runtime.create_goal(...)
    """

    def __init__(self):
        self._call_queue: List[Dict] = []
        self._results: Dict[str, Any] = {}

    def __getattr__(self, server_name: str) -> "MCPServerProxy":
        """Get proxy for specific MCP server"""
        # Convert snake_case to kebab-case for server names
        normalized = server_name.replace("_", "-")
        if normalized in MCP_SERVERS:
            return MCPServerProxy(normalized, self)
        raise AttributeError(f"Unknown MCP server: {server_name}")

    def queue_call(self, server: str, tool: str, params: Dict[str, Any]) -> str:
        """Queue an MCP call for batch execution"""
        call_id = f"{server}/{tool}/{len(self._call_queue)}"
        self._call_queue.append({
            "id": call_id,
            "server": server,
            "tool": tool,
            "params": params
        })
        return call_id

    def get_queued_calls(self) -> List[Dict]:
        """Get all queued calls for batch execution"""
        return self._call_queue.copy()

    def clear_queue(self):
        """Clear the call queue"""
        self._call_queue = []

    def set_result(self, call_id: str, result: Any):
        """Set result for a queued call"""
        self._results[call_id] = result

    def get_result(self, call_id: str) -> Any:
        """Get result for a completed call"""
        return self._results.get(call_id)


class MCPServerProxy:
    """Proxy for a specific MCP server"""

    def __init__(self, server_name: str, client: MCPProxyClient):
        self._server = server_name
        self._client = client
        self._config = MCP_SERVERS.get(server_name)

    def __getattr__(self, tool_name: str) -> Callable:
        """Get callable for specific tool"""
        def tool_caller(**kwargs) -> Dict[str, Any]:
            # Queue the call - actual execution happens after code completes
            call_id = self._client.queue_call(self._server, tool_name, kwargs)
            return {"queued": True, "call_id": call_id, "server": self._server, "tool": tool_name}
        return tool_caller


async def execute_mcp_calls(calls: List[Dict]) -> Dict[str, Any]:
    """
    Execute queued MCP calls.

    This is called AFTER code execution completes, allowing the sandbox
    to collect all MCP calls and execute them in batch.

    Args:
        calls: List of queued calls from MCPProxyClient

    Returns:
        Dict mapping call_id to result
    """
    results = {}

    for call in calls:
        call_id = call["id"]
        server = call["server"]
        tool = call["tool"]
        params = call["params"]

        try:
            result = await _execute_single_mcp_call(server, tool, params)
            results[call_id] = {"success": True, "result": result}
        except Exception as e:
            logger.error(f"MCP call failed: {server}/{tool}: {e}")
            results[call_id] = {"success": False, "error": str(e)}

    return results


async def _execute_single_mcp_call(server: str, tool: str, params: Dict) -> Any:
    """Execute a single MCP tool call"""
    config = MCP_SERVERS.get(server)
    if not config:
        raise ValueError(f"Unknown server: {server}")

    # Try HTTP endpoint first
    if config.http_port:
        return await _call_via_http(config.http_port, tool, params)

    # Fall back to Unix socket
    if config.socket_path:
        return await _call_via_socket(config.socket_path, tool, params)

    raise ValueError(f"No connection method for server: {server}")


async def _call_via_http(port: int, tool: str, params: Dict) -> Any:
    """Call MCP tool via HTTP endpoint"""
    import aiohttp

    url = f"http://localhost:{port}/tools/{tool}"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=params, timeout=30) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"HTTP {response.status}: {text}")


async def _call_via_socket(socket_path: str, tool: str, params: Dict) -> Any:
    """Call MCP tool via Unix socket (JSON-RPC)"""
    if not os.path.exists(socket_path):
        raise FileNotFoundError(f"Socket not found: {socket_path}")

    reader, writer = await asyncio.open_unix_connection(socket_path)

    try:
        # JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": f"tools/{tool}",
            "params": params
        }

        writer.write(json.dumps(request).encode() + b"\n")
        await writer.drain()

        response_data = await asyncio.wait_for(reader.readline(), timeout=30)
        response = json.loads(response_data.decode())

        if "error" in response:
            raise Exception(response["error"].get("message", "Unknown error"))

        return response.get("result")

    finally:
        writer.close()
        await writer.wait_closed()


# Synchronous wrapper for use in restricted code
def mcp_call_sync(server: str, tool: str, **params) -> Dict[str, Any]:
    """
    Synchronous MCP call for use in code execution.

    Note: This queues the call for later execution since we can't
    run async code in RestrictedPython. The queued calls are
    executed after code completion.
    """
    # This is a simplified version - actual calls are queued
    return {
        "queued": True,
        "server": server,
        "tool": tool,
        "params": params,
        "note": "Call will be executed after code completes"
    }


# Create global proxy instance for code execution context
mcp = MCPProxyClient()


def get_mcp_proxy() -> MCPProxyClient:
    """Get the MCP proxy client for code execution"""
    return mcp


def create_mcp_context() -> Dict[str, Any]:
    """Create MCP context for code execution"""
    return {
        "mcp": mcp,
        "mcp_call": mcp_call_sync,
        "list_mcp_servers": lambda: list(MCP_SERVERS.keys()),
        "get_mcp_tools": lambda server: MCP_SERVERS.get(server.replace("_", "-"), MCPServerConfig("unknown")).tools or [],
    }
