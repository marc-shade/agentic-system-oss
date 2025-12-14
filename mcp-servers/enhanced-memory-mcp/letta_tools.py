#!/usr/bin/env python3
"""
Letta Memory Block Tools for FastMCP

Registers MCP tools for Letta-style memory blocks that agents can use to:
- Create and manage memory blocks (identity, human, task, learnings)
- Append and replace content (core_memory_append, core_memory_replace)
- Render blocks for context window insertion
- Create and attach shared blocks for multi-agent coordination
"""

import logging
import os
from typing import Dict, List, Any
from letta_memory_blocks import MemoryBlockManager

logger = logging.getLogger(__name__)


def register_letta_tools(app, db_path):
    """Register all Letta memory block tools with FastMCP app"""

    # Initialize memory block manager
    manager = MemoryBlockManager(db_path)
    logger.info(f"📦 Letta MemoryBlockManager initialized at {db_path}")

    # Tool 1: Create Memory Block
    @app.tool()
    async def create_memory_block(
        agent_id: str,
        label: str,
        description: str,
        initial_value: str = "",
        limit: int = 2000,
        read_only: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new Letta-style memory block for in-context agent memory.

        Memory blocks are self-editing, limited-size memory units that stay in the
        agent's context window. They are DIFFERENT from entities:
        - Blocks: In-context, self-editable, limited size (like Letta)
        - Entities: Long-term, consolidated, unlimited (enhanced-memory)

        Args:
            agent_id: Agent identifier (e.g., "my_agent", "default")
            label: Block identifier (e.g., "identity", "human", "task", "learnings")
            description: What this block contains
            initial_value: Starting content (optional)
            limit: Character limit (default 2000)
            read_only: Whether block can be edited (default False)

        Returns:
            Result with block_id and creation details

        Example:
            create_memory_block(
                agent_id="my_agent",
                label="identity",
                description="My identity and capabilities",
                initial_value="I am a cluster node...",
                limit=2000
            )
        """
        return manager.create_block(
            agent_id=agent_id,
            label=label,
            description=description,
            initial_value=initial_value,
            limit=limit,
            read_only=read_only
        )

    # Tool 2: Core Memory Append (Letta-style)
    @app.tool()
    async def core_memory_append(
        agent_id: str,
        label: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Append content to a memory block (like Letta's core_memory_append).

        This is the primary way agents edit their own memory blocks.
        Appended content is added to the end of the block with a newline.

        Args:
            agent_id: Agent identifier
            label: Block label to append to (e.g., "task", "learnings")
            content: Content to append

        Returns:
            Result with success status and character counts

        Example:
            core_memory_append(
                agent_id="my_agent",
                label="task",
                content="Currently implementing Letta memory blocks - Phase 1 complete"
            )
        """
        return manager.append_to_block(agent_id, label, content)

    # Tool 3: Core Memory Replace (Letta-style)
    @app.tool()
    async def core_memory_replace(
        agent_id: str,
        label: str,
        old_content: str,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Replace content in a memory block (like Letta's core_memory_replace).

        Use this to edit or delete content in blocks. To delete, use empty string
        for new_content. The old_content must be an exact match.

        Args:
            agent_id: Agent identifier
            label: Block label to edit
            old_content: Exact text to find and replace
            new_content: New text to replace with (empty string to delete)

        Returns:
            Result with success status and character counts

        Example:
            core_memory_replace(
                agent_id="my_agent",
                label="identity",
                old_content="Builder Node",
                new_content="Builder Node with Letta integration"
            )
        """
        return manager.replace_in_block(agent_id, label, old_content, new_content)

    # Tool 4: List Memory Blocks
    @app.tool()
    async def list_memory_blocks(agent_id: str) -> Dict[str, Any]:
        """
        List all memory blocks for an agent.

        Returns detailed information about each block including current size,
        character limits, and timestamps.

        Args:
            agent_id: Agent identifier

        Returns:
            List of blocks with metadata

        Example:
            list_memory_blocks(agent_id="my_agent")
        """
        blocks = manager.list_blocks(agent_id)
        return {
            "success": True,
            "agent_id": agent_id,
            "count": len(blocks),
            "blocks": blocks
        }

    # Tool 5: Get Memory Block
    @app.tool()
    async def get_memory_block(agent_id: str, label: str) -> Dict[str, Any]:
        """
        Get a specific memory block's content and metadata.

        Args:
            agent_id: Agent identifier
            label: Block label to retrieve

        Returns:
            Block details or error if not found

        Example:
            get_memory_block(agent_id="my_agent", label="identity")
        """
        block = manager.get_block(agent_id, label)

        if not block:
            return {
                "success": False,
                "error": f"Block '{label}' not found for agent '{agent_id}'"
            }

        return {
            "success": True,
            "block": block.to_dict()
        }

    # Tool 6: Render Memory Blocks (for context window)
    @app.tool()
    async def render_memory_blocks(
        agent_id: str,
        use_line_numbers: bool = False
    ) -> Dict[str, Any]:
        """
        Render all memory blocks as XML for insertion into agent's context window.

        This generates Letta-style XML formatting that can be included in the
        agent's system prompt or context. Blocks are rendered with descriptions,
        metadata (character counts), and current values.

        Args:
            agent_id: Agent identifier
            use_line_numbers: Whether to add line numbers to block values (default False)

        Returns:
            XML-formatted memory blocks

        Example:
            render_memory_blocks(agent_id="my_agent", use_line_numbers=False)

        Output format:
        <memory_blocks>
        <identity>
        <description>My identity and capabilities</description>
        <metadata>
        - chars_current=429
        - chars_limit=2000
        </metadata>
        <value>
        I am a cluster node...
        </value>
        </identity>
        ...
        </memory_blocks>
        """
        xml = manager.render_blocks(agent_id, use_line_numbers)
        return {
            "success": True,
            "agent_id": agent_id,
            "xml": xml,
            "chars_total": len(xml)
        }

    # Tool 7: Create Default Blocks
    @app.tool()
    async def create_default_memory_blocks(
        agent_id: str,
        node_id: str = None
    ) -> Dict[str, Any]:
        """
        Create default memory blocks for a new agent.

        Creates standard blocks:
        - identity: Agent persona and capabilities
        - human: Information about the human user
        - task: Current work and goals
        - learnings: Recent insights (updated by sleeptime agent)

        Args:
            agent_id: Agent identifier
            node_id: Node identifier for identity block (default: auto-detect from hostname)

        Returns:
            Result with blocks created

        Example:
            create_default_memory_blocks(agent_id="my_agent", node_id="builder")
        """
        import socket
        if node_id is None:
            node_id = os.environ.get("NODE_ID", socket.gethostname())
        return manager.create_default_blocks(agent_id, node_id)

    # Tool 8: Create Shared Block (Multi-Agent)
    @app.tool()
    async def create_shared_memory_block(
        label: str,
        description: str,
        initial_value: str = "",
        limit: int = 5000
    ) -> Dict[str, Any]:
        """
        Create a shared memory block for multi-agent coordination.

        Shared blocks can be attached to multiple agents, enabling them to
        maintain shared context. When one agent updates a shared block, all
        attached agents see the change.

        Args:
            label: Block label (e.g., "cluster_context", "organization")
            description: What this shared block contains
            initial_value: Starting content (optional)
            limit: Character limit (default 5000, larger than personal blocks)

        Returns:
            Result with shared_block_id

        Example:
            create_shared_memory_block(
                label="cluster_context",
                description="Cluster-wide coordination state",
                initial_value="Active Goal: Integrate Letta memory blocks"
            )
        """
        return manager.create_shared_block(label, description, initial_value, limit)

    # Tool 9: Attach Shared Block to Agent
    @app.tool()
    async def attach_shared_block(
        agent_id: str,
        shared_block_id: int
    ) -> Dict[str, Any]:
        """
        Attach a shared memory block to an agent.

        Once attached, the agent can read and update the shared block.
        Changes are visible to all other agents with the same block attached.

        Args:
            agent_id: Agent to attach block to
            shared_block_id: ID of shared block to attach

        Returns:
            Result with attachment status

        Example:
            attach_shared_block(agent_id="my_agent", shared_block_id=1)
        """
        return manager.attach_shared_block(agent_id, shared_block_id)

    # Tool 10: Get Shared Block
    @app.tool()
    async def get_shared_memory_block(label: str) -> Dict[str, Any]:
        """
        Get a shared memory block by label.

        Args:
            label: Shared block label

        Returns:
            Block details or error if not found

        Example:
            get_shared_memory_block(label="cluster_context")
        """
        block = manager.get_shared_block(label)

        if not block:
            return {
                "success": False,
                "error": f"Shared block '{label}' not found"
            }

        return {
            "success": True,
            "block": block
        }

    # Tool 11: Update Shared Block
    @app.tool()
    async def update_shared_memory_block(
        label: str,
        new_value: str
    ) -> Dict[str, Any]:
        """
        Update a shared memory block's value.

        This update is visible to all agents with the block attached.

        Args:
            label: Shared block label
            new_value: New content for the block

        Returns:
            Result with success status

        Example:
            update_shared_memory_block(
                label="cluster_context",
                new_value="Active Goal: Phase 1 complete, moving to Phase 2..."
            )
        """
        return manager.update_shared_block(label, new_value)

    logger.info("✅ Letta Memory Block tools registered (11 tools)")
    logger.info("   - core_memory_append, core_memory_replace")
    logger.info("   - create/list/get memory blocks")
    logger.info("   - shared blocks for multi-agent coordination")
