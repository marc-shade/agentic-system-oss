#!/usr/bin/env python3
"""
Anti-Hallucination System for AGI

Ported from ruvnet/agentic-flow TypeScript implementation.

Provides:
- ConfidenceScorer: Multi-component confidence scoring with citation validation
- ConfidenceMonitor: Real-time confidence monitoring with threshold enforcement
- CitationValidator: Source validation against trusted sources
- VerificationPipeline: Pre/post output verification with hallucination detection
- HallucinationDetector: Pattern-based and semantic hallucination detection

Components work together to prevent AI hallucinations:
1. Pre-output verification catches issues before generation
2. Real-time monitoring flags low-confidence segments
3. Post-output validation ensures factual accuracy
4. Citation validation verifies source reliability
"""

import re
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Set, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Type Definitions
# =============================================================================

class EvidenceLevel(str, Enum):
    """Evidence quality levels (A=highest, D=lowest)"""
    A = "A"  # Randomized controlled trials, meta-analyses
    B = "B"  # Controlled studies, good cohort studies
    C = "C"  # Case studies, expert opinion
    D = "D"  # Expert opinion without explicit evidence


class CitationType(str, Enum):
    """Types of citations"""
    PEER_REVIEWED = "peer-reviewed"
    CLINICAL_TRIAL = "clinical-trial"
    META_ANALYSIS = "meta-analysis"
    EXPERT_OPINION = "expert-opinion"
    GUIDELINE = "guideline"
    ACADEMIC_PAPER = "academic-paper"
    OFFICIAL_DOC = "official-doc"
    TECHNICAL_SPEC = "technical-spec"


class HallucinationType(str, Enum):
    """Types of hallucinations"""
    FACTUAL = "factual"
    CITATION = "citation"
    LOGICAL = "logical"
    TEMPORAL = "temporal"
    QUANTITATIVE = "quantitative"
    SEMANTIC = "semantic"


class Severity(str, Enum):
    """Severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueType(str, Enum):
    """Validation issue types"""
    LOW_CONFIDENCE = "low_confidence"
    MISSING_CITATION = "missing_citation"
    INCONSISTENCY = "inconsistency"
    HALLUCINATION = "hallucination"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Citation:
    """Citation reference"""
    id: str
    source: str
    title: str
    year: Optional[int] = None
    url: Optional[str] = None
    excerpt: Optional[str] = None
    citation_type: CitationType = CitationType.ACADEMIC_PAPER
    evidence_level: EvidenceLevel = EvidenceLevel.C
    relevance_score: float = 0.5
    verified: bool = False
    citation_count: int = 0
    impact_factor: Optional[float] = None
    doi: Optional[str] = None


@dataclass
class ValidationIssue:
    """Validation issue detected"""
    type: IssueType
    severity: Severity
    description: str
    suggestion: Optional[str] = None
    location: Optional[str] = None


@dataclass
class HallucinationDetection:
    """Detected hallucination"""
    type: HallucinationType
    severity: Severity
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ConfidenceMetadata:
    """Confidence calculation metadata"""
    source_count: int = 0
    peer_reviewed_sources: int = 0
    expert_opinions: int = 0
    conflicting_evidence: int = 0
    recency_score: float = 0.0
    sample_size: Optional[int] = None
    confidence_interval: Optional[Tuple[float, float]] = None


@dataclass
class ConfidenceScore:
    """Multi-component confidence score"""
    overall: float = 0.0
    statistical: float = 0.0
    citation_strength: float = 0.0
    source_agreement: float = 0.0
    expert_consensus: float = 0.0
    contradictions: List[str] = field(default_factory=list)
    metadata: ConfidenceMetadata = field(default_factory=ConfidenceMetadata)


@dataclass
class ConfidenceMetrics:
    """Confidence metrics by component"""
    overall: float = 0.0
    by_component: Dict[str, float] = field(default_factory=dict)
    uncertainty_factors: List[str] = field(default_factory=list)
    data_quality: float = 0.0
    model_agreement: Optional[float] = None


@dataclass
class ValidationResult:
    """Validation result"""
    is_valid: bool
    confidence: float
    issues: List[ValidationIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Verification pipeline result"""
    verified: bool
    confidence: ConfidenceScore
    hallucinations: List[HallucinationDetection] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_review: bool = False
    suggestions: List[str] = field(default_factory=list)
    timestamp_ms: int = 0


@dataclass
class ProviderReview:
    """Human review record"""
    reviewer_id: str
    approved: bool
    corrections: List[str] = field(default_factory=list)
    feedback: str = ""
    timestamp: int = 0


# =============================================================================
# ConfidenceScorer
# =============================================================================

