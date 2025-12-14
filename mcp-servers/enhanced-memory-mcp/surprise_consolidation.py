#!/usr/bin/env python3
"""
Surprise-Based Memory Consolidation Integration

Integrates the Titans/MIRAS-inspired surprise scoring with the
memory consolidation pipeline.

This module provides:
1. Surprise-aware episodic → semantic promotion
2. Retention gate for memory capacity management
3. Metrics and logging for consolidation decisions
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# Import surprise scoring
from surprise_memory import SurpriseBasedMemory, RetentionGate, SurpriseScore

logger = logging.getLogger(__name__)

# Configuration
CONSOLIDATION_CONFIG = {
    "min_surprise_for_promotion": 0.4,  # Minimum surprise to promote episodic → semantic
    "high_surprise_immediate_promote": 0.8,  # Immediately promote very surprising memories
    "max_semantic_memories": 50000,  # Trigger cleanup above this
    "retention_decay_rate": 0.02,  # Daily decay rate for retention scoring
    "momentum_window": 5,  # Store related memories after high-surprise event
    "metrics_file": "/mnt/agentic-system/databases/surprise_consolidation_metrics.jsonl"
}


@dataclass
class ConsolidationMetrics:
    """Metrics for a consolidation run."""
    timestamp: str
    memories_evaluated: int
    memories_promoted: int
    memories_skipped: int
    memories_forgotten: int
    average_surprise_score: float
    high_surprise_count: int
    low_surprise_count: int
    retention_gate_triggered: bool
    duration_seconds: float


class SurpriseConsolidator:
    """
    Consolidator that uses surprise-based scoring to decide
    which memories to promote from episodic to semantic.
    """

    def __init__(self, qdrant_client=None, embedding_model=None):
        """
        Initialize consolidator with Qdrant and embedding support.

        Args:
            qdrant_client: Qdrant client for vector operations
            embedding_model: Model for generating embeddings
        """
        self.qdrant_client = qdrant_client
        self.embedding_model = embedding_model

        # Initialize surprise scorer
        self.surprise_scorer = self._create_scorer()

        # Initialize retention gate
        self.retention_gate = RetentionGate(
            max_memories=CONSOLIDATION_CONFIG["max_semantic_memories"],
            decay_rate=CONSOLIDATION_CONFIG["retention_decay_rate"]
        )

        # Metrics storage
        self.current_run_metrics = None

    def _create_scorer(self) -> SurpriseBasedMemory:
        """Create surprise scorer with embedding functions."""

        def embedding_fn(text: str) -> List[float]:
            if self.embedding_model:
                return self.embedding_model.encode(text).tolist()
            # Try SAFLA as fallback
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent))
                from safla_tools import generate_embeddings_sync
                return generate_embeddings_sync([text])[0]
            except Exception as e:
                logger.warning(f"Embedding fallback failed: {e}")
                return []

        def search_fn(embedding: List[float], limit: int, threshold: float) -> List[Dict]:
            if not self.qdrant_client or not embedding:
                return []
            try:
                results = self.qdrant_client.search(
                    collection_name="semantic_memories",
                    query_vector=embedding,
                    limit=limit,
                    score_threshold=threshold
                )
                return [{'id': str(r.id), 'score': r.score} for r in results]
            except Exception as e:
                logger.warning(f"Search failed: {e}")
                return []

        return SurpriseBasedMemory(
            embedding_fn=embedding_fn,
            search_fn=search_fn
        )

    def consolidate_episodic_memories(
        self,
        episodic_memories: List[Dict],
        time_window_hours: int = 24
    ) -> Dict:
        """
        Consolidate episodic memories to semantic using surprise-based filtering.

        This is the main entry point for the consolidation daemon.

        Args:
            episodic_memories: List of episodic memories to evaluate
            time_window_hours: Only consider memories from this window

        Returns:
            Consolidation results with metrics
        """
        start_time = datetime.now()
        logger.info(f"Starting surprise-based consolidation of {len(episodic_memories)} memories")

        # Filter by time window
        cutoff = datetime.now() - timedelta(hours=time_window_hours)
        recent_memories = [
            m for m in episodic_memories
            if datetime.fromisoformat(m.get('created_at', datetime.now().isoformat())) > cutoff
        ]

        logger.info(f"Filtered to {len(recent_memories)} memories in {time_window_hours}h window")

        # Track metrics
        scores = []
        promoted = []
        skipped = []
        context = {'recent_topics': []}

        # Evaluate each memory
        for memory in recent_memories:
            content = memory.get('content', '')
            memory_type = memory.get('memory_type', 'episodic')

            # Calculate surprise score
            score = self.surprise_scorer.calculate_surprise(
                content=content,
                memory_type=memory_type,
                context=context
            )

            scores.append(score.score)

            # Update context with recent topics
            if len(context['recent_topics']) >= 5:
                context['recent_topics'].pop(0)
            context['recent_topics'].append(content[:100])

            # Decision based on surprise
            if score.should_store or score.score >= CONSOLIDATION_CONFIG["high_surprise_immediate_promote"]:
                promoted.append({
                    'memory': memory,
                    'surprise_score': score,
                    'reason': score.reasoning
                })
                logger.debug(f"PROMOTE: {content[:50]}... (score={score.score:.2f})")
            else:
                skipped.append({
                    'memory_id': memory.get('id'),
                    'surprise_score': score.score,
                    'reason': score.reasoning
                })
                logger.debug(f"SKIP: {content[:50]}... (score={score.score:.2f})")

        # Check if we need to trigger retention gate (memory cleanup)
        retention_triggered = False
        forgotten = []
        if len(promoted) > 0:
            current_semantic_count = self._get_semantic_memory_count()
            if current_semantic_count + len(promoted) > CONSOLIDATION_CONFIG["max_semantic_memories"]:
                retention_triggered = True
                excess = (current_semantic_count + len(promoted)) - CONSOLIDATION_CONFIG["max_semantic_memories"]
                forgotten = self._apply_retention_gate(excess)
                logger.info(f"Retention gate triggered: forgetting {len(forgotten)} memories")

        # Calculate metrics
        duration = (datetime.now() - start_time).total_seconds()
        avg_score = sum(scores) / len(scores) if scores else 0

        metrics = ConsolidationMetrics(
            timestamp=datetime.now().isoformat(),
            memories_evaluated=len(recent_memories),
            memories_promoted=len(promoted),
            memories_skipped=len(skipped),
            memories_forgotten=len(forgotten),
            average_surprise_score=avg_score,
            high_surprise_count=len([s for s in scores if s >= 0.7]),
            low_surprise_count=len([s for s in scores if s < 0.3]),
            retention_gate_triggered=retention_triggered,
            duration_seconds=duration
        )

        # Save metrics
        self._save_metrics(metrics)

        logger.info(f"Consolidation complete: promoted={len(promoted)}, skipped={len(skipped)}, "
                   f"forgotten={len(forgotten)}, avg_surprise={avg_score:.2f}, duration={duration:.1f}s")

        return {
            'success': True,
            'promoted': promoted,
            'skipped': skipped,
            'forgotten': forgotten,
            'metrics': asdict(metrics)
        }

    def _get_semantic_memory_count(self) -> int:
        """Get current count of semantic memories."""
        if not self.qdrant_client:
            return 0
        try:
            info = self.qdrant_client.get_collection("semantic_memories")
            return info.points_count
        except:
            return 0

    def _apply_retention_gate(self, count_to_remove: int) -> List[str]:
        """
        Apply retention gate to remove low-priority memories.

        Returns list of forgotten memory IDs.
        """
        if not self.qdrant_client:
            return []

        try:
            # Get all semantic memories with scores
            # Note: In production, this should be paginated
            results = self.qdrant_client.scroll(
                collection_name="semantic_memories",
                limit=10000,
                with_payload=True
            )

            memories = []
            for point in results[0]:
                memories.append({
                    'id': str(point.id),
                    'surprise_score': point.payload.get('surprise_score', 0.5),
                    'created_at': point.payload.get('created_at', datetime.now().isoformat()),
                    'memory_type': point.payload.get('memory_type', 'semantic')
                })

            # Get candidates for forgetting
            candidates = self.retention_gate.get_candidates_for_forgetting(
                memories=memories,
                count_to_remove=count_to_remove
            )

            # Delete from Qdrant
            if candidates:
                self.qdrant_client.delete(
                    collection_name="semantic_memories",
                    points_selector=candidates
                )
                logger.info(f"Deleted {len(candidates)} low-retention memories")

            return candidates

        except Exception as e:
            logger.error(f"Retention gate failed: {e}")
            return []

    def _save_metrics(self, metrics: ConsolidationMetrics):
        """Save metrics to JSONL file."""
        try:
            metrics_path = Path(CONSOLIDATION_CONFIG["metrics_file"])
            metrics_path.parent.mkdir(parents=True, exist_ok=True)

            with open(metrics_path, 'a') as f:
                f.write(json.dumps(asdict(metrics)) + '\n')
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

    def get_consolidation_stats(self, days: int = 7) -> Dict:
        """Get consolidation statistics for reporting."""
        try:
            metrics_path = Path(CONSOLIDATION_CONFIG["metrics_file"])
            if not metrics_path.exists():
                return {'error': 'No metrics available'}

            cutoff = datetime.now() - timedelta(days=days)
            recent_metrics = []

            with open(metrics_path, 'r') as f:
                for line in f:
                    try:
                        m = json.loads(line.strip())
                        if datetime.fromisoformat(m['timestamp']) > cutoff:
                            recent_metrics.append(m)
                    except:
                        continue

            if not recent_metrics:
                return {'error': f'No metrics in last {days} days'}

            total_evaluated = sum(m['memories_evaluated'] for m in recent_metrics)
            total_promoted = sum(m['memories_promoted'] for m in recent_metrics)
            total_skipped = sum(m['memories_skipped'] for m in recent_metrics)
            total_forgotten = sum(m['memories_forgotten'] for m in recent_metrics)
            avg_surprise = sum(m['average_surprise_score'] for m in recent_metrics) / len(recent_metrics)

            return {
                'period_days': days,
                'consolidation_runs': len(recent_metrics),
                'total_evaluated': total_evaluated,
                'total_promoted': total_promoted,
                'total_skipped': total_skipped,
                'total_forgotten': total_forgotten,
                'promotion_rate': total_promoted / total_evaluated if total_evaluated > 0 else 0,
                'average_surprise_score': avg_surprise,
                'retention_gates_triggered': sum(1 for m in recent_metrics if m['retention_gate_triggered'])
            }

        except Exception as e:
            return {'error': str(e)}


# Integration function for consolidation daemon
def surprise_based_consolidation(
    episodic_memories: List[Dict],
    qdrant_client=None,
    embedding_model=None,
    time_window_hours: int = 24
) -> Dict:
    """
    Entry point for surprise-based consolidation.

    Can be called from the memory consolidation daemon.

    Args:
        episodic_memories: Memories to consolidate
        qdrant_client: Optional Qdrant client
        embedding_model: Optional embedding model
        time_window_hours: Time window for filtering

    Returns:
        Consolidation results
    """
    consolidator = SurpriseConsolidator(
        qdrant_client=qdrant_client,
        embedding_model=embedding_model
    )

    return consolidator.consolidate_episodic_memories(
        episodic_memories=episodic_memories,
        time_window_hours=time_window_hours
    )


if __name__ == "__main__":
    # Test consolidation
    print("Testing Surprise-Based Consolidation")
    print("=" * 60)

    # Mock episodic memories
    test_memories = [
        {
            'id': '1',
            'content': 'Discovered that parallel tool calls reduce latency by 60%',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '2',
            'content': 'Had a meeting',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '3',
            'content': 'CRITICAL: Memory leak found in consolidation daemon - fixed by adding cleanup',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '4',
            'content': 'Checked email',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        },
        {
            'id': '5',
            'content': 'Learned that Titans/MIRAS uses surprise-based memorization for efficient long-term memory',
            'memory_type': 'episodic',
            'created_at': datetime.now().isoformat()
        }
    ]

    # Run consolidation (without Qdrant for testing)
    consolidator = SurpriseConsolidator()
    result = consolidator.consolidate_episodic_memories(test_memories)

    print(f"\nResults:")
    print(f"Evaluated: {result['metrics']['memories_evaluated']}")
    print(f"Promoted: {result['metrics']['memories_promoted']}")
    print(f"Skipped: {result['metrics']['memories_skipped']}")
    print(f"Average Surprise: {result['metrics']['average_surprise_score']:.2f}")

    print(f"\nPromoted memories:")
    for p in result['promoted']:
        print(f"  - {p['memory']['content'][:50]}... (score={p['surprise_score'].score:.2f})")

    print(f"\nSkipped memories:")
    for s in result['skipped']:
        print(f"  - Score={s['surprise_score']:.2f}: {s['reason']}")
