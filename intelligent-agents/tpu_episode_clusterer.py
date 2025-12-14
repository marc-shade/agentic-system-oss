#!/usr/bin/env python3
"""
TPU Episode Clusterer - Edge TPU Accelerated Memory Clustering

Clusters episodic memories (visual, audio, action) by semantic similarity
using TPU text embeddings. Enables efficient memory retrieval and pattern
discovery across experiences.

Integration with enhanced-memory system and consciousness daemon.

Usage:
    from tpu_episode_clusterer import TPUEpisodeClusterer

    clusterer = TPUEpisodeClusterer()
    clusters = await clusterer.cluster_episodes(
        episodes=recent_episodes,
        n_clusters=5
    )

    # Find similar episodes
    similar = await clusterer.find_similar_episodes(
        query="debugging memory leak",
        top_k=5
    )
"""
import platform

import os
import sys
import json
import time
import logging
import sqlite3
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_episode_clusterer")

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
class Episode:
    """Represents an episodic memory"""
    episode_id: str
    event_type: str  # task_completion, error, learning, observation, etc.
    description: str
    timestamp: datetime
    significance: float = 0.5
    emotional_valence: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


@dataclass
class EpisodeCluster:
    """A cluster of related episodes"""
    cluster_id: int
    centroid: np.ndarray
    episodes: List[Episode]
    coherence: float  # Average similarity within cluster
    label: str  # Auto-generated label
    dominant_event_type: str
    time_span: Tuple[datetime, datetime]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUEpisodeClusterer:
    """
    Cluster episodic memories using TPU embeddings.

    Uses k-means style clustering on semantic embeddings to group
    related experiences for efficient retrieval and pattern discovery.
    """

    def __init__(self):
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Cluster label templates for auto-labeling
        self.label_templates = {
            "debugging": "Debugging and troubleshooting sessions",
            "implementation": "Feature implementation work",
            "research": "Research and investigation",
            "testing": "Testing and validation",
            "optimization": "Performance optimization",
            "documentation": "Documentation work",
            "planning": "Planning and architecture",
            "error": "Error handling and recovery",
            "learning": "Learning and skill development",
            "coordination": "Multi-agent coordination"
        }

        # Precompute label embeddings
        self._label_embeddings = self._precompute_labels()

        if self.use_tpu:
            logger.info("TPU episode clustering enabled")
        else:
            logger.info("Using fallback clustering")

    def _precompute_labels(self) -> Dict[str, np.ndarray]:
        """Precompute embeddings for cluster labels."""
        labels = {}
        if not self.use_tpu or not _embed_text:
            return labels

        for name, description in self.label_templates.items():
            try:
                embedding = _embed_text(description)
                if embedding is not None:
                    labels[name] = np.array(embedding, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Failed to embed label {name}: {e}")

        return labels

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
                        "episode_embedding",
                        latency_ms=latency,
                        source="episode_clusterer"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _embed_episodes(self, episodes: List[Episode]) -> List[Episode]:
        """Embed all episodes that don't have embeddings."""
        for episode in episodes:
            if episode.embedding is None:
                # Build text representation
                text = f"{episode.event_type}: {episode.description}"
                if episode.tags:
                    text += f" | Tags: {', '.join(episode.tags)}"

                embedding = self._get_embedding(text)
                if embedding is not None:
                    episode.embedding = embedding

        return episodes

    def _kmeans_clustering(
        self,
        embeddings: np.ndarray,
        n_clusters: int,
        max_iterations: int = 100
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simple k-means clustering on embeddings."""
        n_samples = embeddings.shape[0]

        if n_samples <= n_clusters:
            # Each point is its own cluster
            labels = np.arange(n_samples)
            centroids = embeddings.copy()
            return labels, centroids

        # Initialize centroids randomly
        indices = np.random.choice(n_samples, n_clusters, replace=False)
        centroids = embeddings[indices].copy()

        labels = np.zeros(n_samples, dtype=int)

        for iteration in range(max_iterations):
            # Assign points to nearest centroid
            new_labels = np.zeros(n_samples, dtype=int)
            for i in range(n_samples):
                similarities = [
                    cosine_similarity(embeddings[i], centroids[j])
                    for j in range(n_clusters)
                ]
                new_labels[i] = np.argmax(similarities)

            # Check for convergence
            if np.array_equal(labels, new_labels):
                break
            labels = new_labels

            # Update centroids
            for j in range(n_clusters):
                cluster_points = embeddings[labels == j]
                if len(cluster_points) > 0:
                    centroids[j] = np.mean(cluster_points, axis=0)

        return labels, centroids

    def _auto_label_cluster(self, centroid: np.ndarray) -> str:
        """Auto-generate a label for a cluster based on centroid."""
        if not self._label_embeddings:
            return "mixed"

        best_label = "mixed"
        best_similarity = 0.0

        for name, label_emb in self._label_embeddings.items():
            similarity = cosine_similarity(centroid, label_emb)
            if similarity > best_similarity:
                best_similarity = similarity
                best_label = name

        return best_label

    async def cluster_episodes(
        self,
        episodes: List[Episode],
        n_clusters: Optional[int] = None,
        min_cluster_size: int = 2
    ) -> List[EpisodeCluster]:
        """
        Cluster episodes by semantic similarity.

        Args:
            episodes: List of episodes to cluster
            n_clusters: Number of clusters (auto-determined if None)
            min_cluster_size: Minimum episodes per cluster

        Returns:
            List of EpisodeCluster objects
        """
        start_time = time.perf_counter()

        if not episodes:
            return []

        # Embed all episodes
        episodes = self._embed_episodes(episodes)

        # Filter to episodes with embeddings
        embedded_episodes = [e for e in episodes if e.embedding is not None]

        if not embedded_episodes:
            logger.warning("No episodes could be embedded")
            return []

        # Auto-determine cluster count if not specified
        if n_clusters is None:
            # Rule of thumb: sqrt(n/2) clusters
            n_clusters = max(2, int(np.sqrt(len(embedded_episodes) / 2)))
            n_clusters = min(n_clusters, len(embedded_episodes) // min_cluster_size)

        n_clusters = max(1, min(n_clusters, len(embedded_episodes)))

        # Build embedding matrix
        embeddings = np.array([e.embedding for e in embedded_episodes])

        # Run clustering
        labels, centroids = self._kmeans_clustering(embeddings, n_clusters)

        # Build cluster objects
        clusters = []
        for cluster_id in range(n_clusters):
            cluster_episodes = [
                e for e, label in zip(embedded_episodes, labels)
                if label == cluster_id
            ]

            if len(cluster_episodes) < min_cluster_size:
                continue

            centroid = centroids[cluster_id]

            # Calculate coherence (average pairwise similarity)
            if len(cluster_episodes) > 1:
                similarities = []
                for i, e1 in enumerate(cluster_episodes):
                    for e2 in cluster_episodes[i+1:]:
                        sim = cosine_similarity(e1.embedding, e2.embedding)
                        similarities.append(sim)
                coherence = np.mean(similarities) if similarities else 0.0
            else:
                coherence = 1.0

            # Find dominant event type
            event_counts = defaultdict(int)
            for e in cluster_episodes:
                event_counts[e.event_type] += 1
            dominant_type = max(event_counts, key=event_counts.get)

            # Time span
            timestamps = [e.timestamp for e in cluster_episodes]
            time_span = (min(timestamps), max(timestamps))

            # Auto-label
            label = self._auto_label_cluster(centroid)

            clusters.append(EpisodeCluster(
                cluster_id=cluster_id,
                centroid=centroid,
                episodes=cluster_episodes,
                coherence=coherence,
                label=label,
                dominant_event_type=dominant_type,
                time_span=time_span
            ))

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "episode_clustering",
                latency_ms=latency_ms,
                source="episode_clusterer",
                metadata={
                    "episode_count": len(episodes),
                    "cluster_count": len(clusters)
                }
            )

        return clusters

    async def find_similar_episodes(
        self,
        query: str,
        episodes: List[Episode],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[Episode, float]]:
        """
        Find episodes similar to a query.

        Args:
            query: Search query
            episodes: Episodes to search
            top_k: Number of results
            threshold: Minimum similarity threshold

        Returns:
            List of (episode, similarity) tuples
        """
        start_time = time.perf_counter()

        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            # Fallback to keyword matching
            return self._keyword_search(query, episodes, top_k)

        # Embed episodes
        episodes = self._embed_episodes(episodes)

        # Calculate similarities
        results = []
        for episode in episodes:
            if episode.embedding is not None:
                similarity = cosine_similarity(query_embedding, episode.embedding)
                if similarity >= threshold:
                    results.append((episode, similarity))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:top_k]

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "episode_similarity_search",
                latency_ms=latency_ms,
                source="episode_clusterer",
                metadata={"result_count": len(results)}
            )

        return results

    def _keyword_search(
        self,
        query: str,
        episodes: List[Episode],
        top_k: int
    ) -> List[Tuple[Episode, float]]:
        """Fallback keyword-based search."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for episode in episodes:
            text = f"{episode.event_type} {episode.description}".lower()
            text_words = set(text.split())

            overlap = len(query_words & text_words)
            if overlap > 0:
                score = overlap / len(query_words)
                results.append((episode, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def find_cluster_for_episode(
        self,
        episode: Episode,
        clusters: List[EpisodeCluster]
    ) -> Optional[Tuple[EpisodeCluster, float]]:
        """
        Find the best matching cluster for an episode.

        Args:
            episode: Episode to classify
            clusters: Existing clusters

        Returns:
            (cluster, similarity) or None
        """
        if not clusters:
            return None

        # Ensure episode has embedding
        if episode.embedding is None:
            text = f"{episode.event_type}: {episode.description}"
            episode.embedding = self._get_embedding(text)

        if episode.embedding is None:
            return None

        best_cluster = None
        best_similarity = 0.0

        for cluster in clusters:
            similarity = cosine_similarity(episode.embedding, cluster.centroid)
            if similarity > best_similarity:
                best_similarity = similarity
                best_cluster = cluster

        return (best_cluster, best_similarity) if best_cluster else None

    def get_statistics(self) -> Dict[str, Any]:
        """Get clusterer statistics."""
        return {
            "tpu_available": self.use_tpu,
            "cache_size": len(self._embedding_cache),
            "label_templates": len(self.label_templates),
            "labels_embedded": len(self._label_embeddings)
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


    clusterer = TPUEpisodeClusterer()
    print(json.dumps(clusterer.get_statistics(), indent=2))

    # Test clustering
    test_episodes = [
        Episode("1", "debugging", "Fixed memory leak in cache", datetime.now(), 0.8, tags=["bug", "memory"]),
        Episode("2", "debugging", "Traced null pointer exception", datetime.now(), 0.7, tags=["bug", "crash"]),
        Episode("3", "implementation", "Added new API endpoint", datetime.now(), 0.6, tags=["feature"]),
        Episode("4", "implementation", "Implemented user authentication", datetime.now(), 0.8, tags=["feature", "security"]),
        Episode("5", "testing", "Wrote unit tests for parser", datetime.now(), 0.5, tags=["test"]),
        Episode("6", "testing", "Added integration tests", datetime.now(), 0.6, tags=["test"]),
    ]

    clusters = asyncio.run(clusterer.cluster_episodes(test_episodes, n_clusters=3))
    print(f"\nClusters ({len(clusters)}):")
    for c in clusters:
        print(f"  Cluster {c.cluster_id} ({c.label}): {len(c.episodes)} episodes, coherence={c.coherence:.2f}")
        for e in c.episodes:
            print(f"    - {e.description}")

    # Test search
    results = asyncio.run(clusterer.find_similar_episodes("debugging memory issues", test_episodes))
    print(f"\nSearch 'debugging memory issues':")
    for episode, score in results:
        print(f"  {score:.2f}: {episode.description}")
