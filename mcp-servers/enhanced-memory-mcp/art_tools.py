"""
ART (Adaptive Resonance Theory) MCP Tools

Provides MCP tools for Fuzzy ART neural network operations:
- Online learning without catastrophic forgetting
- Vigilance-controlled category granularity
- Hybrid architecture with transformer embeddings

Key Insight: Vigilance (ρ) is THE KEY DIAL
- High vigilance (0.9+): Fine-grained categories, many clusters
- Low vigilance (0.3-0.5): Coarse categories, few broad clusters
- Mid vigilance (0.6-0.8): Balanced clustering
"""

import os
import json
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

# Import core ART implementation
from art_core import FuzzyART, ARTHybrid, ARTCategory


# Global ART instances (lazy initialization)
_art_instance: Optional[FuzzyART] = None
_art_hybrid_instance: Optional[ARTHybrid] = None

# Storage paths
AGENTIC_PATH = os.environ.get('AGENTIC_SYSTEM_PATH', os.path.expanduser('~/agentic-system'))
ART_STORAGE_DIR = Path(AGENTIC_PATH) / 'databases' / 'art'


def get_art_instance(vigilance: float = 0.75) -> FuzzyART:
    """Get or create the global ART instance."""
    global _art_instance
    if _art_instance is None:
        ART_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = ART_STORAGE_DIR / 'fuzzy_art_state.json'

        if state_file.exists():
            _art_instance = FuzzyART.load(str(state_file))
        else:
            _art_instance = FuzzyART(
                vigilance=vigilance,
                learning_rate=1.0
            )
            _art_instance.name = "enhanced_memory_art"
    return _art_instance


def get_art_hybrid_instance(embedding_dim: int = 384, vigilance: float = 0.75) -> ARTHybrid:
    """Get or create the global ART Hybrid instance."""
    global _art_hybrid_instance
    if _art_hybrid_instance is None:
        ART_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = ART_STORAGE_DIR / 'art_hybrid_state.json'

        if state_file.exists():
            _art_hybrid_instance = ARTHybrid.load(str(state_file))
        else:
            # Create a FuzzyART network first
            art_network = FuzzyART(vigilance=vigilance, learning_rate=1.0)
            art_network.name = "enhanced_memory_art_hybrid"
            _art_hybrid_instance = ARTHybrid(
                art_network=art_network,
                embedding_dim=embedding_dim
            )
    return _art_hybrid_instance


def save_art_state() -> None:
    """Persist ART state to disk."""
    global _art_instance, _art_hybrid_instance
    ART_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if _art_instance is not None:
        _art_instance.save(str(ART_STORAGE_DIR / 'fuzzy_art_state.json'))

    if _art_hybrid_instance is not None:
        _art_hybrid_instance.save(str(ART_STORAGE_DIR / 'art_hybrid_state.json'))


