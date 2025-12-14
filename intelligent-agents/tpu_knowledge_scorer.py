#!/usr/bin/env python3
"""
TPU Knowledge Gap Priority Scorer - Intelligent Gap Prioritization

Uses Edge TPU text embeddings to score and prioritize knowledge gaps
based on semantic relevance to current tasks and system goals.

Integration with AGI knowledge gap tracking and autonomous research.

Usage:
    from tpu_knowledge_scorer import TPUKnowledgeScorer

    scorer = TPUKnowledgeScorer()
    prioritized = await scorer.prioritize_gaps(
        gaps=knowledge_gaps,
        task_context="Implementing recursive self-improvement"
    )
"""
import platform

import os
import sys
import json
import time
import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_knowledge_scorer")

# TPU imports
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
except ImportError:
    pass

try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


@dataclass
class KnowledgeGap:
    """Represents a knowledge gap"""
    gap_id: str
    domain: str
    description: str
    gap_type: str  # factual, procedural, conceptual, meta
    severity: float  # 0.0-1.0
    discovered_at: datetime
    relevance_score: Optional[float] = None


@dataclass
class PrioritizedGap:
    """Gap with priority scoring"""
    gap: KnowledgeGap
    priority: float  # Combined priority score
    relevance_to_task: float  # Similarity to current task
    urgency: float  # Based on severity and age
    research_effort: float  # Estimated effort to fill
    reasoning: str


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUKnowledgeScorer:
    """
    Score and prioritize knowledge gaps using TPU embeddings.

    Considers:
    - Relevance to current task
    - Severity of the gap
    - Age/urgency of the gap
    - Estimated research effort
    """

    def __init__(self):
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Domain importance weights (aligned with 75/15/10 rule)
        self.domain_weights = {
            # 75% Reasoning-Centric
            "algorithms": 1.0,
            "mathematics": 1.0,
            "logic": 1.0,
            "formal_methods": 1.0,
            "causal_reasoning": 1.0,
            # 15% Meta-Learning
            "cognitive_science": 0.8,
            "metacognition": 0.8,
            "learning_theory": 0.8,
            "self_improvement": 0.8,
            # 10% Domain Knowledge
            "software_engineering": 0.6,
            "systems": 0.6,
            "security": 0.6,
            "general": 0.4
        }

        # Gap type urgency
        self.type_urgency = {
            "factual": 0.6,
            "procedural": 0.8,
            "conceptual": 0.9,
            "meta": 1.0  # Meta-gaps are most urgent
        }

        if self.use_tpu:
            logger.info("TPU knowledge scoring enabled")
        else:
            logger.info("Using fallback scoring")

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
        cache_key = str(hash(text))
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            start = time.perf_counter()
            embedding = _embed_text(text)
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[cache_key] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "knowledge_embedding",
                        latency_ms=latency,
                        source="knowledge_scorer"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _calculate_urgency(self, gap: KnowledgeGap) -> float:
        """Calculate urgency based on severity and age."""
        # Base urgency from severity
        urgency = gap.severity

        # Boost for older gaps
        age_days = (datetime.now() - gap.discovered_at).days
        age_boost = min(0.3, age_days * 0.02)  # Max 0.3 boost over 15 days

        # Boost for gap type
        type_boost = self.type_urgency.get(gap.gap_type, 0.5) * 0.2

        return min(1.0, urgency + age_boost + type_boost)

    def _estimate_research_effort(self, gap: KnowledgeGap) -> float:
        """Estimate effort to fill gap (0.0 = easy, 1.0 = hard)."""
        effort = 0.5  # Base effort

        # Type-based effort
        if gap.gap_type == "factual":
            effort = 0.3  # Facts are usually quick to look up
        elif gap.gap_type == "procedural":
            effort = 0.5  # Procedures need practice
        elif gap.gap_type == "conceptual":
            effort = 0.7  # Concepts need deep understanding
        elif gap.gap_type == "meta":
            effort = 0.8  # Meta-knowledge is hardest

        # Complexity indicators in description
        complexity_words = ["complex", "advanced", "deep", "fundamental", "theoretical"]
        for word in complexity_words:
            if word in gap.description.lower():
                effort += 0.1

        return min(1.0, effort)

    async def prioritize_gaps(
        self,
        gaps: List[KnowledgeGap],
        task_context: Optional[str] = None,
        goal_context: Optional[str] = None
    ) -> List[PrioritizedGap]:
        """
        Prioritize knowledge gaps.

        Args:
            gaps: List of knowledge gaps to prioritize
            task_context: Current task description (optional)
            goal_context: Current goal description (optional)

        Returns:
            List of gaps sorted by priority (highest first)
        """
        start_time = time.perf_counter()

        # Get context embedding
        context_embedding = None
        if task_context or goal_context:
            full_context = f"{task_context or ''} {goal_context or ''}".strip()
            context_embedding = self._get_embedding(full_context)

        prioritized = []

        for gap in gaps:
            # Calculate relevance to context
            relevance = 0.5  # Default if no context
            if context_embedding is not None:
                gap_embedding = self._get_embedding(gap.description)
                if gap_embedding is not None:
                    relevance = cosine_similarity(context_embedding, gap_embedding)

            # Calculate urgency
            urgency = self._calculate_urgency(gap)

            # Estimate effort
            effort = self._estimate_research_effort(gap)

            # Domain weight
            domain_weight = self.domain_weights.get(gap.domain, 0.5)

            # Calculate priority
            # Higher priority = high relevance, high urgency, low effort, important domain
            priority = (
                0.35 * relevance +
                0.30 * urgency +
                0.15 * (1.0 - effort) +  # Easier = higher priority
                0.20 * domain_weight
            )

            # Build reasoning
            reasoning_parts = []
            if relevance > 0.7:
                reasoning_parts.append(f"Highly relevant to current task")
            if urgency > 0.8:
                reasoning_parts.append(f"Urgent (severity={gap.severity:.2f})")
            if effort < 0.4:
                reasoning_parts.append("Quick to research")
            if domain_weight > 0.8:
                reasoning_parts.append(f"Critical domain ({gap.domain})")

            reasoning = " | ".join(reasoning_parts) if reasoning_parts else "Standard priority"

            prioritized.append(PrioritizedGap(
                gap=gap,
                priority=priority,
                relevance_to_task=relevance,
                urgency=urgency,
                research_effort=effort,
                reasoning=reasoning
            ))

        # Sort by priority (highest first)
        prioritized.sort(key=lambda p: p.priority, reverse=True)

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "gap_prioritization",
                latency_ms=latency_ms,
                source="knowledge_scorer",
                metadata={"gap_count": len(gaps)}
            )

        return prioritized

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "tpu_available": self.use_tpu,
            "cache_size": len(self._embedding_cache),
            "domain_weights": self.domain_weights,
            "type_urgency": self.type_urgency
        }


# CLI
if __name__ == "__main__":
    import asyncio

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


    scorer = TPUKnowledgeScorer()
    print(json.dumps(scorer.get_statistics(), indent=2))

    # Test
    test_gaps = [
        KnowledgeGap(
            gap_id="1", domain="algorithms", description="Recursive optimization algorithms",
            gap_type="conceptual", severity=0.8, discovered_at=datetime.now()
        ),
        KnowledgeGap(
            gap_id="2", domain="general", description="File formatting conventions",
            gap_type="factual", severity=0.3, discovered_at=datetime.now()
        )
    ]

    results = asyncio.run(scorer.prioritize_gaps(
        test_gaps,
        task_context="Implementing self-improvement loop"
    ))

    print("\nPrioritized gaps:")
    for p in results:
        print(f"  {p.gap.description}: priority={p.priority:.3f}")
