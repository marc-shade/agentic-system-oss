#!/usr/bin/env python3
"""
Entropy-Based Tier Assignment for Enhanced Memory

Inspired by PTM (Phonetic Trajectory Memory) paper's anchor/bridge bifurcation.
High-entropy content (proper nouns, numbers, code) needs precision retrieval.
Low-entropy content (articles, common phrases) compresses well.

Reference: "Memory as Resonance" (arXiv:2512.20245)
- Anchor tokens: High entropy, stored in precision tier
- Bridge tokens: Low entropy, compressible to manifold trajectory

Integration with existing TPU scoring:
- TPU score: Semantic importance (0.0-1.0)
- Entropy score: Information density (bits per token)
- Combined: Weighted fusion for tier assignment
"""

import re
import math
from collections import Counter
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger("entropy-scoring")

# PTM paper empirical thresholds (Section 4.2), tuned for enhanced-memory
ENTROPY_HIGH_THRESHOLD = 3.5    # bits - precision tier (anchors)
ENTROPY_LOW_THRESHOLD = 2.8     # bits - compressible tier (bridges)
DEFAULT_ENTROPY_WEIGHT = 0.3    # Weight in combined scoring (TPU gets 0.7)
ANCHOR_RATIO_THRESHOLD = 0.25   # Min anchor ratio to classify as anchor
BRIDGE_RATIO_THRESHOLD = 0.40   # Min bridge ratio to classify as bridge

# High-entropy patterns (proper nouns, numbers, code identifiers)
HIGH_ENTROPY_PATTERNS = [
    r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',  # Proper names (John Smith)
    r'\b[A-Z]{2,}\b',                         # Acronyms (API, HTTP)
    r'\b\d+(?:\.\d+)?\b',                     # Numbers
    r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',            # Code identifiers
    r'[a-f0-9]{8,}',                          # Hashes, UUIDs
    r'\b(?:https?://|www\.)\S+',              # URLs
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
]

# Low-entropy stopwords (common, predictable tokens)
STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
    'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
    'and', 'but', 'if', 'or', 'because', 'until', 'while', 'although',
    'this', 'that', 'these', 'those', 'it', 'its', 'he', 'she', 'they',
    'we', 'you', 'i', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
    'his', 'their', 'our', 'what', 'which', 'who', 'whom', 'whose',
}


@dataclass
class EntropyResult:
    """Result of entropy analysis for an entity."""
    entropy_bits: float          # Shannon entropy in bits
    token_count: int             # Total tokens analyzed
    unique_tokens: int           # Unique token count
    anchor_ratio: float          # Ratio of high-entropy tokens (0.0-1.0)
    bridge_ratio: float          # Ratio of low-entropy tokens (0.0-1.0)
    classification: str          # "anchor", "bridge", or "mixed"
    recommended_tier: str        # "long_term", "episodic", or "working"
    confidence: float            # Confidence in classification (0.0-1.0)

    def to_dict(self) -> Dict:
        return {
            "entropy_bits": round(self.entropy_bits, 3),
            "token_count": self.token_count,
            "unique_tokens": self.unique_tokens,
            "anchor_ratio": round(self.anchor_ratio, 3),
            "bridge_ratio": round(self.bridge_ratio, 3),
            "classification": self.classification,
            "recommended_tier": self.recommended_tier,
            "confidence": round(self.confidence, 3)
        }


def tokenize(text: str) -> List[str]:
    """
    Simple tokenization for entropy calculation.
    Preserves case for proper noun detection.
    """
    # Split on whitespace and punctuation, keep alphanumeric
    tokens = re.findall(r'\b[\w\']+\b', text)
    return tokens


def calculate_shannon_entropy(tokens: List[str]) -> float:
    """
    Calculate Shannon entropy in bits.

    H(X) = -Σ p(x) * log2(p(x))

    Higher entropy = more information content = harder to compress.
    """
    if not tokens:
        return 0.0

    # Normalize to lowercase for frequency counting
    normalized = [t.lower() for t in tokens]
    counts = Counter(normalized)
    total = len(normalized)

    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)

    return entropy


