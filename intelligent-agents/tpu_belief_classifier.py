#!/usr/bin/env python3
"""
TPU Belief State Classifier - Edge TPU Accelerated Belief Analysis

Classifies agent belief states by semantic similarity to belief templates.
Detects belief rigidity, epistemic flexibility, and potential cognitive biases.

Integration with enhanced-memory belief tracking and epistemic monitoring.

Usage:
    from tpu_belief_classifier import TPUBeliefClassifier

    classifier = TPUBeliefClassifier()
    analysis = await classifier.analyze_belief(
        belief_statement="async/await is better than threads for I/O",
        probability=0.85,
        evidence=["benchmarks show 2x throughput", "less context switching"]
    )
    print(f"Category: {analysis.category}, Rigidity: {analysis.rigidity_score}")
"""
import platform

import os
import sys
import json
import time
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_belief_classifier")

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


class BeliefCategory(Enum):
    """Categories of beliefs"""
    IDENTITY = "identity"  # Beliefs about self/role
    FACT = "fact"  # Factual beliefs about the world
    STRATEGY = "strategy"  # Beliefs about best approaches
    GOAL = "goal"  # Beliefs about objectives
    CAPABILITY = "capability"  # Beliefs about what can/can't be done
    PREFERENCE = "preference"  # Beliefs about what's preferred
    ASSUMPTION = "assumption"  # Underlying assumptions


class BeliefBias(Enum):
    """Potential cognitive biases in beliefs"""
    CONFIRMATION = "confirmation"  # Seeking confirming evidence
    ANCHORING = "anchoring"  # Over-relying on initial info
    AVAILABILITY = "availability"  # Overweighting recent/vivid info
    OVERCONFIDENCE = "overconfidence"  # Too certain given evidence
    SUNK_COST = "sunk_cost"  # Continuing due to prior investment
    AUTHORITY = "authority"  # Over-trusting authority sources
    BANDWAGON = "bandwagon"  # Following popular opinion
    NONE = "none"  # No detected bias


@dataclass
class BeliefAnalysis:
    """Analysis of a belief state"""
    belief_statement: str
    category: BeliefCategory
    category_confidence: float
    rigidity_score: float  # 0.0 (flexible) to 1.0 (rigid)
    evidence_balance: float  # -1.0 (all contra) to 1.0 (all supporting)
    potential_biases: List[BeliefBias]
    epistemic_status: str  # certain, probable, uncertain, unknown
    recommended_actions: List[str]
    similar_beliefs: List[Tuple[str, float]]  # Similar past beliefs
    latency_ms: float


# Belief category templates
CATEGORY_TEMPLATES = {
    BeliefCategory.IDENTITY: (
        "I am a helpful assistant. My role is to assist users. "
        "My purpose is to be useful and supportive. Identity and self-concept."
    ),
    BeliefCategory.FACT: (
        "This is true based on evidence. Scientific fact. "
        "Empirically verified. Observable reality. Documented truth."
    ),
    BeliefCategory.STRATEGY: (
        "The best approach is to do it this way. "
        "This method works better. Optimal strategy. Recommended approach."
    ),
    BeliefCategory.GOAL: (
        "The objective is to achieve this. The goal is to accomplish. "
        "We aim to complete. Target outcome. Desired result."
    ),
    BeliefCategory.CAPABILITY: (
        "I can do this. This is possible. This is feasible. "
        "This cannot be done. Limitations. Abilities and constraints."
    ),
    BeliefCategory.PREFERENCE: (
        "I prefer this approach. This is better. This is preferred. "
        "I like this method. Subjective preference. Personal choice."
    ),
    BeliefCategory.ASSUMPTION: (
        "Assuming that this is true. Taking for granted. "
        "Underlying premise. Implicit belief. Foundational assumption."
    )
}

