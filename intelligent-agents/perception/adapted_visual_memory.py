#!/usr/bin/env python3
"""
Adapted Visual Memory - Phase 3 LVR Integration

Extends VisualMemory with learned adapter transformation for
enhanced semantic embeddings. Based on CLIP-Adapter research.

The adapter transforms 1001-dim ImageNet logits into 256-dim
semantically richer embeddings that better capture visual concepts.

Features:
- Automatic adapter loading from trained model
- On-the-fly embedding transformation
- Backward compatibility with raw embeddings
- Optional re-encoding of existing episodes

Usage:
    from adapted_visual_memory import AdaptedVisualMemory

    vm = AdaptedVisualMemory()

    # Store with adapted embedding
    episode_id = vm.store_visual_episode(
        image_path="/path/to/image.jpg",
        context="Working at desk"
    )

    # Find similar (uses adapted embeddings)
    similar = vm.find_similar_visual("/path/to/query.jpg", k=5)

    # Re-encode existing episodes
    stats = vm.reencode_all_episodes()
"""
import os
import platform

import logging
import sqlite3
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("adapted_visual_memory")

# Storage paths
STORAGE_BASE = Path(str(_STORAGE_BASE))
VISUAL_MEMORY_DB = STORAGE_BASE / "databases" / "sensory" / "visual_memories.db"
DEFAULT_ADAPTER_PATH = STORAGE_BASE / "models" / "adapters" / "visual_adapter.npz"

# Embedding dimensions
RAW_EMBEDDING_DIM = 1001  # MobileNet V2 ImageNet logits
ADAPTED_EMBEDDING_DIM = 256  # Adapter output dimension
CROSSMODAL_EMBEDDING_DIM = 1024  # bge-m3 text embedding dimension