def count_high_entropy_tokens(text: str, tokens: List[str]) -> int:
    """
    Count tokens matching high-entropy patterns.
    These are "anchor" tokens that need precision retrieval.
    """
    anchor_count = 0

    # Check each pattern
    for pattern in HIGH_ENTROPY_PATTERNS:
        matches = re.findall(pattern, text)
        anchor_count += len(matches)

    # Also count tokens with mixed case (likely proper nouns/identifiers)
    for token in tokens:
        if len(token) > 1 and not token.islower() and not token.isupper():
            anchor_count += 1

    return min(anchor_count, len(tokens))  # Cap at token count


def count_low_entropy_tokens(tokens: List[str]) -> int:
    """
    Count stopword tokens (low entropy, high predictability).
    These are "bridge" tokens that compress well.
    """
    return sum(1 for t in tokens if t.lower() in STOPWORDS)


def analyze_entropy(text: str) -> EntropyResult:
    """
    Analyze text entropy and classify as anchor/bridge.

    Returns EntropyResult with:
    - entropy_bits: Shannon entropy
    - anchor_ratio: Proportion of high-entropy tokens
    - bridge_ratio: Proportion of low-entropy tokens
    - classification: "anchor", "bridge", or "mixed"
    - recommended_tier: Based on entropy analysis
    """
    tokens = tokenize(text)

    if not tokens:
        return EntropyResult(
            entropy_bits=0.0,
            token_count=0,
            unique_tokens=0,
            anchor_ratio=0.0,
            bridge_ratio=0.0,
            classification="bridge",
            recommended_tier="working",
            confidence=0.5
        )

    # Calculate metrics
    entropy = calculate_shannon_entropy(tokens)
    unique_count = len(set(t.lower() for t in tokens))
    anchor_count = count_high_entropy_tokens(text, tokens)
    bridge_count = count_low_entropy_tokens(tokens)

    total = len(tokens)
    anchor_ratio = anchor_count / total
    bridge_ratio = bridge_count / total

    # Classification based on PTM thresholds
    # Priority: bridge ratio > entropy > anchor ratio
    # High bridge ratio strongly indicates compressible content
    if bridge_ratio >= BRIDGE_RATIO_THRESHOLD:
        classification = "bridge"
        recommended_tier = "working"
        confidence = min(1.0, 0.5 + bridge_ratio)
    elif entropy >= ENTROPY_HIGH_THRESHOLD or anchor_ratio >= ANCHOR_RATIO_THRESHOLD:
        classification = "anchor"
        recommended_tier = "long_term"
        confidence = min(1.0, 0.5 + anchor_ratio + (entropy / 5.0))
    elif entropy <= ENTROPY_LOW_THRESHOLD:
        classification = "bridge"
        recommended_tier = "working"
        confidence = min(1.0, 0.6 + (3.0 - entropy) / 3.0)
    else:
        classification = "mixed"
        recommended_tier = "episodic"
        confidence = 0.65  # Mixed content has moderate confidence

    return EntropyResult(
        entropy_bits=entropy,
        token_count=total,
        unique_tokens=unique_count,
        anchor_ratio=anchor_ratio,
        bridge_ratio=bridge_ratio,
        classification=classification,
        recommended_tier=recommended_tier,
        confidence=min(1.0, confidence)
    )


def combine_scores(
    tpu_score: float,
    entropy_result: EntropyResult,
    tpu_weight: float = 0.7,
    entropy_weight: float = 0.3
) -> Tuple[float, str]:
    """
    Combine TPU importance score with entropy analysis.

    Strategy:
    - TPU score: Semantic importance (what matters)
    - Entropy score: Information density (how unique)

    High TPU + High Entropy → long_term (important & unique)
    High TPU + Low Entropy → episodic (important but compressible)
    Low TPU + High Entropy → episodic (unique but not critical)
    Low TPU + Low Entropy → working (neither important nor unique)

    Returns:
        (combined_score, recommended_tier)
    """
    # Normalize entropy to 0-1 scale (assuming max ~5 bits for natural text)
    entropy_normalized = min(1.0, entropy_result.entropy_bits / 5.0)

    # Combine scores
    combined = (tpu_weight * tpu_score) + (entropy_weight * entropy_normalized)

    # Adjust based on anchor/bridge classification
    if entropy_result.classification == "anchor":
        # Anchors get tier boost (precision retrieval needed)
        combined = min(1.0, combined + 0.1)
    elif entropy_result.classification == "bridge":
        # Bridges get tier reduction (can be compressed)
        combined = max(0.0, combined - 0.1)

    # Determine tier from combined score
    if combined >= 0.75:
        tier = "long_term"
    elif combined >= 0.5:
        tier = "episodic"
    else:
        tier = "working"

    return combined, tier


