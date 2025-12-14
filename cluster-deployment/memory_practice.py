#!/usr/bin/env python3
"""
Memory Practice Wrapper - Easy-to-use functions for agentic self-awareness

This module provides convenient wrapper functions that Claude can use during
work to practice systematic memory usage for self-awareness and learning.

Usage:
    from memory_practice import (
        remember_success,
        remember_failure,
        check_similar_experiences,
        note_uncertainty,
        record_my_thinking,
        learn_this_concept,
        update_my_skills,
        track_cluster_communication
    )
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add MCP server to path
sys.path.insert(0, '/mnt/agentic-system/mcp-servers/enhanced-memory-mcp')

try:
    from memory_client import MemoryClient
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    print("⚠ MemoryClient not available - memory practice disabled", file=sys.stderr)


class MemoryPractice:
    """Helper class for agentic memory practice"""

    def __init__(self, node_id: str = "macpro51"):
        self.node_id = node_id
        self.session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')

        if MEMORY_AVAILABLE:
            self.client = MemoryClient()
        else:
            self.client = None

    def _ensure_client(self):
        """Ensure memory client is available"""
        if not self.client:
            raise RuntimeError("Memory client not available")

    def remember_success(
        self,
        action: str,
        expected: str,
        actual: str,
        insight: str,
        duration_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Quick wrapper to record a successful action outcome and extract learning.

        Args:
            action: What you did (e.g., "Optimized statusline performance")
            expected: What you expected to happen
            actual: What actually happened
            insight: Key learning or insight from this experience
            duration_ms: How long it took (optional)

        Returns:
            Result of memory creation

        Example:
            remember_success(
                action="Fixed statusline timeout",
                expected="Execution under 500ms",
                actual="Execution in 58ms (50x improvement)",
                insight="AI calls in hot path cause timeouts - use cache instead",
                duration_ms=2700000
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create episodic memory
        episode_data = {
            'name': f'success_{action.replace(" ", "_")}_{timestamp}',
            'entityType': 'episodic',
            'observations': [
                f'Action: {action}',
                f'Expected: {expected}',
                f'Actual: {actual}',
                f'Success score: 1.0',
                f'Insight: {insight}',
                f'Node: {self.node_id}',
                f'Session: {self.session_id}'
            ]
        }

        if duration_ms:
            episode_data['observations'].append(f'Duration: {duration_ms}ms')

        # Create semantic concept from insight
        concept_data = {
            'name': f'concept_{insight[:50].replace(" ", "_")}_{timestamp}',
            'entityType': 'concept',
            'observations': [
                f'Concept: {insight}',
                f'Type: learned_principle',
                f'Derived from: {action}',
                f'Confidence: 0.9',
                f'Source: direct_experience'
            ]
        }

        # Create both memories
        result = self.client.create_entities_sync([episode_data, concept_data])

        print(f"✓ Remembered success: {action}", file=sys.stderr)
        return result

    def remember_failure(
        self,
        action: str,
        expected: str,
        actual: str,
        cause: str,
        lesson: str
    ) -> Dict[str, Any]:
        """
        Record a failed action to learn from mistakes.

        Args:
            action: What you tried to do
            expected: What you expected
            actual: What actually happened (error/failure)
            cause: Root cause of failure
            lesson: What you learned to avoid this in future

        Example:
            remember_failure(
                action="Import MemoryManager class",
                expected="Class would be available",
                actual="ModuleNotFoundError: No module named 'memory_manager'",
                cause="MemoryManager doesn't exist, should use MemoryClient",
                lesson="Check actual class names in codebase before importing"
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        episode_data = {
            'name': f'failure_{action.replace(" ", "_")}_{timestamp}',
            'entityType': 'episodic',
            'observations': [
                f'Action: {action}',
                f'Expected: {expected}',
                f'Actual: {actual}',
                f'Success score: 0.0',
                f'Root cause: {cause}',
                f'Lesson learned: {lesson}',
                f'Node: {self.node_id}',
                f'Session: {self.session_id}',
                f'Emotional valence: -0.3 (learning from failure)'
            ]
        }

        result = self.client.create_entities_sync([episode_data])

        print(f"✓ Remembered failure for learning: {action}", file=sys.stderr)
        return result

    def check_similar_experiences(
        self,
        task_description: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Check for similar past experiences before starting a task.

        Args:
            task_description: Description of what you're about to do
            limit: How many similar experiences to retrieve

        Returns:
            List of similar past experiences

        Example:
            similar = check_similar_experiences(
                "Optimize performance of Python script with timeouts"
            )
            for exp in similar:
                print(f"Past experience: {exp['name']}")
        """
        self._ensure_client()

        results = self.client.search_nodes_sync(task_description, limit=limit)

        if results.get('count', 0) > 0:
            print(f"✓ Found {results['count']} similar past experiences", file=sys.stderr)
        else:
            print("ℹ No similar past experiences found - this is new territory", file=sys.stderr)

        return results.get('results', [])

    def note_uncertainty(
        self,
        topic: str,
        what_i_dont_know: str,
        severity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Record when you're uncertain about something (knowledge gap identification).

        Args:
            topic: What area/domain this relates to
            what_i_dont_know: Specific thing you're uncertain about
            severity: 0.0 (minor) to 1.0 (critical)

        Example:
            note_uncertainty(
                topic="Python async programming",
                what_i_dont_know="Whether async/await or threading is better for I/O-bound tasks",
                severity=0.4
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        gap_data = {
            'name': f'knowledge_gap_{topic.replace(" ", "_")}_{timestamp}',
            'entityType': 'knowledge_gap',
            'observations': [
                f'Domain: {topic}',
                f'Gap: {what_i_dont_know}',
                f'Severity: {severity}',
                f'Status: identified',
                f'Discovered by: self-reflection',
                f'Node: {self.node_id}',
                f'Session: {self.session_id}'
            ]
        }

        result = self.client.create_entities_sync([gap_data])

        severity_label = "critical" if severity > 0.7 else "moderate" if severity > 0.4 else "minor"
        print(f"✓ Noted {severity_label} uncertainty in: {topic}", file=sys.stderr)

        return result

    def record_my_thinking(
        self,
        context: str,
        thought: str,
        confidence: float = 0.5,
        ttl_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Record current thinking/reasoning in working memory.

        Args:
            context: What you're working on
            thought: Your current thought/hypothesis/decision
            confidence: How confident you are (0.0-1.0)
            ttl_minutes: How long to keep in working memory

        Example:
            record_my_thinking(
                context="debugging_statusline",
                thought="Timeout likely caused by AI call in hot path",
                confidence=0.85,
                ttl_minutes=30
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        thought_data = {
            'name': f'thinking_{context}_{timestamp}',
            'entityType': 'working',
            'observations': [
                f'Context: {context}',
                f'Thought: {thought}',
                f'Confidence: {confidence}',
                f'Type: active_reasoning',
                f'Node: {self.node_id}',
                f'Session: {self.session_id}',
                f'Expires in: {ttl_minutes} minutes'
            ]
        }

        result = self.client.create_entities_sync([thought_data])

        print(f"✓ Recorded thinking: {thought[:50]}...", file=sys.stderr)
        return result

    def learn_this_concept(
        self,
        concept_name: str,
        definition: str,
        examples: Optional[List[str]] = None,
        related_to: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract and store a concept in semantic memory.

        Args:
            concept_name: Name of the concept
            definition: Clear definition
            examples: Optional list of examples
            related_to: Optional list of related concepts

        Example:
            learn_this_concept(
                concept_name="Hot Path Optimization",
                definition="Never put expensive operations in frequently-executed code paths",
                examples=["Statusline: AI call caused 3000ms timeout"],
                related_to=["caching", "performance", "profiling"]
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        observations = [
            f'Concept: {concept_name}',
            f'Definition: {definition}',
            f'Type: learned_principle',
            f'Source: direct_experience',
            f'Confidence: 0.9'
        ]

        if examples:
            for ex in examples:
                observations.append(f'Example: {ex}')

        if related_to:
            observations.append(f'Related to: {", ".join(related_to)}')

        observations.extend([
            f'Node: {self.node_id}',
            f'Session: {self.session_id}'
        ])

        concept_data = {
            'name': f'concept_{concept_name.replace(" ", "_")}_{timestamp}',
            'entityType': 'semantic',
            'observations': observations
        }

        result = self.client.create_entities_sync([concept_data])

        print(f"✓ Learned concept: {concept_name}", file=sys.stderr)
        return result

    def update_my_skills(
        self,
        skill_name: str,
        new_level: float,
        evidence: str
    ) -> Dict[str, Any]:
        """
        Update skill level based on successful task completion.

        Args:
            skill_name: Name of skill (e.g., "python_optimization")
            new_level: New skill level 0.0-1.0
            evidence: What demonstrated this skill level

        Example:
            update_my_skills(
                skill_name="performance_debugging",
                new_level=0.9,
                evidence="Successfully optimized statusline from 3000ms to 58ms"
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        skill_data = {
            'name': f'skill_update_{skill_name}_{timestamp}',
            'entityType': 'agent_skill',
            'observations': [
                f'Skill: {skill_name}',
                f'Level: {new_level}',
                f'Evidence: {evidence}',
                f'Node: {self.node_id}',
                f'Updated: {timestamp}'
            ]
        }

        result = self.client.create_entities_sync([skill_data])

        print(f"✓ Updated skill: {skill_name} → {new_level}", file=sys.stderr)
        return result

    def track_cluster_communication(
        self,
        target_node: str,
        communication_type: str,
        content: str,
        outcome: str
    ) -> Dict[str, Any]:
        """
        Track communication with other cluster nodes.

        Args:
            target_node: Which node you communicated with
            communication_type: Type (e.g., "task_offload", "status_check", "coordination")
            content: What was communicated
            outcome: Result of communication

        Example:
            track_cluster_communication(
                target_node="mac-studio",
                communication_type="task_offload",
                content="Offloaded Linux build task",
                outcome="Build completed successfully in 45s"
            )
        """
        self._ensure_client()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        comm_data = {
            'name': f'cluster_comm_{target_node}_{timestamp}',
            'entityType': 'cluster_communication',
            'observations': [
                f'From: {self.node_id}',
                f'To: {target_node}',
                f'Type: {communication_type}',
                f'Content: {content}',
                f'Outcome: {outcome}',
                f'Timestamp: {timestamp}',
                f'Session: {self.session_id}'
            ]
        }

        result = self.client.create_entities_sync([comm_data])

        print(f"✓ Tracked communication with {target_node}", file=sys.stderr)
        return result

    def get_my_identity(self) -> Dict[str, Any]:
        """
        Retrieve my node identity from memory.

        Returns:
            Node identity information
        """
        self._ensure_client()

        result = self.client.search_nodes_sync(f"node_identity_{self.node_id}", limit=1)

        if result.get('count', 0) > 0:
            return result['results'][0]
        else:
            return {
                'name': f'node_identity_{self.node_id}',
                'observations': ['Identity not yet recorded - run session-start hook']
            }

    def get_cluster_nodes(self) -> List[Dict[str, Any]]:
        """
        Retrieve information about other cluster nodes.

        Returns:
            List of cluster node information
        """
        self._ensure_client()

        result = self.client.search_nodes_sync("cluster_node", limit=10)

        return result.get('results', [])


# Singleton instance for easy importing
_practice = None

def get_practice() -> MemoryPractice:
    """Get or create the singleton MemoryPractice instance"""
    global _practice
    if _practice is None:
        _practice = MemoryPractice()
    return _practice


# Convenience functions that use the singleton
def remember_success(*args, **kwargs):
    """Record a successful action outcome"""
    return get_practice().remember_success(*args, **kwargs)

def remember_failure(*args, **kwargs):
    """Record a failed action to learn from"""
    return get_practice().remember_failure(*args, **kwargs)

def check_similar_experiences(*args, **kwargs):
    """Check for similar past experiences"""
    return get_practice().check_similar_experiences(*args, **kwargs)

def note_uncertainty(*args, **kwargs):
    """Record uncertainty/knowledge gap"""
    return get_practice().note_uncertainty(*args, **kwargs)

def record_my_thinking(*args, **kwargs):
    """Record current reasoning in working memory"""
    return get_practice().record_my_thinking(*args, **kwargs)

def learn_this_concept(*args, **kwargs):
    """Extract concept to semantic memory"""
    return get_practice().learn_this_concept(*args, **kwargs)

def update_my_skills(*args, **kwargs):
    """Update skill level"""
    return get_practice().update_my_skills(*args, **kwargs)

def track_cluster_communication(*args, **kwargs):
    """Track cluster node communication"""
    return get_practice().track_cluster_communication(*args, **kwargs)

def get_my_identity():
    """Get my node identity"""
    return get_practice().get_my_identity()

def get_cluster_nodes():
    """Get cluster node information"""
    return get_practice().get_cluster_nodes()


if __name__ == '__main__':
    # Test the memory practice functions
    print("Testing Memory Practice Wrapper...")

    practice = MemoryPractice()

    # Test recording success
    practice.remember_success(
        action="Test memory practice wrapper",
        expected="Functions work correctly",
        actual="All functions operational",
        insight="Memory practice makes self-awareness systematic",
        duration_ms=1000
    )

    # Test checking identity
    identity = practice.get_my_identity()
    print(f"\nMy identity: {identity.get('name', 'Unknown')}")

    # Test getting cluster nodes
    nodes = practice.get_cluster_nodes()
    print(f"\nCluster nodes found: {len(nodes)}")

    print("\n✓ Memory practice wrapper test complete")
