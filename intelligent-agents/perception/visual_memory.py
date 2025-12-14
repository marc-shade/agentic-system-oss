#!/usr/bin/env python3
"""
Visual Memory - Embedding Storage and Similarity Search for LVR Integration

Implements Phase 2 of the Latent Visual Reasoning integration plan:
- Store TPU visual embeddings with episodic memories
- Cosine similarity search for visual retrieval
- Manifold-based clustering for compression

Based on research:
- Latent Visual Reasoning (LVR) - arxiv:2509.24251
- Visual reasoning in embedding space, not just language

Usage:
    from visual_memory import VisualMemory

    vm = VisualMemory()

    # Store visual embedding with episode
    episode_id = vm.store_visual_episode(
        image_path="/path/to/image.jpg",
        context="Working at desk",
        metadata={"activity": "coding", "person_present": True}
    )

    # Find similar visual experiences
    similar = vm.find_similar_visual("/path/to/query.jpg", k=5)

    # Find by embedding directly
    similar = vm.find_similar_by_embedding(embedding_vector, k=5)
"""
import os
import platform

import json
import sqlite3
import logging
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import hashlib

logger = logging.getLogger("visual_memory")

# Storage configuration
STORAGE_BASE = Path(str(_STORAGE_BASE))
CLUSTER_DB = STORAGE_BASE / "databases" / "cluster" / "shared_memories.db"
VISUAL_MEMORY_DB = STORAGE_BASE / "databases" / "sensory" / "visual_memories.db"

# Embedding dimensions (MobileNet V2 final layer)
EMBEDDING_DIM = 1001  # ImageNet softmax output
FEATURE_EMBEDDING_DIM = 1280  # Penultimate layer features


