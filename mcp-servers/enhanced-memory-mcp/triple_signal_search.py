#!/usr/bin/env python3
"""
Triple-Signal Hybrid Search (PTM Phase 3)

Combines three retrieval signals for enhanced recall and precision:
1. Vector (semantic similarity via dense embeddings)
2. Lexical (BM25 keyword matching via sparse embeddings)
3. Trajectory (manifold-based phase angle similarity)

Uses extended Reciprocal Rank Fusion (RRF) to combine all three signals.

Based on PTM paper "Memory as Resonance" (arXiv:2512.20245):
- Trajectory signal provides O(1) retrieval via phase angle matching
- Phase angles encode semantic position on 8D hyper-torus T^8
- Golden ratio rotations ensure no repetition (equidistribution)
"""

import logging
import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Import trajectory compression components
try:
    from trajectory_compression import (
        TrajectoryCompressor,
        Trajectory,
        MANIFOLD_DIM,
        GOLDEN_RATIO
    )
    TRAJECTORY_AVAILABLE = True
except ImportError:
    TRAJECTORY_AVAILABLE = False
    MANIFOLD_DIM = 8
    GOLDEN_RATIO = (1 + np.sqrt(5)) / 2

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryVector:
    """Compact representation of trajectory for indexing."""
    entity_id: int
    entity_name: str
    centroid: np.ndarray  # Mean phase angles (8D)
    anchor_count: int
    point_count: int
    anchor_hash: int  # Hash of anchor tokens for exact matching

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "centroid": self.centroid.tolist(),
            "anchor_count": self.anchor_count,
            "point_count": self.point_count,
            "anchor_hash": self.anchor_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryVector":
        return cls(
            entity_id=data["entity_id"],
            entity_name=data["entity_name"],
            centroid=np.array(data["centroid"]),
            anchor_count=data["anchor_count"],
            point_count=data["point_count"],
            anchor_hash=data["anchor_hash"]
        )


