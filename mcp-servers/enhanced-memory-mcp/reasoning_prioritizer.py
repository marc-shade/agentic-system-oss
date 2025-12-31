"""
Reasoning Prioritizer for Enhanced Memory MCP

Implements 75/15 rule from AI vision research:
- 75% priority for reasoning-centric content (code, math, science)
- 15% priority for visual-descriptive content
- 10% priority for general content

Research finding: Reasoning-centric content provides foundation for
visual understanding and should be prioritized in memory storage/retrieval.

STAGE 3 HARDENING (2025-12-17):
- Added semantic coherence checking using sentence-transformers
- Keyword-based classification alone cannot achieve high reasoning scores
- Content must demonstrate semantic similarity to real reasoning examples
- This prevents gaming through keyword stuffing attacks
"""
import re
import logging
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Reference examples of genuine reasoning content for semantic comparison
# These are used to compute semantic similarity - keyword stuffing won't match
REASONING_REFERENCE_EXAMPLES = [
    # Code reasoning
    "The algorithm uses dynamic programming to solve the problem in O(n^2) time complexity by building a table of subproblem solutions.",
    "To implement this function, we first initialize the data structure, then iterate through the input array, updating the accumulator at each step.",
    "The recursive solution has exponential time complexity, so we optimize it using memoization to cache previously computed results.",
    # Math reasoning
    "By applying the chain rule, we can differentiate the composite function to find the rate of change with respect to the input variable.",
    "The proof proceeds by induction: we establish the base case for n=1, then assume the statement holds for n=k and show it holds for n=k+1.",
    "Using the quadratic formula, we solve for x by substituting the coefficients a, b, and c into the expression x = (-b ± √(b²-4ac)) / 2a.",
    # Science reasoning
    "The experimental results show a statistically significant correlation (p < 0.01) between the independent and dependent variables.",
    "According to Newton's second law, the acceleration of the object equals the net force divided by its mass, yielding a = F/m.",
    "The DNA sequence encodes the protein structure through codons, where each triplet of nucleotides specifies an amino acid.",
    # Logic reasoning
    "If the premise A implies B, and we observe A to be true, then by modus ponens we can conclude that B must also be true.",
    "The argument is valid because the conclusion follows necessarily from the premises, regardless of whether the premises are actually true.",
    "By proof by contradiction, we assume the negation of our goal and derive a logical contradiction, thereby establishing the original statement.",
]


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
    semantic_score: float = 0.0  # STAGE 3: Semantic coherence score (0-1)
    keyword_score: float = 0.0   # STAGE 3: Raw keyword score before semantic check