class AdaptedVisualMemory:
    """
    Visual memory with learned adapter transformation.

    Wraps VisualMemory to add:
    1. Adapter-based embedding transformation
    2. Dual storage (raw + adapted embeddings)
    3. Re-encoding capability for existing episodes
    """

    def __init__(
        self,
        use_tpu: bool = True,
        use_adapter: bool = True,
        adapter_path: str = None
    ):
        """
        Initialize adapted visual memory.

        Args:
            use_tpu: Whether to use TPU for embedding extraction
            use_adapter: Whether to use adapter transformation
            adapter_path: Path to adapter weights (uses default if None)
        """
        # Import base visual memory
        from visual_memory import VisualMemory
        self._base = VisualMemory(use_tpu=use_tpu)

        # Load adapter
        self._adapter = None
        self.use_adapter = use_adapter

        if use_adapter:
            self._load_adapter(adapter_path)

        # GPU feature extractor (lazy loaded)
        self._gpu_extractor = None

        # Ensure embedding columns exist
        self._ensure_adapted_column()

    def _load_adapter(self, path: str = None):
        """Load trained adapter weights."""
        from visual_adapter import VisualAdapter, load_adapter

        adapter_path = Path(path) if path else DEFAULT_ADAPTER_PATH

        if adapter_path.exists():
            self._adapter = load_adapter(str(adapter_path))
            if self._adapter:
                logger.info(f"Loaded adapter from {adapter_path}")
                logger.info(f"  Input dim: {self._adapter.input_dim}")
                logger.info(f"  Output dim: {self._adapter.output_dim}")
                logger.info(f"  Alpha: {self._adapter.alpha:.3f}")
                logger.info(f"  Trained: {self._adapter._trained}")
            else:
                logger.warning("Adapter file exists but failed to load")
        else:
            logger.warning(f"No adapter found at {adapter_path}")
            logger.info("Using raw embeddings without adaptation")

    def _ensure_adapted_column(self):
        """Add adapted_embedding and crossmodal columns if they don't exist."""
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Check if columns exist
        cursor.execute("PRAGMA table_info(visual_episodes)")
        columns = [row[1] for row in cursor.fetchall()]

        if "adapted_embedding" not in columns:
            cursor.execute('''
                ALTER TABLE visual_episodes
                ADD COLUMN adapted_embedding BLOB
            ''')
            logger.info("Added adapted_embedding column to visual_episodes")

        if "adapted_dim" not in columns:
            cursor.execute('''
                ALTER TABLE visual_episodes
                ADD COLUMN adapted_dim INTEGER
            ''')

        # Cross-modal embedding columns (for GPU-based text-image alignment)
        if "crossmodal_embedding" not in columns:
            cursor.execute('''
                ALTER TABLE visual_episodes
                ADD COLUMN crossmodal_embedding BLOB
            ''')
            logger.info("Added crossmodal_embedding column to visual_episodes")

        if "crossmodal_dim" not in columns:
            cursor.execute('''
                ALTER TABLE visual_episodes
                ADD COLUMN crossmodal_dim INTEGER
            ''')

        if "visual_description" not in columns:
            cursor.execute('''
                ALTER TABLE visual_episodes
                ADD COLUMN visual_description TEXT
            ''')
            logger.info("Added visual_description column to visual_episodes")

        conn.commit()
        conn.close()

    def _transform_embedding(self, raw_embedding: np.ndarray) -> np.ndarray:
        """Transform raw embedding through adapter."""
        if self._adapter and self.use_adapter:
            return self._adapter.transform(raw_embedding)
        return raw_embedding

    def store_visual_episode(
        self,
        image_path: str,
        context: str = "",
        significance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Store visual episode with both raw and adapted embeddings.

        Args:
            image_path: Path to image file
            context: Text context/description
            significance: Importance score 0.0-1.0
            metadata: Additional metadata dict

        Returns:
            Episode ID if successful, None otherwise
        """
        # Store using base class (gets raw embedding)
        episode_id = self._base.store_visual_episode(
            image_path=image_path,
            context=context,
            significance=significance,
            metadata=metadata
        )

        if episode_id is None:
            return None

        # Add adapted embedding if adapter available
        if self._adapter:
            self._update_adapted_embedding(episode_id)

        return episode_id

    def _update_adapted_embedding(self, episode_id: int) -> bool:
        """Update adapted embedding for a single episode."""
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Get raw embedding
        cursor.execute(
            "SELECT embedding FROM visual_episodes WHERE id = ?",
            (episode_id,)
        )
        row = cursor.fetchone()

        if not row or not row[0]:
            conn.close()
            return False

        raw_embedding = np.frombuffer(row[0], dtype=np.float32)

        # Transform through adapter
        adapted = self._transform_embedding(raw_embedding)
        adapted_blob = adapted.astype(np.float32).tobytes()

        # Update database
        cursor.execute('''
            UPDATE visual_episodes
            SET adapted_embedding = ?, adapted_dim = ?
            WHERE id = ?
        ''', (adapted_blob, len(adapted), episode_id))

        conn.commit()
        conn.close()
        return True

    def find_similar_visual(
        self,
        query_image_path: str,
        k: int = 5,
        min_significance: float = 0.0,
        require_person: Optional[bool] = None,
        use_adapted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find similar episodes using adapted embeddings.

        Args:
            query_image_path: Path to query image
            k: Number of similar episodes to return
            min_significance: Minimum significance threshold
            require_person: If True, only return episodes with person present
            use_adapted: Whether to use adapted embeddings (default True)

        Returns:
            List of similar episodes with similarity scores
        """
        # Extract query embedding
        result = self._base._extract_embedding(query_image_path)
        if not result:
            logger.warning("Could not extract query embedding")
            return []

        query_embedding, _ = result

        # Transform query embedding
        if use_adapted and self._adapter:
            query_embedding = self._transform_embedding(query_embedding)

        return self._find_similar_by_adapted_embedding(
            query_embedding, k, min_significance, require_person, use_adapted
        )

    def _find_similar_by_adapted_embedding(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        min_significance: float = 0.0,
        require_person: Optional[bool] = None,
        use_adapted: bool = True
    ) -> List[Dict[str, Any]]:
        """Find similar episodes by adapted embedding."""
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Determine which embedding column to use
        embedding_col = "adapted_embedding" if use_adapted and self._adapter else "embedding"

        # Build query conditions
        conditions = [f"{embedding_col} IS NOT NULL", "significance >= ?"]
        params = [min_significance]

        if require_person is not None:
            conditions.append("person_present = ?")
            params.append(1 if require_person else 0)

        where_clause = " AND ".join(conditions)

        cursor.execute(f'''
            SELECT id, timestamp, image_path, context, {embedding_col},
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

        # Normalize query embedding
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Calculate similarities
        results = []
        for row in rows:
            (id_, timestamp, image_path, context, embedding_blob,
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

            import json
            results.append({
                "episode_id": id_,
                "timestamp": timestamp,
                "image_path": image_path,
                "context": context,
                "similarity": similarity,
                "significance": significance,
                "person_present": bool(person_present),
                "scene_type": scene_type,
                "metadata": json.loads(metadata_json) if metadata_json else {},
                "embedding_type": "adapted" if use_adapted and self._adapter else "raw"
            })

        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

    def reencode_all_episodes(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Re-encode all existing episodes with adapter.

        Useful after training a new adapter to update all embeddings.

        Args:
            batch_size: Episodes to process at a time

        Returns:
            Statistics about re-encoding
        """
        if not self._adapter:
            return {"error": "No adapter loaded", "success": False}

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Get episodes with raw embeddings but no adapted embeddings
        cursor.execute('''
            SELECT id, embedding
            FROM visual_episodes
            WHERE embedding IS NOT NULL
        ''')

        rows = cursor.fetchall()

        total = len(rows)
        updated = 0
        skipped = 0
        errors = 0

        for episode_id, embedding_blob in rows:
            if not embedding_blob:
                skipped += 1
                continue

            try:
                # Reconstruct raw embedding
                raw_embedding = np.frombuffer(embedding_blob, dtype=np.float32)

                # Transform through adapter
                adapted = self._transform_embedding(raw_embedding)
                adapted_blob = adapted.astype(np.float32).tobytes()

                # Update database
                cursor.execute('''
                    UPDATE visual_episodes
                    SET adapted_embedding = ?, adapted_dim = ?
                    WHERE id = ?
                ''', (adapted_blob, len(adapted), episode_id))

                updated += 1

            except Exception as e:
                logger.error(f"Failed to re-encode episode {episode_id}: {e}")
                errors += 1

        conn.commit()
        conn.close()

        return {
            "success": True,
            "total_episodes": total,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "adapter_dim": self._adapter.output_dim
        }

    def compare_similarity_methods(
        self,
        query_image_path: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Compare raw vs adapted embedding similarity results.

        Useful for evaluating adapter effectiveness.

        Args:
            query_image_path: Path to query image
            k: Number of results per method

        Returns:
            Comparison results
        """
        # Get results with both methods
        raw_results = self.find_similar_visual(
            query_image_path, k=k, use_adapted=False
        )
        adapted_results = self.find_similar_visual(
            query_image_path, k=k, use_adapted=True
        )

        # Extract IDs for comparison
        raw_ids = [r["episode_id"] for r in raw_results]
        adapted_ids = [r["episode_id"] for r in adapted_results]

        # Calculate overlap
        overlap = len(set(raw_ids) & set(adapted_ids))

        # Calculate similarity score changes
        score_changes = []
        for adapted_r in adapted_results:
            for raw_r in raw_results:
                if adapted_r["episode_id"] == raw_r["episode_id"]:
                    score_changes.append({
                        "episode_id": adapted_r["episode_id"],
                        "raw_similarity": raw_r["similarity"],
                        "adapted_similarity": adapted_r["similarity"],
                        "delta": adapted_r["similarity"] - raw_r["similarity"]
                    })
                    break

        return {
            "query_image": query_image_path,
            "raw_results": raw_results,
            "adapted_results": adapted_results,
            "overlap_count": overlap,
            "overlap_ratio": overlap / k if k > 0 else 0,
            "score_changes": score_changes,
            "avg_raw_similarity": np.mean([r["similarity"] for r in raw_results]) if raw_results else 0,
            "avg_adapted_similarity": np.mean([r["similarity"] for r in adapted_results]) if adapted_results else 0
        }

    def get_adapted_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about adapted visual memory."""
        # Get base stats
        stats = self._base.get_visual_memory_stats()

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Episodes with adapted embeddings
        cursor.execute(
            "SELECT COUNT(*) FROM visual_episodes WHERE adapted_embedding IS NOT NULL"
        )
        with_adapted = cursor.fetchone()[0]

        conn.close()

        stats["with_adapted_embeddings"] = with_adapted
        stats["adapter_loaded"] = self._adapter is not None
        if self._adapter:
            stats["adapter_config"] = {
                "input_dim": self._adapter.input_dim,
                "hidden_dim": self._adapter.hidden_dim,
                "output_dim": self._adapter.output_dim,
                "alpha": self._adapter.alpha,
                "trained": self._adapter._trained
            }

        return stats

    # Delegate other methods to base class
    def get_recent_visual_episodes(self, hours: int = 24, limit: int = 50):
        return self._base.get_recent_visual_episodes(hours, limit)

    def cluster_visual_memories(self, n_clusters: int = 10):
        return self._base.cluster_visual_memories(n_clusters)

    def hybrid_search(self, *args, **kwargs):
        return self._base.hybrid_search(*args, **kwargs)

    # =========================================================================
    # Cross-Modal Embedding Methods (GPU-based text-image alignment)
    # =========================================================================

    def _get_gpu_extractor(self):
        """Get GPU feature extractor (lazy loaded)."""
        if self._gpu_extractor is None:
            try:
                from gpu_visual_features import GPUVisualFeatureExtractor
                self._gpu_extractor = GPUVisualFeatureExtractor()
                if self._gpu_extractor.is_available:
                    logger.info("GPU feature extractor initialized")
                else:
                    logger.warning("GPU node not available")
            except Exception as e:
                logger.error(f"Failed to initialize GPU extractor: {e}")
                return None
        return self._gpu_extractor

    def add_crossmodal_embedding(self, episode_id: int) -> Dict[str, Any]:
        """
        Add cross-modal embedding to an existing episode using GPU.

        Uses moondream to describe the image, then bge-m3 to embed
        the description. This bridges visual content to text embedding space.

        Args:
            episode_id: ID of episode to update

        Returns:
            Dict with embedding info and description
        """
        extractor = self._get_gpu_extractor()
        if extractor is None or not extractor.is_available:
            return {"error": "GPU extractor not available", "success": False}

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        # Get image path
        cursor.execute(
            "SELECT image_path FROM visual_episodes WHERE id = ?",
            (episode_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"error": f"Episode {episode_id} not found", "success": False}

        image_path = row[0]
        conn.close()

        # Create cross-modal embedding via GPU
        result = extractor.create_cross_modal_embedding(image_path)
        if not result:
            return {"error": "Failed to create cross-modal embedding", "success": False}

        # Store in database
        embedding = result["embedding"]
        description = result["description"]

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        embedding_blob = embedding.astype(np.float32).tobytes()

        cursor.execute('''
            UPDATE visual_episodes
            SET crossmodal_embedding = ?,
                crossmodal_dim = ?,
                visual_description = ?
            WHERE id = ?
        ''', (embedding_blob, len(embedding), description, episode_id))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "episode_id": episode_id,
            "description": description,
            "embedding_dim": len(embedding),
            "model_vision": result["model_vision"],
            "model_embed": result["model_embed"]
        }

    def batch_add_crossmodal_embeddings(
        self,
        episode_ids: List[int] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Add cross-modal embeddings to multiple episodes.

        If episode_ids not specified, processes episodes without
        crossmodal_embedding up to limit.

        Args:
            episode_ids: Specific episodes to process (optional)
            limit: Maximum episodes to process if IDs not specified

        Returns:
            Statistics about processing
        """
        extractor = self._get_gpu_extractor()
        if extractor is None or not extractor.is_available:
            return {"error": "GPU extractor not available", "success": False}

        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        if episode_ids:
            placeholders = ",".join("?" * len(episode_ids))
            cursor.execute(f'''
                SELECT id FROM visual_episodes
                WHERE id IN ({placeholders})
            ''', episode_ids)
        else:
            # Get episodes without crossmodal embedding
            cursor.execute('''
                SELECT id FROM visual_episodes
                WHERE crossmodal_embedding IS NULL
                ORDER BY significance DESC
                LIMIT ?
            ''', (limit,))

        ids_to_process = [row[0] for row in cursor.fetchall()]
        conn.close()

        results = {
            "success": True,
            "total": len(ids_to_process),
            "processed": 0,
            "errors": 0,
            "episodes": []
        }

        for episode_id in ids_to_process:
            result = self.add_crossmodal_embedding(episode_id)
            if result.get("success"):
                results["processed"] += 1
                results["episodes"].append({
                    "episode_id": episode_id,
                    "description": result.get("description", "")[:100] + "..."
                })
            else:
                results["errors"] += 1
                logger.error(f"Failed to process episode {episode_id}: {result.get('error')}")

        return results

    def find_by_text(
        self,
        text_query: str,
        k: int = 10,
        min_significance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find visually similar episodes using text query.

        Text-to-image search: embeds the text query with bge-m3,
        then finds episodes with similar crossmodal_embeddings.

        Args:
            text_query: Natural language description to search for
            k: Number of results to return
            min_significance: Minimum significance threshold

        Returns:
            List of matching episodes with similarity scores
        """
        extractor = self._get_gpu_extractor()
        if extractor is None or not extractor.is_available:
            logger.warning("GPU extractor not available for text search")
            return []

        # Embed the text query
        query_embedding = extractor.get_text_embedding(text_query)
        if query_embedding is None:
            logger.error("Failed to embed text query")
            return []

        # Search against crossmodal_embeddings
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, image_path, context, crossmodal_embedding,
                   significance, person_present, scene_type, visual_description,
                   metadata_json
            FROM visual_episodes
            WHERE crossmodal_embedding IS NOT NULL
              AND significance >= ?
            ORDER BY significance DESC
            LIMIT 1000
        ''', (min_significance,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # Normalize query embedding
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Calculate similarities
        results = []
        import json
        for row in rows:
            (id_, timestamp, image_path, context, embedding_blob,
             significance, person_present, scene_type, visual_description,
             metadata_json) = row

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
                "visual_description": visual_description,
                "metadata": json.loads(metadata_json) if metadata_json else {},
                "search_type": "text_to_image"
            })

        # Sort by similarity and return top k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

    def multimodal_search(
        self,
        text_query: str = "",
        image_path: str = None,
        k: int = 10,
        text_weight: float = 0.5,
        visual_weight: float = 0.5,
        use_crossmodal: bool = True,
        use_adapted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Multimodal search combining text and visual queries.

        Supports three search modes:
        1. Text only: Uses crossmodal embeddings for text-to-image search
        2. Image only: Uses adapted embeddings for visual similarity
        3. Both: Combines scores with configurable weights

        Args:
            text_query: Natural language query
            image_path: Query image path
            k: Number of results to return
            text_weight: Weight for text similarity (0.0-1.0)
            visual_weight: Weight for visual similarity (0.0-1.0)
            use_crossmodal: Use GPU crossmodal for text search
            use_adapted: Use adapter for visual search

        Returns:
            List of results with combined scores
        """
        text_results = []
        visual_results = []

        # Text-based search
        if text_query and use_crossmodal:
            text_results = self.find_by_text(text_query, k=k*2)

        # Visual-based search
        if image_path:
            visual_results = self.find_similar_visual(
                image_path, k=k*2, use_adapted=use_adapted
            )

        # If only one mode, return those results
        if not text_results and visual_results:
            return visual_results[:k]
        if text_results and not visual_results:
            return text_results[:k]
        if not text_results and not visual_results:
            return []

        # Combine results
        combined = {}

        for r in text_results:
            ep_id = r["episode_id"]
            combined[ep_id] = {
                **r,
                "text_similarity": r["similarity"],
                "visual_similarity": 0.0,
                "combined_score": r["similarity"] * text_weight
            }

        for r in visual_results:
            ep_id = r["episode_id"]
            if ep_id in combined:
                combined[ep_id]["visual_similarity"] = r["similarity"]
                combined[ep_id]["combined_score"] += r["similarity"] * visual_weight
            else:
                combined[ep_id] = {
                    **r,
                    "text_similarity": 0.0,
                    "visual_similarity": r["similarity"],
                    "combined_score": r["similarity"] * visual_weight
                }

        # Sort by combined score
        results = list(combined.values())
        results.sort(key=lambda x: x["combined_score"], reverse=True)

        for r in results:
            r["search_type"] = "multimodal"

        return results[:k]

    def get_crossmodal_stats(self) -> Dict[str, Any]:
        """Get statistics about cross-modal embeddings."""
        conn = sqlite3.connect(str(VISUAL_MEMORY_DB))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM visual_episodes")
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM visual_episodes WHERE crossmodal_embedding IS NOT NULL"
        )
        with_crossmodal = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM visual_episodes WHERE visual_description IS NOT NULL"
        )
        with_description = cursor.fetchone()[0]

        conn.close()

        extractor = self._get_gpu_extractor()

        return {
            "total_episodes": total,
            "with_crossmodal_embedding": with_crossmodal,
            "with_visual_description": with_description,
            "coverage_percent": (with_crossmodal / total * 100) if total > 0 else 0,
            "gpu_available": extractor is not None and extractor.is_available if extractor else False,
            "crossmodal_dim": CROSSMODAL_EMBEDDING_DIM
        }


def main():
    """Test adapted visual memory."""
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


    parser = argparse.ArgumentParser(description="Adapted Visual Memory")
    parser.add_argument("--reencode", action="store_true", help="Re-encode all episodes")
    parser.add_argument("--compare", help="Compare methods with query image")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    # Initialize (may not have TPU in test environment)
    vm = AdaptedVisualMemory(use_tpu=False)

    if args.reencode:
        print("Re-encoding all episodes with adapter...")
        result = vm.reencode_all_episodes()
        print(f"Result: {result}")

    elif args.compare:
        print(f"Comparing similarity methods for: {args.compare}")
        result = vm.compare_similarity_methods(args.compare)
        print(f"\nRaw top results:")
        for r in result["raw_results"][:5]:
            print(f"  [{r['episode_id']}] sim={r['similarity']:.3f} | {r.get('context', '')[:40]}")
        print(f"\nAdapted top results:")
        for r in result["adapted_results"][:5]:
            print(f"  [{r['episode_id']}] sim={r['similarity']:.3f} | {r.get('context', '')[:40]}")
        print(f"\nOverlap: {result['overlap_count']}/{len(result['raw_results'])}")
        print(f"Avg raw similarity: {result['avg_raw_similarity']:.3f}")
        print(f"Avg adapted similarity: {result['avg_adapted_similarity']:.3f}")

    elif args.stats:
        stats = vm.get_adapted_memory_stats()
        print("Adapted Visual Memory Statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")

    else:
        print("Adapted Visual Memory")
        print("  --reencode    Re-encode all episodes with adapter")
        print("  --compare IMG Compare raw vs adapted similarity")
        print("  --stats       Show memory statistics")


if __name__ == "__main__":
    main()
