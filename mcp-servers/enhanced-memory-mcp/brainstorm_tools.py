#!/usr/bin/env python3
"""
Brainstorm Memory Tools - Enhanced Memory MCP Extension

Provides specialized memory operations for brainstorming sessions,
including idea storage, pattern extraction, and session management.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BrainstormMemoryTools:
    """
    Memory tools specifically designed for brainstorming sessions.

    Integrates with the enhanced-memory 4-tier architecture:
    - Working Memory: Active session state
    - Episodic Memory: Session history
    - Semantic Memory: Idea patterns and insights
    - Procedural Memory: Effective brainstorming techniques
    """

    def __init__(self, memory_manager=None):
        """
        Initialize brainstorm memory tools.

        Args:
            memory_manager: Reference to main MemoryManager instance
        """
        self.memory_manager = memory_manager
        self.namespace = "brainstorm"

    async def create_session(
        self,
        topic: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new brainstorm session in working memory.

        Args:
            topic: Brainstorm topic
            config: Session configuration

        Returns:
            Session metadata including session_id
        """
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        session_data = {
            "session_id": session_id,
            "topic": topic,
            "phase": "initializing",
            "topology": "mesh",
            "created_at": timestamp,
            "ideas_count": 0,
            "current_round": 0,
            "max_rounds": config.get("max_rounds", 3) if config else 3,
            "agents": config.get("agents", ["ideator", "critic", "strategist", "builder", "synthesizer"]) if config else [],
            "config": config or {}
        }

        # Store in working memory with TTL
        if self.memory_manager:
            await self.memory_manager.add_to_working_memory(
                context_key=f"brainstorm/session/{session_id}/state",
                content=json.dumps(session_data),
                priority=9,  # High priority
                ttl_minutes=120  # 2 hour session max
            )

        logger.info(f"Created brainstorm session: {session_id}")
        return session_data

    async def store_idea(
        self,
        session_id: str,
        content: str,
        author: str,
        phase: str,
        round_num: int,
        builds_on: Optional[List[str]] = None,
        weight: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a brainstorm idea.

        Args:
            session_id: Session identifier
            content: Idea content
            author: Agent or user who generated the idea
            phase: Current phase when idea was generated
            round_num: Round number
            builds_on: List of idea IDs this builds on
            weight: Idea weight (user ideas = 1.5)
            metadata: Additional metadata

        Returns:
            Idea data including idea_id
        """
        idea_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        idea_data = {
            "id": idea_id,
            "session_id": session_id,
            "content": content,
            "author": author,
            "phase": phase,
            "round": round_num,
            "timestamp": timestamp,
            "builds_on": builds_on or [],
            "weight": weight,
            "votes": {},
            "status": "active",
            "metadata": metadata or {}
        }

        # Store in working memory
        if self.memory_manager:
            await self.memory_manager.add_to_working_memory(
                context_key=f"brainstorm/session/{session_id}/ideas/{idea_id}",
                content=json.dumps(idea_data),
                priority=7,
                ttl_minutes=120
            )

        logger.debug(f"Stored idea {idea_id} in session {session_id}")
        return idea_data

    async def vote_on_idea(
        self,
        session_id: str,
        idea_id: str,
        voter: str,
        vote: int  # +1 or -1
    ) -> Dict[str, Any]:
        """
        Record a vote on an idea.

        Args:
            session_id: Session identifier
            idea_id: Idea to vote on
            voter: Agent or user voting
            vote: +1 (support) or -1 (oppose)

        Returns:
            Updated vote counts
        """
        # In production, would update the idea in memory
        return {
            "idea_id": idea_id,
            "voter": voter,
            "vote": vote,
            "recorded": True
        }

    async def get_session_ideas(
        self,
        session_id: str,
        phase: Optional[str] = None,
        author: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ideas from a session with optional filtering.

        Args:
            session_id: Session identifier
            phase: Filter by phase
            author: Filter by author

        Returns:
            List of idea data
        """
        # In production, would query working memory
        return []

    async def conclude_session(
        self,
        session_id: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Conclude a brainstorm session and store results.

        Args:
            session_id: Session identifier
            results: Final results including recommendations

        Returns:
            Storage confirmation
        """
        timestamp = datetime.now().isoformat()

        # Store to episodic memory
        if self.memory_manager:
            await self.memory_manager.add_episode(
                event_type="brainstorm_session",
                episode_data={
                    "session_id": session_id,
                    "topic": results.get("topic"),
                    "total_ideas": results.get("total_ideas"),
                    "top_ideas": results.get("top_ideas", [])[:3],
                    "recommendation": results.get("recommendation"),
                    "core_insight": results.get("core_insight"),
                    "concluded_at": timestamp
                },
                significance_score=0.8,  # Brainstorm sessions are significant
                tags=["brainstorm", "collective-reasoning"]
            )

        logger.info(f"Concluded brainstorm session: {session_id}")
        return {"stored": True, "session_id": session_id}

    async def promote_insight(
        self,
        insight: str,
        source_session: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Promote a brainstorm insight to semantic memory.

        Args:
            insight: The insight to store
            source_session: Session that generated the insight
            confidence: Confidence score (0-1)

        Returns:
            Storage confirmation
        """
        if self.memory_manager:
            await self.memory_manager.add_concept(
                concept_name=f"brainstorm-insight-{source_session}",
                concept_type="brainstorm-insight",
                definition=insight,
                confidence_score=confidence
            )

        return {"promoted": True, "insight": insight[:50] + "..."}

    async def store_technique(
        self,
        technique_name: str,
        description: str,
        success_rate: float,
        best_for: List[str],
        avoid_for: List[str]
    ) -> Dict[str, Any]:
        """
        Store an effective brainstorming technique to procedural memory.

        Args:
            technique_name: Name of the technique
            description: How to apply the technique
            success_rate: Historical success rate
            best_for: Types of problems this works for
            avoid_for: Types of problems to avoid this for

        Returns:
            Storage confirmation
        """
        if self.memory_manager:
            await self.memory_manager.add_skill(
                skill_name=f"brainstorm-technique-{technique_name}",
                skill_category="brainstorm-technique",
                procedure_steps=[description],
                preconditions=best_for,
                success_criteria=[f"success_rate > {success_rate}"]
            )

        return {"stored": True, "technique": technique_name}

    async def find_similar_sessions(
        self,
        topic: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past brainstorm sessions.

        Args:
            topic: Topic to search for
            limit: Maximum results

        Returns:
            List of similar session summaries
        """
        # In production, would use semantic search on episodic memory
        if self.memory_manager:
            results = await self.memory_manager.get_episodes(
                event_type="brainstorm_session",
                limit=limit
            )
            return results

        return []

    async def get_effective_techniques(
        self,
        problem_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get effective brainstorming techniques from procedural memory.

        Args:
            problem_type: Optional filter by problem type

        Returns:
            List of technique data
        """
        if self.memory_manager:
            skills = await self.memory_manager.get_skills(
                skill_category="brainstorm-technique",
                min_success_rate=0.6
            )
            return skills

        return []


# MCP Tool Definitions for brainstorm operations
BRAINSTORM_TOOLS = [
    {
        "name": "brainstorm_create_session",
        "description": "Create a new brainstorm session in working memory",
        "parameters": {
            "topic": {"type": "string", "description": "Brainstorm topic"},
            "max_rounds": {"type": "integer", "description": "Max rounds per phase", "default": 3}
        },
        "required": ["topic"]
    },
    {
        "name": "brainstorm_store_idea",
        "description": "Store an idea from a brainstorm session",
        "parameters": {
            "session_id": {"type": "string", "description": "Session identifier"},
            "content": {"type": "string", "description": "Idea content"},
            "author": {"type": "string", "description": "Agent or user who generated it"},
            "phase": {"type": "string", "description": "Current phase"},
            "round": {"type": "integer", "description": "Round number"}
        },
        "required": ["session_id", "content", "author", "phase", "round"]
    },
    {
        "name": "brainstorm_vote",
        "description": "Vote on a brainstorm idea",
        "parameters": {
            "session_id": {"type": "string"},
            "idea_id": {"type": "string"},
            "voter": {"type": "string"},
            "vote": {"type": "integer", "description": "+1 or -1"}
        },
        "required": ["session_id", "idea_id", "voter", "vote"]
    },
    {
        "name": "brainstorm_conclude",
        "description": "Conclude brainstorm session and store results",
        "parameters": {
            "session_id": {"type": "string"},
            "topic": {"type": "string"},
            "total_ideas": {"type": "integer"},
            "recommendation": {"type": "string"},
            "core_insight": {"type": "string"}
        },
        "required": ["session_id", "topic"]
    },
    {
        "name": "brainstorm_find_similar",
        "description": "Find similar past brainstorm sessions",
        "parameters": {
            "topic": {"type": "string", "description": "Topic to search for"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["topic"]
    },
    {
        "name": "brainstorm_get_techniques",
        "description": "Get effective brainstorming techniques",
        "parameters": {
            "problem_type": {"type": "string", "description": "Optional problem type filter"}
        },
        "required": []
    }
]


def register_brainstorm_tools(server):
    """
    Register brainstorm tools with MCP server.

    Args:
        server: MCP server instance to register tools with
    """
    brainstorm_tools = BrainstormMemoryTools()

    # In production, would register each tool with the server
    logger.info(f"Registered {len(BRAINSTORM_TOOLS)} brainstorm tools")
    return brainstorm_tools


if __name__ == "__main__":
    # Test the tools
    import asyncio

    async def test():
        tools = BrainstormMemoryTools()

        # Create session
        session = await tools.create_session(
            topic="Test brainstorm",
            config={"max_rounds": 2}
        )
        print(f"Created session: {session['session_id']}")

        # Store idea
        idea = await tools.store_idea(
            session_id=session['session_id'],
            content="Test idea content",
            author="ideator",
            phase="divergent",
            round_num=1
        )
        print(f"Stored idea: {idea['id']}")

        # Conclude
        result = await tools.conclude_session(
            session_id=session['session_id'],
            results={
                "topic": "Test brainstorm",
                "total_ideas": 1,
                "recommendation": "Proceed with test idea"
            }
        )
        print(f"Concluded: {result}")

    asyncio.run(test())
