"""
SAFLA Tools Registration
Tool endpoints for 4-tier memory system
"""

from typing import Dict, List, Optional


def register_safla_tools(app, safla):
    """Register SAFLA 4-tier memory tools with FastMCP app."""

    # === WORKING MEMORY TOOLS ===

    @app.tool()
    def add_to_working_memory(
        context_key: str,
        content: str,
        priority: int = 5,
        ttl_minutes: int = 60,
        entity_id: Optional[int] = None
    ) -> str:
        """
        Add item to working memory (temporary, volatile storage).

        Working memory is for active context that expires after TTL.
        High-access items are automatically promoted to episodic memory.

        Args:
            context_key: Context identifier (e.g., "current_task", "active_goal")
            content: Content to store
            priority: Priority 1-10 (10 is highest)
            ttl_minutes: Time to live in minutes (default 60)
            entity_id: Optional entity ID to associate with

        Returns:
            JSON with working memory ID and expiration time
        """
        import json
        from datetime import datetime, timedelta

        wm_id = safla.add_to_working_memory(context_key, content, priority, ttl_minutes, entity_id)
        expires_at = (datetime.now() + timedelta(minutes=ttl_minutes)).isoformat()

        return json.dumps({
            "working_memory_id": wm_id,
            "context_key": context_key,
            "expires_at": expires_at,
            "ttl_minutes": ttl_minutes
        }, indent=2)

    @app.tool()
    def get_working_memory(context_key: Optional[str] = None, limit: int = 50) -> str:
        """
        Get items from working memory.

        Args:
            context_key: Optional context filter
            limit: Maximum items to return (default 50)

        Returns:
            JSON array of working memory items
        """
        import json

        items = safla.get_working_memory(context_key, limit)
        return json.dumps(items, indent=2)

    # === EPISODIC MEMORY TOOLS ===

    @app.tool()
    def add_episode(
        event_type: str,
        episode_data: Dict,
        significance_score: float = 0.5,
        emotional_valence: Optional[float] = None,
        tags: Optional[List[str]] = None,
        entity_id: Optional[int] = None
    ) -> str:
        """
        Add an episode to episodic memory (experiences and events).

        Episodic memory stores time-bound experiences. High-significance
        episodes are consolidated into semantic concepts.

        Args:
            event_type: Type of event (e.g., "task_completion", "error", "learning")
            episode_data: Event data dictionary
            significance_score: Significance 0.0-1.0 (default 0.5)
            emotional_valence: Optional emotional score -1.0 to 1.0
            tags: Optional tags for categorization
            entity_id: Optional entity ID to associate with

        Returns:
            JSON with episode ID and metadata
        """
        import json

        episode_id = safla.add_episode(
            event_type,
            episode_data,
            significance_score,
            emotional_valence,
            tags,
            entity_id
        )

        return json.dumps({
            "episode_id": episode_id,
            "event_type": event_type,
            "significance_score": significance_score
        }, indent=2)

    @app.tool()
    def get_episodes(
        event_type: Optional[str] = None,
        min_significance: float = 0.0,
        limit: int = 50
    ) -> str:
        """
        Get episodes from episodic memory.

        Args:
            event_type: Optional event type filter
            min_significance: Minimum significance score (default 0.0)
            limit: Maximum episodes to return (default 50)

        Returns:
            JSON array of episodes sorted by significance
        """
        import json

        episodes = safla.get_episodes(event_type, min_significance, limit)
        return json.dumps(episodes, indent=2)

    # === SEMANTIC MEMORY TOOLS ===

    @app.tool()
    def add_concept(
        concept_name: str,
        concept_type: str,
        definition: str,
        related_concepts: Optional[List[str]] = None,
        confidence_score: float = 0.5
    ) -> str:
        """
        Add or update a concept in semantic memory (timeless knowledge).

        Semantic memory stores abstract concepts and relationships.
        Concepts are automatically derived from episodic patterns.

        Args:
            concept_name: Unique concept name
            concept_type: Type of concept (e.g., "pattern", "principle", "fact")
            definition: Concept definition
            related_concepts: Optional list of related concept names
            confidence_score: Confidence 0.0-1.0 (default 0.5)

        Returns:
            JSON with concept ID and metadata
        """
        import json

        concept_id = safla.add_concept(
            concept_name,
            concept_type,
            definition,
            related_concepts,
            confidence_score
        )

        return json.dumps({
            "concept_id": concept_id,
            "concept_name": concept_name,
            "confidence_score": confidence_score
        }, indent=2)

    @app.tool()
    def get_concepts(
        concept_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50
    ) -> str:
        """
        Get concepts from semantic memory.

        Args:
            concept_type: Optional concept type filter
            min_confidence: Minimum confidence score (default 0.0)
            limit: Maximum concepts to return (default 50)

        Returns:
            JSON array of concepts sorted by confidence
        """
        import json

        concepts = safla.get_concepts(concept_type, min_confidence, limit)
        return json.dumps(concepts, indent=2)

    # === PROCEDURAL MEMORY TOOLS ===

    @app.tool()
    def add_skill(
        skill_name: str,
        skill_category: str,
        procedure_steps: List[str],
        preconditions: Optional[List[str]] = None,
        success_criteria: Optional[List[str]] = None
    ) -> str:
        """
        Add or update a skill in procedural memory (how-to knowledge).

        Procedural memory stores executable skills and procedures.
        Skills improve through execution tracking.

        Args:
            skill_name: Unique skill name
            skill_category: Skill category (e.g., "coding", "analysis", "communication")
            procedure_steps: List of steps to execute
            preconditions: Optional list of preconditions
            success_criteria: Optional list of success criteria

        Returns:
            JSON with skill ID and metadata
        """
        import json

        skill_id = safla.add_skill(
            skill_name,
            skill_category,
            procedure_steps,
            preconditions,
            success_criteria
        )

        return json.dumps({
            "skill_id": skill_id,
            "skill_name": skill_name,
            "steps_count": len(procedure_steps)
        }, indent=2)

    @app.tool()
    def record_skill_execution(
        skill_name: str,
        success: bool,
        execution_time_ms: int
    ) -> str:
        """
        Record skill execution for learning and improvement.

        Updates success rate and average execution time.

        Args:
            skill_name: Name of skill that was executed
            success: Whether execution succeeded
            execution_time_ms: Execution time in milliseconds

        Returns:
            Confirmation message
        """
        import json

        safla.record_skill_execution(skill_name, success, execution_time_ms)

        return json.dumps({
            "skill_name": skill_name,
            "recorded": True,
            "success": success,
            "execution_time_ms": execution_time_ms
        }, indent=2)

    @app.tool()
    def get_skills(
        skill_category: Optional[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50
    ) -> str:
        """
        Get skills from procedural memory.

        Args:
            skill_category: Optional skill category filter
            min_success_rate: Minimum success rate (default 0.0)
            limit: Maximum skills to return (default 50)

        Returns:
            JSON array of skills sorted by success rate
        """
        import json

        skills = safla.get_skills(skill_category, min_success_rate, limit)
        return json.dumps(skills, indent=2)

    # === AUTONOMOUS CURATION ===

    @app.tool()
    async def autonomous_memory_curation() -> str:
        """
        Run autonomous memory curation across all tiers.

        Promotions:
        - Working → Episodic: High-access items become episodes
        - Episodic → Semantic: Patterns become concepts
        - Episodic → Procedural: Repeated actions become skills

        This should be run periodically to maintain memory health.

        Returns:
            JSON with curation statistics
        """
        import json

        stats = await safla.autonomous_memory_curation()
        return json.dumps(stats, indent=2)

    @app.tool()
    async def analyze_memory_usage_patterns() -> str:
        """
        Analyze memory usage across all 4 tiers.

        Provides statistics and recommendations for memory optimization.

        Returns:
            JSON with analysis and recommendations
        """
        import json

        analysis = await safla.analyze_memory_usage_patterns()
        return json.dumps(analysis, indent=2)