def register_art_tools(app, nmf_instance=None, db_path: str = None) -> None:
    """
    Register ART tools with FastMCP app.

    Args:
        app: FastMCP application instance
        nmf_instance: Optional Neural Memory Fabric instance for hybrid mode
        db_path: Optional database path for persistence
    """

    @app.tool()
    async def art_learn(
        data: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        vigilance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Learn a new pattern using Fuzzy ART.

        Performs online learning - the pattern is either:
        1. Matched to existing category (resonance) - updates prototype
        2. Creates new category if no match exceeds vigilance

        Args:
            data: Input vector (will be complement-coded internally)
            metadata: Optional metadata to associate with this learning event
            vigilance: Optional vigilance override for this learning (0.0-1.0)
                      Higher = finer categories, Lower = broader categories

        Returns:
            Dict with category_id, is_new_category, match_score, stats
        """
        art = get_art_instance()

        # Temporarily adjust vigilance if specified
        original_vigilance = None
        if vigilance is not None:
            original_vigilance = art.vigilance
            art.adjust_vigilance(vigilance)

        try:
            input_array = np.array(data, dtype=np.float32)
            category_id, is_new, match_score = art.learn(input_array, metadata)

            # Auto-save after learning
            save_art_state()

            return {
                "success": True,
                "category_id": category_id,
                "is_new_category": is_new,
                "match_score": float(match_score),
                "vigilance_used": art.vigilance,
                "total_categories": len(art.categories),
                "total_patterns_learned": art.stats.get("total_patterns_learned", 0)
            }
        finally:
            if original_vigilance is not None:
                art.adjust_vigilance(original_vigilance)


    @app.tool()
    async def art_classify(
        data: List[float],
        vigilance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Classify a pattern without learning (inference only).

        Args:
            data: Input vector to classify
            vigilance: Optional vigilance threshold for classification

        Returns:
            Dict with best matching category or indication of novel pattern
        """
        art = get_art_instance()

        if not art.categories:
            return {
                "success": True,
                "classified": False,
                "reason": "No categories learned yet",
                "total_categories": 0
            }

        input_array = np.array(data, dtype=np.float32)
        coded = art._complement_code(input_array)

        vig = vigilance if vigilance is not None else art.vigilance

        # Find best matching category
        best_match_cat = None
        best_score = -1.0

        for category in art.categories:
            match_score = art._match_function(coded, category.prototype)
            if match_score > best_score:
                best_score = match_score
                best_match_cat = category

        if best_score >= vig and best_match_cat is not None:
            return {
                "success": True,
                "classified": True,
                "category_id": best_match_cat.id,
                "match_score": float(best_score),
                "vigilance_threshold": vig,
                "category_metadata": best_match_cat.metadata,
                "category_pattern_count": best_match_cat.match_count
            }
        else:
            return {
                "success": True,
                "classified": False,
                "best_match_id": best_match_cat.id if best_match_cat else None,
                "best_match_score": float(best_score),
                "vigilance_threshold": vig,
                "reason": f"Best match ({best_score:.3f}) below vigilance ({vig})"
            }


    @app.tool()
    async def art_adjust_vigilance(
        vigilance: float,
        instance: str = "main"
    ) -> Dict[str, Any]:
        """
        Adjust THE KEY DIAL - vigilance parameter.

        This controls category granularity:
        - 0.9+: Very fine-grained (many specific categories)
        - 0.7-0.8: Balanced (good default)
        - 0.5-0.6: Moderate grouping
        - 0.3-0.4: Coarse grouping (few broad categories)

        Args:
            vigilance: New vigilance value (0.0 to 1.0)
            instance: Which instance to adjust ("main" or "hybrid")

        Returns:
            Dict with old and new vigilance values
        """
        if not 0.0 <= vigilance <= 1.0:
            return {
                "success": False,
                "error": f"Vigilance must be between 0.0 and 1.0, got {vigilance}"
            }

        if instance == "main":
            art = get_art_instance()
            old_vigilance = art.vigilance
            art.adjust_vigilance(vigilance)
            save_art_state()

            return {
                "success": True,
                "instance": "main",
                "old_vigilance": old_vigilance,
                "new_vigilance": vigilance,
                "effect": _describe_vigilance_effect(vigilance)
            }
        elif instance == "hybrid":
            art_hybrid = get_art_hybrid_instance()
            old_vigilance = art_hybrid.art.vigilance
            art_hybrid.art.adjust_vigilance(vigilance)
            save_art_state()

            return {
                "success": True,
                "instance": "hybrid",
                "old_vigilance": old_vigilance,
                "new_vigilance": vigilance,
                "effect": _describe_vigilance_effect(vigilance)
            }
        else:
            return {
                "success": False,
                "error": f"Unknown instance: {instance}. Use 'main' or 'hybrid'"
            }


    @app.tool()
    async def art_get_categories() -> Dict[str, Any]:
        """
        Get all learned ART categories with their prototypes and stats.

        Returns:
            Dict with list of categories and their metadata
        """
        art = get_art_instance()

        categories = []
        for category in art.categories:
            categories.append({
                "category_id": category.id,
                "match_count": category.match_count,
                "created_at": category.created_at.isoformat() if hasattr(category.created_at, 'isoformat') else str(category.created_at),
                "last_matched": category.last_matched.isoformat() if hasattr(category.last_matched, 'isoformat') else str(category.last_matched),
                "metadata": category.metadata,
                "prototype_norm": float(np.linalg.norm(category.prototype))
            })

        return {
            "success": True,
            "total_categories": len(categories),
            "categories": categories,
            "vigilance": art.vigilance,
            "stats": art.get_stats()
        }


    @app.tool()
    async def art_hybrid_learn(
        embedding: List[float],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Learn from a pre-computed embedding using ART Hybrid architecture.

        This combines transformer embeddings with ART clustering for:
        - Fast category assignment
        - No catastrophic forgetting
        - Interpretable clusters

        Args:
            embedding: Pre-computed embedding vector (e.g., from sentence-transformers)
            content: Original text content for reference
            metadata: Optional metadata to store with the pattern

        Returns:
            Dict with category assignment and cluster info
        """
        art_hybrid = get_art_hybrid_instance(embedding_dim=len(embedding))

        embedding_array = np.array(embedding, dtype=np.float32)
        full_metadata = metadata or {}
        full_metadata["content_preview"] = content[:200] if content else ""
        full_metadata["learned_at"] = datetime.now().isoformat()

        category_id, is_new, match_score = art_hybrid.art.learn(
            embedding_array,
            full_metadata
        )

        # Auto-save
        save_art_state()

        # Find the category to get match count
        cat_match_count = 0
        for cat in art_hybrid.art.categories:
            if cat.id == category_id:
                cat_match_count = cat.match_count
                break

        return {
            "success": True,
            "category_id": category_id,
            "is_new_category": is_new,
            "match_score": float(match_score),
            "cluster_info": {
                "total_clusters": len(art_hybrid.art.categories),
                "patterns_in_cluster": cat_match_count
            },
            "vigilance": art_hybrid.art.vigilance
        }


    @app.tool()
    async def art_hybrid_find_similar(
        embedding: List[float],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Find similar categories for an embedding without learning.

        Args:
            embedding: Query embedding vector
            top_k: Number of top matches to return

        Returns:
            Dict with ranked category matches
        """
        art_hybrid = get_art_hybrid_instance(embedding_dim=len(embedding))

        if not art_hybrid.art.categories:
            return {
                "success": True,
                "matches": [],
                "message": "No categories learned yet"
            }

        embedding_array = np.array(embedding, dtype=np.float32)
        coded = art_hybrid.art._complement_code(embedding_array)

        # Score all categories
        scores = []
        for category in art_hybrid.art.categories:
            match_score = art_hybrid.art._match_function(coded, category.prototype)
            scores.append({
                "category_id": category.id,
                "match_score": float(match_score),
                "match_count": category.match_count,
                "metadata": category.metadata
            })

        # Sort by score descending
        scores.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "success": True,
            "matches": scores[:top_k],
            "total_categories": len(art_hybrid.art.categories),
            "vigilance": art_hybrid.art.vigilance
        }


    @app.tool()
    async def art_get_stats() -> Dict[str, Any]:
        """
        Get comprehensive ART system statistics.

        Returns:
            Dict with stats for both main and hybrid instances
        """
        stats = {
            "success": True,
            "storage_path": str(ART_STORAGE_DIR),
            "instances": {}
        }

        # Main instance stats
        if _art_instance is not None:
            stats["instances"]["main"] = {
                "initialized": True,
                "name": _art_instance.name,
                "vigilance": _art_instance.vigilance,
                "learning_rate": _art_instance.learning_rate,
                "total_categories": len(_art_instance.categories),
                "stats": _art_instance.stats
            }
        else:
            state_file = ART_STORAGE_DIR / 'fuzzy_art_state.json'
            stats["instances"]["main"] = {
                "initialized": False,
                "has_saved_state": state_file.exists()
            }

        # Hybrid instance stats
        if _art_hybrid_instance is not None:
            stats["instances"]["hybrid"] = {
                "initialized": True,
                "name": _art_hybrid_instance.name,
                "vigilance": _art_hybrid_instance.art.vigilance,
                "total_categories": len(_art_hybrid_instance.art.categories),
                "stats": _art_hybrid_instance.art.stats
            }
        else:
            state_file = ART_STORAGE_DIR / 'art_hybrid_state.json'
            stats["instances"]["hybrid"] = {
                "initialized": False,
                "has_saved_state": state_file.exists()
            }

        return stats


    @app.tool()
    async def art_reset(
        instance: str = "main",
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Reset an ART instance (clear all learned categories).

        WARNING: This deletes all learned knowledge!

        Args:
            instance: Which instance to reset ("main" or "hybrid")
            confirm: Must be True to actually reset

        Returns:
            Dict with reset status
        """
        if not confirm:
            return {
                "success": False,
                "error": "Must set confirm=True to reset. This will delete all learned categories!"
            }

        global _art_instance, _art_hybrid_instance

        if instance == "main":
            if _art_instance is not None:
                old_count = len(_art_instance.categories)
                _art_instance.reset()
                save_art_state()
                return {
                    "success": True,
                    "instance": "main",
                    "categories_deleted": old_count
                }
            else:
                state_file = ART_STORAGE_DIR / 'fuzzy_art_state.json'
                if state_file.exists():
                    state_file.unlink()
                return {
                    "success": True,
                    "instance": "main",
                    "message": "Deleted saved state file"
                }

        elif instance == "hybrid":
            if _art_hybrid_instance is not None:
                old_count = len(_art_hybrid_instance.art.categories)
                _art_hybrid_instance.art.reset()
                save_art_state()
                return {
                    "success": True,
                    "instance": "hybrid",
                    "categories_deleted": old_count
                }
            else:
                state_file = ART_STORAGE_DIR / 'art_hybrid_state.json'
                if state_file.exists():
                    state_file.unlink()
                return {
                    "success": True,
                    "instance": "hybrid",
                    "message": "Deleted saved state file"
                }

        return {
            "success": False,
            "error": f"Unknown instance: {instance}"
        }


def _describe_vigilance_effect(vigilance: float) -> str:
    """Describe the effect of a vigilance value."""
    if vigilance >= 0.9:
        return "Very fine-grained: Creates many specific categories"
    elif vigilance >= 0.7:
        return "Balanced: Good default for most use cases"
    elif vigilance >= 0.5:
        return "Moderate: Groups similar patterns together"
    elif vigilance >= 0.3:
        return "Coarse: Creates few broad categories"
    else:
        return "Very coarse: Almost everything grouped together"


# Export for use in server.py
__all__ = [
    'register_art_tools',
    'get_art_instance',
    'get_art_hybrid_instance',
    'save_art_state',
    'FuzzyART',
    'ARTHybrid'
]