# Bias detection patterns
BIAS_PATTERNS = {
    BeliefBias.CONFIRMATION: [
        "proves", "confirms", "supports my view", "as expected",
        "validates", "I knew", "of course"
    ],
    BeliefBias.ANCHORING: [
        "first", "initially", "original", "started with",
        "from the beginning", "based on early"
    ],
    BeliefBias.AVAILABILITY: [
        "recently", "just happened", "fresh in mind",
        "just saw", "memorable", "vivid example"
    ],
    BeliefBias.OVERCONFIDENCE: [
        "definitely", "certainly", "absolutely", "100%",
        "no doubt", "guaranteed", "obvious"
    ],
    BeliefBias.SUNK_COST: [
        "already invested", "too late to change",
        "come this far", "can't give up now"
    ],
    BeliefBias.AUTHORITY: [
        "expert says", "according to authority",
        "official says", "the expert"
    ],
    BeliefBias.BANDWAGON: [
        "everyone thinks", "popular opinion", "mainstream view",
        "most people", "widely believed"
    ]
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUBeliefClassifier:
    """
    Classify and analyze belief states using TPU embeddings.

    Detects belief categories, rigidity, biases, and provides
    recommendations for epistemic health.
    """

    def __init__(self):
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Precompute category embeddings
        self._category_embeddings = self._precompute_categories()

        # Track belief history for pattern detection
        self.belief_history: List[Dict] = []
        self.max_history = 100

        if self.use_tpu:
            logger.info("TPU belief classification enabled")
        else:
            logger.info("Using fallback belief classification")

    def _precompute_categories(self) -> Dict[BeliefCategory, np.ndarray]:
        """Precompute embeddings for belief categories."""
        categories = {}
        if not self.use_tpu or not _embed_text:
            return categories

        for category, template in CATEGORY_TEMPLATES.items():
            try:
                start = time.perf_counter()
                embedding = _embed_text(template)
                latency = (time.perf_counter() - start) * 1000

                if embedding is not None:
                    categories[category] = np.array(embedding, dtype=np.float32)

                    if HAS_TPU_MONITOR:
                        record_tpu_usage(
                            "belief_category_embedding",
                            latency_ms=latency,
                            source="belief_classifier",
                            metadata={"category": category.value}
                        )
            except Exception as e:
                logger.warning(f"Failed to embed category {category}: {e}")

        logger.info(f"Precomputed {len(categories)} belief category templates")
        return categories

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
                        "belief_embedding",
                        latency_ms=latency,
                        source="belief_classifier"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _detect_biases(self, belief: str, evidence: List[str]) -> List[BeliefBias]:
        """Detect potential cognitive biases in belief formulation."""
        detected = []
        combined_text = f"{belief} {' '.join(evidence)}".lower()

        for bias, patterns in BIAS_PATTERNS.items():
            for pattern in patterns:
                if pattern in combined_text:
                    detected.append(bias)
                    break

        return detected if detected else [BeliefBias.NONE]

    def _calculate_rigidity(
        self,
        probability: float,
        evidence: List[str],
        contradicting_evidence: List[str]
    ) -> float:
        """
        Calculate belief rigidity score.

        Rigidity = high probability + ignoring contradicting evidence
        """
        # High probability without proportional evidence = rigidity
        evidence_ratio = len(evidence) / max(len(contradicting_evidence), 1)

        # Very high probability with little evidence = rigid
        if probability > 0.9 and len(evidence) < 3:
            rigidity = 0.8
        # Ignoring contradicting evidence = rigid
        elif len(contradicting_evidence) > len(evidence) and probability > 0.7:
            rigidity = 0.7
        # Balanced consideration = flexible
        elif 0.3 <= probability <= 0.7:
            rigidity = 0.3
        else:
            # Scale based on probability extremity
            rigidity = abs(probability - 0.5) * 1.2

        return min(1.0, max(0.0, rigidity))

    def _get_epistemic_status(self, probability: float, confidence: float) -> str:
        """Determine epistemic status from probability and confidence."""
        if probability > 0.9 and confidence > 0.7:
            return "certain"
        elif probability > 0.7:
            return "probable"
        elif probability > 0.3:
            return "uncertain"
        else:
            return "unlikely"

    def _generate_recommendations(
        self,
        rigidity: float,
        biases: List[BeliefBias],
        evidence_balance: float,
        category: BeliefCategory
    ) -> List[str]:
        """Generate recommendations for epistemic health."""
        recommendations = []

        if rigidity > 0.7:
            recommendations.append("Consider seeking disconfirming evidence")
            recommendations.append("Reduce certainty to match evidence strength")

        if BeliefBias.CONFIRMATION in biases:
            recommendations.append("Actively seek opposing viewpoints")

        if BeliefBias.OVERCONFIDENCE in biases:
            recommendations.append("Calibrate confidence with track record")

        if evidence_balance < -0.3:
            recommendations.append("Contradicting evidence outweighs support - consider revising")

        if category == BeliefCategory.ASSUMPTION:
            recommendations.append("Explicitly validate assumption with evidence")

        if not recommendations:
            recommendations.append("Belief appears epistemically healthy")

        return recommendations

    async def analyze_belief(
        self,
        belief_statement: str,
        probability: float = 0.5,
        evidence: Optional[List[str]] = None,
        contradicting_evidence: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> BeliefAnalysis:
        """
        Analyze a belief statement.

        Args:
            belief_statement: The belief to analyze
            probability: Belief probability (0.0-1.0)
            evidence: Supporting evidence
            contradicting_evidence: Contradicting evidence
            context: Additional context

        Returns:
            BeliefAnalysis with category, rigidity, biases, and recommendations
        """
        start_time = time.perf_counter()

        evidence = evidence or []
        contradicting_evidence = contradicting_evidence or []

        # Get belief embedding
        belief_embedding = self._get_embedding(belief_statement)

        # Classify category
        if belief_embedding is not None and self._category_embeddings:
            category_scores = {}
            for category, cat_emb in self._category_embeddings.items():
                similarity = cosine_similarity(belief_embedding, cat_emb)
                category_scores[category] = similarity

            best_category = max(category_scores, key=category_scores.get)
            category_confidence = category_scores[best_category]
        else:
            # Fallback to keyword classification
            best_category, category_confidence = self._keyword_classify(belief_statement)

        # Detect biases
        biases = self._detect_biases(belief_statement, evidence)

        # Calculate rigidity
        rigidity = self._calculate_rigidity(probability, evidence, contradicting_evidence)

        # Evidence balance (-1 to 1)
        total_evidence = len(evidence) + len(contradicting_evidence)
        if total_evidence > 0:
            evidence_balance = (len(evidence) - len(contradicting_evidence)) / total_evidence
        else:
            evidence_balance = 0.0

        # Epistemic status
        epistemic_status = self._get_epistemic_status(probability, category_confidence)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            rigidity, biases, evidence_balance, best_category
        )

        # Find similar past beliefs
        similar_beliefs = await self._find_similar_beliefs(belief_statement)

        # Record in history
        self.belief_history.append({
            "timestamp": datetime.now().isoformat(),
            "statement": belief_statement[:100],
            "category": best_category.value,
            "rigidity": rigidity
        })
        while len(self.belief_history) > self.max_history:
            self.belief_history.pop(0)

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "belief_analysis",
                latency_ms=latency_ms,
                source="belief_classifier",
                metadata={
                    "category": best_category.value,
                    "rigidity": rigidity
                }
            )

        return BeliefAnalysis(
            belief_statement=belief_statement,
            category=best_category,
            category_confidence=category_confidence,
            rigidity_score=rigidity,
            evidence_balance=evidence_balance,
            potential_biases=biases,
            epistemic_status=epistemic_status,
            recommended_actions=recommendations,
            similar_beliefs=similar_beliefs,
            latency_ms=latency_ms
        )

    def _keyword_classify(self, belief: str) -> Tuple[BeliefCategory, float]:
        """Fallback keyword-based classification."""
        belief_lower = belief.lower()

        keywords = {
            BeliefCategory.IDENTITY: ["i am", "my role", "my purpose", "as an"],
            BeliefCategory.FACT: ["is true", "evidence shows", "research", "proven"],
            BeliefCategory.STRATEGY: ["best way", "should", "approach", "method"],
            BeliefCategory.GOAL: ["goal", "objective", "aim", "target", "want to"],
            BeliefCategory.CAPABILITY: ["can", "cannot", "able", "unable", "possible"],
            BeliefCategory.PREFERENCE: ["prefer", "better", "like", "rather"],
            BeliefCategory.ASSUMPTION: ["assume", "suppose", "given that", "if"]
        }

        best_category = BeliefCategory.FACT
        best_score = 0

        for category, kws in keywords.items():
            score = sum(1 for kw in kws if kw in belief_lower)
            if score > best_score:
                best_score = score
                best_category = category

        confidence = min(0.8, best_score * 0.2) if best_score > 0 else 0.3
        return best_category, confidence

    async def _find_similar_beliefs(
        self,
        belief: str,
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """Find similar past beliefs."""
        if not self.belief_history:
            return []

        belief_embedding = self._get_embedding(belief)
        if belief_embedding is None:
            return []

        similarities = []
        for past in self.belief_history:
            past_embedding = self._get_embedding(past["statement"])
            if past_embedding is not None:
                sim = cosine_similarity(belief_embedding, past_embedding)
                similarities.append((past["statement"], sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    async def check_belief_consistency(
        self,
        beliefs: List[Tuple[str, float]]
    ) -> Dict[str, Any]:
        """
        Check consistency among a set of beliefs.

        Args:
            beliefs: List of (statement, probability) tuples

        Returns:
            Consistency analysis
        """
        if len(beliefs) < 2:
            return {"consistent": True, "conflicts": []}

        conflicts = []

        # Embed all beliefs
        embeddings = []
        for statement, prob in beliefs:
            emb = self._get_embedding(statement)
            if emb is not None:
                embeddings.append((statement, prob, emb))

        # Check for high-similarity beliefs with conflicting probabilities
        for i, (s1, p1, e1) in enumerate(embeddings):
            for s2, p2, e2 in embeddings[i+1:]:
                similarity = cosine_similarity(e1, e2)
                prob_diff = abs(p1 - p2)

                # Similar statements with very different probabilities = conflict
                if similarity > 0.8 and prob_diff > 0.4:
                    conflicts.append({
                        "belief1": s1,
                        "belief2": s2,
                        "similarity": similarity,
                        "probability_diff": prob_diff,
                        "issue": "Similar beliefs with conflicting certainty"
                    })

        return {
            "consistent": len(conflicts) == 0,
            "conflicts": conflicts,
            "total_beliefs": len(beliefs),
            "beliefs_analyzed": len(embeddings)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            "tpu_available": self.use_tpu,
            "categories_loaded": len(self._category_embeddings),
            "cache_size": len(self._embedding_cache),
            "history_size": len(self.belief_history),
            "bias_patterns": len(BIAS_PATTERNS)
        }


# CLI
if __name__ == "__main__":
    import asyncio
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


    parser = argparse.ArgumentParser(description="TPU Belief Classifier")
    parser.add_argument("command", choices=["analyze", "stats"],
                       help="Command to run")
    parser.add_argument("--belief", "-b", type=str, help="Belief statement")
    parser.add_argument("--probability", "-p", type=float, default=0.5,
                       help="Belief probability (0.0-1.0)")
    parser.add_argument("--evidence", "-e", type=str, nargs="*",
                       help="Supporting evidence")

    args = parser.parse_args()

    classifier = TPUBeliefClassifier()

    if args.command == "analyze":
        if not args.belief:
            print("Error: --belief required")
            sys.exit(1)

        analysis = asyncio.run(classifier.analyze_belief(
            belief_statement=args.belief,
            probability=args.probability,
            evidence=args.evidence or []
        ))

        print(json.dumps({
            "category": analysis.category.value,
            "category_confidence": analysis.category_confidence,
            "rigidity_score": analysis.rigidity_score,
            "evidence_balance": analysis.evidence_balance,
            "biases": [b.value for b in analysis.potential_biases],
            "epistemic_status": analysis.epistemic_status,
            "recommendations": analysis.recommended_actions,
            "latency_ms": analysis.latency_ms
        }, indent=2))

    elif args.command == "stats":
        stats = classifier.get_statistics()
        print(json.dumps(stats, indent=2))
