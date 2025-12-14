#!/usr/bin/env python3
"""
Cluster Brain MCP Tools

Provides MCP tools for accessing the unified cluster brain from any node.
Each node can:
- Read shared knowledge
- Contribute learnings
- Access cluster goals
- Route tasks to appropriate nodes
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def register_cluster_brain_tools(app, brain_instance=None):
    """
    Register cluster brain tools with the FastMCP app.

    Args:
        app: FastMCP application instance
        brain_instance: Optional pre-initialized ClusterBrain instance
    """
    from cluster_brain import ClusterBrain, get_cluster_brain

    # Use provided instance or create new one
    brain = brain_instance or get_cluster_brain()

    @app.tool()
    async def cluster_brain_status() -> Dict[str, Any]:
        """
        Get the current status of the unified cluster brain.

        Shows:
        - This node's identity and role
        - Cluster brain contents (knowledge, goals, learnings)
        - All node statuses

        Returns:
            Complete cluster brain status
        """
        summary = brain.get_brain_summary()
        cluster_status = brain.get_cluster_status()
        active_goals = brain.get_active_goals()

        return {
            "this_node": summary["this_node"],
            "brain_contents": {
                "shared_knowledge": summary["shared_knowledge"],
                "active_goals": summary["active_goals"],
                "shared_learnings": summary["shared_learnings"],
                "routed_tasks": summary["routed_tasks"]
            },
            "cluster_nodes": cluster_status,
            "current_goals": [
                {"id": g["id"], "goal": g["goal"], "priority": g["priority"], "progress": g["progress"]}
                for g in active_goals[:5]
            ]
        }

    @app.tool()
    async def cluster_add_knowledge(
        concept: str,
        category: str,
        content: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        Add knowledge to the shared cluster brain.

        This knowledge becomes accessible to ALL nodes in the cluster.

        Args:
            concept: Name/title of the knowledge (e.g., "SELinux Policy Creation")
            category: Category - architecture, patterns, tools, operations, etc.
            content: The actual knowledge content
            confidence: How confident we are (0.0-1.0)

        Returns:
            Result with knowledge_id
        """
        result = brain.add_knowledge(concept, category, content, confidence)
        logger.info(f"Added cluster knowledge: {concept}")
        return result

    @app.tool()
    async def cluster_query_knowledge(
        query: str = None,
        category: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Query the shared cluster knowledge base.

        Access knowledge contributed by ANY node in the cluster.

        Args:
            query: Search term (searches concept and content)
            category: Filter by category (architecture, patterns, tools, operations)
            limit: Max results to return

        Returns:
            List of matching knowledge entries
        """
        results = brain.query_knowledge(query, category, limit)
        return {
            "success": True,
            "count": len(results),
            "results": results
        }

    @app.tool()
    async def cluster_add_goal(
        goal: str,
        description: str = None,
        priority: int = 5,
        assigned_nodes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Add a cluster-wide goal that all nodes work toward.

        Args:
            goal: Short goal statement
            description: Detailed description
            priority: 1-10 (10 is highest priority)
            assigned_nodes: Which nodes should work on this (optional, all if not specified)

        Returns:
            Result with goal_id
        """
        result = brain.add_goal(goal, description, priority, assigned_nodes)
        logger.info(f"Added cluster goal: {goal}")
        return result

    @app.tool()
    async def cluster_get_goals(assigned_to: str = None) -> Dict[str, Any]:
        """
        Get active cluster goals.

        Args:
            assigned_to: Filter by assigned node (optional)

        Returns:
            List of active goals with their progress
        """
        goals = brain.get_active_goals(assigned_to)
        return {
            "success": True,
            "count": len(goals),
            "goals": goals
        }

    @app.tool()
    async def cluster_update_goal_progress(
        goal_id: int,
        progress: float,
        status: str = None
    ) -> Dict[str, Any]:
        """
        Update progress on a cluster goal.

        Args:
            goal_id: Goal to update
            progress: Progress 0.0-1.0
            status: New status - 'active', 'completed', 'blocked' (optional)

        Returns:
            Update result
        """
        result = brain.update_goal_progress(goal_id, progress, status)
        return result

    @app.tool()
    async def cluster_add_learning(
        learning: str,
        category: str = None,
        source_task: str = None,
        success_score: float = None,
        applies_to: List[str] = None
    ) -> Dict[str, Any]:
        """
        Share a learning with the entire cluster.

        Learnings help other nodes avoid mistakes and build on successes.

        Args:
            learning: What was learned
            category: Learning category (patterns, operations, debugging, etc.)
            source_task: What task led to this learning
            success_score: How successful was the outcome (0.0-1.0)
            applies_to: Which node roles might benefit (builder, orchestrator, researcher, inference)

        Returns:
            Result with learning_id
        """
        result = brain.add_learning(learning, category, source_task, success_score, applies_to)
        logger.info(f"Shared cluster learning: {learning[:50]}...")
        return result

    @app.tool()
    async def cluster_get_learnings(
        category: str = None,
        applies_to: str = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get learnings from the cluster brain.

        Access insights and lessons learned from ALL nodes.

        Args:
            category: Filter by category
            applies_to: Filter by applicable role
            limit: Max results

        Returns:
            List of learnings
        """
        learnings = brain.get_learnings(category, applies_to, limit)
        return {
            "success": True,
            "count": len(learnings),
            "learnings": learnings
        }

    @app.tool()
    async def cluster_route_task(
        task_type: str,
        task_description: str = None
    ) -> Dict[str, Any]:
        """
        Get recommendation for which node should handle a task.

        Uses node capabilities and historical success rates.

        Args:
            task_type: Type of task (build, test, research, infer, analyze, etc.)
            task_description: Optional description for better routing

        Returns:
            Routing recommendation with node_id and reasoning
        """
        result = brain.route_task(task_type, task_description)
        return result

    @app.tool()
    async def cluster_record_task_result(
        task_type: str,
        routed_to: str,
        success: bool,
        execution_time_ms: int = None,
        task_description: str = None
    ) -> Dict[str, Any]:
        """
        Record the result of a task for cluster learning.

        Helps improve future task routing decisions.

        Args:
            task_type: Type of task
            routed_to: Which node handled it
            success: Whether it succeeded
            execution_time_ms: How long it took
            task_description: Description of the task

        Returns:
            Recording result
        """
        result = brain.record_task_result(
            task_type, routed_to, success, execution_time_ms, task_description
        )
        return result

    @app.tool()
    async def cluster_update_node_status(
        current_task: str = None,
        cpu_percent: float = None,
        memory_percent: float = None
    ) -> Dict[str, Any]:
        """
        Update this node's status in the cluster brain.

        Other nodes can see what we're working on and our resource availability.

        Args:
            current_task: What we're currently working on
            cpu_percent: Current CPU usage
            memory_percent: Current memory usage

        Returns:
            Update result
        """
        result = brain.update_status(current_task, cpu_percent, memory_percent)
        return result

    logger.info(f"✅ Cluster Brain tools registered for node: {brain.node_id}")
    return brain
