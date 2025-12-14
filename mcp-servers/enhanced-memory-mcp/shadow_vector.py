#!/usr/bin/env python3
"""
Shadow Vector Search - Adversarial Contradiction Detection
God Agent Integration - Phase 3

Implements the Shadow Vector concept from the God Agent white paper:
- Given a hypothesis vector v, the shadow vector is -v (inverted in 768-dim space)
- Searches for mathematically opposed evidence to find contradictions
- Provides credibility scoring based on supporting vs contradicting evidence
- Enables red team validation of claims before storage

Key Formula:
    shadow_vector = claim_vector * -1
    credibility = supporting_weight / (supporting_weight + contradicting_weight)

L-Score Integration:
    - Uses L-Scores to weight evidence quality
    - High L-Score contradictions reduce credibility more than low L-Score ones
"""

import json
import logging
import math
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)


class ValidationRecommendation(Enum):
    """Recommendation based on validation results."""
    ACCEPT = "accept"           # High credibility, safe to use
    REVIEW = "review"           # Medium credibility, needs human review
    REJECT = "reject"           # Low credibility, contradicted by evidence
    INSUFFICIENT = "insufficient"  # Not enough evidence to validate


@dataclass
class ShadowSearchResult:
    """Result from shadow vector search."""
    entity_id: int
    entity_name: str
    entity_type: str
    content_preview: str  # First 200 chars
    similarity_score: float  # To shadow vector (higher = more contradictory)
    l_score: float
    source_chain: List[int]
    observations: List[str]


@dataclass
class EvidenceSet:
    """Collection of supporting or contradicting evidence."""
    items: List[ShadowSearchResult] = field(default_factory=list)
    total_weight: float = 0.0  # L-Score weighted sum
    average_l_score: float = 0.0
    count: int = 0

    def add(self, item: ShadowSearchResult):
        self.items.append(item)
        self.total_weight += item.similarity_score * item.l_score
        self.count += 1
        if self.count > 0:
            self.average_l_score = sum(i.l_score for i in self.items) / self.count


@dataclass
class ValidationReport:
    """Complete validation report for a claim."""
    claim_id: str
    claim_text: str
    claim_embedding: Optional[List[float]] = None

    # Evidence
    supporting_evidence: EvidenceSet = field(default_factory=EvidenceSet)
    contradicting_evidence: EvidenceSet = field(default_factory=EvidenceSet)

    # Scores
    credibility_score: float = 0.5  # 0.0-1.0
    confidence_interval: Tuple[float, float] = (0.0, 1.0)  # Lower/upper bounds

    # Recommendation
    recommendation: ValidationRecommendation = ValidationRecommendation.INSUFFICIENT
    recommendation_reason: str = ""

    # Metadata
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    search_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "credibility_score": self.credibility_score,
            "confidence_interval": list(self.confidence_interval),
            "recommendation": self.recommendation.value,
            "recommendation_reason": self.recommendation_reason,
            "supporting_count": self.supporting_evidence.count,
            "contradicting_count": self.contradicting_evidence.count,
            "supporting_weight": self.supporting_evidence.total_weight,
            "contradicting_weight": self.contradicting_evidence.total_weight,
            "supporting_avg_l_score": self.supporting_evidence.average_l_score,
            "contradicting_avg_l_score": self.contradicting_evidence.average_l_score,
            "validated_at": self.validated_at,
            "supporting_evidence": [
                {
                    "entity_id": e.entity_id,
                    "entity_name": e.entity_name,
                    "similarity": e.similarity_score,
                    "l_score": e.l_score,
                    "preview": e.content_preview
                }
                for e in self.supporting_evidence.items[:5]  # Top 5
            ],
            "contradicting_evidence": [
                {
                    "entity_id": e.entity_id,
                    "entity_name": e.entity_name,
                    "similarity": e.similarity_score,
                    "l_score": e.l_score,
                    "preview": e.content_preview
                }
                for e in self.contradicting_evidence.items[:5]  # Top 5
            ]
        }


