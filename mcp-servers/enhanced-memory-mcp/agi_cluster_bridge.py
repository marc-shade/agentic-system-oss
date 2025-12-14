#!/usr/bin/env python3
"""
AGI-Cluster Brain Bridge

Connects the AGI system (identity, meta-learning, self-improvement) to the
unified cluster brain, enabling:

1. Shared AGI Learnings - Meta-learning insights available to all nodes
2. Distributed Skill Tracking - Skills learned by any node benefit all
3. Collective Goal Pursuit - AGI goals tracked at cluster level
4. Cross-Node Memory - Working memory accessible cluster-wide

This bridges:
- agi_tools.py (agent identity, skills, beliefs)
- safla_orchestrator.py (working memory, episodes, concepts)
- cluster_brain.py (shared knowledge, goals, learnings, routing)
"""
import platform

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class AGIClusterBridge:
    """
    Bridge between AGI system and Cluster Brain.

    Automatically syncs:
    - Agent skills → Cluster knowledge
    - Meta-learning insights → Cluster learnings
    - Self-improvement outcomes → Cluster learnings
    - Episodic memories → Shared when significant
    """

    def __init__(self, cluster_brain=None, safla=None):
        """
        Initialize bridge with optional pre-existing instances.

        Args:
            cluster_brain: ClusterBrain instance (created if None)
            safla: SAFLAOrchestrator instance (created if None)
        """
        # Lazy import to avoid circular dependencies
        if cluster_brain is None:
            from cluster_brain import get_cluster_brain
            cluster_brain = get_cluster_brain()

        if safla is None:
            from safla_orchestrator import SAFLAOrchestrator
            db_path = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "databases/mcp/memory.db"))
            safla = SAFLAOrchestrator(db_path)

        self.brain = cluster_brain
        self.safla = safla
        self.node_id = self.brain.node_id

        logger.info(f"AGI-Cluster Bridge initialized for node: {self.node_id}")

    def _load_capability_map(self) -> Dict[str, str]:
        """
        Load capability-to-node mapping from environment.

        Set CAPABILITY_NODE_MAP_JSON env var with JSON like:
        {"compilation": "builder-node", "testing": "builder-node",
         "coordination": "orchestrator", "inference": "gpu-node"}

        Returns empty dict if not configured (no capability routing).
        """
        env_config = os.environ.get("CAPABILITY_NODE_MAP_JSON")
        if env_config:
            try:
                return json.loads(env_config)
            except json.JSONDecodeError:
                pass
        return {}

    # =========================================================================
    # SKILL SYNCING
    # =========================================================================

    def sync_skill_to_cluster(
        self,
        skill_name: str,
        proficiency: float,
        source_task: str = None,
        learned_from: str = None
    ) -> Dict[str, Any]:
        """
        Share a skill improvement with the cluster brain.

        Args:
            skill_name: Name of the skill (e.g., "python_async", "sql_optimization")
            proficiency: Current proficiency level (0.0-1.0)
            source_task: What task led to this skill improvement
            learned_from: What source taught this (documentation, practice, etc.)

        Returns:
            Result with knowledge_id and learning_id
        """
        # Add as cluster knowledge (permanent reference)
        knowledge_content = f"""
Skill: {skill_name}
Proficiency: {proficiency:.2f}
Learned by: {self.node_id}
Source: {learned_from or 'practice'}
Timestamp: {datetime.now().isoformat()}

This skill can be leveraged by routing relevant tasks to {self.node_id}.
"""
        knowledge_result = self.brain.add_knowledge(
            concept=f"Skill: {skill_name}",
            category="skills",
            content=knowledge_content,
            confidence=proficiency
        )

        # Add as learning (for meta-learning)
        learning_result = self.brain.add_learning(
            learning=f"Node {self.node_id} achieved {proficiency:.0%} proficiency in {skill_name}",
            category="skill_acquisition",
            source_task=source_task,
            success_score=proficiency,
            applies_to=["builder", "researcher", "orchestrator", "inference"]
        )

        logger.info(f"Synced skill {skill_name} to cluster brain")

        return {
            "success": True,
            "skill": skill_name,
            "proficiency": proficiency,
            "knowledge_id": knowledge_result.get("knowledge_id"),
            "learning_id": learning_result.get("learning_id")
        }

    def get_cluster_skills(self, category: str = None) -> List[Dict]:
        """
        Get skills from across the cluster.

        Args:
            category: Filter by skill category (optional)

        Returns:
            List of skill knowledge entries from all nodes
        """
        return self.brain.query_knowledge(query="Skill:", category="skills")

    # =========================================================================
    # META-LEARNING INTEGRATION
    # =========================================================================

    def share_meta_learning_insight(
        self,
        domain: str,
        best_strategy: str,
        success_rate: float,
        sample_size: int,
        details: str = None
    ) -> Dict[str, Any]:
        """
        Share a meta-learning insight with the cluster.

        Meta-learning insights tell other nodes which strategies work best
        for which types of problems.

        Args:
            domain: Problem domain (e.g., "nlp", "tabular", "optimization")
            best_strategy: Most effective strategy for this domain
            success_rate: Success rate of the strategy (0.0-1.0)
            sample_size: Number of trials this is based on
            details: Additional context

        Returns:
            Result with learning_id
        """
        learning_text = f"""
META-LEARNING INSIGHT from {self.node_id}:
Domain: {domain}
Best Strategy: {best_strategy}
Success Rate: {success_rate:.1%}
Sample Size: {sample_size} trials
{f'Details: {details}' if details else ''}

Recommendation: Route {domain} tasks to nodes using {best_strategy} approach.
"""

        result = self.brain.add_learning(
            learning=learning_text,
            category="meta_learning",
            source_task=f"Meta-learning analysis of {domain}",
            success_score=success_rate,
            applies_to=["orchestrator", "researcher", "builder", "inference"]
        )

        # Also add as actionable knowledge
        self.brain.add_knowledge(
            concept=f"Meta-Learning: {domain}",
            category="patterns",
            content=f"For {domain} problems, use {best_strategy} strategy. "
                   f"Based on {sample_size} trials with {success_rate:.1%} success.",
            confidence=min(0.5 + (sample_size / 100), 0.95)  # Confidence grows with samples
        )

        logger.info(f"Shared meta-learning insight for {domain}")
        return result

    def get_meta_learning_insights(self, domain: str = None) -> List[Dict]:
        """
        Get meta-learning insights from the cluster.

        Args:
            domain: Filter by domain (optional)

        Returns:
            List of meta-learning insights
        """
        query = f"META-LEARNING INSIGHT"
        if domain:
            query = f"{query} {domain}"

        learnings = self.brain.get_learnings(category="meta_learning")

        if domain:
            learnings = [l for l in learnings if domain.lower() in l.get("learning", "").lower()]

        return learnings

    # =========================================================================
    # SELF-IMPROVEMENT TRACKING
    # =========================================================================

    def record_self_improvement(
        self,
        improvement_type: str,
        description: str,
        metrics_before: Dict[str, float],
        metrics_after: Dict[str, float],
        technique_used: str = None
    ) -> Dict[str, Any]:
        """
        Record a self-improvement outcome in the cluster brain.

        Args:
            improvement_type: Type of improvement (performance, capability, efficiency)
            description: What was improved
            metrics_before: Metrics before improvement
            metrics_after: Metrics after improvement
            technique_used: Self-improvement technique used

        Returns:
            Result with learning_id
        """
        # Calculate improvement
        improvements = {}
        for metric, after in metrics_after.items():
            before = metrics_before.get(metric, 0)
            if before > 0:
                pct_change = ((after - before) / before) * 100
                improvements[metric] = pct_change

        improvement_summary = ", ".join(
            f"{k}: {v:+.1f}%" for k, v in improvements.items()
        )

        learning_text = f"""
SELF-IMPROVEMENT OUTCOME from {self.node_id}:
Type: {improvement_type}
Description: {description}
Technique: {technique_used or 'unspecified'}
Metrics Change: {improvement_summary}

Before: {metrics_before}
After: {metrics_after}

This technique can be applied by other nodes for similar improvements.
"""

        # Calculate success score based on average improvement
        avg_improvement = sum(improvements.values()) / len(improvements) if improvements else 0
        success_score = min(1.0, max(0.0, 0.5 + (avg_improvement / 100)))

        result = self.brain.add_learning(
            learning=learning_text,
            category="self_improvement",
            source_task=description,
            success_score=success_score,
            applies_to=["builder", "researcher", "orchestrator", "inference"]
        )

        logger.info(f"Recorded self-improvement: {improvement_type}")
        return {
            "success": True,
            "improvement_type": improvement_type,
            "metrics_change": improvements,
            "learning_id": result.get("learning_id")
        }

    # =========================================================================
    # EPISODIC MEMORY SHARING
    # =========================================================================

    def share_significant_episode(
        self,
        episode_summary: str,
        outcome: str,
        significance_score: float,
        lessons_learned: List[str] = None
    ) -> Dict[str, Any]:
        """
        Share a significant episodic memory with the cluster.

        Only share episodes that are valuable for cluster learning.

        Args:
            episode_summary: Brief summary of what happened
            outcome: What was the result (success/failure/partial)
            significance_score: How significant (0.0-1.0)
            lessons_learned: Key takeaways from this episode

        Returns:
            Result with learning_id
        """
        if significance_score < 0.5:
            return {"success": False, "reason": "Episode not significant enough to share"}

        lessons_text = "\n".join(f"- {lesson}" for lesson in (lessons_learned or []))

        learning_text = f"""
SIGNIFICANT EPISODE from {self.node_id}:
Summary: {episode_summary}
Outcome: {outcome}
Significance: {significance_score:.1%}

Lessons Learned:
{lessons_text or '- No specific lessons extracted'}
"""

        success_score = 0.9 if outcome.lower() == "success" else (
            0.5 if "partial" in outcome.lower() else 0.3
        )

        result = self.brain.add_learning(
            learning=learning_text,
            category="episodes",
            source_task=episode_summary[:100],
            success_score=success_score,
            applies_to=["builder", "researcher", "orchestrator", "inference"]
        )

        logger.info(f"Shared significant episode: {episode_summary[:50]}...")
        return result

    # =========================================================================
    # GOAL COORDINATION
    # =========================================================================

    def propose_agi_goal(
        self,
        goal: str,
        description: str,
        priority: int = 5,
        requires_capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Propose a new AGI goal for the cluster.

        Args:
            goal: Short goal statement
            description: Detailed description
            priority: Priority 1-10 (10 highest)
            requires_capabilities: What capabilities are needed

        Returns:
            Result with goal_id
        """
        # Determine which nodes should work on this based on capabilities
        # Configure capability mappings via CAPABILITY_NODE_MAP_JSON env var
        # Example: {"compilation": "builder-node", "inference": "gpu-node"}
        capability_to_node = self._load_capability_map()

        assigned_nodes = set()
        for cap in (requires_capabilities or []):
            cap_lower = cap.lower()
            for key, node in capability_to_node.items():
                if key in cap_lower:
                    assigned_nodes.add(node)

        result = self.brain.add_goal(
            goal=goal,
            description=description,
            priority=priority,
            assigned_nodes=list(assigned_nodes) if assigned_nodes else None
        )

        logger.info(f"Proposed AGI goal: {goal}")
        return result

    def get_agi_goals(self) -> List[Dict]:
        """Get all active AGI goals from the cluster brain."""
        return self.brain.get_active_goals()

    def update_goal_progress(self, goal_id: int, progress: float, status: str = None) -> Dict:
        """Update progress on an AGI goal."""
        return self.brain.update_goal_progress(goal_id, progress, status)

    # =========================================================================
    # TASK ROUTING WITH AGI AWARENESS
    # =========================================================================

    def route_agi_task(
        self,
        task_type: str,
        task_description: str,
        required_skills: List[str] = None
    ) -> Dict[str, Any]:
        """
        Route an AGI task to the best node, considering:
        - Node capabilities (from cluster brain)
        - Historical success rates
        - Required skills

        Args:
            task_type: Type of task
            task_description: Description of the task
            required_skills: Skills needed for this task

        Returns:
            Routing recommendation
        """
        # Get base routing from cluster brain
        routing = self.brain.route_task(task_type, task_description)

        # Enhance with skill-based routing if skills specified
        if required_skills:
            skills_knowledge = self.get_cluster_skills()

            # Find nodes with required skills
            skill_matches = {}
            for skill in skills_knowledge:
                for req_skill in required_skills:
                    if req_skill.lower() in skill.get("concept", "").lower():
                        node = skill.get("contributed_by")
                        if node:
                            skill_matches[node] = skill_matches.get(node, 0) + 1

            if skill_matches:
                # Prefer node with most matching skills
                best_node = max(skill_matches.items(), key=lambda x: x[1])
                routing["skill_based_recommendation"] = {
                    "node": best_node[0],
                    "matching_skills": best_node[1],
                    "total_required": len(required_skills)
                }

        return routing

    # =========================================================================
    # WORKING MEMORY COORDINATION
    # =========================================================================

    def sync_working_memory_to_cluster(
        self,
        context_key: str,
        important_items: List[Dict]
    ) -> Dict[str, Any]:
        """
        Sync important working memory items to cluster for coordination.

        Args:
            context_key: Context identifier (e.g., "current_project")
            important_items: Items to share

        Returns:
            Sync result
        """
        import json

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


        content = f"""
Working Memory Snapshot from {self.node_id}
Context: {context_key}
Timestamp: {datetime.now().isoformat()}

Items:
{json.dumps(important_items, indent=2)}
"""

        result = self.brain.add_knowledge(
            concept=f"Working Memory: {context_key}",
            category="working_memory",
            content=content,
            confidence=0.9
        )

        return {"success": True, "synced_items": len(important_items)}


# Singleton instance
_bridge_instance = None

def get_agi_cluster_bridge() -> AGIClusterBridge:
    """Get or create singleton AGI-Cluster Bridge."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = AGIClusterBridge()
    return _bridge_instance


def register_agi_cluster_bridge_tools(app, bridge_instance=None):
    """
    Register AGI-Cluster Bridge tools with FastMCP.

    Args:
        app: FastMCP application instance
        bridge_instance: Optional pre-initialized bridge
    """
    bridge = bridge_instance or get_agi_cluster_bridge()

    @app.tool()
    async def agi_sync_skill(
        skill_name: str,
        proficiency: float,
        source_task: str = None
    ) -> Dict[str, Any]:
        """
        Sync a learned skill to the cluster brain.

        Makes your skill improvements available to the whole cluster
        for better task routing and knowledge sharing.

        Args:
            skill_name: Name of the skill
            proficiency: Proficiency level (0.0-1.0)
            source_task: What task taught this skill

        Returns:
            Sync result with IDs
        """
        return bridge.sync_skill_to_cluster(skill_name, proficiency, source_task)

    @app.tool()
    async def agi_share_meta_insight(
        domain: str,
        best_strategy: str,
        success_rate: float,
        sample_size: int
    ) -> Dict[str, Any]:
        """
        Share a meta-learning insight with the cluster.

        Tells other nodes which strategies work best for which problems.

        Args:
            domain: Problem domain (nlp, tabular, optimization, etc.)
            best_strategy: Most effective strategy
            success_rate: Success rate (0.0-1.0)
            sample_size: Number of trials

        Returns:
            Result with learning_id
        """
        return bridge.share_meta_learning_insight(
            domain, best_strategy, success_rate, sample_size
        )

    @app.tool()
    async def agi_record_improvement(
        improvement_type: str,
        description: str,
        metrics_before: Dict[str, float],
        metrics_after: Dict[str, float],
        technique: str = None
    ) -> Dict[str, Any]:
        """
        Record a self-improvement outcome.

        Shares what techniques led to measurable improvements.

        Args:
            improvement_type: Type (performance, capability, efficiency)
            description: What was improved
            metrics_before: Metrics before
            metrics_after: Metrics after
            technique: Technique used

        Returns:
            Result with metrics change
        """
        return bridge.record_self_improvement(
            improvement_type, description, metrics_before, metrics_after, technique
        )

    @app.tool()
    async def agi_route_task(
        task_type: str,
        task_description: str,
        required_skills: List[str] = None
    ) -> Dict[str, Any]:
        """
        Route an AGI task to the best node.

        Uses cluster brain + skill matching for optimal routing.

        Args:
            task_type: Task type
            task_description: Description
            required_skills: Skills needed

        Returns:
            Routing recommendation
        """
        return bridge.route_agi_task(task_type, task_description, required_skills)

    @app.tool()
    async def agi_propose_goal(
        goal: str,
        description: str,
        priority: int = 5,
        capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Propose a new AGI goal for the cluster.

        Goals are tracked at the cluster level with automatic
        node assignment based on capabilities.

        Args:
            goal: Short goal statement
            description: Detailed description
            priority: 1-10 (10 highest)
            capabilities: Required capabilities

        Returns:
            Result with goal_id
        """
        return bridge.propose_agi_goal(goal, description, priority, capabilities)

    @app.tool()
    async def agi_get_cluster_learnings(category: str = None) -> Dict[str, Any]:
        """
        Get learnings from the cluster brain.

        Access insights from all nodes including:
        - Meta-learning insights
        - Self-improvement outcomes
        - Significant episodes
        - Skill acquisitions

        Args:
            category: Filter by category (optional)

        Returns:
            List of learnings
        """
        learnings = bridge.brain.get_learnings(category=category)
        return {
            "success": True,
            "count": len(learnings),
            "learnings": learnings
        }

    logger.info(f"✅ AGI-Cluster Bridge tools registered for node: {bridge.node_id}")
    return bridge