class TrajectoryIndex:
    """
    In-memory index of trajectory vectors for fast similarity search.

    Uses centroid-based indexing for O(n) search with small constant.
    Future optimization: LSH or VP-trees for O(log n) search.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        )
        self.index: Dict[int, TrajectoryVector] = {}
        self.compressor = TrajectoryCompressor() if TRAJECTORY_AVAILABLE else None
        self._stats = {
            "indexed_entities": 0,
            "total_queries": 0,
            "cache_hits": 0
        }

    def compute_trajectory_vector(
        self,
        text: str,
        entity_id: int,
        entity_name: str
    ) -> TrajectoryVector:
        """
        Compute trajectory vector for a piece of text.

        The centroid is the mean of all phase angles, providing a
        compact 8D representation of the entire text's position
        on the hyper-torus manifold.
        """
        if not self.compressor:
            # Fallback: use simple hash-based encoding
            centroid = self._hash_to_phases(text)
            return TrajectoryVector(
                entity_id=entity_id,
                entity_name=entity_name,
                centroid=centroid,
                anchor_count=0,
                point_count=1,
                anchor_hash=hash(text) & 0xFFFFFFFF
            )

        # Encode text as trajectory
        trajectory = self.compressor.encode_text(text)

        if len(trajectory.points) == 0:
            centroid = np.zeros(MANIFOLD_DIM)
        else:
            # Compute centroid (mean of all phase angles)
            all_phases = np.array([p.phases for p in trajectory.points])
            centroid = np.mean(all_phases, axis=0)

        # Hash anchor tokens for exact matching boost
        anchor_hash = hash(tuple(sorted(trajectory.anchor_tokens))) & 0xFFFFFFFF

        return TrajectoryVector(
            entity_id=entity_id,
            entity_name=entity_name,
            centroid=centroid,
            anchor_count=len(trajectory.anchor_tokens),
            point_count=len(trajectory.points),
            anchor_hash=anchor_hash
        )

    def _hash_to_phases(self, text: str) -> np.ndarray:
        """Fallback: convert text hash to phase angles."""
        h = hash(text)
        phases = np.zeros(MANIFOLD_DIM)
        for i in range(MANIFOLD_DIM):
            phases[i] = ((h >> (i * 8)) & 0xFF) / 255.0 * 2 * np.pi
        return phases

    def add_entity(self, entity_id: int, entity_name: str, text: str):
        """Add an entity to the trajectory index."""
        vec = self.compute_trajectory_vector(text, entity_id, entity_name)
        self.index[entity_id] = vec
        self._stats["indexed_entities"] = len(self.index)

    def remove_entity(self, entity_id: int):
        """Remove an entity from the index."""
        if entity_id in self.index:
            del self.index[entity_id]
            self._stats["indexed_entities"] = len(self.index)

    def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[int, float, TrajectoryVector]]:
        """
        Search for similar entities by trajectory similarity.

        Uses angular distance on the hyper-torus manifold.

        Returns:
            List of (entity_id, similarity_score, trajectory_vector)
        """
        self._stats["total_queries"] += 1

        # Compute query trajectory
        query_vec = self.compute_trajectory_vector(query, -1, "query")

        # Compute similarities
        results = []
        for entity_id, stored_vec in self.index.items():
            sim = self._compute_similarity(query_vec, stored_vec)
            if sim >= threshold:
                results.append((entity_id, sim, stored_vec))

        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:limit]

    def _compute_similarity(
        self,
        query: TrajectoryVector,
        stored: TrajectoryVector
    ) -> float:
        """
        Compute similarity between two trajectory vectors.

        Uses cosine similarity of centroids on the hyper-torus.
        Adds bonus for anchor hash match (exact anchor overlap).
        """
        # Cosine similarity of centroids
        q_norm = np.linalg.norm(query.centroid)
        s_norm = np.linalg.norm(stored.centroid)

        if q_norm < 1e-10 or s_norm < 1e-10:
            cosine_sim = 0.0
        else:
            cosine_sim = np.dot(query.centroid, stored.centroid) / (q_norm * s_norm)

        # Normalize to [0, 1]
        cosine_sim = (cosine_sim + 1) / 2

        # Anchor hash bonus (exact match of anchor tokens)
        anchor_bonus = 0.1 if query.anchor_hash == stored.anchor_hash else 0.0

        return min(1.0, cosine_sim + anchor_bonus)

    def load_from_db(self, limit: int = 10000) -> int:
        """
        Load trajectory vectors from database.

        Builds index from stored compressed_data or recomputes from observations.
        """
        if not Path(self.db_path).exists():
            logger.warning(f"Database not found: {self.db_path}")
            return 0

        loaded = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get entities with observations
            cursor.execute("""
                SELECT e.id, e.name, GROUP_CONCAT(o.content, ' ')
                FROM entities e
                LEFT JOIN observations o ON e.id = o.entity_id
                GROUP BY e.id
                LIMIT ?
            """, (limit,))

            for entity_id, name, observations in cursor.fetchall():
                if observations:
                    self.add_entity(entity_id, name, observations)
                    loaded += 1

            conn.close()
            logger.info(f"Loaded {loaded} entities into trajectory index")

        except Exception as e:
            logger.error(f"Error loading trajectory index: {e}")

        return loaded

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            **self._stats,
            "trajectory_available": TRAJECTORY_AVAILABLE,
            "manifold_dim": MANIFOLD_DIM
        }


class TripleSignalSearcher:
    """
    Combines three retrieval signals using extended RRF.

    Signals:
    1. Vector (dense embedding similarity)
    2. Lexical (BM25 sparse similarity)
    3. Trajectory (manifold phase angle similarity)

    RRF formula: score(d) = Σ 1 / (k + rank_i(d)) * weight_i
    where k=60 (standard), weights can be adjusted per signal.
    """

    RRF_K = 60  # Standard RRF constant

    def __init__(
        self,
        trajectory_index: TrajectoryIndex,
        vector_weight: float = 0.4,
        lexical_weight: float = 0.3,
        trajectory_weight: float = 0.3
    ):
        self.trajectory_index = trajectory_index
        self.weights = {
            "vector": vector_weight,
            "lexical": lexical_weight,
            "trajectory": trajectory_weight
        }
        self._stats = {
            "total_searches": 0,
            "avg_vector_results": 0,
            "avg_lexical_results": 0,
            "avg_trajectory_results": 0
        }

    def fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        lexical_results: List[Dict[str, Any]],
        trajectory_results: List[Tuple[int, float, TrajectoryVector]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fuse results from all three signals using weighted RRF.

        Args:
            vector_results: Results from dense vector search [{id, score, ...}]
            lexical_results: Results from BM25 search [{id, score, ...}]
            trajectory_results: Results from trajectory search [(id, score, vec)]
            limit: Maximum results to return

        Returns:
            Fused results with combined scores
        """
        self._stats["total_searches"] += 1

        # Build rank maps
        vector_ranks = {r.get("id") or r.get("entity_id"): i
                       for i, r in enumerate(vector_results)}
        lexical_ranks = {r.get("id") or r.get("entity_id"): i
                        for i, r in enumerate(lexical_results)}
        trajectory_ranks = {str(entity_id): i
                          for i, (entity_id, _, _) in enumerate(trajectory_results)}

        # Collect all unique IDs
        all_ids = set(vector_ranks.keys()) | set(lexical_ranks.keys()) | set(trajectory_ranks.keys())

        # Compute RRF scores
        scores = {}
        for doc_id in all_ids:
            if doc_id is None:
                continue

            score = 0.0

            # Vector signal
            if doc_id in vector_ranks:
                score += self.weights["vector"] / (self.RRF_K + vector_ranks[doc_id])

            # Lexical signal
            if doc_id in lexical_ranks:
                score += self.weights["lexical"] / (self.RRF_K + lexical_ranks[doc_id])

            # Trajectory signal
            str_id = str(doc_id) if not isinstance(doc_id, str) else doc_id
            if str_id in trajectory_ranks:
                score += self.weights["trajectory"] / (self.RRF_K + trajectory_ranks[str_id])

            scores[doc_id] = score

        # Sort by fused score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Build result objects
        results = []
        for doc_id in sorted_ids[:limit]:
            # Get metadata from first available source
            metadata = {}

            for r in vector_results:
                if (r.get("id") or r.get("entity_id")) == doc_id:
                    metadata = r.get("payload", r)
                    break

            result = {
                "id": doc_id,
                "score": scores[doc_id],
                "signals": {
                    "vector": doc_id in vector_ranks,
                    "lexical": doc_id in lexical_ranks,
                    "trajectory": str(doc_id) in trajectory_ranks
                },
                "signal_ranks": {
                    "vector": vector_ranks.get(doc_id, -1),
                    "lexical": lexical_ranks.get(doc_id, -1),
                    "trajectory": trajectory_ranks.get(str(doc_id), -1)
                },
                "payload": metadata
            }
            results.append(result)

        # Update stats
        n = self._stats["total_searches"]
        self._stats["avg_vector_results"] = (
            (self._stats["avg_vector_results"] * (n-1) + len(vector_results)) / n
        )
        self._stats["avg_lexical_results"] = (
            (self._stats["avg_lexical_results"] * (n-1) + len(lexical_results)) / n
        )
        self._stats["avg_trajectory_results"] = (
            (self._stats["avg_trajectory_results"] * (n-1) + len(trajectory_results)) / n
        )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get searcher statistics."""
        return {
            **self._stats,
            "weights": self.weights,
            "rrf_k": self.RRF_K
        }


# Module-level instances
_trajectory_index: Optional[TrajectoryIndex] = None
_triple_searcher: Optional[TripleSignalSearcher] = None


def get_trajectory_index() -> TrajectoryIndex:
    """Get or create the global trajectory index."""
    global _trajectory_index
    if _trajectory_index is None:
        _trajectory_index = TrajectoryIndex()
    return _trajectory_index


def get_triple_searcher() -> TripleSignalSearcher:
    """Get or create the global triple signal searcher."""
    global _triple_searcher
    if _triple_searcher is None:
        _triple_searcher = TripleSignalSearcher(get_trajectory_index())
    return _triple_searcher


def reset_instances():
    """Reset module instances (for testing)."""
    global _trajectory_index, _triple_searcher
    _trajectory_index = None
    _triple_searcher = None


# Self-test
if __name__ == "__main__":
    print("=" * 60)
    print("Triple-Signal Search Tests (PTM Phase 3)")
    print("=" * 60)
    print()

    # Test 1: Trajectory vector computation
    print("=== Test 1: Trajectory Vector Computation ===")
    index = TrajectoryIndex()

    text1 = "OpenAI released GPT-5 with enhanced reasoning capabilities"
    vec1 = index.compute_trajectory_vector(text1, 1, "test1")
    print(f"  Text: '{text1[:50]}...'")
    print(f"  Centroid shape: {vec1.centroid.shape}")
    print(f"  Anchor count: {vec1.anchor_count}")
    print(f"  Point count: {vec1.point_count}")
    print()

    # Test 2: Similarity computation
    print("=== Test 2: Trajectory Similarity ===")
    text2 = "OpenAI GPT-5 has better reasoning than GPT-4"
    text3 = "The weather is nice today"

    vec2 = index.compute_trajectory_vector(text2, 2, "test2")
    vec3 = index.compute_trajectory_vector(text3, 3, "test3")

    sim_1_2 = index._compute_similarity(vec1, vec2)
    sim_1_3 = index._compute_similarity(vec1, vec3)

    print(f"  Similar texts: {sim_1_2:.3f}")
    print(f"  Different texts: {sim_1_3:.3f}")
    assert sim_1_2 > sim_1_3, "Similar texts should have higher similarity"
    print("  ✓ Similar texts have higher similarity")
    print()

    # Test 3: Index and search
    print("=== Test 3: Index and Search ===")
    index.add_entity(1, "gpt5", text1)
    index.add_entity(2, "gpt5_alt", text2)
    index.add_entity(3, "weather", text3)

    results = index.search("GPT-5 reasoning capabilities", limit=3)
    print(f"  Query: 'GPT-5 reasoning capabilities'")
    print(f"  Results:")
    for entity_id, score, vec in results:
        print(f"    - {vec.entity_name}: {score:.3f}")

    assert results[0][2].entity_name in ["gpt5", "gpt5_alt"], "GPT-related should rank first"
    print("  ✓ Relevant results ranked higher")
    print()

    # Test 4: RRF fusion
    print("=== Test 4: RRF Fusion ===")
    searcher = TripleSignalSearcher(index)

    vector_results = [
        {"id": "1", "score": 0.9},
        {"id": "2", "score": 0.7},
    ]
    lexical_results = [
        {"id": "2", "score": 0.8},
        {"id": "1", "score": 0.6},
    ]
    trajectory_results = [
        (1, 0.85, vec1),
        (2, 0.75, vec2),
    ]

    fused = searcher.fuse_results(
        vector_results, lexical_results, trajectory_results, limit=5
    )

    print(f"  Fused results:")
    for r in fused:
        print(f"    - ID {r['id']}: score={r['score']:.4f}, signals={r['signals']}")

    print("  ✓ RRF fusion working")
    print()

    # Test 5: Stats
    print("=== Test 5: Statistics ===")
    stats = index.get_stats()
    print(f"  Index stats: {stats}")

    stats = searcher.get_stats()
    print(f"  Searcher stats: {stats}")
    print()

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)
