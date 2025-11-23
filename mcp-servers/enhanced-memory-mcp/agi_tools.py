"""
AGI Memory Tools - MCP Server Integration

Exposes Phase 1 AGI capabilities (cross-session identity & memory-action loop) via MCP tools.
"""

import logging
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP

from agi import AgentIdentity, SessionManager, ActionTracker

logger = logging.getLogger("agi-tools")


def register_agi_tools(app: FastMCP, db_path: str):
    """Register AGI memory tools with FastMCP app"""

    # ============================================================================
    # AGENT IDENTITY TOOLS
    # ============================================================================

    @app.tool(
        outputSchema={
            "type": "object",
            "additionalProperties": True
        }
    )
    def get_agent_identity(agent_id: str = "default_agent") -> Dict[str, Any]:
        """
        Get persistent agent identity

        Returns complete identity including skills, traits, beliefs, and stats.
        """
        identity = AgentIdentity(agent_id)
        return identity.get_identity()

    @app.tool()
    def update_agent_skills(
        skill_updates: Dict[str, float],
        agent_id: str = "default_agent"
    ) -> Dict[str, str]:
        """
        Update agent skill levels (0.0 to 1.0)

        Example: {"coding": 0.85, "research": 0.92, "debugging": 0.78}

        Skills track learned capabilities that improve over time.
        """
        identity = AgentIdentity(agent_id)
        identity.update_skills(skill_updates)
        return {"status": "success", "updated": list(skill_updates.keys())}

    @app.tool()
    def add_agent_belief(
        belief: str,
        agent_id: str = "default_agent"
    ) -> Dict[str, str]:
        """
        Add a core belief/knowledge to agent identity

        Example: "async/await is better than threads for I/O-bound tasks"

        Beliefs are persistent truths the agent has learned.
        """
        identity = AgentIdentity(agent_id)
        identity.add_belief(belief)
        return {"status": "success", "belief": belief}

    @app.tool()
    def update_agent_personality(
        trait_updates: Dict[str, float],
        agent_id: str = "default_agent"
    ) -> Dict[str, str]:
        """
        Update agent personality traits (0.0 to 1.0)

        Example: {"curiosity": 0.8, "caution": 0.6, "creativity": 0.9}

        Personality traits evolve based on experiences and preferences.
        """
        identity = AgentIdentity(agent_id)
        identity.update_personality(trait_updates)
        return {"status": "success", "updated": list(trait_updates.keys())}

    @app.tool()
    def set_agent_preference(
        key: str,
        value: Any,
        agent_id: str = "default_agent"
    ) -> Dict[str, str]:
        """
        Set an agent preference

        Example: set_agent_preference("preferred_editor", "vim")

        Preferences customize agent behavior and choices.
        """
        identity = AgentIdentity(agent_id)
        identity.set_preference(key, value)
        return {"status": "success", "preference": key, "value": value}

    # ============================================================================
    # SESSION MANAGEMENT TOOLS
    # ============================================================================

    @app.tool()
    def start_session(
        context_summary: Optional[str] = None,
        agent_id: str = "default_agent"
    ) -> Dict[str, str]:
        """
        Start a new session with context from previous session

        Returns session_id for tracking work in this session.

        Sessions are automatically linked to maintain continuity.
        """
        manager = SessionManager(agent_id)
        session_id = manager.start_session(context_summary)
        return {
            "status": "success",
            "session_id": session_id,
            "agent_id": agent_id
        }

    @app.tool()
    def end_session(
        session_id: str,
        key_learnings: Optional[List[str]] = None,
        unfinished_work: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        End a session and record outcomes

        Args:
            session_id: Session to end
            key_learnings: What was learned this session
            unfinished_work: Tasks/goals not completed
            performance_metrics: Success rates, error counts, etc.
        """
        manager = SessionManager()
        manager.end_session(session_id, key_learnings, unfinished_work, performance_metrics)
        return {"status": "success", "session_id": session_id}

    @app.tool()
    def get_session_context(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete context for a session

        Includes learnings, unfinished work, and performance metrics.
        """
        manager = SessionManager()
        return manager.get_session_context(session_id)

    @app.tool()
    def get_recent_sessions(
        limit: int = 10,
        agent_id: str = "default_agent"
    ) -> List[Dict[str, Any]]:
        """
        Get recent sessions for continuity

        Returns sessions from most recent to oldest with all context.
        """
        manager = SessionManager(agent_id)
        return manager.get_recent_sessions(limit)

    @app.tool()
    def get_session_chain(
        session_id: str,
        depth: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get chain of linked sessions going backwards

        Shows session history and how work evolved across sessions.
        """
        manager = SessionManager()
        return manager.get_session_chain(session_id, depth)

    # ============================================================================
    # ACTION OUTCOME TRACKING TOOLS
    # ============================================================================

    @app.tool(
        outputSchema={
            "type": "object",
            "additionalProperties": True
        }
    )
    def record_action_outcome(
        action_type: str,
        action_description: str,
        expected_result: str,
        actual_result: str,
        success_score: float,
        session_id: Optional[str] = None,
        entity_id: Optional[int] = None,
        action_context: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record an action and its outcome for learning

        Args:
            action_type: Type of action ("code_change", "command", "research", etc.)
            action_description: What was done
            expected_result: What we expected
            actual_result: What actually happened
            success_score: 0.0 (failure) to 1.0 (success)
            session_id: Optional session ID
            entity_id: Optional memory entity ID
            action_context: Why this action was taken
            duration_ms: How long it took
            metadata: Additional data

        Returns:
            action_id for reference
        """
        tracker = ActionTracker()
        action_id = tracker.record_action(
            action_type, action_description,
            expected_result, actual_result,
            success_score, session_id, entity_id,
            action_context, duration_ms, metadata
        )
        return {
            "status": "success",
            "action_id": action_id,
            "success_score": success_score
        }

    @app.tool()
    def get_similar_actions(
        action_type: str,
        context: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar past actions to learn from

        Returns actions with outcomes, sorted by recency.

        Use this before taking action to see what worked before.
        """
        tracker = ActionTracker()
        return tracker.get_similar_actions(action_type, context, limit)

    @app.tool()
    def get_action_success_rate(
        action_type: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get success rate for an action type

        Returns:
            {
                "action_type": str,
                "total_actions": int,
                "success_count": int,
                "success_rate": float,
                "avg_score": float,
                "time_window_hours": int
            }

        Use this to know if you're improving at specific actions.
        """
        tracker = ActionTracker()
        return tracker.get_success_rate(action_type, time_window_hours)

    @app.tool()
    def get_learnings_for_action(
        action_type: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get key learnings from past actions

        Returns lessons learned from successes and failures.

        Use this to avoid repeating mistakes.
        """
        tracker = ActionTracker()
        return tracker.get_learnings_for_action(action_type, limit)

    @app.tool(
        outputSchema={
            "type": "object",
            "additionalProperties": True
        }
    )
    def should_retry_action(
        original_action_id: int,
        proposed_changes: str
    ) -> Dict[str, Any]:
        """
        Decide if an action should be retried with changes

        Returns:
            {
                "should_retry": bool,
                "confidence": float,
                "reasoning": str,
                "suggested_changes": List[str]
            }

        Use this to decide if failure warrants a retry with modifications.
        """
        tracker = ActionTracker()
        return tracker.should_retry_action(original_action_id, proposed_changes)

    @app.tool(
        outputSchema={
            "type": "object",
            "additionalProperties": True
        }
    )
    def get_action_statistics() -> Dict[str, Any]:
        """
        Get overall action outcome statistics

        Returns comprehensive stats on all actions, success rates,
        trends, and performance over time.

        Use this to monitor agent learning progress.
        """
        tracker = ActionTracker()
        return tracker.get_action_statistics()

    logger.info("✅ AGI Memory tools registered (Phase 1: Identity & Actions)")
