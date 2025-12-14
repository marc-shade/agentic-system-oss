#!/usr/bin/env python3
"""
Conversation-Feedback Bridge
=============================

Integrates the conversation memory system with the feedback loop to enable:
1. Learning from inter-node task outcomes
2. Recording facts about node performance/reliability
3. Tracking relationship quality between nodes
4. Using conversation history to inform improvement proposals

Integration Points:
- FeedbackLoop events -> ConversationContextManager fact storage
- Node performance data -> Meta-learning recommendations
"""
import os
import platform

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "node-chat-mcp"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationFeedbackBridge:
    """
    Bridges the conversation memory system with the feedback loop.

    This enables the cluster to:
    - Learn which nodes are reliable for specific task types
    - Build up relationship knowledge through task outcomes
    - Use conversation history to inform improvement proposals
    """

    def __init__(self, storage_base: str = str(_STORAGE_BASE)):
        self.storage_base = Path(storage_base)
        self._feedback_loop = None
        self._context_manager = None
        self._node_id = self._detect_node_id()
        self._subscribed = False

    def _detect_node_id(self) -> str:
        """Detect current node ID from environment or config."""
        import socket
        hostname = socket.gethostname().lower()

        node_map = {
            'mac-studio': 'mac-studio',
            'macpro51': 'macpro51',
            'macbook-air': 'macbook-air-m3',
            'completeu': 'completeu-server'
        }

        for key, node_id in node_map.items():
            if key in hostname:
                return node_id
        return 'unknown'

    @property
    def feedback_loop(self):
        """Lazy load feedback loop."""
        if self._feedback_loop is None:
            try:
                from feedback_loop import get_feedback_loop
                self._feedback_loop = get_feedback_loop()
            except ImportError as e:
                logger.warning(f"Feedback loop not available: {e}")
        return self._feedback_loop

    @property
    def context_manager(self):
        """Lazy load conversation context manager."""
        if self._context_manager is None:
            try:
                from conversation_context import ConversationContextManager
                self._context_manager = ConversationContextManager(
                    node_id=self._node_id,
                    storage_base=str(self.storage_base)
                )
            except ImportError as e:
                logger.warning(f"Conversation context manager not available: {e}")
        return self._context_manager

    def subscribe_to_feedback_events(self):
        """Subscribe to feedback loop events to capture inter-node task outcomes."""
        if self._subscribed or not self.feedback_loop:
            return

        # Subscribe to evaluation completions
        self.feedback_loop.subscribe('eval_complete', self._on_eval_complete)

        # Subscribe to improvement events
        self.feedback_loop.subscribe('improvement_verified', self._on_improvement_verified)

        # Subscribe to modification events
        self.feedback_loop.subscribe('modification_applied', self._on_modification_applied)

        self._subscribed = True
        logger.info("ConversationFeedbackBridge subscribed to feedback events")

    def _on_eval_complete(self, event):
        """Handle evaluation completion - record as node fact if inter-node task."""
        if not self.context_manager:
            return

        data = event.data
        agent_id = data.get('agent_id', '')

        # Check if this is an inter-node task (agent_id contains node name)
        target_node = self._extract_node_from_agent(agent_id)
        if not target_node or target_node == self._node_id:
            return

        score = data.get('score', 0.0)
        passed = data.get('passed', False)
        eval_type = data.get('eval_type', 'unknown')

        # Determine fact type and content based on outcome
        if passed and score > 0.8:
            fact_type = 'capability'
            content = f"Excellent performance on {eval_type} task (score: {score:.2f})"
            confidence = min(score, 0.95)
        elif passed:
            fact_type = 'capability'
            content = f"Completed {eval_type} task successfully (score: {score:.2f})"
            confidence = score * 0.9
        else:
            fact_type = 'limitation'
            content = f"Struggled with {eval_type} task (score: {score:.2f})"
            confidence = 0.7

        # Store fact about the node
        self.context_manager.add_fact_about_node(
            about_node=target_node,
            fact_type=fact_type,
            fact_content=content,
            confidence=confidence
        )

        logger.info(f"Recorded fact about {target_node}: {fact_type} - {content}")

    def _on_improvement_verified(self, event):
        """Handle improvement verification - update relationship quality."""
        if not self.context_manager:
            return

        data = event.data
        decision = data.get('decision')
        improvement = data.get('improvement', 0.0)

        # If improvement was significant, record as highlight
        if decision == 'keep' and improvement > 0.1:
            # Record as a significant cluster event
            content = f"Improvement cycle verified: {improvement:.1%} gain"

            # Add as highlight for all nodes we've interacted with
            for node_id in ['mac-studio', 'macpro51', 'macbook-air-m3', 'completeu-server']:
                if node_id != self._node_id:
                    self._add_highlight(node_id, content, 'improvement')

    def _on_modification_applied(self, event):
        """Handle modification applied - log as conversation event."""
        data = event.data
        modification_id = data.get('modification_id', 'unknown')

        logger.info(f"Modification {modification_id} applied - tracking for feedback")

    def _extract_node_from_agent(self, agent_id: str) -> Optional[str]:
        """Extract node ID from agent ID if it's an inter-node agent."""
        agent_lower = agent_id.lower()

        node_patterns = {
            'macpro51': 'macpro51',
            'mac-studio': 'mac-studio',
            'macbook-air': 'macbook-air-m3',
            'completeu': 'completeu-server'
        }

        for pattern, node_id in node_patterns.items():
            if pattern in agent_lower:
                return node_id
        return None

    def _add_highlight(self, node_id: str, content: str, reason: str):
        """Add a conversation highlight."""
        if not self.context_manager:
            return

        try:
            self.context_manager.add_highlight(
                with_node=node_id,
                message_content=content,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to add highlight: {e}")

    def get_node_reliability_for_task(self, task_type: str, node_id: str) -> float:
        """
        Get reliability score for a node on a specific task type.

        This can be used by meta-learning to inform agent recommendations.
        """
        if not self.context_manager:
            return 0.5  # Default neutral score

        facts = self.context_manager._get_facts_about_node(node_id)

        relevant_facts = [
            f for f in facts
            if task_type.lower() in f.get('content', '').lower()
        ]

        if not relevant_facts:
            return 0.5

        # Calculate weighted score from facts
        total_weight = 0.0
        weighted_score = 0.0

        for fact in relevant_facts:
            confidence = fact.get('confidence', 0.5)
            fact_type = fact.get('type', '')

            if fact_type == 'capability':
                score = 0.8
            elif fact_type == 'limitation':
                score = 0.3
            else:
                score = 0.5

            weighted_score += score * confidence
            total_weight += confidence

        return weighted_score / total_weight if total_weight > 0 else 0.5

    def recommend_node_for_task(self, task_type: str) -> Dict[str, Any]:
        """
        Recommend the best node for a task based on conversation memory.

        Returns node rankings based on stored facts and relationship history.
        """
        nodes = ['mac-studio', 'macpro51', 'macbook-air-m3', 'completeu-server']
        rankings = {}

        for node in nodes:
            if node == self._node_id:
                continue

            reliability = self.get_node_reliability_for_task(task_type, node)

            # Get relationship info if available
            relationship_bonus = 0.0
            if self.context_manager:
                relationship = self.context_manager._get_relationship(node)
                if relationship.get('relationship_exists'):
                    # Bonus for existing relationship
                    relationship_bonus = 0.1

            rankings[node] = {
                'reliability_score': reliability,
                'relationship_bonus': relationship_bonus,
                'total_score': reliability + relationship_bonus
            }

        # Sort by total score
        sorted_nodes = sorted(
            rankings.items(),
            key=lambda x: x[1]['total_score'],
            reverse=True
        )

        return {
            'recommended_node': sorted_nodes[0][0] if sorted_nodes else None,
            'rankings': dict(sorted_nodes),
            'task_type': task_type
        }

    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of the conversation-feedback integration."""
        return {
            'bridge_active': True,
            'node_id': self._node_id,
            'feedback_loop_connected': self._feedback_loop is not None,
            'context_manager_connected': self._context_manager is not None,
            'subscribed_to_events': self._subscribed,
            'storage_base': str(self.storage_base)
        }


# Singleton instance
_bridge_instance = None


def get_bridge() -> ConversationFeedbackBridge:
    """Get or create the singleton bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ConversationFeedbackBridge()
        _bridge_instance.subscribe_to_feedback_events()
    return _bridge_instance


if __name__ == "__main__":
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


    # Demo usage
    bridge = ConversationFeedbackBridge()

    print("=== Conversation-Feedback Bridge Status ===")
    print(json.dumps(bridge.get_integration_status(), indent=2))

    print("\n=== Node Recommendation for 'build' task ===")
    recommendation = bridge.recommend_node_for_task('build')
    print(json.dumps(recommendation, indent=2))

    print("\n=== Node Recommendation for 'research' task ===")
    recommendation = bridge.recommend_node_for_task('research')
    print(json.dumps(recommendation, indent=2))
