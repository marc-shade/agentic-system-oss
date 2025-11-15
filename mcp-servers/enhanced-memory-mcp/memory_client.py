#!/usr/bin/env python3
"""
Memory Database Client - Unix Socket Client for concurrent access

Connects to memory-db service via Unix socket for lock-free concurrent access.
Allows multiple MCP servers and subagents to access memory simultaneously.
"""

import asyncio
import json
import socket
from pathlib import Path
from typing import Dict, List, Any, Optional


class MemoryClient:
    """Client for memory-db Unix socket service"""

    def __init__(self, socket_path: str = "/tmp/memory-db.sock"):
        self.socket_path = socket_path

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request to memory-db service and get response"""
        if params is None:
            params = {}

        request = {
            "method": method,
            "params": params
        }

        # Connect to Unix socket
        reader, writer = await asyncio.open_unix_connection(self.socket_path)

        try:
            # Send request
            request_data = json.dumps(request).encode()
            writer.write(request_data)
            await writer.drain()

            # Read response in chunks until EOF
            chunks = []
            while True:
                chunk = await reader.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                chunks.append(chunk)

            response_data = b''.join(chunks)
            response = json.loads(response_data.decode())

            return response

        finally:
            writer.close()
            await writer.wait_closed()

    def _send_request_sync(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous version for non-async contexts"""
        return asyncio.run(self._send_request(method, params))

    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create entities (async)"""
        return await self._send_request("create_entities", {"entities": entities})

    def create_entities_sync(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create entities (sync)"""
        return self._send_request_sync("create_entities", {"entities": entities})

    async def search_nodes(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search entities (async)"""
        return await self._send_request("search_nodes", {"query": query, "limit": limit})

    def search_nodes_sync(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search entities (sync)"""
        return self._send_request_sync("search_nodes", {"query": query, "limit": limit})

    async def get_memory_status(self) -> Dict[str, Any]:
        """Get memory status (async)"""
        return await self._send_request("get_memory_status")

    def get_memory_status_sync(self) -> Dict[str, Any]:
        """Get memory status (sync)"""
        return self._send_request_sync("get_memory_status")

    async def ping(self) -> Dict[str, Any]:
        """Ping server (async)"""
        return await self._send_request("ping")

    def ping_sync(self) -> Dict[str, Any]:
        """Ping server (sync)"""
        return self._send_request_sync("ping")


# Global client instance
_client: Optional[MemoryClient] = None


def get_client() -> MemoryClient:
    """Get or create global memory client"""
    global _client
    if _client is None:
        _client = MemoryClient()
    return _client


# Convenience functions for easy migration
def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create entities - synchronous wrapper"""
    client = get_client()
    return client.create_entities_sync(entities)


def search_nodes(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search entities - synchronous wrapper"""
    client = get_client()
    return client.search_nodes_sync(query, limit)


def get_memory_status() -> Dict[str, Any]:
    """Get memory status - synchronous wrapper"""
    client = get_client()
    return client.get_memory_status_sync()
