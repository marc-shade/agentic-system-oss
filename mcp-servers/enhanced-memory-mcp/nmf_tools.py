#!/usr/bin/env python3
"""
Neural Memory Fabric MCP Tools
Exposes NMF functionality as MCP tools
"""

import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

from neural_memory_fabric import get_nmf, RetrievalMode

logger = logging.getLogger("nmf-tools")


def register_nmf_tools(app: FastMCP):
    """Register all NMF tools with the FastMCP app"""

    @app.tool()
    async def nmf_remember(
        content: str,
        agent_id: str = "default",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Store a new memory in the Neural Memory Fabric.

        Args:
            content: The memory content to store
            agent_id: The agent ID (default: "default")
            tags: Optional list of tags
            metadata: Optional additional metadata

        Returns:
            Result dictionary with memory_id and status
        """
        nmf = await get_nmf()

        # Merge tags into metadata
        if metadata is None:
            metadata = {}
        if tags:
            metadata['tags'] = tags

        result = await nmf.remember(content, metadata, agent_id)
        return result

    @app.tool()
    async def nmf_recall(
        query: str,
        mode: str = "hybrid",
        agent_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories from the Neural Memory Fabric.

        Args:
            query: Search query string
            mode: Retrieval mode - "semantic", "graph", "temporal", or "hybrid"
            agent_id: Optional filter by agent ID
            limit: Maximum number of results (default: 10)

        Returns:
            List of memory dictionaries
        """
        nmf = await get_nmf()
        results = await nmf.recall(query, mode, agent_id, limit)
        return results

    @app.tool()
    async def nmf_open_block(
        agent_id: str,
        block_name: str
    ) -> Dict[str, Any]:
        """
        Load a memory block into context (Letta-style).

        Args:
            agent_id: The agent ID
            block_name: Name of the memory block (e.g., "identity", "context", "knowledge")

        Returns:
            Memory block content and metadata
        """
        nmf = await get_nmf()
        result = await nmf.open_block(agent_id, block_name)
        return result

    @app.tool()
    async def nmf_edit_block(
        agent_id: str,
        block_name: str,
        new_value: str
    ) -> Dict[str, Any]:
        """
        Edit a memory block (Letta-style).

        Args:
            agent_id: The agent ID
            block_name: Name of the memory block
            new_value: New content for the block

        Returns:
            Update confirmation
        """
        nmf = await get_nmf()
        result = await nmf.edit_block(agent_id, block_name, new_value)
        return result

    @app.tool()
    async def nmf_close_block(
        agent_id: str,
        block_name: str
    ) -> Dict[str, Any]:
        """
        Close a memory block (remove from active context).

        Args:
            agent_id: The agent ID
            block_name: Name of the memory block

        Returns:
            Confirmation
        """
        # For now, this is a no-op (blocks are automatically managed)
        # In future: could implement LRU eviction
        return {
            'success': True,
            'message': f'Block {block_name} closed for agent {agent_id}'
        }

    @app.tool()
    async def nmf_get_status() -> Dict[str, Any]:
        """
        Get Neural Memory Fabric system status.

        Returns:
            System statistics and health information
        """
        nmf = await get_nmf()
        status = await nmf.get_status()
        return status

    @app.tool()
    async def nmf_list_blocks(agent_id: str) -> List[Dict[str, Any]]:
        """
        List all memory blocks for an agent.

        Args:
            agent_id: The agent ID

        Returns:
            List of memory blocks
        """
        nmf = await get_nmf()

        # Query SQLite for agent's blocks
        cursor = nmf.sqlite_conn.cursor()
        cursor.execute('''
            SELECT block_name, block_value, version, last_updated, persistence
            FROM nmf_memory_blocks
            WHERE agent_id = ?
        ''', (agent_id,))

        blocks = []
        for row in cursor.fetchall():
            blocks.append({
                'block_name': row[0],
                'value_preview': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                'version': row[2],
                'last_updated': row[3],
                'persistence': row[4]
            })

        return blocks

    logger.info("NMF tools registered")