class VisualMemory:
    """
    Visual memory storage with embedding-based similarity search.

    Implements LVR-style visual reasoning by storing embeddings
    and enabling similarity search across visual experiences.
    """

    def __init__(self, use_tpu: bool = True):
        """
        Initialize visual memory system.

        Args:
            use_tpu: Whether to use TPU for embedding extraction
        """
        self._tpu = None
        self.use_tpu = use_tpu

        if use_tpu:
            self._init_tpu()

        self._ensure_tables()

    def _init_tpu(self):
        """Initialize TPU for embedding extraction."""
        try:
            from tpu_visual_inference import TPUVisualInference
            self._tpu = TPUVisualInference()
            if self._tpu.is_available:
                logger.info("TPU available for visual embedding extraction")
            else:
                self._tpu = None
                logger.warning("TPU not available - visual memory limited to storage only")
        except ImportError:
            logger.warning("TPU inference module not available")
            self._tpu = None

    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        # Ensure directory exists
        VISUAL_MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Visual episodes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visual_episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                image_hash TEXT UNIQUE,
                image_path TEXT,
                context TEXT,
                embedding BLOB,
                embedding_dim INTEGER,
                significance REAL DEFAULT 0.5,
                person_present INTEGER DEFAULT 0,
                activity TEXT,
                scene_type TEXT,
                metadata_json TEXT,
                cluster_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Visual clusters for manifold compression
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visual_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                centroid BLOB,
                centroid_dim INTEGER,
                member_count INTEGER DEFAULT 0,
                cluster_label TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
        ''')

        # Similarity cache for frequent queries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS similarity_cache (
                query_hash TEXT PRIMARY KEY,
                results_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT
            )
        ''')

        # Create indices for fast search
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_visual_timestamp
            ON visual_episodes(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_visual_significance
            ON visual_episodes(significance DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_visual_person
            ON visual_episodes(person_present)
        ''')

        conn.commit()
        conn.close()
        logger.info(f"Visual memory tables ensured at {VISUAL_MEMORY_DB}")

    def _get_image_hash(self, image_path: str) -> str:
        """Get hash of image file for deduplication."""
        try:
            with open(image_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return hashlib.md5(image_path.encode()).hexdigest()

    def _extract_embedding(self, image_path: str) -> Optional[Tuple[np.ndarray, Dict[str, Any]]]:
        """
        Extract visual embedding from image using TPU.

        Returns:
            Tuple of (embedding array, metadata dict) or None
        """
        if not self._tpu:
            logger.warning("No TPU available for embedding extraction")
            return None

        try:
            import cv2
            frame = cv2.imread(image_path)
            if frame is None:
                logger.error(f"Failed to read image: {image_path}")
                return None

            # Get embedding
            result = self._tpu.get_visual_embedding(frame)
            if result is None:
                return None

            embedding, latency_ms = result

            # Also get detection metadata
            metadata = {
                "extraction_latency_ms": latency_ms,
                "embedding_dim": len(embedding),
            }

            # Add scene classification
            scene = self._tpu.classify_scene(frame, top_k=3)
            if scene:
                metadata["scene_classifications"] = [
                    {"label": s["label"], "confidence": s["confidence"]}
                    for s in scene
                ]
                metadata["primary_scene"] = scene[0]["label"]

            # Add face detection
            faces = self._tpu.detect_faces(frame, threshold=0.5)
            metadata["face_count"] = len(faces)
            metadata["person_present"] = len(faces) > 0

            # Add object detection
            objects = self._tpu.detect_objects(frame, threshold=0.4)
            if objects:
                metadata["detected_objects"] = [
                    {"label": o["label"], "confidence": o["confidence"]}
                    for o in objects[:10]
                ]

            return embedding, metadata

        except Exception as e:
            logger.error(f"Embedding extraction failed: {e}")
            return None

    def store_visual_episode(
        self,
        image_path: str,
        context: str = "",
        significance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Store a visual episode with its embedding.

        Args:
            image_path: Path to image file
            context: Text context/description
            significance: Importance score 0.0-1.0
            metadata: Additional metadata dict

        Returns:
            Episode ID if successful, None otherwise
        """
        image_hash = self._get_image_hash(image_path)

        # Check for duplicate
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM visual_episodes WHERE image_hash = ?",
            (image_hash,)
        )
        existing = cursor.fetchone()
        if existing:
            logger.info(f"Image already stored with episode ID {existing[0]}")
            conn.close()
            return existing[0]

        # Extract embedding
        embedding_data = None
        embedding_blob = None
        embedding_dim = None
        tpu_metadata = {}

        if self._tpu:
            result = self._extract_embedding(image_path)
            if result:
                embedding, tpu_metadata = result
                embedding_blob = embedding.astype(np.float32).tobytes()
                embedding_dim = len(embedding)

        # Merge metadata
        full_metadata = metadata.copy() if metadata else {}
        full_metadata.update(tpu_metadata)

        # Determine person presence and activity
        person_present = full_metadata.get("person_present", 0)
        activity = full_metadata.get("activity", "")
        scene_type = full_metadata.get("primary_scene", "")

        # Adjust significance based on person presence
        if person_present:
            significance = min(1.0, significance + 0.3)

        try:
            cursor.execute('''
                INSERT INTO visual_episodes
                (timestamp, image_hash, image_path, context, embedding, embedding_dim,
                 significance, person_present, activity, scene_type, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                image_hash,
                image_path,
                context,
                embedding_blob,
                embedding_dim,
                significance,
                1 if person_present else 0,
                activity,
                scene_type,
                json.dumps(full_metadata)
            ))

            episode_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Stored visual episode {episode_id}: {scene_type}, embedding_dim={embedding_dim}")
            return episode_id

        except Exception as e:
            logger.error(f"Failed to store visual episode: {e}")
            conn.close()
            return None

    def find_similar_visual(
        self,
        query_image_path: str,
        k: int = 5,
        min_significance: float = 0.0,
        require_person: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Find visually similar episodes to a query image.

        Args:
            query_image_path: Path to query image
            k: Number of similar episodes to return
            min_significance: Minimum significance threshold
            require_person: If True, only return episodes with person present

        Returns:
            List of similar episodes with similarity scores
        """
        # Extract query embedding
        result = self._extract_embedding(query_image_path)
        if not result:
            logger.warning("Could not extract query embedding")
            return []

        query_embedding, _ = result
        return self.find_similar_by_embedding(
            query_embedding, k, min_significance, require_person
        )

    def find_similar_by_embedding(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        min_significance: float = 0.0,
        require_person: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar episodes by embedding vector (cosine similarity).

        Args:
            query_embedding: Query embedding vector
            k: Number of similar episodes to return
            min_significance: Minimum significance threshold
            require_person: If True, only return episodes with person present

        Returns:
            List of similar episodes with similarity scores
        """
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Build query conditions
        conditions = ["embedding IS NOT NULL", "significance >= ?"]
        params = [min_significance]

        if require_person is not None:
            conditions.append("person_present = ?")
            params.append(1 if require_person else 0)

        where_clause = " AND ".join(conditions)

        cursor.execute(f'''
            SELECT id, timestamp, image_path, context, embedding, embedding_dim,
                   significance, person_present, scene_type, metadata_json
            FROM visual_episodes
            WHERE {where_clause}
            ORDER BY significance DESC
            LIMIT 1000
        ''', params)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # Normalize query embedding for cosine similarity
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Calculate similarities
        results = []
        for row in rows:
            (id_, timestamp, image_path, context, embedding_blob, embedding_dim,
             significance, person_present, scene_type, metadata_json) = row

            if not embedding_blob:
                continue

            # Reconstruct embedding
            stored_embedding = np.frombuffer(embedding_blob, dtype=np.float32)

            # Skip if dimensions don't match
            if len(stored_embedding) != len(query_embedding):
                continue

            # Cosine similarity
            stored_norm = stored_embedding / (np.linalg.norm(stored_embedding) + 1e-8)
            similarity = float(np.dot(query_norm, stored_norm))

            results.append({
                "episode_id": id_,
                "timestamp": timestamp,
                "image_path": image_path,
                "context": context,
                "similarity": similarity,
                "significance": significance,
                "person_present": bool(person_present),
                "scene_type": scene_type,
                "metadata": json.loads(metadata_json) if metadata_json else {}
            })

        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

    def get_recent_visual_episodes(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent visual episodes.

        Args:
            hours: Lookback period in hours
            limit: Maximum episodes to return

        Returns:
            List of recent visual episodes
        """
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, image_path, context, significance,
                   person_present, scene_type, metadata_json
            FROM visual_episodes
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (cutoff, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "episode_id": row[0],
                "timestamp": row[1],
                "image_path": row[2],
                "context": row[3],
                "significance": row[4],
                "person_present": bool(row[5]),
                "scene_type": row[6],
                "metadata": json.loads(row[7]) if row[7] else {}
            }
            for row in rows
        ]

    def get_visual_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about visual memory."""
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Total episodes
        cursor.execute("SELECT COUNT(*) FROM visual_episodes")
        total = cursor.fetchone()[0]

        # Episodes with embeddings
        cursor.execute("SELECT COUNT(*) FROM visual_episodes WHERE embedding IS NOT NULL")
        with_embeddings = cursor.fetchone()[0]

        # Person-present episodes
        cursor.execute("SELECT COUNT(*) FROM visual_episodes WHERE person_present = 1")
        with_person = cursor.fetchone()[0]

        # Scene type distribution
        cursor.execute('''
            SELECT scene_type, COUNT(*) as cnt
            FROM visual_episodes
            WHERE scene_type IS NOT NULL AND scene_type != ''
            GROUP BY scene_type
            ORDER BY cnt DESC
            LIMIT 10
        ''')
        scene_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Average significance
        cursor.execute("SELECT AVG(significance) FROM visual_episodes")
        avg_significance = cursor.fetchone()[0] or 0.0

        # Cluster count
        cursor.execute("SELECT COUNT(*) FROM visual_clusters")
        cluster_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total_episodes": total,
            "episodes_with_embeddings": with_embeddings,
            "episodes_with_person": with_person,
            "embedding_coverage": with_embeddings / total if total > 0 else 0,
            "person_presence_ratio": with_person / total if total > 0 else 0,
            "scene_distribution": scene_distribution,
            "average_significance": avg_significance,
            "cluster_count": cluster_count,
            "tpu_available": self._tpu is not None
        }

    def cluster_visual_memories(self, n_clusters: int = 10) -> Dict[str, Any]:
        """
        Cluster visual memories for manifold-based compression.

        Uses k-means on embeddings to group similar visual experiences.
        This implements the manifold hypothesis from the LVR paper.

        Args:
            n_clusters: Number of clusters to create

        Returns:
            Clustering results with cluster assignments
        """
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Get all embeddings
        cursor.execute('''
            SELECT id, embedding, embedding_dim
            FROM visual_episodes
            WHERE embedding IS NOT NULL
        ''')
        rows = cursor.fetchall()

        if len(rows) < n_clusters:
            conn.close()
            return {
                "error": f"Not enough episodes ({len(rows)}) for {n_clusters} clusters",
                "episodes_available": len(rows)
            }

        # Reconstruct embeddings
        episode_ids = []
        embeddings = []
        expected_dim = None

        for row in rows:
            id_, embedding_blob, embedding_dim = row
            emb = np.frombuffer(embedding_blob, dtype=np.float32)

            if expected_dim is None:
                expected_dim = len(emb)
            elif len(emb) != expected_dim:
                continue

            episode_ids.append(id_)
            embeddings.append(emb)

        if not embeddings:
            conn.close()
            return {"error": "No valid embeddings found"}

        X = np.array(embeddings)

        # Simple k-means clustering
        try:
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            centroids = kmeans.cluster_centers_
        except ImportError:
            # Manual k-means if sklearn not available
            logger.warning("sklearn not available, using manual clustering")
            labels, centroids = self._manual_kmeans(X, n_clusters)

        # Store clusters and update episodes
        cursor.execute("DELETE FROM visual_clusters")  # Clear old clusters

        cluster_info = []
        for i, centroid in enumerate(centroids):
            member_ids = [episode_ids[j] for j in range(len(labels)) if labels[j] == i]

            cursor.execute('''
                INSERT INTO visual_clusters (centroid, centroid_dim, member_count, cluster_label, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                centroid.astype(np.float32).tobytes(),
                len(centroid),
                len(member_ids),
                f"cluster_{i}",
                datetime.now().isoformat()
            ))
            cluster_id = cursor.lastrowid

            # Update episode cluster assignments
            for ep_id in member_ids:
                cursor.execute(
                    "UPDATE visual_episodes SET cluster_id = ? WHERE id = ?",
                    (cluster_id, ep_id)
                )

            cluster_info.append({
                "cluster_id": cluster_id,
                "member_count": len(member_ids),
                "member_ids": member_ids
            })

        conn.commit()
        conn.close()

        return {
            "clusters_created": len(cluster_info),
            "total_episodes_clustered": len(episode_ids),
            "clusters": cluster_info
        }

    def _manual_kmeans(self, X: np.ndarray, k: int, max_iter: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """Simple k-means implementation when sklearn unavailable."""
        n_samples = X.shape[0]

        # Random initialization
        indices = np.random.choice(n_samples, k, replace=False)
        centroids = X[indices].copy()

        for _ in range(max_iter):
            # Assign points to nearest centroid
            distances = np.array([
                [np.linalg.norm(x - c) for c in centroids]
                for x in X
            ])
            labels = np.argmin(distances, axis=1)

            # Update centroids
            new_centroids = np.array([
                X[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
                for i in range(k)
            ])

            # Check convergence
            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        return labels, centroids

    def hybrid_search(
        self,
        text_query: str = "",
        query_image_path: Optional[str] = None,
        k: int = 10,
        text_weight: float = 0.5,
        visual_weight: float = 0.5,
        min_significance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Hybrid text + visual search combining multiple signals.

        This implements LVR-style multimodal retrieval:
        - Text search on context/activity/scene_type fields
        - Visual similarity search using TPU embeddings
        - Combined scoring with configurable weights

        Args:
            text_query: Text to search in context/metadata
            query_image_path: Optional image for visual similarity
            k: Number of results to return
            text_weight: Weight for text relevance (0.0-1.0)
            visual_weight: Weight for visual similarity (0.0-1.0)
            min_significance: Minimum significance threshold

        Returns:
            List of episodes with combined_score, text_score, visual_score
        """
        if not text_query and not query_image_path:
            logger.warning("Hybrid search requires text_query or query_image_path")
            return []

        # Normalize weights
        total_weight = text_weight + visual_weight
        if total_weight > 0:
            text_weight /= total_weight
            visual_weight /= total_weight

        # Get text-matching episodes
        text_results = {}
        if text_query:
            conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
            cursor = conn.cursor()

            # Search in context, activity, scene_type, and metadata
            search_pattern = f"%{text_query.lower()}%"
            cursor.execute('''
                SELECT id, timestamp, image_path, context, significance,
                       person_present, activity, scene_type, metadata_json
                FROM visual_episodes
                WHERE significance >= ?
                  AND (LOWER(context) LIKE ?
                       OR LOWER(activity) LIKE ?
                       OR LOWER(scene_type) LIKE ?
                       OR LOWER(metadata_json) LIKE ?)
                ORDER BY significance DESC
                LIMIT 500
            ''', (min_significance, search_pattern, search_pattern,
                  search_pattern, search_pattern))

            rows = cursor.fetchall()
            conn.close()

            # Calculate text relevance scores based on match quality
            query_lower = text_query.lower()
            for row in rows:
                (id_, timestamp, image_path, context, significance,
                 person_present, activity, scene_type, metadata_json) = row

                # Simple relevance scoring: count matches in different fields
                score = 0.0
                context_lower = (context or "").lower()
                activity_lower = (activity or "").lower()
                scene_lower = (scene_type or "").lower()
                metadata_lower = (metadata_json or "").lower()

                # Exact match bonuses
                if query_lower in context_lower:
                    score += 0.4
                if query_lower in activity_lower:
                    score += 0.3
                if query_lower in scene_lower:
                    score += 0.2
                if query_lower in metadata_lower:
                    score += 0.1

                # Boost by significance
                score *= (0.5 + significance * 0.5)

                text_results[id_] = {
                    "episode_id": id_,
                    "timestamp": timestamp,
                    "image_path": image_path,
                    "context": context,
                    "significance": significance,
                    "person_present": bool(person_present),
                    "activity": activity,
                    "scene_type": scene_type,
                    "metadata": json.loads(metadata_json) if metadata_json else {},
                    "text_score": min(1.0, score),
                    "visual_score": 0.0
                }

        # Get visual-matching episodes
        visual_results = {}
        if query_image_path and self._tpu:
            similar = self.find_similar_visual(
                query_image_path,
                k=min(500, k * 10),  # Get more candidates for merging
                min_significance=min_significance
            )

            for result in similar:
                ep_id = result["episode_id"]
                visual_results[ep_id] = {
                    "episode_id": ep_id,
                    "timestamp": result["timestamp"],
                    "image_path": result["image_path"],
                    "context": result["context"],
                    "significance": result["significance"],
                    "person_present": result["person_present"],
                    "scene_type": result["scene_type"],
                    "metadata": result["metadata"],
                    "text_score": 0.0,
                    "visual_score": result["similarity"]
                }

        # Merge results
        all_ids = set(text_results.keys()) | set(visual_results.keys())
        merged_results = []

        for ep_id in all_ids:
            text_entry = text_results.get(ep_id, {})
            visual_entry = visual_results.get(ep_id, {})

            # Merge episode data
            result = text_entry if text_entry else visual_entry

            # Combine scores
            text_score = text_entry.get("text_score", 0.0)
            visual_score = visual_entry.get("visual_score", 0.0)

            combined_score = (text_score * text_weight) + (visual_score * visual_weight)

            result["text_score"] = text_score
            result["visual_score"] = visual_score
            result["combined_score"] = combined_score
            result["search_mode"] = "hybrid" if (text_score > 0 and visual_score > 0) else \
                                    "text" if text_score > 0 else "visual"

            merged_results.append(result)

        # Sort by combined score
        merged_results.sort(key=lambda x: x["combined_score"], reverse=True)

        logger.info(f"Hybrid search: {len(text_results)} text matches, "
                   f"{len(visual_results)} visual matches, "
                   f"{len(merged_results)} merged results")

        return merged_results[:k]


def main():
    """Test visual memory system."""
    import argparse

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


    parser = argparse.ArgumentParser(description="Visual Memory System")
    parser.add_argument("--store", help="Store image as visual episode")
    parser.add_argument("--context", default="", help="Context for stored image")
    parser.add_argument("--search", help="Find similar images to query")
    parser.add_argument("--recent", action="store_true", help="Show recent episodes")
    parser.add_argument("--stats", action="store_true", help="Show memory stats")
    parser.add_argument("--cluster", type=int, help="Cluster memories into N groups")
    parser.add_argument("-k", type=int, default=5, help="Number of results")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    vm = VisualMemory()

    if args.stats:
        stats = vm.get_visual_memory_stats()
        print("\nVisual Memory Statistics:")
        print(f"  Total episodes: {stats['total_episodes']}")
        print(f"  With embeddings: {stats['episodes_with_embeddings']} ({stats['embedding_coverage']:.1%})")
        print(f"  With person: {stats['episodes_with_person']} ({stats['person_presence_ratio']:.1%})")
        print(f"  Avg significance: {stats['average_significance']:.2f}")
        print(f"  TPU available: {stats['tpu_available']}")
        if stats['scene_distribution']:
            print(f"  Top scenes: {list(stats['scene_distribution'].items())[:5]}")

    elif args.store:
        print(f"Storing: {args.store}")
        episode_id = vm.store_visual_episode(args.store, args.context)
        if episode_id:
            print(f"Stored as episode {episode_id}")
        else:
            print("Failed to store")

    elif args.search:
        print(f"Searching for images similar to: {args.search}")
        results = vm.find_similar_visual(args.search, k=args.k)

        if results:
            print(f"\nFound {len(results)} similar episodes:")
            for r in results:
                print(f"  [{r['episode_id']}] sim={r['similarity']:.3f} | {r['scene_type']} | {r['image_path']}")
        else:
            print("No similar episodes found")

    elif args.recent:
        episodes = vm.get_recent_visual_episodes(hours=24, limit=args.k)
        print(f"\n{len(episodes)} recent visual episodes:")
        for ep in episodes:
            person = "person" if ep['person_present'] else "empty"
            print(f"  [{ep['episode_id']}] {ep['timestamp'][:16]} | {person} | {ep['scene_type']} | sig={ep['significance']:.2f}")

    elif args.cluster:
        print(f"Clustering into {args.cluster} groups...")
        result = vm.cluster_visual_memories(args.cluster)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Created {result['clusters_created']} clusters")
            for c in result['clusters']:
                print(f"  Cluster {c['cluster_id']}: {c['member_count']} members")

    else:
        print("Visual Memory System")
        print("  --stats       Show memory statistics")
        print("  --store IMG   Store image as visual episode")
        print("  --search IMG  Find similar images")
        print("  --recent      Show recent episodes")
        print("  --cluster N   Cluster memories")


if __name__ == "__main__":
    main()
