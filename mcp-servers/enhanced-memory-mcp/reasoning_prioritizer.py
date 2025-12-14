"""
Reasoning Prioritizer for Enhanced Memory MCP

Implements 75/15 rule from AI vision research:
- 75% priority for reasoning-centric content (code, math, science)
- 15% priority for visual-descriptive content
- 10% priority for general content

Research finding: Reasoning-centric content provides foundation for
visual understanding and should be prioritized in memory storage/retrieval.
"""
import re
from enum import Enum
from typing import Dict, List, Tuple
from dataclasses import dataclass


class ContentCategory(Enum):
    """Content categories based on 75/15 rule."""
    REASONING_CENTRIC = "reasoning_centric"  # Code, math, science, logic
    VISUAL_CENTRIC = "visual_centric"        # Visual descriptions
    GENERAL = "general"                      # General text


@dataclass
class PriorityScore:
    """Priority scoring for memory content."""
    category: ContentCategory
    weight: float  # 0.75, 0.15, or 0.10
    reasoning_score: float  # 0-1
    visual_score: float     # 0-1
    confidence: float       # 0-1


class ReasoningPrioritizer:
    """
    Classifies and prioritizes memory content based on 75/15 rule.

    Priority weights:
    - Reasoning (code/math/science): 0.75
    - Visual (descriptions): 0.15
    - General (other): 0.10
    """

    def __init__(self):
        self._initialize_patterns()

    def _initialize_patterns(self):
        """Initialize regex patterns for content detection."""
        # Code patterns
        self.code_patterns = [
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'function\s+\w+\s*\(',
            r'import\s+\w+',
            r'=>',
            r'for\s*\(',
            r'if\s*\(',
            r'\{[^}]*\}',
        ]

        # Math patterns
        self.math_patterns = [
            r'\$.*?\$',
            r'theorem|lemma|proof|corollary',
            r'\\frac|\\sum|\\int',
            r'\d+\s*[+\-*/]\s*\d+',
            r'∀|∃|∈|∉|⊂|⊃',
        ]

        # Science patterns
        self.science_patterns = [
            r'experiment|hypothesis|methodology',
            r'Figure\s+\d+',
            r'p\s*[<>=]\s*0\.\d+',
            r'DNA|RNA|protein',
            r'velocity|acceleration|force',
        ]

        # Logic patterns
        self.logic_patterns = [
            r'if\s+.*\s+then',
            r'therefore|thus|hence',
            r'assume|suppose|given',
            r'necessary|sufficient',
        ]

        # Visual patterns
        self.visual_patterns = [
            r'color|colour|red|blue|green',
            r'shape|circle|square|triangle',
            r'image|picture|photo',
            r'looks like|appears',
            r'visual|visible|sight',
            r'left|right|top|bottom',
        ]

    def classify_content(self, content: str) -> PriorityScore:
        """
        Classify content and assign priority score.

        Args:
            content: Text content to classify

        Returns:
            PriorityScore with category and weights
        """
        # Calculate scores for each content type
        code_score = self._calculate_pattern_score(content, self.code_patterns)
        math_score = self._calculate_pattern_score(content, self.math_patterns)
        science_score = self._calculate_pattern_score(content, self.science_patterns)
        logic_score = self._calculate_pattern_score(content, self.logic_patterns)
        visual_score = self._calculate_pattern_score(content, self.visual_patterns)

        # Overall reasoning score
        reasoning_score = max(code_score, math_score, science_score, logic_score)

        # Determine category and weight
        if reasoning_score > 0.5:
            category = ContentCategory.REASONING_CENTRIC
            weight = 0.75
        elif visual_score > 0.5:
            category = ContentCategory.VISUAL_CENTRIC
            weight = 0.15
        else:
            category = ContentCategory.GENERAL
            weight = 0.10

        return PriorityScore(
            category=category,
            weight=weight,
            reasoning_score=reasoning_score,
            visual_score=visual_score,
            confidence=max(reasoning_score, visual_score, 0.3)
        )

    def _calculate_pattern_score(self, content: str, patterns: List[str]) -> float:
        """Calculate score based on pattern matches."""
        matches = sum(
            len(re.findall(pattern, content, re.IGNORECASE))
            for pattern in patterns
        )

        # Normalize by content length
        words = len(content.split())
        if words == 0:
            return 0.0

        score = min(1.0, matches / max(1, words // 10))
        return score

    def rank_memories(
        self,
        memories: List[Dict],
        query: str,
        boost_reasoning: bool = True
    ) -> List[Tuple[Dict, float]]:
        """
        Rank memories with reasoning prioritization.

        Args:
            memories: List of memory dictionaries
            query: Search query
            boost_reasoning: Whether to boost reasoning-centric results

        Returns:
            List of (memory, score) tuples, sorted by score
        """
        ranked = []
        query_priority = self.classify_content(query)

        for memory in memories:
            # Get memory content
            content = str(memory.get('observations', ''))

            # Classify memory
            memory_priority = self.classify_content(content)

            # Base relevance score (simplified - should use semantic similarity)
            base_score = self._calculate_relevance(query, content)

            # Apply priority boost
            priority_multiplier = 1.0
            if boost_reasoning:
                # Boost if memory matches query category
                if memory_priority.category == query_priority.category:
                    priority_multiplier = 1.2

                # Always boost reasoning-centric content
                if memory_priority.category == ContentCategory.REASONING_CENTRIC:
                    priority_multiplier *= 1.3  # 75% boost

            final_score = base_score * priority_multiplier * memory_priority.weight

            ranked.append((memory, final_score))

        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate basic relevance score (simplified)."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        intersection = query_words & content_words
        return len(intersection) / len(query_words)

    def get_compression_level(self, content: str) -> int:
        """
        Get optimal compression level based on content category.

        Reasoning-centric content (75%): Lower compression (level 6) - preserve detail
        Visual content (15%): Higher compression (level 9) - less critical
        General content (10%): Highest compression (level 9) - least critical

        Args:
            content: Content to compress

        Returns:
            Compression level (1-9)
        """
        priority = self.classify_content(content)

        if priority.category == ContentCategory.REASONING_CENTRIC:
            return 6  # Moderate compression, preserve reasoning details
        elif priority.category == ContentCategory.VISUAL_CENTRIC:
            return 8  # Higher compression, less critical
        else:
            return 9  # Maximum compression for general content

    def should_prioritize_storage(self, content: str) -> Tuple[bool, str]:
        """
        Determine if content should be prioritized for storage.

        Args:
            content: Content to evaluate

        Returns:
            Tuple of (should_prioritize, reason)
        """
        priority = self.classify_content(content)

        if priority.category == ContentCategory.REASONING_CENTRIC:
            return True, f"Reasoning-centric content (weight: {priority.weight})"
        elif priority.category == ContentCategory.VISUAL_CENTRIC:
            if priority.visual_score > 0.7:
                return True, "High-quality visual description"
            return False, "Visual content below quality threshold"
        else:
            return False, "General content (lowest priority)"

    def calculate_tier_priority(self, content: str, access_count: int) -> str:
        """
        Calculate optimal tier for content based on category and access.

        Tiers:
        - core: Essential reasoning patterns, frequently accessed
        - working: Active reasoning content, moderate access
        - reference: Archived reasoning, visual, and general content

        Args:
            content: Content to tier
            access_count: Number of times accessed

        Returns:
            Tier name (core, working, or reference)
        """
        priority = self.classify_content(content)

        # Reasoning-centric content gets priority tiers
        if priority.category == ContentCategory.REASONING_CENTRIC:
            if access_count > 10 or priority.reasoning_score > 0.8:
                return "core"  # Hot, frequently accessed reasoning
            else:
                return "working"  # Active reasoning

        # Visual and general content mostly in reference
        elif priority.category == ContentCategory.VISUAL_CENTRIC:
            if access_count > 20:  # Very frequently accessed visual
                return "working"
            return "reference"

        else:  # General content
            return "reference"


# Singleton instance
_prioritizer = None

def get_prioritizer() -> ReasoningPrioritizer:
    """Get singleton prioritizer instance."""
    global _prioritizer
    if _prioritizer is None:
        _prioritizer = ReasoningPrioritizer()
    return _prioritizer