class ReasoningPrioritizer:
    """
    Classifies and prioritizes memory content based on 75/15 rule.

    Priority weights:
    - Reasoning (code/math/science): 0.75
    - Visual (descriptions): 0.15
    - General (other): 0.10

    STAGE 3 HARDENING:
    - Uses sentence-transformers for semantic coherence checking
    - Keyword scores alone cannot achieve reasoning classification
    - Requires semantic similarity to genuine reasoning examples
    """

    def __init__(self):
        self._initialize_patterns()
        self._initialize_semantic_model()

    def _initialize_semantic_model(self):
        """
        Initialize sentence-transformers model for semantic analysis.

        STAGE 3 HARDENING: This model is used to verify that content
        semantically resembles genuine reasoning, not just keyword matches.
        """
        self._model = None
        self._reference_embeddings = None

        try:
            from sentence_transformers import SentenceTransformer
            # Use all-MiniLM-L6-v2 - a bi-encoder model for semantic embeddings
            # (cross-encoders don't produce embeddings, they score pairs)
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
            # Pre-compute reference embeddings for efficiency
            self._reference_embeddings = self._model.encode(
                REASONING_REFERENCE_EXAMPLES,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            logger.info(f"STAGE 3: Semantic coherence model initialized ({len(REASONING_REFERENCE_EXAMPLES)} reference examples)")
        except ImportError:
            logger.warning("sentence-transformers not available, falling back to keyword-only classification")
            self._model = None
        except Exception as e:
            logger.warning(f"Failed to initialize semantic model: {e}, falling back to keyword-only")
            self._model = None

    def _initialize_patterns(self):
        """Initialize regex patterns for content detection."""
        # Code patterns - expanded for real code discussion
        self.code_patterns = [
            r'def\s+\w+\s*\(',
            r'class\s+\w+',
            r'function\s+\w+\s*\(',
            r'import\s+\w+',
            r'=>',
            r'for\s*\(',
            r'if\s*\(',
            r'\{[^}]*\}',
            r'algorithm|recursive|iteration|loop',
            r'array|list|dict|hash|map|set|queue|stack',
            r'variable|parameter|argument|return',
            r'method|call|invoke|execute',
        ]

        # Math patterns - expanded for computational discussion
        self.math_patterns = [
            r'\$.*?\$',
            r'theorem|lemma|proof|corollary',
            r'\\frac|\\sum|\\int',
            r'\d+\s*[+\-*/]\s*\d+',
            r'∀|∃|∈|∉|⊂|⊃',
            r'O\([^\)]+\)',  # Big-O notation
            r'complexity|runtime|space\s+complexity',
            r'equation|formula|compute|calculate',
        ]

        # Science patterns - expanded for technical writing
        self.science_patterns = [
            r'experiment|hypothesis|methodology',
            r'Figure\s+\d+',
            r'p\s*[<>=]\s*0\.\d+',
            r'DNA|RNA|protein',
            r'velocity|acceleration|force',
            r'analysis|implementation|approach',
            r'traverse|graph|tree|node|edge',
        ]

        # Logic patterns - expanded for reasoning discussion
        self.logic_patterns = [
            r'if\s+.*\s+then',
            r'therefore|thus|hence',
            r'assume|suppose|given',
            r'necessary|sufficient',
            r'initialize|process|step|first|then|finally',
            r'worst\s+case|best\s+case|average\s+case',
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

    def _compute_semantic_coherence(self, content: str) -> float:
        """
        STAGE 3 HARDENING: Compute semantic coherence score.

        Uses sentence-transformers to verify content semantically resembles
        genuine reasoning content, not just keyword matches.

        Returns:
            Semantic coherence score (0-1), where:
            - > 0.5: Content semantically resembles reasoning
            - < 0.3: Content is semantically dissimilar (likely gaming/gibberish)
            - 0.3-0.5: Borderline, may be weak reasoning or partial gaming
        """
        if self._model is None or self._reference_embeddings is None:
            # No model available - return neutral score
            return 0.5

        try:
            # Encode the input content
            content_embedding = self._model.encode(
                [content],
                convert_to_numpy=True,
                normalize_embeddings=True
            )[0]

            # Compute cosine similarity with each reference example
            similarities = np.dot(self._reference_embeddings, content_embedding)

            # Use max similarity (best match to any reference)
            max_similarity = float(np.max(similarities))
            # Also consider average (overall coherence)
            avg_similarity = float(np.mean(similarities))

            # Combine: weight max higher (finding one good match matters)
            # but average catches if it's only similar to one thing (gaming)
            semantic_score = 0.7 * max_similarity + 0.3 * avg_similarity

            # Normalize to 0-1 range (similarity can be negative for very dissimilar)
            semantic_score = max(0.0, min(1.0, (semantic_score + 1.0) / 2.0))

            return semantic_score
        except Exception as e:
            logger.warning(f"Semantic coherence computation failed: {e}")
            return 0.5  # Neutral on failure

    def classify_content(self, content: str) -> PriorityScore:
        """
        Classify content and assign priority score.

        STAGE 3 HARDENING: Now requires BOTH keyword matches AND semantic
        coherence to classify as reasoning. Keyword stuffing attacks will
        fail because they won't have semantic similarity to real reasoning.

        Args:
            content: Text content to classify

        Returns:
            PriorityScore with category and weights
        """
        # ANTI-GAMING: Global check for keyword stuffing across ALL reasoning patterns
        # This prevents gaming by spreading keywords across multiple pattern categories
        all_reasoning_patterns = (
            self.code_patterns + self.math_patterns +
            self.science_patterns + self.logic_patterns
        )
        global_gaming_penalty = self._detect_global_keyword_stuffing(content, all_reasoning_patterns)

        # Calculate scores for each content type
        code_score = self._calculate_pattern_score(content, self.code_patterns)
        math_score = self._calculate_pattern_score(content, self.math_patterns)
        science_score = self._calculate_pattern_score(content, self.science_patterns)
        logic_score = self._calculate_pattern_score(content, self.logic_patterns)
        visual_score = self._calculate_pattern_score(content, self.visual_patterns)

        # Raw keyword-based reasoning score (with global gaming penalty)
        keyword_score = max(code_score, math_score, science_score, logic_score) * global_gaming_penalty

        # STAGE 3 HARDENING: Compute semantic coherence
        # This checks if the content actually makes semantic sense as reasoning
        semantic_score = self._compute_semantic_coherence(content)

        # STAGE 3 HARDENING: Combined reasoning score requires BOTH:
        # 1. Keyword matches (patterns found)
        # 2. Semantic coherence (actually makes sense as reasoning)
        #
        # Formula: geometric mean ensures both must be high
        # If semantic_score < 0.3, content is likely gibberish/gaming
        if semantic_score < 0.3:
            # Low semantic coherence = severe penalty regardless of keywords
            reasoning_score = keyword_score * 0.2  # 80% penalty
            logger.debug(f"Low semantic coherence ({semantic_score:.2f}) - keyword stuffing suspected")
        elif semantic_score < 0.5:
            # Borderline semantic coherence = moderate penalty
            reasoning_score = keyword_score * semantic_score
        else:
            # Good semantic coherence = geometric mean of both scores
            reasoning_score = (keyword_score * semantic_score) ** 0.5

        # Determine category and weight
        # STAGE 3: Threshold raised to 0.5 AND requires semantic backing
        if reasoning_score > 0.5 and semantic_score >= 0.4:
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
            confidence=max(reasoning_score, visual_score, 0.3),
            semantic_score=semantic_score,
            keyword_score=keyword_score
        )

    def _detect_global_keyword_stuffing(self, content: str, all_patterns: List[str]) -> float:
        """
        Global anti-gaming check across ALL reasoning patterns.

        Detects keyword stuffing that spans multiple pattern categories
        (e.g., mixing math, science, and code keywords to game each individually).

        Returns:
            Penalty multiplier: 1.0 = no penalty, 0.0 = full penalty
        """
        import re

        words = content.split()
        word_count = len(words)

        if word_count < 10:
            return 0.0  # Too short - block entirely

        # Count all keyword matches across ALL patterns
        total_keyword_words = 0
        unique_keywords = set()

        for pattern in all_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    unique_keywords.add(match.lower().strip())
                    total_keyword_words += len(match.split())

        # Global keyword density check
        keyword_density = total_keyword_words / word_count

        # Heavy penalty for keyword-dense content
        if keyword_density > 0.6:
            return 0.1  # 90% penalty - obvious keyword stuffing
        elif keyword_density > 0.4:
            return 0.3  # 70% penalty - likely keyword stuffing
        elif keyword_density > 0.3:
            return 0.6  # 40% penalty - suspicious density

        # Check for lack of "filler" words (prepositions, articles, conjunctions)
        # Real content has connective tissue
        filler_patterns = [
            r'\b(the|a|an|is|are|was|were|be|been|being)\b',
            r'\b(of|in|to|for|with|on|at|by|from|about)\b',
            r'\b(and|or|but|if|then|when|while|because|although)\b',
            r'\b(this|that|these|those|it|its|they|their)\b',
        ]

        filler_count = 0
        for pattern in filler_patterns:
            filler_count += len(re.findall(pattern, content, re.IGNORECASE))

        filler_ratio = filler_count / word_count
        if filler_ratio < 0.1 and keyword_density > 0.2:
            # Keyword-heavy with almost no natural language structure
            return 0.3  # 70% penalty

        # GLOBAL Edge-clustering detection (keywords at start/end, filler in middle)
        # This catches gaming that spreads keywords across categories
        if word_count >= 20 and len(unique_keywords) >= 2:
            first_fifth = ' '.join(words[:word_count // 5])
            last_fifth = ' '.join(words[-word_count // 5:])
            middle = ' '.join(words[word_count // 5:-word_count // 5])

            edge_keywords = 0
            middle_keywords = 0
            for pattern in all_patterns:
                edge_keywords += len(re.findall(pattern, first_fifth + ' ' + last_fifth, re.IGNORECASE))
                middle_keywords += len(re.findall(pattern, middle, re.IGNORECASE))

            total_matches = edge_keywords + middle_keywords
            if total_matches > 0:
                edge_ratio = edge_keywords / total_matches
                # If >75% of keywords are at edges, it's likely gaming
                if edge_ratio > 0.75 and edge_keywords >= 4:
                    return 0.4  # 60% penalty for edge clustering

        return 1.0  # No penalty

    def _calculate_pattern_score(self, content: str, patterns: List[str]) -> float:
        """
        Calculate score based on pattern matches with anti-gaming measures.

        Anti-gaming features:
        1. Unique keyword counting (repetition doesn't increase score)
        2. Semantic density check (keywords must be <50% of total words)
        3. Minimum content length requirement
        4. Keyword distribution check (spread across content, not clustered)
        """
        words = content.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Minimum content length to prevent gaming with short keyword soup
        if word_count < 10:
            return 0.0

        # Count UNIQUE pattern matches (not total occurrences)
        unique_matches = set()
        total_keyword_words = 0

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                unique_matches.add(match.lower().strip())
                total_keyword_words += len(match.split())

        unique_match_count = len(unique_matches)

        # Anti-gaming: If keywords make up >50% of content, it's likely keyword stuffing
        keyword_density = total_keyword_words / word_count
        if keyword_density > 0.5:
            # Penalize keyword stuffing severely
            return 0.1  # Minimal score for gaming attempts

        # Anti-gaming: Check keyword distribution (should be spread, not clustered)
        # If all keywords are in first 20% or last 20% of content, likely gaming
        if word_count >= 20:
            first_fifth = ' '.join(words[:word_count // 5])
            last_fifth = ' '.join(words[-word_count // 5:])
            middle = ' '.join(words[word_count // 5:-word_count // 5])

            first_matches = sum(1 for p in patterns if re.search(p, first_fifth, re.IGNORECASE))
            last_matches = sum(1 for p in patterns if re.search(p, last_fifth, re.IGNORECASE))
            middle_matches = sum(1 for p in patterns if re.search(p, middle, re.IGNORECASE))

            total_distributed = first_matches + last_matches + middle_matches
            if total_distributed > 0:
                # If >80% of matches are at edges, it's likely gaming
                edge_ratio = (first_matches + last_matches) / total_distributed
                if edge_ratio > 0.8 and unique_match_count > 3:
                    return 0.2  # Penalize edge clustering

        # Calculate score from unique matches, normalized by content complexity
        # More sophisticated normalization: sqrt to prevent linear gaming
        import math
        normalized_score = min(1.0, math.sqrt(unique_match_count) / math.sqrt(max(1, word_count // 15)))

        return normalized_score

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