class ConfidenceScorer:
    """
    Statistical confidence metrics, citation strength, and evidence validation.

    Calculates multi-component confidence scores based on:
    - Statistical significance of evidence
    - Citation quality and impact
    - Source agreement levels
    - Expert consensus
    - Contradiction detection
    """

    MIN_CONFIDENCE_THRESHOLD = 0.7

    CITATION_WEIGHTS = {
        CitationType.PEER_REVIEWED: 1.0,
        CitationType.CLINICAL_TRIAL: 1.2,
        CitationType.META_ANALYSIS: 1.5,
        CitationType.EXPERT_OPINION: 0.7,
        CitationType.GUIDELINE: 1.3,
        CitationType.ACADEMIC_PAPER: 1.0,
        CitationType.OFFICIAL_DOC: 1.1,
        CitationType.TECHNICAL_SPEC: 0.9,
    }

    EVIDENCE_WEIGHTS = {
        EvidenceLevel.A: 1.0,
        EvidenceLevel.B: 0.8,
        EvidenceLevel.C: 0.6,
        EvidenceLevel.D: 0.4,
    }

    def __init__(self):
        self.current_year = datetime.now().year

    async def calculate_confidence(
        self,
        claim: str,
        citations: List[Citation],
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceScore:
        """Calculate overall confidence score for a claim."""
        statistical = self._calculate_statistical_confidence(citations, context)
        citation_strength = self._calculate_citation_strength(citations)
        source_agreement = self._calculate_source_agreement(citations)
        expert_consensus = self._calculate_expert_consensus(citations)
        contradictions = await self._detect_contradictions(claim, citations)

        overall = self._calculate_overall_score(
            statistical,
            citation_strength,
            source_agreement,
            expert_consensus,
            len(contradictions)
        )

        return ConfidenceScore(
            overall=overall,
            statistical=statistical,
            citation_strength=citation_strength,
            source_agreement=source_agreement,
            expert_consensus=expert_consensus,
            contradictions=contradictions,
            metadata=self._build_metadata(citations, context)
        )

    def _calculate_statistical_confidence(
        self,
        citations: List[Citation],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate statistical confidence based on evidence quality."""
        if not citations:
            return 0.0

        # Quality score based on evidence levels
        quality_score = sum(
            self.EVIDENCE_WEIGHTS.get(c.evidence_level, 0.5)
            for c in citations
        ) / len(citations)

        # Recency score (newer studies weighted higher)
        recency_score = sum(
            max(0, 1 - ((self.current_year - (c.year or self.current_year)) / 10))
            for c in citations
        ) / len(citations)

        # Sample size score if provided
        sample_size_score = 0.5
        if context and context.get("sample_size"):
            import math
            sample_size_score = min(1.0, math.log10(context["sample_size"]) / 4)

        return quality_score * 0.5 + recency_score * 0.3 + sample_size_score * 0.2

    def _calculate_citation_strength(self, citations: List[Citation]) -> float:
        """Calculate citation strength based on quality and impact."""
        if not citations:
            return 0.0

        import math

        total_score = 0.0
        for citation in citations:
            type_weight = self.CITATION_WEIGHTS.get(citation.citation_type, 0.8)

            # Impact factor contribution (normalize around 10)
            impact_score = (
                min(1.0, citation.impact_factor / 10)
                if citation.impact_factor else 0.5
            )

            # Citation count contribution (log scale)
            citation_score = min(1.0, math.log10(citation.citation_count + 1) / 4)

            total_score += type_weight * (impact_score * 0.5 + citation_score * 0.5)

        return min(1.0, total_score / len(citations))

    def _calculate_source_agreement(self, citations: List[Citation]) -> float:
        """Calculate source agreement level."""
        if len(citations) < 2:
            return 0.5  # Insufficient data

        # Count citations by evidence level
        evidence_counts: Dict[EvidenceLevel, int] = {}
        for citation in citations:
            level = citation.evidence_level
            evidence_counts[level] = evidence_counts.get(level, 0) + 1

        # High agreement if most are Level A or B
        high_quality = evidence_counts.get(EvidenceLevel.A, 0) + evidence_counts.get(EvidenceLevel.B, 0)
        return high_quality / len(citations)

    def _calculate_expert_consensus(self, citations: List[Citation]) -> float:
        """Calculate expert consensus level."""
        if not citations:
            return 0.0

        # Guidelines and meta-analyses indicate strong consensus
        consensus_sources = [
            c for c in citations
            if c.citation_type in (CitationType.GUIDELINE, CitationType.META_ANALYSIS)
        ]

        if not consensus_sources:
            return 0.0

        consensus_ratio = len(consensus_sources) / len(citations)

        # Weight by evidence quality
        quality_weight = sum(
            self.EVIDENCE_WEIGHTS.get(c.evidence_level, 0.5)
            for c in consensus_sources
        ) / len(consensus_sources)

        return consensus_ratio * quality_weight

    async def _detect_contradictions(
        self,
        claim: str,
        citations: List[Citation]
    ) -> List[str]:
        """Detect contradictions in citations and claims."""
        contradictions = []

        # Check for conflicting evidence levels
        has_high_quality = any(c.evidence_level == EvidenceLevel.A for c in citations)
        has_low_quality = any(c.evidence_level == EvidenceLevel.D for c in citations)

        if has_high_quality and has_low_quality:
            contradictions.append("Mixed evidence quality detected (Level A and D present)")

        # Check for temporal contradictions
        old_studies = [c for c in citations if c.year and self.current_year - c.year > 10]
        new_studies = [c for c in citations if c.year and self.current_year - c.year <= 5]

        if old_studies and new_studies:
            contradictions.append("Temporal evidence gap detected (10+ year span)")

        # Check for citation type conflicts
        has_guideline = any(c.citation_type == CitationType.GUIDELINE for c in citations)
        has_expert_opinion = any(c.citation_type == CitationType.EXPERT_OPINION for c in citations)
        has_clinical_trial = any(c.citation_type == CitationType.CLINICAL_TRIAL for c in citations)

        if has_guideline and has_expert_opinion and not has_clinical_trial:
            contradictions.append("Guidelines present without supporting trials")

        return contradictions

    def _calculate_overall_score(
        self,
        statistical: float,
        citation_strength: float,
        source_agreement: float,
        expert_consensus: float,
        contradiction_count: int
    ) -> float:
        """Calculate overall weighted confidence score."""
        base_score = (
            statistical * 0.3 +
            citation_strength * 0.25 +
            source_agreement * 0.25 +
            expert_consensus * 0.2
        )

        # Penalty for contradictions (5% per contradiction)
        contradiction_penalty = min(0.3, contradiction_count * 0.05)

        return max(0.0, base_score - contradiction_penalty)

    def _build_metadata(
        self,
        citations: List[Citation],
        context: Optional[Dict[str, Any]] = None
    ) -> ConfidenceMetadata:
        """Build confidence metadata."""
        return ConfidenceMetadata(
            source_count=len(citations),
            peer_reviewed_sources=len([c for c in citations if c.citation_type == CitationType.PEER_REVIEWED]),
            expert_opinions=len([c for c in citations if c.citation_type == CitationType.EXPERT_OPINION]),
            conflicting_evidence=len([c for c in citations if c.evidence_level == EvidenceLevel.D]),
            recency_score=sum(
                max(0, 1 - ((self.current_year - (c.year or self.current_year)) / 10))
                for c in citations
            ) / max(1, len(citations)),
            sample_size=context.get("sample_size") if context else None,
            confidence_interval=context.get("confidence_interval") if context else None,
        )

    def is_confident(self, score: ConfidenceScore) -> bool:
        """Check if confidence meets threshold."""
        return score.overall >= self.MIN_CONFIDENCE_THRESHOLD

    def get_confidence_level(self, score: float) -> str:
        """Get confidence level description."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        return "very-low"


# =============================================================================
# ConfidenceMonitor
# =============================================================================

class ConfidenceMonitor:
    """
    Real-time Confidence Monitoring.
    Continuously monitors analysis confidence and flags low-confidence outputs.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.8,
        critical_threshold: float = 0.6
    ):
        self.confidence_threshold = confidence_threshold
        self.critical_threshold = critical_threshold

    def monitor_confidence(self, analysis: Dict[str, Any]) -> ConfidenceMetrics:
        """Monitor confidence levels in real-time."""
        overall = analysis.get("confidence", 0.5)

        metrics = ConfidenceMetrics(
            overall=overall,
            by_component={
                "claims": self._calculate_claims_confidence(analysis),
                "evidence": self._calculate_evidence_confidence(analysis),
                "reasoning": self._calculate_reasoning_confidence(analysis),
            },
            uncertainty_factors=self._identify_uncertainty_factors(analysis),
            data_quality=self._assess_data_quality(analysis),
        )

        # Check for agreement across multiple sources
        metrics.model_agreement = self._check_model_agreement(analysis)

        return metrics

    def validate_confidence(self, metrics: ConfidenceMetrics) -> List[ValidationIssue]:
        """Validate confidence levels and flag issues."""
        issues = []

        # Check overall confidence
        if metrics.overall < self.critical_threshold:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE,
                severity=Severity.CRITICAL,
                description=f"Overall confidence ({metrics.overall:.2f}) is critically low",
                suggestion="Require immediate review before acting on analysis"
            ))
        elif metrics.overall < self.confidence_threshold:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE,
                severity=Severity.WARNING,
                description=f"Overall confidence ({metrics.overall:.2f}) is below threshold",
                suggestion="Consider additional verification or consultation"
            ))

        # Check component-specific confidence
        for component, confidence in metrics.by_component.items():
            if confidence < self.confidence_threshold:
                issues.append(ValidationIssue(
                    type=IssueType.LOW_CONFIDENCE,
                    severity=Severity.WARNING,
                    description=f"{component} confidence ({confidence:.2f}) is low",
                    suggestion=f"Review {component} analysis with additional sources"
                ))

        # Check data quality
        if metrics.data_quality < 0.7:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.ERROR,
                description=f"Data quality ({metrics.data_quality:.2f}) is insufficient",
                suggestion="Gather more reliable data before proceeding"
            ))

        # Check model agreement
        if metrics.model_agreement is not None and metrics.model_agreement < 0.6:
            issues.append(ValidationIssue(
                type=IssueType.INCONSISTENCY,
                severity=Severity.WARNING,
                description=f"Low model agreement ({metrics.model_agreement:.2f})",
                suggestion="Multiple sources disagree; seek expert consensus"
            ))

        # Flag uncertainty factors
        if len(metrics.uncertainty_factors) > 3:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE,
                severity=Severity.INFO,
                description=f"Multiple uncertainty factors: {', '.join(metrics.uncertainty_factors)}",
                suggestion="Address uncertainty factors to improve confidence"
            ))

        return issues

    def _calculate_claims_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in claims."""
        claims = analysis.get("claims", [])
        if not claims:
            return 0.5

        avg_confidence = sum(
            c.get("confidence", 0.5) for c in claims
        ) / len(claims)

        # Penalize if too many unverified claims
        verified_ratio = sum(1 for c in claims if c.get("verified")) / len(claims)

        return avg_confidence * (0.7 + 0.3 * verified_ratio)

    def _calculate_evidence_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in evidence."""
        citations = analysis.get("citations", [])
        if not citations:
            return 0.3

        # Check citation quality
        has_verified = any(c.get("verified") for c in citations)
        has_peer_reviewed = any(c.get("source_type") == "peer_reviewed" for c in citations)

        confidence = 0.5
        if has_verified:
            confidence += 0.25
        if has_peer_reviewed:
            confidence += 0.25

        return min(1.0, confidence)

    def _calculate_reasoning_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in reasoning chain."""
        reasoning = analysis.get("reasoning", "")

        # Simple heuristic based on reasoning presence and length
        if not reasoning:
            return 0.3

        # More reasoning generally indicates more thought
        confidence = min(1.0, 0.5 + len(reasoning) / 1000)

        return confidence

    def _identify_uncertainty_factors(self, analysis: Dict[str, Any]) -> List[str]:
        """Identify factors contributing to uncertainty."""
        factors = []

        claims = analysis.get("claims", [])
        citations = analysis.get("citations", [])

        if len(claims) > 5:
            factors.append("Multiple claims to verify")

        if len(citations) < 2:
            factors.append("Limited supporting evidence")

        if any(not c.get("verified") for c in citations):
            factors.append("Unverified citations")

        if analysis.get("confidence", 1.0) < 0.8:
            factors.append("Low model confidence")

        if analysis.get("has_contradictions"):
            factors.append("Detected contradictions")

        return factors

    def _assess_data_quality(self, analysis: Dict[str, Any]) -> float:
        """Assess overall data quality."""
        citations = analysis.get("citations", [])

        score = 0.5

        if len(citations) >= 3:
            score += 0.2
        if all(c.get("verified") for c in citations):
            score += 0.15
        if any(c.get("source_type") == "clinical_guideline" for c in citations):
            score += 0.1
        if all(c.get("relevance_score", 0) > 0.7 for c in citations):
            score += 0.05

        return min(1.0, score)

    def _check_model_agreement(self, analysis: Dict[str, Any]) -> float:
        """Check agreement across multiple models/sources."""
        citations = analysis.get("citations", [])

        if not citations:
            return 0.5

        # Use citation consensus as proxy
        consensus_citations = [
            c for c in citations
            if c.get("relevance_score", 0) > 0.8
        ]

        return min(1.0, len(consensus_citations) / 3)


# =============================================================================
# CitationValidator
# =============================================================================

class CitationValidator:
    """
    Citation Validation.
    Validates citations against trusted sources.
    """

    def __init__(self):
        # Trusted sources (extensible)
        self.trusted_sources: Set[str] = {
            # Academic
            "PubMed", "Cochrane Library", "arXiv", "IEEE", "ACM",
            "Nature", "Science", "Cell", "PNAS",
            # Medical
            "NICE Guidelines", "UpToDate", "New England Journal of Medicine",
            "The Lancet", "JAMA", "BMJ", "Mayo Clinic", "CDC", "WHO", "FDA",
            # Technical
            "GitHub", "Stack Overflow", "MDN", "W3C",
            "Python Documentation", "TypeScript Handbook",
            # General
            "Wikipedia", "Britannica", "Reuters", "Associated Press",
        }

        # Minimum acceptable year (last 10 years)
        self.minimum_year = datetime.now().year - 10

    def add_trusted_source(self, source: str):
        """Add a trusted source."""
        self.trusted_sources.add(source)

    def validate_citation(self, citation: Citation) -> ValidationResult:
        """Validate a single citation."""
        issues = []

        # Check source trustworthiness
        if not self._is_trusted_source(citation.source):
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.WARNING,
                description=f'Source "{citation.source}" is not in trusted sources list',
                suggestion="Verify citation from trusted databases"
            ))

        # Check citation age
        if citation.year and citation.year < self.minimum_year:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.INFO,
                description=f"Citation is from {citation.year}, may be outdated",
                suggestion="Consider more recent sources for current best practices"
            ))

        # Check for required fields
        if not citation.url and not citation.excerpt:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.ERROR,
                description="Citation lacks both URL and excerpt",
                suggestion="Provide URL or excerpt for verification"
            ))

        # Check relevance score
        if citation.relevance_score < 0.7:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE,
                severity=Severity.WARNING,
                description=f"Low relevance score ({citation.relevance_score:.2f})",
                suggestion="Find more relevant citations to support claims"
            ))

        # Check verification status
        if not citation.verified:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.ERROR,
                description="Citation has not been verified",
                suggestion="Verify citation against original source"
            ))

        is_valid = all(issue.severity not in (Severity.ERROR, Severity.CRITICAL) for issue in issues)
        confidence = self._calculate_citation_confidence(citation, issues)

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            recommendations=self._generate_recommendations(issues)
        )

    def validate_citations(self, citations: List[Citation]) -> ValidationResult:
        """Validate multiple citations for consistency."""
        issues = []

        # Check minimum citation count
        if len(citations) < 2:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.ERROR,
                description="Insufficient citations (minimum 2 required)",
                suggestion="Add more citations from trusted sources"
            ))

        # Check for citation diversity
        unique_sources = set(c.source for c in citations)
        if len(unique_sources) < min(2, len(citations)):
            issues.append(ValidationIssue(
                type=IssueType.INCONSISTENCY,
                severity=Severity.WARNING,
                description="Citations lack source diversity",
                suggestion="Include citations from multiple independent sources"
            ))

        # Check verification rate
        verified_count = sum(1 for c in citations if c.verified)
        if verified_count < len(citations) * 0.8:
            issues.append(ValidationIssue(
                type=IssueType.MISSING_CITATION,
                severity=Severity.ERROR,
                description=f"Only {verified_count}/{len(citations)} citations verified",
                suggestion="Verify all citations before use"
            ))

        # Check average relevance
        avg_relevance = sum(c.relevance_score for c in citations) / max(1, len(citations))
        if avg_relevance < 0.75:
            issues.append(ValidationIssue(
                type=IssueType.LOW_CONFIDENCE,
                severity=Severity.WARNING,
                description=f"Average relevance score ({avg_relevance:.2f}) is low",
                suggestion="Find more relevant citations"
            ))

        # Validate each citation individually
        for citation in citations:
            result = self.validate_citation(citation)
            issues.extend(result.issues)

        is_valid = all(issue.severity not in (Severity.ERROR, Severity.CRITICAL) for issue in issues)
        confidence = self._calculate_overall_confidence(citations, issues)

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            recommendations=self._generate_recommendations(issues)
        )

    async def verify_citation_source(self, citation: Citation) -> bool:
        """Verify citation against source (simplified)."""
        # In production, this would fetch and verify against original source
        is_verified = (
            self._is_trusted_source(citation.source) and
            citation.relevance_score > 0.7 and
            (not citation.year or citation.year >= self.minimum_year)
        )
        return is_verified

    def _is_trusted_source(self, source: str) -> bool:
        """Check if source is trusted."""
        source_lower = source.lower()
        return any(
            trusted.lower() in source_lower
            for trusted in self.trusted_sources
        )

    def _calculate_citation_confidence(
        self,
        citation: Citation,
        issues: List[ValidationIssue]
    ) -> float:
        """Calculate citation confidence."""
        confidence = 1.0

        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                confidence -= 0.4
            elif issue.severity == Severity.ERROR:
                confidence -= 0.2
            elif issue.severity == Severity.WARNING:
                confidence -= 0.1
            elif issue.severity == Severity.INFO:
                confidence -= 0.05

        # Boost for trusted source
        if self._is_trusted_source(citation.source):
            confidence += 0.1

        # Boost for verification
        if citation.verified:
            confidence += 0.1

        return max(0.0, min(1.0, confidence))

    def _calculate_overall_confidence(
        self,
        citations: List[Citation],
        issues: List[ValidationIssue]
    ) -> float:
        """Calculate overall confidence across citations."""
        if not citations:
            return 0.0

        avg_citation_score = sum(c.relevance_score for c in citations) / len(citations)
        verification_rate = sum(1 for c in citations if c.verified) / len(citations)

        confidence = (avg_citation_score + verification_rate) / 2

        # Penalize for critical/error issues
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        error_count = sum(1 for i in issues if i.severity == Severity.ERROR)

        confidence -= critical_count * 0.3
        confidence -= error_count * 0.15

        return max(0.0, min(1.0, confidence))

    def _generate_recommendations(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate recommendations based on issues."""
        recommendations = set()

        for issue in issues:
            if issue.suggestion:
                recommendations.add(issue.suggestion)

        # Add general recommendations
        if any(i.type == IssueType.MISSING_CITATION for i in issues):
            recommendations.add("Add citations from peer-reviewed literature")

        if any(i.type == IssueType.LOW_CONFIDENCE for i in issues):
            recommendations.add("Seek additional supporting evidence")

        return list(recommendations)


# =============================================================================
# VerificationPipeline
# =============================================================================

class VerificationPipeline:
    """
    Verification Pipeline.
    Pre-output verification, real-time hallucination detection, post-output validation.
    """

    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()
        self.hallucination_patterns: Dict[str, re.Pattern] = {}
        self.provider_reviews: Dict[str, List[ProviderReview]] = {}
        self._initialize_hallucination_patterns()

    def _initialize_hallucination_patterns(self):
        """Initialize common hallucination patterns."""
        # Overly confident language
        self.hallucination_patterns["overconfident"] = re.compile(
            r"\b(always|never|absolutely|definitely|certainly|guaranteed|100%|impossible)\b",
            re.IGNORECASE
        )

        # Unsupported quantitative claims
        self.hallucination_patterns["unsupported-numbers"] = re.compile(
            r"\b(\d+%|\d+\s*times?\s*(more|less|better|worse))\b",
            re.IGNORECASE
        )

        # Temporal hallucinations
        self.hallucination_patterns["temporal-vague"] = re.compile(
            r"\b(recent studies|latest research|modern research|new findings)\b",
            re.IGNORECASE
        )

        # Absolute claims without support
        self.hallucination_patterns["unsupported-absolute"] = re.compile(
            r"\b(cures?|eliminates?|completely|permanently fixes?|proven fact)\b",
            re.IGNORECASE
        )

        # Fabricated entities
        self.hallucination_patterns["fabricated"] = re.compile(
            r"\b(according to experts|studies show|research proves|scientists agree)\b",
            re.IGNORECASE
        )

    async def pre_output_verification(
        self,
        claim: str,
        citations: Optional[List[Citation]] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Pre-output verification - check before generating output."""
        import time
        start_time = time.time()

        warnings = []
        hallucinations = []

        # Step 1: Check citation availability
        if not citations:
            warnings.append("No citations provided - confidence will be limited")
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.CITATION,
                severity=Severity.MEDIUM,
                description="Claim made without supporting citations",
                suggestion="Provide sources to support this claim"
            ))

        # Step 2: Pattern-based hallucination detection
        pattern_hallucinations = self._detect_pattern_hallucinations(claim)
        hallucinations.extend(pattern_hallucinations)

        # Step 3: Calculate confidence
        confidence = await self.confidence_scorer.calculate_confidence(
            claim,
            citations or [],
            context
        )

        # Step 4: Determine if verification passed
        verified = (
            self.confidence_scorer.is_confident(confidence) and
            not any(h.severity == Severity.CRITICAL for h in hallucinations)
        )

        # Step 5: Determine if review required
        requires_review = (
            not verified or
            (metadata and metadata.get("requires_review")) or
            any(h.severity in (Severity.HIGH, Severity.CRITICAL) for h in hallucinations)
        )

        return VerificationResult(
            verified=verified,
            confidence=confidence,
            hallucinations=hallucinations,
            warnings=warnings,
            requires_review=requires_review,
            suggestions=self._generate_suggestions(confidence, hallucinations),
            timestamp_ms=int((time.time() - start_time) * 1000)
        )

    async def detect_hallucinations(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[HallucinationDetection]:
        """Real-time hallucination detection."""
        hallucinations = []

        # Pattern-based detection
        hallucinations.extend(self._detect_pattern_hallucinations(text))

        # Logical consistency checks
        hallucinations.extend(self._detect_logical_inconsistencies(text))

        # Quantitative claim validation
        hallucinations.extend(self._detect_quantitative_hallucinations(text))

        # Temporal accuracy checks
        hallucinations.extend(self._detect_temporal_hallucinations(text))

        return hallucinations

    def _detect_pattern_hallucinations(self, text: str) -> List[HallucinationDetection]:
        """Pattern-based hallucination detection."""
        hallucinations = []

        # Check overconfident language
        overconfident_matches = self.hallucination_patterns["overconfident"].findall(text)
        if len(overconfident_matches) > 2:
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.FACTUAL,
                severity=Severity.MEDIUM,
                description="Overconfident language detected (always/never/guaranteed)",
                suggestion="Use more measured language with appropriate qualifiers"
            ))

        # Check unsupported quantitative claims
        if self.hallucination_patterns["unsupported-numbers"].search(text):
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.QUANTITATIVE,
                severity=Severity.HIGH,
                description="Quantitative claims detected without citations",
                suggestion="Provide sources for statistical claims"
            ))

        # Check temporal vagueness
        if self.hallucination_patterns["temporal-vague"].search(text):
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.TEMPORAL,
                severity=Severity.LOW,
                description="Vague temporal references (recent studies, latest research)",
                suggestion="Specify exact years and studies"
            ))

        # Check unsupported absolute claims
        if self.hallucination_patterns["unsupported-absolute"].search(text):
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.FACTUAL,
                severity=Severity.CRITICAL,
                description="Absolute claims detected (cures, eliminates, completely)",
                suggestion="Use evidence-based language and provide citations"
            ))

        # Check fabricated entities
        if self.hallucination_patterns["fabricated"].search(text):
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.CITATION,
                severity=Severity.MEDIUM,
                description="Vague authority references (according to experts, studies show)",
                suggestion="Name specific sources and studies"
            ))

        return hallucinations

    def _detect_logical_inconsistencies(self, text: str) -> List[HallucinationDetection]:
        """Detect logical inconsistencies."""
        hallucinations = []

        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

        negation_words = ["not", "no", "never", "none", "neither", "nor"]
        has_positive = any(
            not any(n in s.lower().split() for n in negation_words)
            for s in sentences
        )
        has_negative = any(
            any(n in s.lower().split() for n in negation_words)
            for s in sentences
        )

        if has_positive and has_negative and len(sentences) < 5:
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.LOGICAL,
                severity=Severity.MEDIUM,
                description="Potential logical contradiction detected",
                suggestion="Review for internal consistency"
            ))

        return hallucinations

    def _detect_quantitative_hallucinations(self, text: str) -> List[HallucinationDetection]:
        """Detect quantitative hallucinations."""
        hallucinations = []

        # Check for percentages over 100%
        percentage_matches = re.findall(r'(\d+)%', text)
        for match in percentage_matches:
            value = int(match)
            if value > 100:
                hallucinations.append(HallucinationDetection(
                    type=HallucinationType.QUANTITATIVE,
                    severity=Severity.CRITICAL,
                    description=f"Invalid percentage: {value}%",
                    suggestion="Percentages cannot exceed 100%"
                ))

        # Check for suspiciously precise numbers
        precise_matches = re.findall(r'\b(\d+\.\d{3,})\b', text)
        if precise_matches:
            hallucinations.append(HallucinationDetection(
                type=HallucinationType.QUANTITATIVE,
                severity=Severity.LOW,
                description="Suspiciously precise numbers detected",
                suggestion="Round to appropriate precision with confidence intervals"
            ))

        return hallucinations

    def _detect_temporal_hallucinations(self, text: str) -> List[HallucinationDetection]:
        """Detect temporal hallucinations."""
        hallucinations = []
        current_year = datetime.now().year

        # Check for future dates
        year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        for year_str in year_matches:
            year = int(year_str)
            if year > current_year:
                hallucinations.append(HallucinationDetection(
                    type=HallucinationType.TEMPORAL,
                    severity=Severity.CRITICAL,
                    description=f"Future date referenced: {year}",
                    suggestion="Cannot cite sources from the future"
                ))

        return hallucinations

    async def post_output_validation(
        self,
        output: str,
        original_claim: str,
        citations: Optional[List[Citation]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> VerificationResult:
        """Post-output validation."""
        result = await self.pre_output_verification(output, citations, context)

        # Add additional post-output checks
        if result.verified:
            fidelity = self._check_output_fidelity(original_claim, output)
            if not fidelity["faithful"]:
                result.warnings.append(fidelity["reason"])
                result.requires_review = True

        return result

    def _check_output_fidelity(
        self,
        input_text: str,
        output_text: str
    ) -> Dict[str, Any]:
        """Check if output is faithful to input."""
        # Check length inflation
        if len(output_text) > len(input_text) * 3:
            return {
                "faithful": False,
                "reason": "Output significantly longer than input - potential elaboration beyond evidence"
            }

        # Check for added quantitative claims
        input_numbers = len(re.findall(r'\d+', input_text))
        output_numbers = len(re.findall(r'\d+', output_text))

        if output_numbers > input_numbers * 2:
            return {
                "faithful": False,
                "reason": "Output contains many more numbers than input - potential quantitative hallucination"
            }

        return {"faithful": True, "reason": ""}

    async def add_provider_review(self, claim_id: str, review: ProviderReview):
        """Integrate provider review."""
        if claim_id not in self.provider_reviews:
            self.provider_reviews[claim_id] = []
        self.provider_reviews[claim_id].append(review)

    def get_provider_reviews(self, claim_id: str) -> List[ProviderReview]:
        """Get provider reviews for a claim."""
        return self.provider_reviews.get(claim_id, [])

    def _generate_suggestions(
        self,
        confidence: ConfidenceScore,
        hallucinations: List[HallucinationDetection]
    ) -> List[str]:
        """Generate suggestions for improvement."""
        suggestions = []

        if confidence.citation_strength < 0.6:
            suggestions.append("Add more high-quality sources")

        if confidence.source_agreement < 0.7:
            suggestions.append("Ensure consensus across multiple sources")

        if confidence.expert_consensus < 0.5:
            suggestions.append("Include guidelines or meta-analyses")

        if hallucinations:
            suggestions.append("Address detected hallucinations and unsupported claims")

        if confidence.contradictions:
            suggestions.append("Resolve contradictions in evidence base")

        return suggestions


# =============================================================================
# MCP Tool Registration
# =============================================================================

def register_anti_hallucination_tools(app) -> VerificationPipeline:
    """Register Anti-Hallucination MCP tools."""
    pipeline = VerificationPipeline()
    citation_validator = CitationValidator()
    confidence_monitor = ConfidenceMonitor()

    @app.tool()
    async def verify_claim(
        claim: str,
        citations: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify a claim for hallucinations and calculate confidence.

        Args:
            claim: The claim to verify
            citations: Optional list of supporting citations
            context: Optional context for verification

        Returns:
            Verification result with confidence score and detected issues
        """
        # Convert dict citations to Citation objects
        citation_objects = []
        if citations:
            for c in citations:
                citation_objects.append(Citation(
                    id=c.get("id", ""),
                    source=c.get("source", ""),
                    title=c.get("title", ""),
                    year=c.get("year"),
                    url=c.get("url"),
                    excerpt=c.get("excerpt"),
                    citation_type=CitationType(c.get("type", "academic-paper")),
                    evidence_level=EvidenceLevel(c.get("evidence_level", "C")),
                    relevance_score=c.get("relevance_score", 0.5),
                    verified=c.get("verified", False)
                ))

        result = await pipeline.pre_output_verification(claim, citation_objects, context)

        return {
            "verified": result.verified,
            "confidence": {
                "overall": result.confidence.overall,
                "statistical": result.confidence.statistical,
                "citation_strength": result.confidence.citation_strength,
                "source_agreement": result.confidence.source_agreement,
                "expert_consensus": result.confidence.expert_consensus,
                "contradictions": result.confidence.contradictions,
            },
            "hallucinations": [
                {
                    "type": h.type.value,
                    "severity": h.severity.value,
                    "description": h.description,
                    "suggestion": h.suggestion
                }
                for h in result.hallucinations
            ],
            "warnings": result.warnings,
            "requires_review": result.requires_review,
            "suggestions": result.suggestions,
            "processing_time_ms": result.timestamp_ms
        }

    @app.tool()
    async def detect_hallucinations(
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect hallucinations in text using pattern matching and heuristics.

        Args:
            text: Text to analyze for hallucinations
            context: Optional context for detection

        Returns:
            List of detected hallucinations with severity and suggestions
        """
        hallucinations = await pipeline.detect_hallucinations(text, context)

        return {
            "hallucinations_found": len(hallucinations),
            "has_critical": any(h.severity == Severity.CRITICAL for h in hallucinations),
            "hallucinations": [
                {
                    "type": h.type.value,
                    "severity": h.severity.value,
                    "description": h.description,
                    "suggestion": h.suggestion
                }
                for h in hallucinations
            ],
            "is_safe": len(hallucinations) == 0 or not any(
                h.severity in (Severity.HIGH, Severity.CRITICAL)
                for h in hallucinations
            )
        }

    @app.tool()
    async def validate_citations(
        citations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a list of citations for quality and trustworthiness.

        Args:
            citations: List of citations to validate

        Returns:
            Validation result with issues and recommendations
        """
        citation_objects = [
            Citation(
                id=c.get("id", ""),
                source=c.get("source", ""),
                title=c.get("title", ""),
                year=c.get("year"),
                url=c.get("url"),
                excerpt=c.get("excerpt"),
                relevance_score=c.get("relevance_score", 0.5),
                verified=c.get("verified", False)
            )
            for c in citations
        ]

        result = citation_validator.validate_citations(citation_objects)

        return {
            "is_valid": result.is_valid,
            "confidence": result.confidence,
            "issues": [
                {
                    "type": i.type.value,
                    "severity": i.severity.value,
                    "description": i.description,
                    "suggestion": i.suggestion
                }
                for i in result.issues
            ],
            "recommendations": result.recommendations
        }

    @app.tool()
    async def monitor_confidence(
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Monitor confidence levels of an analysis in real-time.

        Args:
            analysis: Analysis object with claims, citations, and confidence

        Returns:
            Confidence metrics and validation issues
        """
        metrics = confidence_monitor.monitor_confidence(analysis)
        issues = confidence_monitor.validate_confidence(metrics)

        return {
            "overall_confidence": metrics.overall,
            "by_component": metrics.by_component,
            "uncertainty_factors": metrics.uncertainty_factors,
            "data_quality": metrics.data_quality,
            "model_agreement": metrics.model_agreement,
            "issues": [
                {
                    "type": i.type.value,
                    "severity": i.severity.value,
                    "description": i.description,
                    "suggestion": i.suggestion
                }
                for i in issues
            ],
            "passed": len([i for i in issues if i.severity in (Severity.CRITICAL, Severity.ERROR)]) == 0
        }

    @app.tool()
    async def add_trusted_source(
        source: str
    ) -> Dict[str, Any]:
        """
        Add a trusted source to the citation validator.

        Args:
            source: Name of the trusted source to add

        Returns:
            Confirmation of source addition
        """
        citation_validator.add_trusted_source(source)
        return {
            "success": True,
            "source": source,
            "total_trusted_sources": len(citation_validator.trusted_sources)
        }

    @app.tool()
    async def anti_hallucination_status() -> Dict[str, Any]:
        """
        Get Anti-Hallucination system status.

        Returns:
            System status and configuration
        """
        return {
            "status": "active",
            "components": {
                "confidence_scorer": True,
                "confidence_monitor": True,
                "citation_validator": True,
                "verification_pipeline": True
            },
            "thresholds": {
                "min_confidence": ConfidenceScorer.MIN_CONFIDENCE_THRESHOLD,
                "confidence_threshold": confidence_monitor.confidence_threshold,
                "critical_threshold": confidence_monitor.critical_threshold
            },
            "trusted_sources_count": len(citation_validator.trusted_sources),
            "hallucination_patterns": list(pipeline.hallucination_patterns.keys()),
            "version": "1.0.0"
        }

    logger.info("✅ Anti-Hallucination tools registered")
    return pipeline


# =============================================================================
# Convenience Functions
# =============================================================================

_pipeline: Optional[VerificationPipeline] = None


def get_pipeline() -> VerificationPipeline:
    """Get or create the global verification pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = VerificationPipeline()
    return _pipeline


async def verify(claim: str, citations: Optional[List[Citation]] = None) -> VerificationResult:
    """Convenience function to verify a claim."""
    return await get_pipeline().pre_output_verification(claim, citations)


async def detect(text: str) -> List[HallucinationDetection]:
    """Convenience function to detect hallucinations."""
    return await get_pipeline().detect_hallucinations(text)


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    # Quick test
    async def test():
        pipeline = VerificationPipeline()

        # Test hallucination detection
        test_text = "This always works and never fails. Studies show it cures everything 100% of the time."
        hallucinations = await pipeline.detect_hallucinations(test_text)

        print(f"Found {len(hallucinations)} hallucinations:")
        for h in hallucinations:
            print(f"  - [{h.severity.value}] {h.type.value}: {h.description}")

        # Test verification
        result = await pipeline.pre_output_verification(
            "Python is a programming language created by Guido van Rossum.",
            [Citation(
                id="1",
                source="Python Documentation",
                title="Python History",
                year=2024,
                verified=True,
                relevance_score=0.9
            )]
        )

        print(f"\nVerification result: verified={result.verified}, confidence={result.confidence.overall:.2f}")

    asyncio.run(test())
