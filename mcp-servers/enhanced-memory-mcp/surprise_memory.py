#!/usr/bin/env python3
"""
Surprise-Based Memory Consolidation - Inspired by Google Titans/MIRAS Research

Key Concepts from Titans:
1. Surprise Metrics: Only store unexpected/novel information
2. Low surprise = skip storage, High surprise = trigger memorization
3. Retention Gates: Balance new learning against historical preservation
4. Test-Time Adaptation: Update during inference

This module implements surprise scoring for memory consolidation decisions.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class SurpriseScore:
    """Result of surprise analysis for a memory candidate."""
    score: float  # 0.0 (predictable) to 1.0 (highly surprising)
    novelty_component: float  # How different from existing memories
    salience_component: float  # How important/meaningful
    temporal_component: float  # How unexpected given recent context
    should_store: bool  # Final decision
    reasoning: str  # Explanation for the decision


class SurpriseBasedMemory:
    """
    Implements surprise-based memory consolidation inspired by Titans/MIRAS.

    Key Features:
    - Embedding-based novelty detection
    - Adaptive thresholds based on memory pressure
    - Momentum for capturing related follow-up information
    - Retention gates for forgetting management
    """

    # Thresholds (tunable)
    BASE_SURPRISE_THRESHOLD = 0.4  # Minimum surprise to store
    HIGH_SURPRISE_THRESHOLD = 0.7  # Definitely store
    MOMENTUM_WINDOW = 3  # Store N memories after high-surprise event
    MAX_SIMILAR_MEMORIES = 5  # Max near-duplicates before raising threshold

    # MIRAS-style momentum smoothing parameters
    MOMENTUM_BETA = 0.9  # EMA decay factor (higher = more smoothing)
    MOMENTUM_BOOST = 1.3  # Boost factor for high-momentum periods

    def __init__(self, embedding_fn=None, search_fn=None):
        """
        Initialize surprise-based memory system.

        Args:
            embedding_fn: Function to generate embeddings for text
            search_fn: Function to search existing memories by embedding
        """
        self.embedding_fn = embedding_fn
        self.search_fn = search_fn
        self.momentum_counter = 0
        self.recent_surprises: List[float] = []
        self.adaptive_threshold = self.BASE_SURPRISE_THRESHOLD

        # MIRAS-style momentum smoothing (EMA)
        self.momentum_ema = 0.5  # Running EMA of surprise scores
        self.momentum_gradient = 0.0  # Rate of change in surprise

    def calculate_surprise(
        self,
        content: str,
        memory_type: str = "episodic",
        context: Optional[Dict] = None
    ) -> SurpriseScore:
        """
        Calculate surprise score for a memory candidate.

        Inspired by Titans: Uses gradient-like signals to detect novelty.
        In our case, we use embedding distance as the "gradient signal".

        Args:
            content: The memory content to evaluate
            memory_type: Type of memory (episodic, semantic, procedural)
            context: Optional context (recent memories, session info)

        Returns:
            SurpriseScore with decision and components
        """
        if not self.embedding_fn or not self.search_fn:
            # Fallback: always store if no embedding system
            return SurpriseScore(
                score=0.5,
                novelty_component=0.5,
                salience_component=0.5,
                temporal_component=0.5,
                should_store=True,
                reasoning="No embedding system - defaulting to store"
            )

        try:
            # Generate embedding for candidate
            candidate_embedding = self.embedding_fn(content)

            # Search for similar existing memories
            similar_memories = self.search_fn(
                embedding=candidate_embedding,
                limit=10,
                threshold=0.7  # Cosine similarity threshold
            )

            # Calculate novelty component (inverse of max similarity)
            novelty = self._calculate_novelty(similar_memories)

            # Calculate salience component (importance indicators)
            salience = self._calculate_salience(content, memory_type)

            # Calculate temporal component (unexpected given recent context)
            temporal = self._calculate_temporal_surprise(content, context)

            # Combine components (weighted average)
            # Novelty is most important, followed by salience, then temporal
            raw_score = (
                novelty * 0.5 +
                salience * 0.3 +
                temporal * 0.2
            )

            # MIRAS-style momentum smoothing (EMA)
            # m_t = β * m_{t-1} + (1-β) * score_t
            old_ema = self.momentum_ema
            self.momentum_ema = (
                self.MOMENTUM_BETA * self.momentum_ema +
                (1 - self.MOMENTUM_BETA) * raw_score
            )
            self.momentum_gradient = raw_score - old_ema

            # Apply momentum boost when gradient is positive (rising surprise)
            # This implements MIRAS's "momentum smooths surprise signals"
            if self.momentum_gradient > 0.1:
                # Rising surprise trend - boost current score
                combined_score = min(1.0, raw_score * self.MOMENTUM_BOOST)
            elif self.momentum_gradient < -0.1:
                # Falling surprise trend - slight dampening
                combined_score = raw_score * 0.95
            else:
                combined_score = raw_score

            # Apply momentum: if we recently saw high surprise, lower threshold
            effective_threshold = self._get_effective_threshold()

            # Make decision
            should_store = combined_score >= effective_threshold

            # Update momentum if high surprise
            if combined_score >= self.HIGH_SURPRISE_THRESHOLD:
                self.momentum_counter = self.MOMENTUM_WINDOW
            elif self.momentum_counter > 0:
                self.momentum_counter -= 1
                should_store = True  # Store due to momentum

            # Update recent surprises for adaptive threshold
            self.recent_surprises.append(combined_score)
            if len(self.recent_surprises) > 100:
                self.recent_surprises = self.recent_surprises[-100:]
            self._update_adaptive_threshold()

            reasoning = self._generate_reasoning(
                novelty, salience, temporal, combined_score,
                effective_threshold, should_store, len(similar_memories)
            )

            return SurpriseScore(
                score=combined_score,
                novelty_component=novelty,
                salience_component=salience,
                temporal_component=temporal,
                should_store=should_store,
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"Error calculating surprise: {e}")
            # On error, default to storing (conservative)
            return SurpriseScore(
                score=0.5,
                novelty_component=0.5,
                salience_component=0.5,
                temporal_component=0.5,
                should_store=True,
                reasoning=f"Error in calculation, defaulting to store: {e}"
            )

    def _calculate_novelty(self, similar_memories: List[Dict]) -> float:
        """
        Calculate novelty score based on similarity to existing memories.

        High novelty = low similarity to existing memories = high surprise
        """
        if not similar_memories:
            return 1.0  # Completely novel - nothing similar exists

        # Get highest similarity score
        max_similarity = max(m.get('score', 0) for m in similar_memories)

        # Novelty is inverse of similarity
        novelty = 1.0 - max_similarity

        # Penalize if too many similar memories exist
        similar_count = len([m for m in similar_memories if m.get('score', 0) > 0.8])
        if similar_count >= self.MAX_SIMILAR_MEMORIES:
            novelty *= 0.5  # Reduce novelty if we have many similar memories

        return min(1.0, max(0.0, novelty))

    def _calculate_salience(self, content: str, memory_type: str) -> float:
        """
        Calculate salience/importance score based on content characteristics.

        Indicators of importance:
        - Length (but not too long - verbose != important)
        - Presence of key terms (error, success, learned, discovered, etc.)
        - Memory type (procedural > semantic > episodic for salience)
        - Structured content (code, lists, specific data)
        """
        salience = 0.5  # Base salience

        # Length factor (optimal around 100-500 chars)
        length = len(content)
        if 100 <= length <= 500:
            salience += 0.1
        elif length > 1000:
            salience -= 0.1

        # Key terms indicating importance
        importance_terms = [
            'error', 'bug', 'fix', 'solution', 'learned', 'discovered',
            'important', 'critical', 'success', 'failure', 'insight',
            'pattern', 'principle', 'rule', 'always', 'never', 'must'
        ]
        content_lower = content.lower()
        term_count = sum(1 for term in importance_terms if term in content_lower)
        salience += min(0.3, term_count * 0.05)

        # Memory type factor
        type_factors = {
            'procedural': 0.15,  # Skills are valuable
            'semantic': 0.10,   # Knowledge is valuable
            'episodic': 0.0,    # Experiences baseline
            'working': -0.1     # Working memory less important for long-term
        }
        salience += type_factors.get(memory_type, 0)

        # Structured content bonus
        if any(indicator in content for indicator in ['```', '- ', '1.', '* ']):
            salience += 0.1

        return min(1.0, max(0.0, salience))

    def _calculate_temporal_surprise(
        self,
        content: str,
        context: Optional[Dict]
    ) -> float:
        """
        Calculate temporal surprise - how unexpected given recent context.

        Topic shifts, unexpected outcomes, contradictions = high temporal surprise
        """
        if not context:
            return 0.5  # Neutral if no context

        temporal = 0.5

        # Check for topic continuity
        recent_topics = context.get('recent_topics', [])
        if recent_topics:
            # Simple word overlap check (could use embeddings for better)
            content_words = set(content.lower().split())
            topic_overlap = sum(
                len(content_words.intersection(set(t.lower().split())))
                for t in recent_topics
            ) / max(1, len(recent_topics))

            # Low overlap = topic shift = higher temporal surprise
            if topic_overlap < 2:
                temporal += 0.2
            elif topic_overlap > 10:
                temporal -= 0.1

        # Check for outcome surprise (if tracking expectations)
        expected_outcome = context.get('expected_outcome')
        if expected_outcome:
            if 'error' in content.lower() and 'success' in expected_outcome.lower():
                temporal += 0.3  # Unexpected failure
            elif 'success' in content.lower() and 'error' in expected_outcome.lower():
                temporal += 0.2  # Unexpected success

        return min(1.0, max(0.0, temporal))

    def _get_effective_threshold(self) -> float:
        """
        Get effective threshold, accounting for momentum.

        After high-surprise event, lower threshold to capture related info.
        """
        if self.momentum_counter > 0:
            # Lower threshold during momentum window
            return self.adaptive_threshold * 0.7
        return self.adaptive_threshold

    def _update_adaptive_threshold(self):
        """
        Update adaptive threshold based on recent surprise distribution.

        If seeing lots of high-surprise items, raise threshold (more selective).
        If seeing lots of low-surprise items, lower threshold (capture more).
        """
        if len(self.recent_surprises) < 10:
            return

        avg_surprise = np.mean(self.recent_surprises[-50:])

        # Adjust threshold to maintain ~30% storage rate
        if avg_surprise > 0.6:
            # Too much surprising content, be more selective
            self.adaptive_threshold = min(0.7, self.adaptive_threshold + 0.05)
        elif avg_surprise < 0.3:
            # Too little surprising content, be less selective
            self.adaptive_threshold = max(0.2, self.adaptive_threshold - 0.05)

    def _generate_reasoning(
        self,
        novelty: float,
        salience: float,
        temporal: float,
        combined: float,
        threshold: float,
        should_store: bool,
        similar_count: int
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        parts = []

        if should_store:
            parts.append(f"STORE (score={combined:.2f} >= threshold={threshold:.2f})")
        else:
            parts.append(f"SKIP (score={combined:.2f} < threshold={threshold:.2f})")

        # Explain components
        if novelty > 0.7:
            parts.append("highly novel content")
        elif novelty < 0.3:
            parts.append(f"similar to {similar_count} existing memories")

        if salience > 0.7:
            parts.append("high importance indicators")
        elif salience < 0.3:
            parts.append("low importance signals")

        if temporal > 0.7:
            parts.append("unexpected topic/outcome")
        elif temporal < 0.3:
            parts.append("follows expected pattern")

        if self.momentum_counter > 0:
            parts.append(f"momentum active ({self.momentum_counter} remaining)")

        # MIRAS momentum smoothing info
        if self.momentum_gradient > 0.1:
            parts.append(f"⬆ rising surprise (grad={self.momentum_gradient:.2f})")
        elif self.momentum_gradient < -0.1:
            parts.append(f"⬇ falling surprise (grad={self.momentum_gradient:.2f})")

        return " | ".join(parts)


class RetentionGate:
    """
    Retention gate for managing memory capacity - inspired by MIRAS.

    Balances:
    - New learning (storing fresh information)
    - Historical preservation (keeping important old memories)
    - Capacity management (forgetting less important items)
    """

    def __init__(self, max_memories: int = 10000, decay_rate: float = 0.01):
        """
        Initialize retention gate.

        Args:
            max_memories: Maximum memories before triggering cleanup
            decay_rate: How fast old memories lose retention priority
        """
        self.max_memories = max_memories
        self.decay_rate = decay_rate
        self.access_counts: Dict[str, int] = {}
        self.last_access: Dict[str, datetime] = {}

    def calculate_retention_score(
        self,
        memory_id: str,
        original_surprise: float,
        created_at: datetime,
        memory_type: str
    ) -> float:
        """
        Calculate retention priority for a memory.

        Higher score = more likely to be retained during cleanup.
        """
        # Base score from original surprise
        score = original_surprise * 0.4

        # Access frequency bonus
        access_count = self.access_counts.get(memory_id, 0)
        frequency_bonus = min(0.3, access_count * 0.02)
        score += frequency_bonus

        # Recency bonus (exponential decay)
        age_days = (datetime.now() - created_at).days
        recency_bonus = 0.2 * np.exp(-self.decay_rate * age_days)
        score += recency_bonus

        # Memory type factor
        type_retention = {
            'procedural': 0.15,  # Skills persist
            'semantic': 0.10,   # Knowledge persists
            'episodic': 0.05,   # Episodes fade faster
            'working': 0.0      # Working memory most transient
        }
        score += type_retention.get(memory_type, 0)

        return min(1.0, max(0.0, score))

    def record_access(self, memory_id: str):
        """Record memory access for retention scoring."""
        self.access_counts[memory_id] = self.access_counts.get(memory_id, 0) + 1
        self.last_access[memory_id] = datetime.now()

    def get_candidates_for_forgetting(
        self,
        memories: List[Dict],
        count_to_remove: int
    ) -> List[str]:
        """
        Get memory IDs that are candidates for forgetting.

        Returns lowest retention score memories.
        """
        scored = []
        for mem in memories:
            mem_id = mem.get('id', '')
            score = self.calculate_retention_score(
                memory_id=mem_id,
                original_surprise=mem.get('surprise_score', 0.5),
                created_at=datetime.fromisoformat(mem.get('created_at', datetime.now().isoformat())),
                memory_type=mem.get('memory_type', 'episodic')
            )
            scored.append((mem_id, score))

        # Sort by score (ascending) and return lowest
        scored.sort(key=lambda x: x[1])
        return [mem_id for mem_id, _ in scored[:count_to_remove]]


# Convenience functions for integration
def create_surprise_scorer(qdrant_client=None, embedding_model=None):
    """
    Factory function to create surprise scorer with Qdrant integration.
    """
    def embedding_fn(text: str) -> List[float]:
        if embedding_model:
            return embedding_model.encode(text).tolist()
        # Fallback to SAFLA embeddings if available
        try:
            from safla_tools import generate_embeddings
            return generate_embeddings([text])[0]
        except:
            return []

    def search_fn(embedding: List[float], limit: int, threshold: float) -> List[Dict]:
        if not qdrant_client or not embedding:
            return []
        try:
            results = qdrant_client.search(
                collection_name="memories",
                query_vector=embedding,
                limit=limit,
                score_threshold=threshold
            )
            return [{'id': r.id, 'score': r.score} for r in results]
        except:
            return []

    return SurpriseBasedMemory(
        embedding_fn=embedding_fn if embedding_model or True else None,
        search_fn=search_fn if qdrant_client else None
    )


if __name__ == "__main__":
    # Test the surprise scoring
    import sys

    scorer = SurpriseBasedMemory()

    test_cases = [
        ("I learned that Python dict comprehensions are faster than loops for building dictionaries.", "semantic"),
        ("The meeting was at 2pm.", "episodic"),
        ("CRITICAL ERROR: Database connection failed after timeout. Fixed by increasing pool size.", "procedural"),
        ("Had coffee.", "episodic"),
        ("Discovered that using batch operations reduces API calls by 90% - major performance insight!", "semantic"),
    ]

    print("Surprise-Based Memory Scoring Test")
    print("=" * 60)

    for content, mem_type in test_cases:
        score = scorer.calculate_surprise(content, mem_type)
        print(f"\nContent: {content[:60]}...")
        print(f"Type: {mem_type}")
        print(f"Score: {score.score:.2f} | Store: {score.should_store}")
        print(f"Components: novelty={score.novelty_component:.2f}, "
              f"salience={score.salience_component:.2f}, "
              f"temporal={score.temporal_component:.2f}")
        print(f"Reasoning: {score.reasoning}")
