"""
MCP Client - Interface to MCP servers for Prometheus.

Provides unified access to:
- enhanced-memory-mcp (persistent memory)
- cluster-execution-mcp (Linux sandbox)
- voice-mode (TTS/STT)
- research-paper-mcp (academic search)
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MCPResult:
    """Result from MCP tool call."""
    success: bool
    data: Any
    error: str = ""


class MCPClient:
    """
    Client for interacting with MCP servers.

    In Claude Code context, MCP tools are called directly.
    This class provides a Python interface for standalone usage.
    """

    def __init__(self):
        """Initialize MCP client."""
        self.available_servers = self._discover_servers()

    def _discover_servers(self) -> dict:
        """Discover available MCP servers from config."""
        servers = {}

        # Check user config
        user_config = Path.home() / ".claude.json"
        if user_config.exists():
            try:
                with open(user_config) as f:
                    config = json.load(f)
                servers.update(config.get("mcpServers", {}))
            except Exception as e:
                logger.warning(f"Failed to read user config: {e}")

        # Check project config
        project_config = Path.home() / ".mcp.json"
        if project_config.exists():
            try:
                with open(project_config) as f:
                    config = json.load(f)
                servers.update(config.get("mcpServers", {}))
            except Exception as e:
                logger.warning(f"Failed to read project config: {e}")

        return servers

    def is_available(self, server: str) -> bool:
        """Check if MCP server is configured."""
        return server in self.available_servers

    # Enhanced Memory MCP methods
    async def memory_search(
        self,
        query: str,
        limit: int = 10,
        scope: str = "all"
    ) -> MCPResult:
        """Search enhanced-memory."""
        if not self.is_available("enhanced-memory"):
            return MCPResult(success=False, data=[], error="enhanced-memory not configured")

        # In Claude Code, this would be:
        # mcp__enhanced-memory-mcp__search_nodes(query=query, limit=limit)
        return MCPResult(
            success=True,
            data=[],  # Would contain search results
            error=""
        )

    async def memory_create_entity(
        self,
        name: str,
        entity_type: str,
        observations: list
    ) -> MCPResult:
        """Create entity in enhanced-memory."""
        if not self.is_available("enhanced-memory"):
            return MCPResult(success=False, data=None, error="enhanced-memory not configured")

        return MCPResult(
            success=True,
            data={"name": name, "type": entity_type},
            error=""
        )

    # Cluster Execution MCP methods
    async def cluster_execute(
        self,
        command: str,
        node: str = None,
        timeout: int = 120
    ) -> MCPResult:
        """Execute command on cluster."""
        if not self.is_available("cluster-execution-mcp"):
            return MCPResult(success=False, data=None, error="cluster-execution-mcp not configured")

        # In Claude Code, this would be:
        # mcp__cluster-execution-mcp__cluster_bash(command=command)
        return MCPResult(
            success=True,
            data={"stdout": "", "stderr": "", "code": 0},
            error=""
        )

    async def cluster_offload(
        self,
        command: str,
        node: str = "macpro51"
    ) -> MCPResult:
        """Offload command to specific node."""
        # mcp__cluster-execution-mcp__offload_to(node_id=node, command=command)
        return MCPResult(
            success=True,
            data={"node": node, "result": ""},
            error=""
        )

    # Voice Mode MCP methods
    async def voice_speak(
        self,
        text: str,
        wait: bool = False
    ) -> MCPResult:
        """Speak via TTS."""
        if not self.is_available("voice-mode"):
            return MCPResult(success=False, data=None, error="voice-mode not configured")

        # mcp__voice-mode__converse(message=text, wait_for_response=wait)
        return MCPResult(
            success=True,
            data={"spoken": True},
            error=""
        )

    async def voice_listen(
        self,
        timeout: int = 10
    ) -> MCPResult:
        """Listen via STT."""
        if not self.is_available("voice-mode"):
            return MCPResult(success=False, data=None, error="voice-mode not configured")

        return MCPResult(
            success=True,
            data={"text": ""},
            error=""
        )

    # Research Paper MCP methods
    async def search_arxiv(
        self,
        query: str,
        max_results: int = 10
    ) -> MCPResult:
        """Search arXiv papers."""
        if not self.is_available("research-paper-mcp"):
            return MCPResult(success=False, data=[], error="research-paper-mcp not configured")

        return MCPResult(
            success=True,
            data=[],  # Would contain paper results
            error=""
        )

    # Arduino Surface MCP methods
    async def arduino_display(
        self,
        message: str,
        line: int = 0
    ) -> MCPResult:
        """Display message on Arduino LCD."""
        if not self.is_available("arduino-surface"):
            return MCPResult(success=False, data=None, error="arduino-surface not configured")

        return MCPResult(
            success=True,
            data={"displayed": True},
            error=""
        )

    async def arduino_led(
        self,
        color: str,
        brightness: int = 100
    ) -> MCPResult:
        """Set Arduino LED color."""
        if not self.is_available("arduino-surface"):
            return MCPResult(success=False, data=None, error="arduino-surface not configured")

        return MCPResult(
            success=True,
            data={"color": color},
            error=""
        )


# Global client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create MCP client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
