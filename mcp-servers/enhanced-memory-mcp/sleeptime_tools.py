#!/usr/bin/env python3
"""
Sleeptime Agent Tools for FastMCP

Registers MCP tools for background memory consolidation using the sleeptime agent pattern.
"""

import logging
from typing import Dict, Any
from sleeptime_agent import SleetimeAgent

logger = logging.getLogger(__name__)


def register_sleeptime_tools(app, db_path):
    """Register all sleeptime agent tools with FastMCP app"""

    # Tool 1: Run Consolidation Cycle
    @app.tool()
    async def run_memory_consolidation(
        agent_id: str = "default_agent",
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Run background memory consolidation cycle (sleeptime agent pattern).

        This consolidates recent experiences into learnings:
        1. Extract patterns from episodic memories
        2. Create semantic concepts from patterns
        3. Discover causal relationships
        4. Update "learnings" memory block
        5. Compress old low-importance memories

        This is like sleep consolidation in humans - running in the background
        to strengthen important memories and discard unimportant details.

        Args:
            agent_id: Agent to consolidate memories for (default "default_agent")
            time_window_hours: Hours of memory to consolidate (default 24)

        Returns:
            Consolidation results with statistics

        Example:
            run_memory_consolidation(agent_id="my_agent", time_window_hours=24)

        Expected output:
        {
            "success": true,
            "memories_processed": 25,
            "patterns_found": 5,
            "concepts_created": 3,
            "causal_chains_discovered": 8,
            "learnings_updated": true,
            "duration_seconds": 1.23
        }
        """
        agent = SleetimeAgent(agent_id=agent_id, db_path=db_path)
        return agent.run_consolidation_cycle(time_window_hours)

    # Tool 2: Get Recent Episodic Memories (for manual inspection)
    @app.tool()
    async def get_recent_episodic_memories(
        agent_id: str = "default_agent",
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get recent episodic memories for inspection.

        Useful for understanding what the sleeptime agent will consolidate.

        Args:
            agent_id: Agent identifier
            time_window_hours: Hours to look back (default 24)

        Returns:
            List of episodic memories

        Example:
            get_recent_episodic_memories(agent_id="my_agent", time_window_hours=24)
        """
        agent = SleetimeAgent(agent_id=agent_id, db_path=db_path)
        memories = agent.get_recent_episodic_memories(time_window_hours)

        return {
            "success": True,
            "agent_id": agent_id,
            "time_window_hours": time_window_hours,
            "count": len(memories),
            "memories": memories
        }

    # Tool 3: Extract Patterns (without full consolidation)
    @app.tool()
    async def extract_memory_patterns(
        agent_id: str = "default_agent",
        time_window_hours: int = 24,
        min_frequency: int = 2
    ) -> Dict[str, Any]:
        """
        Extract patterns from recent memories without full consolidation.

        Useful for previewing what patterns would be learned.

        Args:
            agent_id: Agent identifier
            time_window_hours: Hours to analyze (default 24)
            min_frequency: Minimum occurrences to be a pattern (default 2)

        Returns:
            Identified patterns

        Example:
            extract_memory_patterns(agent_id="my_agent", time_window_hours=24, min_frequency=2)
        """
        agent = SleetimeAgent(agent_id=agent_id, db_path=db_path)
        memories = agent.get_recent_episodic_memories(time_window_hours)
        patterns = agent.extract_patterns(memories, min_frequency)

        return {
            "success": True,
            "agent_id": agent_id,
            "time_window_hours": time_window_hours,
            "memories_analyzed": len(memories),
            "patterns_found": len(patterns),
            "patterns": patterns
        }

    # Tool 4: Discover Causal Relationships
    @app.tool()
    async def discover_causal_patterns(
        agent_id: str = "default_agent",
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Discover causal relationships from recent memories.

        Identifies action → outcome patterns and temporal sequences.

        Args:
            agent_id: Agent identifier
            time_window_hours: Hours to analyze (default 24)

        Returns:
            Discovered causal chains

        Example:
            discover_causal_patterns(agent_id="my_agent", time_window_hours=24)
        """
        agent = SleetimeAgent(agent_id=agent_id, db_path=db_path)
        memories = agent.get_recent_episodic_memories(time_window_hours)
        causal_chains = agent.discover_causal_relationships(memories)

        return {
            "success": True,
            "agent_id": agent_id,
            "time_window_hours": time_window_hours,
            "memories_analyzed": len(memories),
            "causal_chains_found": len(causal_chains),
            "causal_chains": causal_chains
        }

    logger.info("✅ Sleeptime Agent tools registered (4 tools)")
    logger.info("   - run_memory_consolidation (main consolidation cycle)")
    logger.info("   - get_recent_episodic_memories")
    logger.info("   - extract_memory_patterns")
    logger.info("   - discover_causal_patterns")
