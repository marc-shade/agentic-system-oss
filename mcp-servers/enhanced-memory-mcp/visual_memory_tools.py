#!/usr/bin/env python3
"""
Visual Memory MCP Tools

Provides MCP tools for visual embedding storage and similarity search.
Implements Phase 2 of the Latent Visual Reasoning (LVR) integration.

Features:
- Store visual episodes with TPU embeddings
- Find similar visual experiences via cosine similarity
- Cluster visual memories for manifold compression
- Get visual memory statistics

Research basis:
- Latent Visual Reasoning (LVR) - arxiv:2509.24251
- Manifold hypothesis for visual concept organization
"""
import platform

import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import os

logger = logging.getLogger(__name__)

# Add perception module to path
PERCEPTION_PATH = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "intelligent-agents/perception"))
sys.path.insert(0, str(PERCEPTION_PATH))


def register_visual_memory_tools(app, use_tpu: bool = True):
    """
    Register visual memory tools with the FastMCP app.

    Args:
        app: FastMCP application instance
        use_tpu: Whether to use TPU for embedding extraction
    """
    # Lazy import to avoid loading TPU if not needed
    visual_memory = None

    def get_visual_memory():
        nonlocal visual_memory
        if visual_memory is None:
            try:
                from visual_memory import VisualMemory
                visual_memory = VisualMemory(use_tpu=use_tpu)
                logger.info("Visual memory initialized")
            except Exception as e:
                logger.error(f"Failed to initialize visual memory: {e}")
                return None
        return visual_memory

    @app.tool()
    async def store_visual_episode(
        image_path: str,
        context: str = "",
        significance: float = 0.5,
        activity: str = "",
        person_present: bool = False
    ) -> Dict[str, Any]:
        """
        Store a visual episode with TPU embedding for similarity search.

        Uses Edge TPU to extract visual embeddings for LVR-style reasoning.
        Embeddings enable finding similar visual experiences later.

        Args:
            image_path: Path to image file
            context: Text description of what's happening
            significance: Importance score 0.0-1.0 (default 0.5)
            activity: What activity is occurring (e.g., "coding", "meeting")
            person_present: Whether a person is in the image

        Returns:
            Dict with episode_id and extraction metadata

        Example:
            result = await store_visual_episode(
                image_path="/path/to/webcam.jpg",
                context="Working at main desk",
                significance=0.7,
                activity="coding"
            )
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            metadata = {}
            if activity:
                metadata["activity"] = activity
            if person_present:
                metadata["person_present"] = person_present

            episode_id = vm.store_visual_episode(
                image_path=image_path,
                context=context,
                significance=significance,
                metadata=metadata if metadata else None
            )

            if episode_id:
                return {
                    "success": True,
                    "episode_id": episode_id,
                    "message": f"Stored visual episode {episode_id}",
                    "image_path": image_path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to store visual episode"
                }

        except Exception as e:
            logger.error(f"store_visual_episode error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def find_similar_visual(
        query_image_path: str,
        k: int = 5,
        min_significance: float = 0.0,
        require_person: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Find visually similar episodes to a query image.

        Uses cosine similarity on TPU embeddings to find
        semantically similar visual experiences.

        Args:
            query_image_path: Path to query image
            k: Number of similar episodes to return (default 5)
            min_significance: Minimum significance threshold (default 0.0)
            require_person: If set, filter by person presence

        Returns:
            List of similar episodes with similarity scores

        Example:
            results = await find_similar_visual(
                query_image_path="/path/to/current.jpg",
                k=10,
                require_person=True
            )
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            results = vm.find_similar_visual(
                query_image_path=query_image_path,
                k=k,
                min_significance=min_significance,
                require_person=require_person
            )

            return {
                "success": True,
                "query_image": query_image_path,
                "similar_episodes": results,
                "count": len(results)
            }

        except Exception as e:
            logger.error(f"find_similar_visual error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def get_recent_visual_episodes(
        hours: int = 24,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get recent visual episodes from memory.

        Args:
            hours: Lookback period in hours (default 24)
            limit: Maximum episodes to return (default 50)

        Returns:
            List of recent visual episodes with metadata

        Example:
            episodes = await get_recent_visual_episodes(hours=4, limit=20)
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            episodes = vm.get_recent_visual_episodes(
                hours=hours,
                limit=limit
            )

            return {
                "success": True,
                "episodes": episodes,
                "count": len(episodes),
                "lookback_hours": hours
            }

        except Exception as e:
            logger.error(f"get_recent_visual_episodes error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def get_visual_memory_stats() -> Dict[str, Any]:
        """
        Get statistics about visual memory system.

        Returns:
            Statistics including episode counts, embedding coverage,
            scene distribution, and TPU availability

        Example:
            stats = await get_visual_memory_stats()
            print(f"Total episodes: {stats['total_episodes']}")
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            stats = vm.get_visual_memory_stats()
            stats["success"] = True
            return stats

        except Exception as e:
            logger.error(f"get_visual_memory_stats error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def cluster_visual_memories(
        n_clusters: int = 10
    ) -> Dict[str, Any]:
        """
        Cluster visual memories for manifold-based compression.

        Uses k-means clustering on embeddings to group similar
        visual experiences. Implements the manifold hypothesis
        from LVR research for organized visual concept space.

        Args:
            n_clusters: Number of clusters to create (default 10)

        Returns:
            Clustering results with cluster assignments

        Example:
            result = await cluster_visual_memories(n_clusters=5)
            print(f"Created {result['clusters_created']} clusters")
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            result = vm.cluster_visual_memories(n_clusters=n_clusters)
            result["success"] = "error" not in result
            return result

        except Exception as e:
            logger.error(f"cluster_visual_memories error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def hybrid_visual_search(
        text_query: str = "",
        query_image_path: str = "",
        k: int = 10,
        text_weight: float = 0.5,
        visual_weight: float = 0.5,
        min_significance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Hybrid text + visual search across visual memories.

        Combines text-based search (context, activity, scene) with
        visual similarity (TPU embeddings) for multimodal retrieval.

        Implements LVR-style multimodal memory recall where both
        semantic and visual signals contribute to finding relevant
        past experiences.

        Args:
            text_query: Text to search in context/metadata
            query_image_path: Optional image path for visual similarity
            k: Number of results to return (default 10)
            text_weight: Weight for text relevance (default 0.5)
            visual_weight: Weight for visual similarity (default 0.5)
            min_significance: Minimum significance threshold (default 0.0)

        Returns:
            Results with combined_score, text_score, and visual_score

        Example:
            # Text-only search
            results = await hybrid_visual_search(
                text_query="coding at desk",
                k=5
            )

            # Visual-only search
            results = await hybrid_visual_search(
                query_image_path="/path/to/current.jpg",
                k=5
            )

            # Hybrid search (best for context-aware recall)
            results = await hybrid_visual_search(
                text_query="working",
                query_image_path="/path/to/current.jpg",
                text_weight=0.4,
                visual_weight=0.6,
                k=10
            )
        """
        vm = get_visual_memory()
        if vm is None:
            return {"error": "Visual memory not available", "success": False}

        try:
            results = vm.hybrid_search(
                text_query=text_query,
                query_image_path=query_image_path if query_image_path else None,
                k=k,
                text_weight=text_weight,
                visual_weight=visual_weight,
                min_significance=min_significance
            )

            # Summarize search mode distribution
            modes = {}
            for r in results:
                mode = r.get("search_mode", "unknown")
                modes[mode] = modes.get(mode, 0) + 1

            return {
                "success": True,
                "text_query": text_query,
                "query_image": query_image_path if query_image_path else None,
                "results": results,
                "count": len(results),
                "mode_distribution": modes,
                "weights": {"text": text_weight, "visual": visual_weight}
            }

        except Exception as e:
            logger.error(f"hybrid_visual_search error: {e}")
            return {"error": str(e), "success": False}

    # Adapted visual memory tools (Phase 3)
    adapted_memory = None

    def get_adapted_visual_memory():
        nonlocal adapted_memory
        if adapted_memory is None:
            try:
                from adapted_visual_memory import AdaptedVisualMemory
                adapted_memory = AdaptedVisualMemory(use_tpu=use_tpu)
                logger.info("Adapted visual memory initialized")
            except Exception as e:
                logger.error(f"Failed to initialize adapted visual memory: {e}")
                return None
        return adapted_memory

    @app.tool()
    async def find_similar_adapted(
        query_image_path: str,
        k: int = 5,
        min_significance: float = 0.0,
        use_adapted: bool = True
    ) -> Dict[str, Any]:
        """
        Find similar episodes using adapter-enhanced embeddings.

        Uses CLIP-Adapter style transformation for improved
        semantic similarity. Transforms 1001-dim TPU logits
        to 256-dim adapted embeddings.

        Args:
            query_image_path: Path to query image
            k: Number of similar episodes to return (default 5)
            min_significance: Minimum significance threshold (default 0.0)
            use_adapted: Use adapted embeddings (default True)

        Returns:
            List of similar episodes with similarity scores

        Example:
            results = await find_similar_adapted(
                query_image_path="/path/to/current.jpg",
                k=10,
                use_adapted=True
            )
        """
        avm = get_adapted_visual_memory()
        if avm is None:
            return {"error": "Adapted visual memory not available", "success": False}

        try:
            results = avm.find_similar_visual(
                query_image_path=query_image_path,
                k=k,
                min_significance=min_significance,
                use_adapted=use_adapted
            )

            return {
                "success": True,
                "query_image": query_image_path,
                "similar_episodes": results,
                "count": len(results),
                "embedding_type": "adapted" if use_adapted else "raw"
            }

        except Exception as e:
            logger.error(f"find_similar_adapted error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def reencode_visual_episodes() -> Dict[str, Any]:
        """
        Re-encode all visual episodes with the trained adapter.

        Transforms existing 1001-dim embeddings to 256-dim adapted
        embeddings. Run after training a new adapter to update
        all stored episodes.

        Returns:
            Statistics about re-encoding process

        Example:
            result = await reencode_visual_episodes()
            print(f"Updated {result['updated']} episodes")
        """
        avm = get_adapted_visual_memory()
        if avm is None:
            return {"error": "Adapted visual memory not available", "success": False}

        try:
            result = avm.reencode_all_episodes()
            return result

        except Exception as e:
            logger.error(f"reencode_visual_episodes error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def compare_visual_similarity_methods(
        query_image_path: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Compare raw vs adapted embedding similarity results.

        Useful for evaluating adapter effectiveness. Shows
        results from both methods side-by-side with statistics.

        Args:
            query_image_path: Path to query image
            k: Number of results per method (default 10)

        Returns:
            Comparison results with both rankings and statistics

        Example:
            result = await compare_visual_similarity_methods(
                query_image_path="/path/to/query.jpg",
                k=5
            )
            print(f"Improvement: {result['avg_adapted_similarity'] - result['avg_raw_similarity']:.3f}")
        """
        avm = get_adapted_visual_memory()
        if avm is None:
            return {"error": "Adapted visual memory not available", "success": False}

        try:
            result = avm.compare_similarity_methods(query_image_path, k)
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"compare_visual_similarity_methods error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def get_adapted_visual_stats() -> Dict[str, Any]:
        """
        Get statistics about adapted visual memory system.

        Returns adapter configuration, embedding coverage, and
        comparison between raw and adapted embedding counts.

        Returns:
            Comprehensive statistics about the adapted visual memory

        Example:
            stats = await get_adapted_visual_stats()
            print(f"Adapter trained: {stats['adapter_config']['trained']}")
        """
        avm = get_adapted_visual_memory()
        if avm is None:
            return {"error": "Adapted visual memory not available", "success": False}

        try:
            stats = avm.get_adapted_memory_stats()
            stats["success"] = True
            return stats

        except Exception as e:
            logger.error(f"get_adapted_visual_stats error: {e}")
            return {"error": str(e), "success": False}

    # GPU Visual Feature Extraction tools (Phase 3+)
    gpu_extractor = None

    def get_gpu_extractor():
        nonlocal gpu_extractor
        if gpu_extractor is None:
            try:
                from gpu_visual_features import GPUVisualFeatureExtractor

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

                gpu_extractor = GPUVisualFeatureExtractor()
                logger.info("GPU visual feature extractor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize GPU extractor: {e}")
                return None
        return gpu_extractor

    @app.tool()
    async def gpu_describe_image(
        image_path: str,
        prompt: str = "Describe this image in detail, including objects, scene, actions, and any text visible."
    ) -> Dict[str, Any]:
        """
        Get natural language description of image using GPU vision model.

        Uses moondream vision-language model on GPU inference node for
        rich semantic understanding of image content.

        Args:
            image_path: Path to image file
            prompt: Optional custom description prompt

        Returns:
            Dict with description, model, and latency

        Example:
            result = await gpu_describe_image(
                image_path="/path/to/image.jpg"
            )
            print(result["description"])
        """
        extractor = get_gpu_extractor()
        if extractor is None:
            return {"error": "GPU extractor not available", "success": False}

        if not extractor.is_available:
            return {"error": "GPU node not reachable", "success": False}

        try:
            result = extractor.describe_image(image_path, prompt)
            if result:
                result["success"] = True
                return result
            return {"error": "Failed to describe image", "success": False}

        except Exception as e:
            logger.error(f"gpu_describe_image error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def gpu_extract_visual_features(
        image_path: str,
        include_description: bool = True
    ) -> Dict[str, Any]:
        """
        Extract structured visual features using GPU vision model.

        Extracts objects, scene type, and description from image
        using moondream for structured understanding.

        Args:
            image_path: Path to image file
            include_description: Include text description (default True)

        Returns:
            Dict with objects, scene, description, and latency

        Example:
            result = await gpu_extract_visual_features(
                image_path="/path/to/image.jpg"
            )
            print(f"Scene: {result['scene']}")
            print(f"Objects: {result['objects']}")
        """
        extractor = get_gpu_extractor()
        if extractor is None:
            return {"error": "GPU extractor not available", "success": False}

        if not extractor.is_available:
            return {"error": "GPU node not reachable", "success": False}

        try:
            features = extractor.extract_features(image_path, include_description)
            if features:
                return {
                    "success": True,
                    "description": features.description,
                    "objects": features.objects,
                    "scene": features.scene,
                    "confidence": features.confidence,
                    "latency_ms": features.latency_ms,
                    "model": features.model,
                    "image_path": image_path
                }
            return {"error": "Failed to extract features", "success": False}

        except Exception as e:
            logger.error(f"gpu_extract_visual_features error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def gpu_create_cross_modal_embedding(
        image_path: str
    ) -> Dict[str, Any]:
        """
        Create cross-modal embedding for image via text description.

        Bridges visual content to text embedding space:
        1. Describe image with moondream vision model
        2. Embed description with bge-m3 text model
        3. Return 1024-dim embedding for hybrid search

        Use for text-image alignment and multimodal retrieval.

        Args:
            image_path: Path to image file

        Returns:
            Dict with description, embedding, and dimensions

        Example:
            result = await gpu_create_cross_modal_embedding(
                image_path="/path/to/image.jpg"
            )
            embedding = result["embedding"]  # 1024-dim numpy array
        """
        extractor = get_gpu_extractor()
        if extractor is None:
            return {"error": "GPU extractor not available", "success": False}

        if not extractor.is_available:
            return {"error": "GPU node not reachable", "success": False}

        try:
            result = extractor.create_cross_modal_embedding(image_path)
            if result:
                # Convert numpy array to list for JSON serialization
                embedding_list = result["embedding"].tolist() if hasattr(result["embedding"], "tolist") else result["embedding"]
                return {
                    "success": True,
                    "image_path": result["image_path"],
                    "description": result["description"],
                    "embedding": embedding_list,
                    "embedding_dim": result["embedding_dim"],
                    "model_vision": result["model_vision"],
                    "model_embed": result["model_embed"]
                }
            return {"error": "Failed to create cross-modal embedding", "success": False}

        except Exception as e:
            logger.error(f"gpu_create_cross_modal_embedding error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def check_gpu_visual_status() -> Dict[str, Any]:
        """
        Check GPU visual feature extraction availability.

        Returns GPU node status, available models, and configuration.

        Returns:
            Dict with availability status and configuration

        Example:
            status = await check_gpu_visual_status()
            if status["available"]:
                print(f"Vision model: {status['vision_model']}")
        """
        extractor = get_gpu_extractor()
        if extractor is None:
            return {
                "success": False,
                "available": False,
                "error": "GPU extractor not initialized"
            }

        try:
            return {
                "success": True,
                "available": extractor.is_available,
                "host": extractor.host,
                "port": extractor.port,
                "vision_model": extractor.vision_model,
                "embed_model": extractor.embed_model,
                "api_base": extractor.api_base
            }

        except Exception as e:
            logger.error(f"check_gpu_visual_status error: {e}")
            return {"error": str(e), "success": False, "available": False}

    # ==================== Cross-Modal Search Tools ====================

    @app.tool()
    async def find_visual_by_text(
        text_query: str,
        k: int = 10,
        min_significance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Text-to-image search using cross-modal embeddings.

        Embeds the text query and finds visually similar episodes
        based on their cross-modal (text description) embeddings.

        Args:
            text_query: Natural language query (e.g., "working at desk")
            k: Number of results to return (default 10)
            min_significance: Minimum significance threshold (default 0.0)

        Returns:
            List of matching episodes with similarity scores

        Example:
            results = await find_visual_by_text(
                text_query="coding on laptop",
                k=5
            )
            for r in results["results"]:
                print(f"{r['context']}: {r['similarity']:.3f}")
        """
        memory = get_adapted_visual_memory()
        if memory is None:
            return {"error": "Adapted visual memory not initialized", "success": False}

        try:
            results = memory.find_by_text(
                text_query=text_query,
                k=k,
                min_significance=min_significance
            )

            return {
                "success": True,
                "query": text_query,
                "result_count": len(results),
                "results": results
            }

        except Exception as e:
            logger.error(f"find_visual_by_text error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def multimodal_visual_search(
        text_query: str = "",
        image_path: str = None,
        k: int = 10,
        text_weight: float = 0.5,
        visual_weight: float = 0.5,
        min_significance: float = 0.0
    ) -> Dict[str, Any]:
        """
        Multimodal search combining text and visual queries.

        Performs hybrid search using both text (cross-modal embeddings)
        and visual (adapted TPU embeddings) similarity signals.

        Args:
            text_query: Text description to search for
            image_path: Optional image for visual similarity
            k: Number of results to return (default 10)
            text_weight: Weight for text similarity (default 0.5)
            visual_weight: Weight for visual similarity (default 0.5)
            min_significance: Minimum significance threshold

        Returns:
            Results with combined_score, text_score, and visual_score

        Example:
            # Text-only search
            results = await multimodal_visual_search(
                text_query="meeting room",
                k=5
            )

            # Hybrid search (text + visual)
            results = await multimodal_visual_search(
                text_query="working",
                image_path="/path/to/reference.jpg",
                text_weight=0.4,
                visual_weight=0.6,
                k=10
            )
        """
        memory = get_adapted_visual_memory()
        if memory is None:
            return {"error": "Adapted visual memory not initialized", "success": False}

        try:
            results = memory.multimodal_search(
                text_query=text_query,
                image_path=image_path,
                k=k,
                text_weight=text_weight,
                visual_weight=visual_weight
            )

            # Filter by min_significance if specified
            if min_significance > 0:
                results = [r for r in results if r.get('significance', 0) >= min_significance]

            return {
                "success": True,
                "text_query": text_query,
                "image_path": image_path,
                "weights": {"text": text_weight, "visual": visual_weight},
                "result_count": len(results),
                "results": results
            }

        except Exception as e:
            logger.error(f"multimodal_visual_search error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def add_crossmodal_to_episode(episode_id: int) -> Dict[str, Any]:
        """
        Add cross-modal embedding to an existing visual episode.

        Uses GPU node to generate text description and 1024-dim
        cross-modal embedding for the episode's image.

        Args:
            episode_id: ID of the visual episode to process

        Returns:
            Processing result with embedding dimensions

        Example:
            result = await add_crossmodal_to_episode(episode_id=42)
            if result["success"]:
                print(f"Added {result['crossmodal_dim']}-dim embedding")
        """
        memory = get_adapted_visual_memory()
        if memory is None:
            return {"error": "Adapted visual memory not initialized", "success": False}

        try:
            result = memory.add_crossmodal_embedding(episode_id)
            return result

        except Exception as e:
            logger.error(f"add_crossmodal_to_episode error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def batch_add_crossmodal(
        episode_ids: List[int] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Add cross-modal embeddings to multiple episodes.

        Processes episodes that don't have cross-modal embeddings yet.
        Uses GPU node for rich visual descriptions.

        Args:
            episode_ids: Specific episodes to process (optional)
            limit: Maximum episodes to process if no IDs given (default 50)

        Returns:
            Processing statistics

        Example:
            # Process up to 100 episodes without crossmodal embeddings
            result = await batch_add_crossmodal(limit=100)
            print(f"Processed: {result['processed']}, Failed: {result['failed']}")
        """
        memory = get_adapted_visual_memory()
        if memory is None:
            return {"error": "Adapted visual memory not initialized", "success": False}

        try:
            result = memory.batch_add_crossmodal_embeddings(
                episode_ids=episode_ids,
                limit=limit
            )
            return result

        except Exception as e:
            logger.error(f"batch_add_crossmodal error: {e}")
            return {"error": str(e), "success": False}

    @app.tool()
    async def get_crossmodal_coverage() -> Dict[str, Any]:
        """
        Get statistics about cross-modal embedding coverage.

        Shows how many episodes have cross-modal embeddings
        and overall coverage percentage.

        Returns:
            Coverage statistics and recommendations

        Example:
            stats = await get_crossmodal_coverage()
            print(f"Coverage: {stats['coverage_percent']:.1f}%")
            print(f"Episodes with crossmodal: {stats['with_crossmodal']}")
        """
        memory = get_adapted_visual_memory()
        if memory is None:
            return {"error": "Adapted visual memory not initialized", "success": False}

        try:
            stats = memory.get_crossmodal_stats()
            return {"success": True, **stats}

        except Exception as e:
            logger.error(f"get_crossmodal_coverage error: {e}")
            return {"error": str(e), "success": False}

    logger.info("Registered 19 visual memory tools (LVR Phase 2+3 + Adapter + GPU + CrossModal)")
