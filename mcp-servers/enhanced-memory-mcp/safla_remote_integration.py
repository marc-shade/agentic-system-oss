#!/usr/bin/env python3
"""
SAFLA Remote Integration Module
===============================

Provides access to the remote SAFLA instance at https://safla.fly.dev.
This module ports the safla-mcp server tools into enhanced-memory-mcp,
enabling consolidation of MCP servers.

Remote SAFLA provides:
- High-performance embeddings (1.75M+ ops/sec)
- Hybrid memory system (episodic, semantic, procedural)
- Performance metrics and analytics

Tools:
- safla_generate_embeddings: Generate embeddings via remote SAFLA engine
- safla_store_memory: Store in remote SAFLA hybrid memory
- safla_retrieve_memories: Search remote SAFLA memory
- safla_get_performance: Get remote SAFLA performance metrics
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("safla-remote-integration")

# Configuration
SAFLA_URL = os.environ.get("SAFLA_REMOTE_URL", "https://safla.fly.dev")


class SAFLARemoteClient:
    """Client for remote SAFLA API at https://safla.fly.dev"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or SAFLA_URL
        self._session = None

    async def _get_session(self):
        """Get or create aiohttp session"""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None

    async def _call_api(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call the remote SAFLA API"""
        import aiohttp

        session = await self._get_session()
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"safla_{method}",
            "method": method,
            "params": params
        }

        try:
            async with session.post(
                f"{self.base_url}/api/safla",
                json=mcp_request,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "data": result.get("result", result)}
                else:
                    return {"success": False, "error": f"API error: {response.status}"}
        except Exception as e:
            logger.error(f"SAFLA API call failed: {e}")
            return {"success": False, "error": str(e)}

    async def generate_embeddings(self, texts: List[str]) -> Dict[str, Any]:
        """Generate embeddings using SAFLA's extreme-optimized engine (1.75M+ ops/sec)"""
        return await self._call_api("generate_embeddings", {"texts": texts})

    async def store_memory(
        self,
        content: str,
        memory_type: str = "episodic"
    ) -> Dict[str, Any]:
        """Store information in SAFLA's hybrid memory system"""
        return await self._call_api("store_memory", {
            "content": content,
            "memory_type": memory_type
        })

    async def retrieve_memories(
        self,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search and retrieve from SAFLA's memory system"""
        return await self._call_api("retrieve_memories", {
            "query": query,
            "limit": limit
        })

    async def get_performance(self) -> Dict[str, Any]:
        """Get SAFLA performance metrics"""
        return await self._call_api("get_performance_metrics", {})


# Singleton instance
_safla_client: Optional[SAFLARemoteClient] = None


def get_safla_remote_client() -> SAFLARemoteClient:
    """Get or create the SAFLA remote client singleton"""
    global _safla_client
    if _safla_client is None:
        _safla_client = SAFLARemoteClient()
    return _safla_client


def register_safla_remote_tools(app):
    """
    Register SAFLA remote API tools with the FastMCP app.

    These tools access the remote SAFLA instance at https://safla.fly.dev
    for high-performance embeddings and hybrid memory operations.

    Args:
        app: FastMCP application instance
    """
    client = get_safla_remote_client()

    @app.tool()
    async def safla_generate_embeddings(texts: List[str]) -> Dict[str, Any]:
        """
        Generate embeddings using SAFLA's extreme-optimized engine (1.75M+ ops/sec).

        Uses remote SAFLA instance for high-throughput embedding generation.

        Args:
            texts: List of texts to embed

        Returns:
            Embeddings result with vectors and performance metrics
        """
        result = await client.generate_embeddings(texts)

        if result.get("success"):
            return {
                "success": True,
                "embeddings": result.get("data", {}),
                "text_count": len(texts),
                "source": "safla_remote"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "source": "safla_remote"
            }

    @app.tool()
    async def safla_store_memory(
        content: str,
        memory_type: str = "episodic"
    ) -> Dict[str, Any]:
        """
        Store information in SAFLA's hybrid memory system.

        Memory types:
        - episodic: Time-bound experiences and events
        - semantic: Abstract concepts and knowledge
        - procedural: Skills and procedures

        Args:
            content: Content to store
            memory_type: Type of memory (episodic, semantic, procedural)

        Returns:
            Storage result with confirmation and memory ID
        """
        if memory_type not in ["episodic", "semantic", "procedural"]:
            return {
                "success": False,
                "error": f"Invalid memory_type: {memory_type}. Use: episodic, semantic, procedural"
            }

        result = await client.store_memory(content, memory_type)

        if result.get("success"):
            return {
                "success": True,
                "stored": True,
                "memory_type": memory_type,
                "data": result.get("data", {}),
                "source": "safla_remote"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "source": "safla_remote"
            }

    @app.tool()
    async def safla_retrieve_memories(
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search and retrieve from SAFLA's memory system.

        Uses semantic search to find relevant memories.

        Args:
            query: Search query
            limit: Maximum number of results (default: 5)

        Returns:
            List of matching memories with relevance scores
        """
        result = await client.retrieve_memories(query, limit)

        if result.get("success"):
            return {
                "success": True,
                "query": query,
                "limit": limit,
                "results": result.get("data", {}),
                "source": "safla_remote"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "source": "safla_remote"
            }

    @app.tool()
    async def safla_get_performance() -> Dict[str, Any]:
        """
        Get SAFLA performance metrics.

        Returns metrics about embedding throughput, memory operations,
        and system performance.

        Returns:
            Performance metrics including ops/sec, memory usage, latency
        """
        result = await client.get_performance()

        if result.get("success"):
            return {
                "success": True,
                "metrics": result.get("data", {}),
                "source": "safla_remote"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "source": "safla_remote"
            }

    logger.info("✅ SAFLA remote tools registered (4 tools: generate_embeddings, store_memory, retrieve_memories, get_performance)")

    return client  # Return client for cleanup if needed