def score_entity_entropy(
    name: str,
    observations: List[str],
    entity_type: str = "general"
) -> EntropyResult:
    """
    Score an entity's entropy based on name and observations.

    Convenience function for integration with create_entities.
    """
    # Combine entity info for analysis
    combined_text = f"{name} ({entity_type}): " + " ".join(
        str(obs) for obs in observations[:10]  # Limit for performance
    )

    return analyze_entropy(combined_text)


# Statistics tracking
_stats = {
    "entities_scored": 0,
    "anchor_count": 0,
    "bridge_count": 0,
    "mixed_count": 0,
    "avg_entropy": 0.0
}


def update_stats(result: EntropyResult):
    """Update running statistics for monitoring."""
    global _stats
    _stats["entities_scored"] += 1

    if result.classification == "anchor":
        _stats["anchor_count"] += 1
    elif result.classification == "bridge":
        _stats["bridge_count"] += 1
    else:
        _stats["mixed_count"] += 1

    # Running average of entropy
    n = _stats["entities_scored"]
    _stats["avg_entropy"] = (
        (_stats["avg_entropy"] * (n - 1) + result.entropy_bits) / n
    )


def get_stats() -> Dict:
    """Get entropy scoring statistics."""
    return _stats.copy()


def reset_stats():
    """Reset statistics."""
    global _stats
    _stats = {
        "entities_scored": 0,
        "anchor_count": 0,
        "bridge_count": 0,
        "mixed_count": 0,
        "avg_entropy": 0.0
    }


# Self-test
if __name__ == "__main__":
    print("=== Entropy Scoring Tests ===\n")

    test_cases = [
        # High entropy (anchors)
        ("John Smith works at OpenAI on GPT-5", "anchor"),
        ("Error code 0x8007045D in module KERNEL32.DLL", "anchor"),
        ("API endpoint: https://api.example.com/v2/users", "anchor"),

        # Low entropy (bridges)
        ("The system is working as expected", "bridge"),
        ("This is a very simple test case", "bridge"),

        # Mixed
        ("The database connection to PostgreSQL failed with timeout", "mixed"),
        ("Memory optimization using the new PTM algorithm", "mixed"),
    ]

    print(f"{'Text':<55} {'Entropy':>8} {'Class':>8} {'Expected':>10} {'Match':>6}")
    print("-" * 95)

    for text, expected in test_cases:
        result = analyze_entropy(text)
        match = "✓" if result.classification == expected else "✗"
        print(f"{text[:53]:<55} {result.entropy_bits:>8.2f} {result.classification:>8} {expected:>10} {match:>6}")

    print("\n=== Combined Scoring Test ===\n")

    # Test combined scoring
    test_entity = "PTM-Memory-Architecture"
    test_obs = [
        "Phonetic Trajectory Memory uses 16D hyper-torus",
        "Achieves >3000x compression ratio",
        "O(1) retrieval complexity"
    ]

    result = score_entity_entropy(test_entity, test_obs)
    print(f"Entity: {test_entity}")
    print(f"Entropy: {result.entropy_bits:.2f} bits")
    print(f"Classification: {result.classification}")
    print(f"Anchor ratio: {result.anchor_ratio:.2%}")
    print(f"Bridge ratio: {result.bridge_ratio:.2%}")
    print(f"Recommended tier: {result.recommended_tier}")
    print(f"Confidence: {result.confidence:.2%}")

    # Test with TPU score combination
    tpu_score = 0.75  # Simulated TPU importance score
    combined, tier = combine_scores(tpu_score, result)
    print(f"\nWith TPU score {tpu_score}:")
    print(f"Combined score: {combined:.2f}")
    print(f"Final tier: {tier}")
