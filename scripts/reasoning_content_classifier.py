#!/usr/bin/env python3
"""
Reasoning Content Classifier

Implements the 75/15/10 rule from memory consolidation research:
- 75% reasoning-centric (code, math, logic, algorithms)
- 15% visual-centric (images, diagrams, spatial)
- 10% general knowledge

This classifier scores content to determine tier placement and retrieval priority.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ContentCategory(Enum):
    REASONING_CENTRIC = "reasoning_centric"
    VISUAL_CENTRIC = "visual_centric"
    GENERAL = "general"


@dataclass
class ClassificationResult:
    category: ContentCategory
    confidence: float
    reasoning_score: float
    visual_score: float
    general_score: float
    tier_boost: float
    details: dict


# Patterns for reasoning-centric content
REASONING_PATTERNS = {
    # Code patterns
    "code_keywords": r"\b(def|class|function|import|export|const|let|var|if|else|for|while|return|async|await|try|catch)\b",
    "code_syntax": r"[{}\[\]();].*[{}\[\]();]",
    "code_operators": r"(===|!==|==|!=|>=|<=|&&|\|\||=>|\+\+|--)",

    # Math patterns
    "math_symbols": r"[∑∏∫∂√∞≈≠≤≥±×÷]",
    "math_notation": r"\b(sum|product|integral|derivative|sqrt|infinity|approximately)\b",
    "equations": r"[a-zA-Z]\s*[=<>]\s*[a-zA-Z0-9+\-*/^()]+",

    # Logic patterns
    "logic_keywords": r"\b(therefore|hence|thus|implies|iff|forall|exists|and|or|not|if and only if)\b",
    "logical_operators": r"(∧|∨|¬|→|↔|⊃|∀|∃)",

    # Algorithm patterns
    "algorithm_keywords": r"\b(algorithm|complexity|O\(|Θ\(|Ω\(|sort|search|traverse|recursive|iterative|dynamic programming|greedy|divide and conquer)\b",
    "data_structures": r"\b(array|list|tree|graph|hash|stack|queue|heap|trie|linked list|binary tree)\b",

    # Scientific method
    "scientific_keywords": r"\b(hypothesis|experiment|data|analysis|conclusion|correlation|causation|variable|control|sample|population)\b",

    # Formal reasoning
    "formal_keywords": r"\b(proof|theorem|lemma|corollary|axiom|definition|proposition|QED|contradiction)\b",
}

# Patterns for visual-centric content
VISUAL_PATTERNS = {
    "image_references": r"\b(image|figure|diagram|chart|graph|plot|visualization|screenshot|photo)\b",
    "spatial_terms": r"\b(above|below|left|right|top|bottom|center|adjacent|parallel|perpendicular)\b",
    "visual_formats": r"\.(png|jpg|jpeg|gif|svg|webp|bmp)\b",
    "ui_elements": r"\b(button|form|input|layout|grid|flex|margin|padding|border|color|font)\b",
}

# Patterns that indicate general content
GENERAL_PATTERNS = {
    "conversational": r"\b(hello|hi|thanks|please|sorry|okay|sure|maybe|probably)\b",
    "opinions": r"\b(I think|in my opinion|I believe|I feel|seems like|might be)\b",
    "filler_words": r"\b(basically|actually|literally|really|very|quite|somewhat)\b",
}


def count_pattern_matches(text: str, patterns: dict) -> int:
    """Count total matches across all patterns in a category"""
    total = 0
    text_lower = text.lower()
    for pattern in patterns.values():
        total += len(re.findall(pattern, text_lower, re.IGNORECASE))
    return total


def classify_content(content: str, metadata: Optional[dict] = None) -> ClassificationResult:
    """
    Classify content according to the 75/15/10 rule.

    Args:
        content: The text content to classify
        metadata: Optional metadata (content_type, source, etc.)

    Returns:
        ClassificationResult with category, confidence, and scores
    """
    if not content:
        return ClassificationResult(
            category=ContentCategory.GENERAL,
            confidence=1.0,
            reasoning_score=0.0,
            visual_score=0.0,
            general_score=1.0,
            tier_boost=0.8,
            details={"reason": "empty_content"}
        )

    # Count pattern matches
    reasoning_matches = count_pattern_matches(content, REASONING_PATTERNS)
    visual_matches = count_pattern_matches(content, VISUAL_PATTERNS)
    general_matches = count_pattern_matches(content, GENERAL_PATTERNS)

    # Normalize by content length (per 100 chars)
    content_length = max(len(content), 1)
    reasoning_density = (reasoning_matches / content_length) * 100
    visual_density = (visual_matches / content_length) * 100
    general_density = (general_matches / content_length) * 100

    # Apply metadata boosts
    if metadata:
        content_type = metadata.get("content_type", "").lower()
        if content_type in ["code", "algorithm", "math", "proof", "analysis"]:
            reasoning_density *= 1.5
        elif content_type in ["image", "diagram", "chart", "ui"]:
            visual_density *= 1.5

    # Calculate normalized scores
    total_density = reasoning_density + visual_density + general_density + 0.001  # Avoid division by zero
    reasoning_score = reasoning_density / total_density
    visual_score = visual_density / total_density
    general_score = general_density / total_density

    # Determine category
    if reasoning_score >= 0.5 or reasoning_density > 2.0:
        category = ContentCategory.REASONING_CENTRIC
        confidence = min(reasoning_score + 0.2, 1.0)
        tier_boost = 1.3  # 30% boost for reasoning content
    elif visual_score >= 0.5 or visual_density > 1.5:
        category = ContentCategory.VISUAL_CENTRIC
        confidence = min(visual_score + 0.2, 1.0)
        tier_boost = 1.0  # Neutral
    else:
        category = ContentCategory.GENERAL
        confidence = max(general_score, 0.5)
        tier_boost = 0.8  # 20% reduction for general content

    return ClassificationResult(
        category=category,
        confidence=confidence,
        reasoning_score=reasoning_score,
        visual_score=visual_score,
        general_score=general_score,
        tier_boost=tier_boost,
        details={
            "reasoning_matches": reasoning_matches,
            "visual_matches": visual_matches,
            "general_matches": general_matches,
            "content_length": content_length,
        }
    )


def should_prioritize_for_storage(content: str, metadata: Optional[dict] = None) -> tuple[bool, float]:
    """
    Determine if content should be prioritized for long-term storage.

    Returns:
        (should_store, priority_weight)
    """
    result = classify_content(content, metadata)

    if result.category == ContentCategory.REASONING_CENTRIC:
        return True, result.tier_boost * result.confidence
    elif result.category == ContentCategory.VISUAL_CENTRIC:
        # Store if confidence is high enough
        return result.confidence > 0.6, result.tier_boost * result.confidence
    else:
        # General content: only store if explicitly important
        importance = metadata.get("importance", 0.5) if metadata else 0.5
        return importance > 0.7, result.tier_boost * importance


def get_retrieval_boost(content: str, metadata: Optional[dict] = None) -> float:
    """
    Get the retrieval weight boost for content based on 75/15 rule.

    This boost is applied during memory search to prioritize reasoning content.
    """
    result = classify_content(content, metadata)
    return result.tier_boost


# Example usage and testing
if __name__ == "__main__":
    test_cases = [
        # Reasoning-centric
        ("def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)", "code"),
        ("The algorithm has O(n log n) time complexity due to the divide and conquer approach", "algorithm"),
        ("∑(i=1 to n) i² = n(n+1)(2n+1)/6", "math"),

        # Visual-centric
        ("The diagram below shows the architecture with boxes on the left and arrows pointing right", "visual"),
        ("See figure 3 for the chart comparing performance metrics", "visual"),

        # General
        ("Hello, I think this is probably a good idea, thanks for asking!", "general"),
        ("The weather seems nice today, maybe we should go outside", "general"),
    ]

    print("Content Classification Test Results")
    print("=" * 70)

    for content, expected in test_cases:
        result = classify_content(content)
        status = "✓" if result.category.value.startswith(expected) else "✗"
        print(f"\n{status} Expected: {expected}")
        print(f"  Category: {result.category.value}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Tier Boost: {result.tier_boost:.2f}")
        print(f"  Scores: R={result.reasoning_score:.2f} V={result.visual_score:.2f} G={result.general_score:.2f}")
        print(f"  Content: {content[:60]}...")
