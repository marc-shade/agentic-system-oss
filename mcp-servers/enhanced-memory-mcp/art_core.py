#!/usr/bin/env python3
"""
Adaptive Resonance Theory (ART) Core Implementation

A biologically-inspired neural network architecture that solves the
stability-plasticity dilemma - learning new information without
catastrophic forgetting of old knowledge.

Developed by Stephen Grossberg (1970s-1980s), ART predates back-propagation
and provides real-time, online learning capabilities that modern transformers lack.

Key Features:
- Online learning (one sample at a time)
- No catastrophic forgetting
- No back-propagation required
- Vigilance parameter controls category granularity
- Interpretable prototype-based memory
- CPU-friendly (no GPU required)

Based on research from:
- Richard Aragon's ART implementation
- Original Grossberg & Carpenter papers
- Fuzzy ART extensions

Author: Pixel (Agentic System)
Date: 2024-12
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class ARTCategory:
    """A learned category prototype in ART network"""
    id: str
    prototype: np.ndarray
    match_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_matched: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prototype": self.prototype.tolist(),
            "match_count": self.match_count,
            "created_at": self.created_at.isoformat(),
            "last_matched": self.last_matched.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ARTCategory":
        return cls(
            id=data["id"],
            prototype=np.array(data["prototype"]),
            match_count=data.get("match_count", 0),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_matched=datetime.fromisoformat(data.get("last_matched", datetime.now().isoformat())),
            metadata=data.get("metadata", {})
        )


class FuzzyART:
    """
    Fuzzy ART Neural Network Implementation

    Fuzzy ART extends basic ART to handle continuous-valued inputs
    using fuzzy set theory operations (fuzzy AND).

    Parameters:
    -----------
    vigilance : float (0.0 to 1.0)
        Controls category specificity. Higher = more specific categories.
        - Low (0.1-0.3): Broad categories, high generalization
        - Medium (0.4-0.6): Balanced clustering
        - High (0.7-0.9): Fine-grained, specific categories

    learning_rate : float (0.0 to 1.0)
        Speed of prototype updates. 1.0 = fast learning.

    choice_param : float (small positive)
        Prevents division by zero and biases toward smaller categories.

    complement_coding : bool
        Whether to use complement coding for inputs.
        Recommended True for bounded inputs.
    """

    def __init__(
        self,
        vigilance: float = 0.75,
        learning_rate: float = 1.0,
        choice_param: float = 0.00001,
        complement_coding: bool = True,
        max_categories: int = 1000
    ):
        # Validate parameters
        if not 0.0 <= vigilance <= 1.0:
            raise ValueError("Vigilance must be between 0.0 and 1.0")
        if not 0.0 <= learning_rate <= 1.0:
            raise ValueError("Learning rate must be between 0.0 and 1.0")
        if choice_param <= 0:
            raise ValueError("Choice parameter must be positive")

        self.vigilance = vigilance  # rho - THE KEY DIAL
        self.learning_rate = learning_rate  # beta
        self.choice_param = choice_param  # alpha
        self.complement_coding = complement_coding
        self.max_categories = max_categories

        self.categories: List[ARTCategory] = []
        self.input_dim: Optional[int] = None

        # Statistics
        self.total_inputs = 0
        self.resonance_count = 0
        self.new_category_count = 0

        logger.info(f"FuzzyART initialized: vigilance={vigilance}, lr={learning_rate}")

    def reset(self) -> None:
        """Reset all learned categories and statistics."""
        self.categories = []
        self.input_dim = None
        self.total_inputs = 0
        self.resonance_count = 0
        self.new_category_count = 0
        logger.info("FuzzyART reset: all categories cleared")

    def _normalize(self, x: np.ndarray) -> np.ndarray:
        """Normalize input to [0, 1] range"""
        x_min, x_max = x.min(), x.max()
        if x_max - x_min == 0:
            return np.zeros_like(x)
        return (x - x_min) / (x_max - x_min)

    def _complement_code(self, x: np.ndarray) -> np.ndarray:
        """
        Apply complement coding: x -> [x, 1-x]

        This encodes both presence AND absence of features,
        preventing category proliferation and improving stability.
        """
        if self.complement_coding:
            x_normalized = self._normalize(x)
            return np.concatenate([x_normalized, 1.0 - x_normalized])
        return x

    def _fuzzy_and(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Fuzzy AND operation: element-wise minimum

        This is the core operation that replaces gradient-based learning.
        No back-propagation needed!
        """
        return np.minimum(a, b)

    def _choice_function(self, input_vec: np.ndarray, prototype: np.ndarray) -> float:
        """
        Calculate choice function T_j for category selection

        T_j = |I ∧ w_j| / (alpha + |w_j|)

        Higher values indicate better match.
        """
        fuzzy_match = self._fuzzy_and(input_vec, prototype)
        return np.sum(fuzzy_match) / (self.choice_param + np.sum(prototype))

    def _match_function(self, input_vec: np.ndarray, prototype: np.ndarray) -> float:
        """
        Calculate match function M for vigilance test

        M = |I ∧ w_j| / |I|

        Must exceed vigilance threshold (rho) for resonance.
        """
        fuzzy_match = self._fuzzy_and(input_vec, prototype)
        input_norm = np.sum(input_vec)
        if input_norm == 0:
            return 0.0
        return np.sum(fuzzy_match) / input_norm

    def _update_prototype(self, prototype: np.ndarray, input_vec: np.ndarray) -> np.ndarray:
        """
        Update category prototype during resonance

        w_j(new) = beta * (I ∧ w_j) + (1-beta) * w_j

        With beta=1 (fast learning), this simplifies to:
        w_j(new) = I ∧ w_j
        """
        fuzzy_match = self._fuzzy_and(input_vec, prototype)
        return self.learning_rate * fuzzy_match + (1 - self.learning_rate) * prototype

    def _generate_category_id(self, prototype: np.ndarray) -> str:
        """Generate unique ID for a category"""
        hash_input = f"{prototype.tobytes()}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def learn(
        self,
        input_data: Union[np.ndarray, List[float]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bool, float]:
        """
        Learn a single input pattern (online learning)

        Parameters:
        -----------
        input_data : array-like
            Input pattern to learn
        metadata : dict, optional
            Additional info to store with category

        Returns:
        --------
        tuple: (category_id, is_new_category, match_score)
        """
        # Convert and preprocess input
        x = np.array(input_data, dtype=np.float64)

        # Initialize input dimension on first sample
        if self.input_dim is None:
            self.input_dim = len(x)
        elif len(x) != self.input_dim:
            raise ValueError(f"Input dimension mismatch: expected {self.input_dim}, got {len(x)}")

        # Apply complement coding
        input_vec = self._complement_code(x)
        coded_dim = len(input_vec)

        self.total_inputs += 1

        # If no categories exist, create first one
        if not self.categories:
            new_id = self._generate_category_id(input_vec)
            new_category = ARTCategory(
                id=new_id,
                prototype=input_vec.copy(),
                match_count=1,
                metadata=metadata or {}
            )
            self.categories.append(new_category)
            self.new_category_count += 1
            logger.debug(f"Created first category: {new_id}")
            return new_id, True, 1.0

        # Calculate choice function for all categories
        choice_values = [
            (i, self._choice_function(input_vec, cat.prototype))
            for i, cat in enumerate(self.categories)
        ]

        # Sort by choice value (descending)
        choice_values.sort(key=lambda x: x[1], reverse=True)

        # Search for resonant category
        for idx, choice_val in choice_values:
            category = self.categories[idx]
            match_score = self._match_function(input_vec, category.prototype)

            # Vigilance test - THE KEY MOMENT
            if match_score >= self.vigilance:
                # RESONANCE! Update category
                category.prototype = self._update_prototype(category.prototype, input_vec)
                category.match_count += 1
                category.last_matched = datetime.now()

                if metadata:
                    category.metadata.update(metadata)

                self.resonance_count += 1
                logger.debug(f"Resonance with category {category.id}, match={match_score:.3f}")
                return category.id, False, match_score

        # No resonant category found - create new one
        if len(self.categories) >= self.max_categories:
            # Find least used category to replace
            min_count_idx = min(range(len(self.categories)),
                               key=lambda i: self.categories[i].match_count)
            removed = self.categories.pop(min_count_idx)
            logger.warning(f"Max categories reached, replacing {removed.id}")

        new_id = self._generate_category_id(input_vec)
        new_category = ARTCategory(
            id=new_id,
            prototype=input_vec.copy(),
            match_count=1,
            metadata=metadata or {}
        )
        self.categories.append(new_category)
        self.new_category_count += 1
        logger.debug(f"Created new category: {new_id}")
        return new_id, True, 1.0

    def classify(
        self,
        input_data: Union[np.ndarray, List[float]],
        return_scores: bool = False
    ) -> Union[Optional[str], Tuple[Optional[str], Dict[str, float]]]:
        """
        Classify input without learning

        Parameters:
        -----------
        input_data : array-like
            Input pattern to classify
        return_scores : bool
            If True, return match scores for all categories

        Returns:
        --------
        Category ID of best match (or None if below vigilance)
        Optionally: dict of category_id -> match_score
        """
        if not self.categories:
            return (None, {}) if return_scores else None

        x = np.array(input_data, dtype=np.float64)
        input_vec = self._complement_code(x)

        scores = {}
        best_match = None
        best_score = 0.0

        for category in self.categories:
            match_score = self._match_function(input_vec, category.prototype)
            scores[category.id] = match_score

            if match_score >= self.vigilance and match_score > best_score:
                best_match = category.id
                best_score = match_score

        return (best_match, scores) if return_scores else best_match

    def get_category(self, category_id: str) -> Optional[ARTCategory]:
        """Get category by ID"""
        for cat in self.categories:
            if cat.id == category_id:
                return cat
        return None

    def get_all_categories(self) -> List[ARTCategory]:
        """Get all learned categories"""
        return self.categories.copy()

    def adjust_vigilance(self, new_vigilance: float) -> None:
        """
        Dynamically adjust vigilance parameter

        This is THE KEY DIAL for controlling category granularity.
        Adjust during runtime based on task requirements.
        """
        if not 0.0 <= new_vigilance <= 1.0:
            raise ValueError("Vigilance must be between 0.0 and 1.0")

        old_vigilance = self.vigilance
        self.vigilance = new_vigilance
        logger.info(f"Vigilance adjusted: {old_vigilance:.3f} -> {new_vigilance:.3f}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get network statistics"""
        return {
            "total_inputs": self.total_inputs,
            "total_categories": len(self.categories),
            "resonance_count": self.resonance_count,
            "new_category_count": self.new_category_count,
            "resonance_rate": self.resonance_count / max(1, self.total_inputs),
            "vigilance": self.vigilance,
            "learning_rate": self.learning_rate,
            "input_dim": self.input_dim,
            "category_sizes": [cat.match_count for cat in self.categories]
        }

    def save(self, filepath: str) -> None:
        """Save network state to file"""
        state = {
            "vigilance": self.vigilance,
            "learning_rate": self.learning_rate,
            "choice_param": self.choice_param,
            "complement_coding": self.complement_coding,
            "max_categories": self.max_categories,
            "input_dim": self.input_dim,
            "total_inputs": self.total_inputs,
            "resonance_count": self.resonance_count,
            "new_category_count": self.new_category_count,
            "categories": [cat.to_dict() for cat in self.categories]
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved ART network to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> "FuzzyART":
        """Load network state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)

        network = cls(
            vigilance=state["vigilance"],
            learning_rate=state["learning_rate"],
            choice_param=state["choice_param"],
            complement_coding=state["complement_coding"],
            max_categories=state["max_categories"]
        )
        network.input_dim = state["input_dim"]
        network.total_inputs = state["total_inputs"]
        network.resonance_count = state["resonance_count"]
        network.new_category_count = state["new_category_count"]
        network.categories = [ARTCategory.from_dict(c) for c in state["categories"]]

        logger.info(f"Loaded ART network from {filepath}")
        return network


class ARTHybrid:
    """
    Hybrid ART + Embeddings Architecture

    Combines modern embedding models (for feature extraction)
    with ART (for stable, interpretable clustering).

    Use Case:
    - Use CNN/Transformer to generate embeddings
    - Feed embeddings to ART for stable memory clustering
    - Get interpretable prototypes without catastrophic forgetting
    """

    def __init__(
        self,
        art_network: FuzzyART,
        embedding_dim: int = 384  # Default for all-MiniLM-L6-v2
    ):
        self.art = art_network
        self.embedding_dim = embedding_dim
        self.embedding_cache: Dict[str, np.ndarray] = {}

    def learn_from_embedding(
        self,
        embedding: np.ndarray,
        content_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bool, float]:
        """
        Learn from a pre-computed embedding

        Parameters:
        -----------
        embedding : np.ndarray
            Pre-computed embedding vector (from Transformer/CNN)
        content_id : str
            ID of the original content
        metadata : dict, optional
            Additional metadata

        Returns:
        --------
        tuple: (category_id, is_new_category, match_score)
        """
        # Normalize embedding
        normalized = embedding / (np.linalg.norm(embedding) + 1e-10)

        # Cache for retrieval
        self.embedding_cache[content_id] = normalized

        # Add content ID to metadata
        meta = metadata or {}
        meta["content_ids"] = meta.get("content_ids", [])
        meta["content_ids"].append(content_id)

        return self.art.learn(normalized, meta)

    def classify_embedding(
        self,
        embedding: np.ndarray
    ) -> Tuple[Optional[str], float]:
        """Classify a pre-computed embedding"""
        normalized = embedding / (np.linalg.norm(embedding) + 1e-10)
        result = self.art.classify(normalized, return_scores=True)

        if result[0] is None:
            return None, 0.0

        return result[0], result[1].get(result[0], 0.0)

    def get_category_content_ids(self, category_id: str) -> List[str]:
        """Get all content IDs associated with a category"""
        category = self.art.get_category(category_id)
        if category and "content_ids" in category.metadata:
            return category.metadata["content_ids"]
        return []


# Example usage and testing
if __name__ == "__main__":
    import time

    print("=" * 60)
    print("Fuzzy ART Neural Network - Test Suite")
    print("=" * 60)

    # Create network with medium vigilance
    art = FuzzyART(vigilance=0.7, learning_rate=1.0)

    # Generate synthetic data - 3 clusters
    np.random.seed(42)
    cluster1 = np.random.randn(100, 10) * 0.3 + [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    cluster2 = np.random.randn(100, 10) * 0.3 + [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
    cluster3 = np.random.randn(100, 10) * 0.3 + [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]

    all_data = np.vstack([cluster1, cluster2, cluster3])
    np.random.shuffle(all_data)

    # Train
    print("\nTraining on 300 samples from 3 clusters...")
    start = time.time()

    for i, sample in enumerate(all_data):
        cat_id, is_new, score = art.learn(sample)
        if is_new:
            print(f"  Sample {i}: Created new category {cat_id[:8]}")

    elapsed = time.time() - start

    # Results
    stats = art.get_statistics()
    print(f"\n{'='*40}")
    print(f"Results:")
    print(f"  Time: {elapsed:.3f}s ({elapsed*1000/300:.2f}ms per sample)")
    print(f"  Categories learned: {stats['total_categories']}")
    print(f"  Resonance rate: {stats['resonance_rate']*100:.1f}%")
    print(f"  Category sizes: {stats['category_sizes']}")

    # Test classification
    print(f"\nClassification test:")
    test_samples = [cluster1[0], cluster2[0], cluster3[0]]
    for i, sample in enumerate(test_samples):
        cat_id, scores = art.classify(sample, return_scores=True)
        best_score = max(scores.values()) if scores else 0
        print(f"  Test {i+1}: Category {cat_id[:8] if cat_id else 'None'}, score={best_score:.3f}")

    # Test vigilance adjustment
    print(f"\nVigilance adjustment test:")
    art.adjust_vigilance(0.9)  # More specific
    for sample in cluster1[:10]:
        art.learn(sample)

    stats2 = art.get_statistics()
    print(f"  After vigilance=0.9: {stats2['total_categories']} categories")

    print("\n" + "=" * 60)
    print("Fuzzy ART test complete!")
    print("=" * 60)