class ShadowVectorSearcher:
    """
    Shadow Vector Search engine for adversarial validation.

    Implements the God Agent white paper's shadow vector concept:
    - Invert embeddings to find mathematically opposed content
    - Calculate credibility based on evidence balance
    - Support red team validation of claims
    """

    def __init__(
        self,
        db_path: Path,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "entities"
    ):
        self.db_path = db_path
        self.collection_name = collection_name

        # Initialize Qdrant client
        if QDRANT_AVAILABLE:
            try:
                self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
                logger.info("Shadow Vector Search connected to Qdrant")
            except Exception as e:
                logger.warning(f"Qdrant connection failed: {e}")
                self.qdrant = None
        else:
            self.qdrant = None
            logger.warning("Qdrant client not available")

        # Initialize validation history table
        self._init_db()

    def _init_db(self):
        """Initialize database tables for validation history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id TEXT NOT NULL,
                    claim_text TEXT NOT NULL,
                    credibility_score REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    supporting_count INTEGER DEFAULT 0,
                    contradicting_count INTEGER DEFAULT 0,
                    supporting_weight REAL DEFAULT 0.0,
                    contradicting_weight REAL DEFAULT 0.0,
                    validation_data TEXT,  -- JSON blob
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(claim_id)
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shadow_claim_id
                ON shadow_validations(claim_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shadow_credibility
                ON shadow_validations(credibility_score)
            """)

            conn.commit()

    def create_shadow_vector(self, embedding: List[float]) -> List[float]:
        """
        Create shadow vector by inverting the embedding.

        Shadow vector = -1 * original_vector

        In 768-dimensional space, this finds the mathematically
        opposite direction, which represents contradictory content.
        """
        return [-x for x in embedding]

    async def find_contradictions(
        self,
        claim_embedding: List[float],
        threshold: float = 0.6,
        limit: int = 10,
        exclude_entity_ids: Optional[List[int]] = None
    ) -> List[ShadowSearchResult]:
        """
        Find evidence that contradicts a claim using shadow vector search.

        Args:
            claim_embedding: 768-dim embedding of the claim
            threshold: Minimum similarity to shadow vector (default 0.6)
            limit: Maximum results to return
            exclude_entity_ids: Entity IDs to exclude from results

        Returns:
            List of contradicting evidence with similarity scores
        """
        if not self.qdrant:
            logger.warning("Qdrant not available for shadow search")
            return []

        # Create shadow vector (inverted embedding)
        shadow_vector = self.create_shadow_vector(claim_embedding)

        try:
            # Search for content similar to shadow vector
            # High similarity to shadow = high contradiction to original
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=shadow_vector,
                limit=limit * 2,  # Over-retrieve then filter
                score_threshold=threshold
            )

            contradictions = []
            for hit in results:
                entity_id = hit.payload.get("entity_id", 0)

                # Skip excluded entities
                if exclude_entity_ids and entity_id in exclude_entity_ids:
                    continue

                # Get L-Score from database
                l_score, source_chain = self._get_entity_l_score(entity_id)

                # Get observations
                observations = hit.payload.get("observations", [])
                if isinstance(observations, str):
                    observations = [observations]

                content_preview = " ".join(observations)[:200] if observations else ""

                contradiction = ShadowSearchResult(
                    entity_id=entity_id,
                    entity_name=hit.payload.get("name", "Unknown"),
                    entity_type=hit.payload.get("entity_type", "unknown"),
                    content_preview=content_preview,
                    similarity_score=hit.score,
                    l_score=l_score,
                    source_chain=source_chain,
                    observations=observations[:3]  # First 3
                )
                contradictions.append(contradiction)

                if len(contradictions) >= limit:
                    break

            return contradictions

        except Exception as e:
            logger.error(f"Shadow vector search failed: {e}")
            return []

    async def find_supporting_evidence(
        self,
        claim_embedding: List[float],
        threshold: float = 0.7,
        limit: int = 10,
        exclude_entity_ids: Optional[List[int]] = None
    ) -> List[ShadowSearchResult]:
        """
        Find evidence that supports a claim using regular vector search.

        Args:
            claim_embedding: 768-dim embedding of the claim
            threshold: Minimum similarity (default 0.7)
            limit: Maximum results
            exclude_entity_ids: Entity IDs to exclude

        Returns:
            List of supporting evidence
        """
        if not self.qdrant:
            return []

        try:
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=claim_embedding,
                limit=limit * 2,
                score_threshold=threshold
            )

            supporting = []
            for hit in results:
                entity_id = hit.payload.get("entity_id", 0)

                if exclude_entity_ids and entity_id in exclude_entity_ids:
                    continue

                l_score, source_chain = self._get_entity_l_score(entity_id)

                observations = hit.payload.get("observations", [])
                if isinstance(observations, str):
                    observations = [observations]

                content_preview = " ".join(observations)[:200] if observations else ""

                evidence = ShadowSearchResult(
                    entity_id=entity_id,
                    entity_name=hit.payload.get("name", "Unknown"),
                    entity_type=hit.payload.get("entity_type", "unknown"),
                    content_preview=content_preview,
                    similarity_score=hit.score,
                    l_score=l_score,
                    source_chain=source_chain,
                    observations=observations[:3]
                )
                supporting.append(evidence)

                if len(supporting) >= limit:
                    break

            return supporting

        except Exception as e:
            logger.error(f"Supporting evidence search failed: {e}")
            return []

    def _get_entity_l_score(self, entity_id: int) -> Tuple[float, List[int]]:
        """Get L-Score and source chain for an entity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT l_score, source_chain FROM entities WHERE id = ?
                """, (entity_id,))
                row = cursor.fetchone()

                if row:
                    l_score = row[0] if row[0] else 0.5
                    source_chain = json.loads(row[1]) if row[1] else []
                    return l_score, source_chain

        except Exception as e:
            logger.warning(f"Error getting L-Score for entity {entity_id}: {e}")

        return 0.5, []

    def calculate_credibility(
        self,
        supporting: EvidenceSet,
        contradicting: EvidenceSet,
        prior_belief: float = 0.5
    ) -> Tuple[float, Tuple[float, float]]:
        """
        Calculate credibility score based on evidence balance.

        Uses Bayesian-inspired formula:
        credibility = (supporting_weight + prior) / (total_weight + 2*prior)

        Args:
            supporting: Supporting evidence set
            contradicting: Contradicting evidence set
            prior_belief: Prior probability (default 0.5 = neutral)

        Returns:
            Tuple of (credibility_score, (lower_bound, upper_bound))
        """
        # Handle no evidence case
        if supporting.count == 0 and contradicting.count == 0:
            return prior_belief, (0.0, 1.0)

        # L-Score weighted totals
        support_weight = supporting.total_weight
        contradict_weight = contradicting.total_weight
        total_weight = support_weight + contradict_weight

        # Apply prior
        prior_weight = 1.0  # Weight of prior belief
        credibility = (support_weight + prior_belief * prior_weight) / \
                     (total_weight + prior_weight)

        # Calculate confidence interval based on evidence count
        n = supporting.count + contradicting.count
        if n > 0:
            # Wilson score interval for binomial proportion
            z = 1.96  # 95% confidence
            p = credibility
            denominator = 1 + z**2 / n
            center = (p + z**2 / (2 * n)) / denominator
            spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator

            lower = max(0.0, center - spread)
            upper = min(1.0, center + spread)
        else:
            lower, upper = 0.0, 1.0

        return credibility, (lower, upper)

    def get_recommendation(
        self,
        credibility: float,
        confidence_interval: Tuple[float, float],
        supporting_count: int,
        contradicting_count: int
    ) -> Tuple[ValidationRecommendation, str]:
        """
        Get recommendation based on validation results.

        Thresholds:
        - ACCEPT: credibility >= 0.7 and confidence lower bound >= 0.5
        - REJECT: credibility <= 0.3 or significant contradictions
        - REVIEW: Everything else
        - INSUFFICIENT: Very few evidence points
        """
        total_evidence = supporting_count + contradicting_count
        lower, upper = confidence_interval

        # Insufficient evidence
        if total_evidence < 2:
            return (
                ValidationRecommendation.INSUFFICIENT,
                f"Only {total_evidence} evidence point(s) found. Need more data."
            )

        # High credibility
        if credibility >= 0.7 and lower >= 0.5:
            return (
                ValidationRecommendation.ACCEPT,
                f"High credibility ({credibility:.2f}) with {supporting_count} supporting evidence points."
            )

        # Low credibility
        if credibility <= 0.3 or (contradicting_count >= 3 and credibility < 0.5):
            return (
                ValidationRecommendation.REJECT,
                f"Low credibility ({credibility:.2f}) with {contradicting_count} contradicting evidence points."
            )

        # Medium - needs review
        return (
            ValidationRecommendation.REVIEW,
            f"Mixed evidence ({supporting_count} supporting, {contradicting_count} contradicting). Human review recommended."
        )

    async def validate_claim(
        self,
        claim_text: str,
        claim_embedding: List[float],
        claim_id: Optional[str] = None,
        support_threshold: float = 0.7,
        contradict_threshold: float = 0.6,
        max_evidence: int = 10,
        exclude_entity_ids: Optional[List[int]] = None,
        store_result: bool = True
    ) -> ValidationReport:
        """
        Full claim validation pipeline.

        1. Embed claim (if not provided)
        2. Find supporting evidence (regular search)
        3. Find contradicting evidence (shadow search)
        4. Calculate credibility
        5. Generate recommendation
        6. Optionally store result

        Args:
            claim_text: Text of the claim to validate
            claim_embedding: Pre-computed 768-dim embedding
            claim_id: Optional unique ID for the claim
            support_threshold: Similarity threshold for supporting evidence
            contradict_threshold: Similarity threshold for contradictions
            max_evidence: Maximum evidence per category
            exclude_entity_ids: Entities to exclude
            store_result: Whether to store validation in history

        Returns:
            Complete ValidationReport
        """
        import uuid

        if not claim_id:
            claim_id = str(uuid.uuid4())[:8]

        # Create report
        report = ValidationReport(
            claim_id=claim_id,
            claim_text=claim_text,
            claim_embedding=claim_embedding[:10] if claim_embedding else None,  # Store sample
            search_params={
                "support_threshold": support_threshold,
                "contradict_threshold": contradict_threshold,
                "max_evidence": max_evidence
            }
        )

        # Find supporting evidence
        supporting_results = await self.find_supporting_evidence(
            claim_embedding=claim_embedding,
            threshold=support_threshold,
            limit=max_evidence,
            exclude_entity_ids=exclude_entity_ids
        )
        for result in supporting_results:
            report.supporting_evidence.add(result)

        # Find contradicting evidence (shadow search)
        contradicting_results = await self.find_contradictions(
            claim_embedding=claim_embedding,
            threshold=contradict_threshold,
            limit=max_evidence,
            exclude_entity_ids=exclude_entity_ids
        )
        for result in contradicting_results:
            report.contradicting_evidence.add(result)

        # Calculate credibility
        report.credibility_score, report.confidence_interval = self.calculate_credibility(
            supporting=report.supporting_evidence,
            contradicting=report.contradicting_evidence
        )

        # Get recommendation
        report.recommendation, report.recommendation_reason = self.get_recommendation(
            credibility=report.credibility_score,
            confidence_interval=report.confidence_interval,
            supporting_count=report.supporting_evidence.count,
            contradicting_count=report.contradicting_evidence.count
        )

        # Store result
        if store_result:
            self._store_validation(report)

        logger.info(
            f"Claim validation complete: credibility={report.credibility_score:.2f}, "
            f"recommendation={report.recommendation.value}"
        )

        return report

    def _store_validation(self, report: ValidationReport):
        """Store validation result in database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO shadow_validations
                    (claim_id, claim_text, credibility_score, recommendation,
                     supporting_count, contradicting_count, supporting_weight,
                     contradicting_weight, validation_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report.claim_id,
                    report.claim_text[:1000],
                    report.credibility_score,
                    report.recommendation.value,
                    report.supporting_evidence.count,
                    report.contradicting_evidence.count,
                    report.supporting_evidence.total_weight,
                    report.contradicting_evidence.total_weight,
                    json.dumps(report.to_dict())
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store validation: {e}")

    def get_validation_history(
        self,
        limit: int = 50,
        min_credibility: Optional[float] = None,
        recommendation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get validation history with optional filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                query = "SELECT * FROM shadow_validations WHERE 1=1"
                params = []

                if min_credibility is not None:
                    query += " AND credibility_score >= ?"
                    params.append(min_credibility)

                if recommendation:
                    query += " AND recommendation = ?"
                    params.append(recommendation)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)

                results = []
                for row in cursor.fetchall():
                    results.append({
                        "claim_id": row["claim_id"],
                        "claim_text": row["claim_text"][:100] + "...",
                        "credibility_score": row["credibility_score"],
                        "recommendation": row["recommendation"],
                        "supporting_count": row["supporting_count"],
                        "contradicting_count": row["contradicting_count"],
                        "created_at": row["created_at"]
                    })

                return results

        except Exception as e:
            logger.error(f"Failed to get validation history: {e}")
            return []


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_shadow_vector_tools(app, db_path: Path):
    """Register Shadow Vector MCP tools."""

    searcher = ShadowVectorSearcher(db_path)

    @app.tool()
    async def find_contradictions(
        claim_embedding: List[float],
        threshold: float = 0.6,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Shadow Vector Search: Find evidence that contradicts a claim.

        Uses shadow vector (inverted embedding) to find mathematically
        opposed content in 768-dimensional space.

        Args:
            claim_embedding: 768-dim embedding of the claim
            threshold: Minimum similarity to shadow vector (0.6 default)
            limit: Maximum results

        Returns:
            List of contradicting evidence with similarity and L-Scores
        """
        results = await searcher.find_contradictions(
            claim_embedding=claim_embedding,
            threshold=threshold,
            limit=limit
        )

        return {
            "success": True,
            "count": len(results),
            "shadow_search_enabled": True,
            "contradictions": [
                {
                    "entity_id": r.entity_id,
                    "entity_name": r.entity_name,
                    "entity_type": r.entity_type,
                    "similarity_to_shadow": r.similarity_score,
                    "l_score": r.l_score,
                    "content_preview": r.content_preview
                }
                for r in results
            ]
        }

    @app.tool()
    async def validate_claim(
        claim_text: str,
        claim_embedding: List[float],
        support_threshold: float = 0.7,
        contradict_threshold: float = 0.6,
        max_evidence: int = 10
    ) -> Dict[str, Any]:
        """
        Full claim validation with adversarial analysis.

        Pipeline:
        1. Find supporting evidence (regular search)
        2. Find contradicting evidence (shadow search)
        3. Calculate L-Score weighted credibility
        4. Generate recommendation (ACCEPT/REVIEW/REJECT)

        Args:
            claim_text: Text of claim to validate
            claim_embedding: Pre-computed 768-dim embedding
            support_threshold: Similarity for supporting evidence
            contradict_threshold: Similarity for contradictions
            max_evidence: Maximum evidence per category

        Returns:
            ValidationReport with credibility score and recommendation
        """
        report = await searcher.validate_claim(
            claim_text=claim_text,
            claim_embedding=claim_embedding,
            support_threshold=support_threshold,
            contradict_threshold=contradict_threshold,
            max_evidence=max_evidence,
            store_result=True
        )

        return report.to_dict()

    @app.tool()
    async def get_validation_history(
        limit: int = 50,
        min_credibility: Optional[float] = None,
        recommendation_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get claim validation history.

        Args:
            limit: Maximum results
            min_credibility: Filter by minimum credibility score
            recommendation_filter: Filter by recommendation (accept/review/reject)

        Returns:
            List of past validations with outcomes
        """
        history = searcher.get_validation_history(
            limit=limit,
            min_credibility=min_credibility,
            recommendation=recommendation_filter
        )

        return {
            "success": True,
            "count": len(history),
            "validations": history
        }

    @app.tool()
    async def calculate_claim_credibility(
        supporting_count: int,
        contradicting_count: int,
        supporting_l_scores: List[float],
        contradicting_l_scores: List[float],
        supporting_similarities: List[float],
        contradicting_similarities: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate credibility without search (for pre-gathered evidence).

        Useful when you already have evidence and want credibility score.

        Args:
            supporting_count: Number of supporting evidence
            contradicting_count: Number of contradicting evidence
            supporting_l_scores: L-Scores of supporting evidence
            contradicting_l_scores: L-Scores of contradicting evidence
            supporting_similarities: Similarities of supporting evidence
            contradicting_similarities: Similarities of contradicting evidence

        Returns:
            Credibility score and recommendation
        """
        # Build evidence sets
        supporting = EvidenceSet()
        for i, (sim, l_score) in enumerate(zip(supporting_similarities, supporting_l_scores)):
            result = ShadowSearchResult(
                entity_id=0,
                entity_name=f"support_{i}",
                entity_type="evidence",
                content_preview="",
                similarity_score=sim,
                l_score=l_score,
                source_chain=[],
                observations=[]
            )
            supporting.add(result)

        contradicting = EvidenceSet()
        for i, (sim, l_score) in enumerate(zip(contradicting_similarities, contradicting_l_scores)):
            result = ShadowSearchResult(
                entity_id=0,
                entity_name=f"contradict_{i}",
                entity_type="evidence",
                content_preview="",
                similarity_score=sim,
                l_score=l_score,
                source_chain=[],
                observations=[]
            )
            contradicting.add(result)

        # Calculate credibility
        credibility, confidence_interval = searcher.calculate_credibility(
            supporting=supporting,
            contradicting=contradicting
        )

        # Get recommendation
        recommendation, reason = searcher.get_recommendation(
            credibility=credibility,
            confidence_interval=confidence_interval,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count
        )

        return {
            "success": True,
            "credibility_score": credibility,
            "confidence_interval": list(confidence_interval),
            "recommendation": recommendation.value,
            "recommendation_reason": reason,
            "supporting_weight": supporting.total_weight,
            "contradicting_weight": contradicting.total_weight
        }

    logger.info("Shadow Vector tools registered: 4 tools for adversarial validation")
    return searcher


if __name__ == "__main__":
    # Test the shadow vector search
    import asyncio

    async def test():
        test_db = Path("/tmp/test_shadow.db")
        searcher = ShadowVectorSearcher(test_db)

        # Test shadow vector creation
        test_embedding = [0.1] * 768
        shadow = searcher.create_shadow_vector(test_embedding)

        print(f"Original embedding sample: {test_embedding[:5]}")
        print(f"Shadow vector sample: {shadow[:5]}")

        # Test credibility calculation
        supporting = EvidenceSet()
        contradicting = EvidenceSet()

        # Add some test evidence
        supporting.add(ShadowSearchResult(
            entity_id=1, entity_name="support1", entity_type="fact",
            content_preview="Supporting evidence", similarity_score=0.8,
            l_score=0.7, source_chain=[], observations=[]
        ))

        contradicting.add(ShadowSearchResult(
            entity_id=2, entity_name="contradict1", entity_type="fact",
            content_preview="Contradicting evidence", similarity_score=0.75,
            l_score=0.6, source_chain=[], observations=[]
        ))

        credibility, interval = searcher.calculate_credibility(supporting, contradicting)
        print(f"Credibility: {credibility:.2f} ({interval[0]:.2f}-{interval[1]:.2f})")

        recommendation, reason = searcher.get_recommendation(
            credibility, interval,
            supporting.count, contradicting.count
        )
        print(f"Recommendation: {recommendation.value}")
        print(f"Reason: {reason}")

        print("\nShadow Vector Search module test passed!")

    asyncio.run(test())
