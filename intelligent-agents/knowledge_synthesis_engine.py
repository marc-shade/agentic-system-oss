#!/usr/bin/env python3
"""
Knowledge Synthesis Engine
===========================

Multi-source knowledge integration and insight synthesis for AGI learning.

Takes knowledge from disparate sources and synthesizes into actionable insights:
- Research papers (arXiv, Semantic Scholar)
- Technical videos (YouTube, conferences)
- Code repositories (GitHub)
- Documentation (API docs, specifications)

Processes:
1. Gather knowledge from multiple sources
2. Extract key concepts and relationships
3. Identify patterns across sources
4. Synthesize into structured insights
5. Store in enhanced-memory for learning

This enables cross-pollination of ideas from different domains and
accelerates AGI learning through knowledge transfer.
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeSource(Enum):
    """Types of knowledge sources"""
    RESEARCH_PAPER = "research_paper"
    VIDEO_TRANSCRIPT = "video_transcript"
    CODE_REPOSITORY = "code_repository"
    DOCUMENTATION = "documentation"
    EXPERIMENT_RESULT = "experiment_result"


@dataclass
class KnowledgeItem:
    """Individual piece of knowledge from a source"""
    item_id: str
    source_type: KnowledgeSource
    source_id: str  # Paper ID, video ID, repo URL, etc.

    # Content
    title: str
    concepts: List[str]
    techniques: List[str]
    insights: List[str]

    # Metadata
    authors: List[str]
    created_at: str
    citations: int
    confidence_score: float  # 0.0 to 1.0

    # Relationships
    related_items: List[str]
    tags: List[str]


@dataclass
class SynthesizedInsight:
    """Insight synthesized from multiple knowledge sources"""
    insight_id: str
    insight_text: str

    # Supporting evidence from multiple sources
    supporting_items: List[str]  # KnowledgeItem IDs
    source_types: List[KnowledgeSource]

    # Cross-domain connections
    connected_concepts: List[str]
    connected_techniques: List[str]

    # Confidence and novelty
    confidence_score: float  # Based on cross-source agreement
    novelty_score: float  # How unique/new is this insight

    created_at: str
    tags: List[str]


class KnowledgeSynthesisEngine:
    """
    Multi-source knowledge synthesis and integration system.

    Combines knowledge from research papers, videos, code, and documentation
    to generate novel insights through cross-domain synthesis.
    """

    def __init__(self, base_path: str = "/mnt/agentic-system"):
        """Initialize knowledge synthesis engine."""
        self.base_path = Path(base_path)
        self.knowledge_dir = self.base_path / "synthesized-knowledge"
        self.knowledge_dir.mkdir(exist_ok=True)

        # Knowledge storage
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.synthesized_insights: Dict[str, SynthesizedInsight] = {}

        # Concept graph (for finding connections)
        self.concept_graph: Dict[str, Set[str]] = defaultdict(set)  # concept -> item_ids
        self.technique_graph: Dict[str, Set[str]] = defaultdict(set)  # technique -> item_ids

        logger.info("Knowledge Synthesis Engine initialized")

    def add_knowledge_item(self, item: KnowledgeItem):
        """Add a knowledge item to the system."""
        logger.info(f"Adding knowledge item: {item.title} ({item.source_type.value})")

        self.knowledge_items[item.item_id] = item

        # Build concept and technique graphs
        for concept in item.concepts:
            self.concept_graph[concept.lower()].add(item.item_id)

        for technique in item.techniques:
            self.technique_graph[technique.lower()].add(item.item_id)

        # Save to disk
        self._save_knowledge_item(item)

    async def synthesize_insights(
        self,
        min_sources: int = 2,
        min_confidence: float = 0.7
    ) -> List[SynthesizedInsight]:
        """
        Synthesize insights from accumulated knowledge items.

        Looks for patterns across multiple sources and generates
        novel insights through cross-domain knowledge transfer.

        Args:
            min_sources: Minimum number of sources needed for synthesis
            min_confidence: Minimum confidence score for insights

        Returns:
            List of synthesized insights
        """
        logger.info(f"Synthesizing insights (min_sources={min_sources}, min_confidence={min_confidence})")

        new_insights = []

        # Pattern 1: Cross-source concept validation
        #   Same concept appears in multiple independent sources
        for concept, item_ids in self.concept_graph.items():
            if len(item_ids) >= min_sources:
                insight = await self._synthesize_concept_insight(concept, item_ids)
                if insight and insight.confidence_score >= min_confidence:
                    new_insights.append(insight)

        # Pattern 2: Technique transfer across domains
        #   Same technique used in different contexts
        for technique, item_ids in self.technique_graph.items():
            if len(item_ids) >= min_sources:
                insight = await self._synthesize_technique_insight(technique, item_ids)
                if insight and insight.confidence_score >= min_confidence:
                    new_insights.append(insight)

        # Pattern 3: Concept-technique relationships
        #   Which techniques apply to which concepts
        relationship_insights = await self._synthesize_relationship_insights(min_sources)
        new_insights.extend([
            i for i in relationship_insights if i.confidence_score >= min_confidence
        ])

        # Store insights
        for insight in new_insights:
            self.synthesized_insights[insight.insight_id] = insight
            self._save_insight(insight)

        logger.info(f"Synthesized {len(new_insights)} new insights")
        return new_insights

    async def _synthesize_concept_insight(
        self,
        concept: str,
        item_ids: Set[str]
    ) -> Optional[SynthesizedInsight]:
        """Synthesize insight from cross-source concept validation."""

        items = [self.knowledge_items[item_id] for item_id in item_ids if item_id in self.knowledge_items]

        if len(items) < 2:
            return None

        # Analyze source diversity
        source_types = list(set(item.source_type for item in items))

        # Gather all insights mentioning this concept
        related_insights = []
        for item in items:
            related_insights.extend(item.insights)

        # Calculate confidence based on source agreement
        confidence = min(1.0, len(items) / 5.0)  # Max at 5 sources

        # Calculate novelty (how recently this concept emerged)
        avg_age_days = sum(
            (datetime.now() - datetime.fromisoformat(item.created_at)).days
            for item in items
        ) / len(items)
        novelty = max(0.0, 1.0 - (avg_age_days / 365.0))  # Newer = more novel

        insight_text = f"{concept.title()}: Validated across {len(items)} independent sources ({', '.join(s.value for s in source_types)}). {related_insights[0] if related_insights else 'Emerging concept.'}"

        insight = SynthesizedInsight(
            insight_id=hashlib.md5(f"concept_{concept}_{len(items)}".encode()).hexdigest()[:8],
            insight_text=insight_text,
            supporting_items=list(item_ids),
            source_types=source_types,
            connected_concepts=[concept],
            connected_techniques=[],
            confidence_score=confidence,
            novelty_score=novelty,
            created_at=datetime.now().isoformat(),
            tags=["cross-source-validation", "concept"]
        )

        return insight

    async def _synthesize_technique_insight(
        self,
        technique: str,
        item_ids: Set[str]
    ) -> Optional[SynthesizedInsight]:
        """Synthesize insight from technique transfer across domains."""

        items = [self.knowledge_items[item_id] for item_id in item_ids if item_id in self.knowledge_items]

        if len(items) < 2:
            return None

        # Analyze domain diversity (different concepts using same technique)
        all_concepts = set()
        for item in items:
            all_concepts.update(item.concepts)

        # Technique applicable to multiple domains = powerful technique
        confidence = min(1.0, len(all_concepts) / 10.0)  # Max at 10 concepts
        novelty = 0.7  # Techniques are generally novel if cross-domain

        insight_text = f"{technique.title()}: Applied across {len(all_concepts)} different domains including {', '.join(list(all_concepts)[:3])}. Versatile technique with broad applicability."

        insight = SynthesizedInsight(
            insight_id=hashlib.md5(f"technique_{technique}_{len(items)}".encode()).hexdigest()[:8],
            insight_text=insight_text,
            supporting_items=list(item_ids),
            source_types=list(set(item.source_type for item in items)),
            connected_concepts=list(all_concepts),
            connected_techniques=[technique],
            confidence_score=confidence,
            novelty_score=novelty,
            created_at=datetime.now().isoformat(),
            tags=["cross-domain-transfer", "technique"]
        )

        return insight

    async def _synthesize_relationship_insights(
        self,
        min_sources: int
    ) -> List[SynthesizedInsight]:
        """Synthesize insights about concept-technique relationships."""

        relationship_insights = []

        # Find concepts and techniques that appear together frequently
        concept_technique_pairs: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        for item in self.knowledge_items.values():
            for concept in item.concepts:
                for technique in item.techniques:
                    concept_technique_pairs[(concept.lower(), technique.lower())].add(item.item_id)

        # Generate insights for strong relationships
        for (concept, technique), item_ids in concept_technique_pairs.items():
            if len(item_ids) >= min_sources:
                items = [self.knowledge_items[item_id] for item_id in item_ids]

                confidence = min(1.0, len(item_ids) / 4.0)
                novelty = 0.6

                insight_text = f"{technique.title()} is particularly effective for {concept}: Confirmed in {len(item_ids)} independent sources."

                insight = SynthesizedInsight(
                    insight_id=hashlib.md5(f"relationship_{concept}_{technique}".encode()).hexdigest()[:8],
                    insight_text=insight_text,
                    supporting_items=list(item_ids),
                    source_types=list(set(item.source_type for item in items)),
                    connected_concepts=[concept],
                    connected_techniques=[technique],
                    confidence_score=confidence,
                    novelty_score=novelty,
                    created_at=datetime.now().isoformat(),
                    tags=["concept-technique-relationship"]
                )

                relationship_insights.append(insight)

        return relationship_insights

    def find_related_knowledge(
        self,
        concepts: List[str],
        techniques: List[str],
        limit: int = 10
    ) -> List[KnowledgeItem]:
        """Find knowledge items related to given concepts/techniques."""

        related_item_ids: Set[str] = set()

        # Find items by concepts
        for concept in concepts:
            related_item_ids.update(self.concept_graph.get(concept.lower(), set()))

        # Find items by techniques
        for technique in techniques:
            related_item_ids.update(self.technique_graph.get(technique.lower(), set()))

        # Get actual items and sort by relevance
        items = [
            self.knowledge_items[item_id]
            for item_id in related_item_ids
            if item_id in self.knowledge_items
        ]

        # Sort by confidence score
        items.sort(key=lambda item: item.confidence_score, reverse=True)

        return items[:limit]

    def get_synthesis_statistics(self) -> Dict[str, Any]:
        """Get statistics about synthesized knowledge."""

        return {
            "total_knowledge_items": len(self.knowledge_items),
            "total_insights": len(self.synthesized_insights),
            "unique_concepts": len(self.concept_graph),
            "unique_techniques": len(self.technique_graph),
            "source_breakdown": {
                source_type.value: sum(
                    1 for item in self.knowledge_items.values()
                    if item.source_type == source_type
                )
                for source_type in KnowledgeSource
            },
            "avg_confidence": sum(
                insight.confidence_score for insight in self.synthesized_insights.values()
            ) / len(self.synthesized_insights) if self.synthesized_insights else 0.0,
            "avg_novelty": sum(
                insight.novelty_score for insight in self.synthesized_insights.values()
            ) / len(self.synthesized_insights) if self.synthesized_insights else 0.0
        }

    def _save_knowledge_item(self, item: KnowledgeItem):
        """Save knowledge item to disk."""
        item_file = self.knowledge_dir / f"item_{item.item_id}.json"

        item_dict = asdict(item)
        item_dict["source_type"] = item.source_type.value

        with open(item_file, 'w') as f:
            json.dump(item_dict, f, indent=2)

    def _save_insight(self, insight: SynthesizedInsight):
        """Save synthesized insight to disk."""
        insight_file = self.knowledge_dir / f"insight_{insight.insight_id}.json"

        insight_dict = asdict(insight)
        insight_dict["source_types"] = [s.value for s in insight.source_types]

        with open(insight_file, 'w') as f:
            json.dump(insight_dict, f, indent=2)


async def main():
    """Example usage of Knowledge Synthesis Engine."""
    engine = KnowledgeSynthesisEngine()

    print("\n" + "=" * 70)
    print("KNOWLEDGE SYNTHESIS ENGINE DEMONSTRATION")
    print("=" * 70)
    print()

    # Add sample knowledge items from different sources
    print("1. Adding knowledge items from multiple sources...")

    # Research paper on meta-learning
    engine.add_knowledge_item(KnowledgeItem(
        item_id="paper_001",
        source_type=KnowledgeSource.RESEARCH_PAPER,
        source_id="arxiv:2024.12345",
        title="Meta-Learning for Few-Shot Classification",
        concepts=["meta-learning", "few-shot learning", "neural networks"],
        techniques=["gradient descent", "optimization", "transfer learning"],
        insights=["Meta-learning enables rapid adaptation with minimal data"],
        authors=["Smith et al."],
        created_at="2024-01-15T00:00:00",
        citations=150,
        confidence_score=0.9,
        related_items=[],
        tags=["AI", "machine-learning"]
    ))

    # Video on meta-learning
    engine.add_knowledge_item(KnowledgeItem(
        item_id="video_001",
        source_type=KnowledgeSource.VIDEO_TRANSCRIPT,
        source_id="youtube:abc123",
        title="Meta-Learning Explained",
        concepts=["meta-learning", "learning to learn"],
        techniques=["gradient descent", "neural architecture search"],
        insights=["Meta-learning outperforms traditional methods on new tasks"],
        authors=["Tech Talks"],
        created_at="2024-02-01T00:00:00",
        citations=0,
        confidence_score=0.7,
        related_items=[],
        tags=["tutorial", "AI"]
    ))

    # Code repository implementing meta-learning
    engine.add_knowledge_item(KnowledgeItem(
        item_id="code_001",
        source_type=KnowledgeSource.CODE_REPOSITORY,
        source_id="github:meta-learning-lib",
        title="Meta-Learning Library",
        concepts=["meta-learning", "few-shot learning"],
        techniques=["gradient descent", "MAML algorithm"],
        insights=["MAML achieves 95% accuracy on Omniglot benchmark"],
        authors=["OpenSource Contributors"],
        created_at="2024-03-01T00:00:00",
        citations=0,
        confidence_score=0.8,
        related_items=[],
        tags=["implementation", "python"]
    ))

    print(f"   Added {len(engine.knowledge_items)} knowledge items")
    print()

    # Synthesize insights
    print("2. Synthesizing insights from knowledge...")
    insights = await engine.synthesize_insights(min_sources=2, min_confidence=0.6)

    print(f"   Generated {len(insights)} synthesized insights:")
    for insight in insights:
        print(f"\n   Insight: {insight.insight_text}")
        print(f"   Confidence: {insight.confidence_score:.1%}, Novelty: {insight.novelty_score:.1%}")
        print(f"   Sources: {len(insight.supporting_items)} ({', '.join(s.value for s in insight.source_types)})")
        print(f"   Tags: {', '.join(insight.tags)}")

    print()

    # Get statistics
    print("3. Synthesis statistics:")
    stats = engine.get_synthesis_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     {k}: {v}")
        else:
            print(f"   {key}: {value}")

    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
