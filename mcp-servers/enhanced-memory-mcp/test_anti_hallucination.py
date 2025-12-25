#!/usr/bin/env python3
"""
Test suite for Anti-Hallucination System.

Tests:
1. ConfidenceScorer - Multi-component confidence scoring
2. ConfidenceMonitor - Real-time monitoring and validation
3. CitationValidator - Citation quality and trustworthiness
4. VerificationPipeline - Pre/post output verification
5. Hallucination Detection - Pattern-based detection
6. MCP Tool Registration - Tool availability and execution
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Set up test environment
os.chdir(Path(__file__).parent)


async def test_confidence_scorer():
    """Test ConfidenceScorer functionality."""
    print("\n=== Test: ConfidenceScorer ===")

    from anti_hallucination import (
        ConfidenceScorer, Citation, CitationType, EvidenceLevel
    )

    scorer = ConfidenceScorer()
    print("  ✓ ConfidenceScorer initialized")

    # Test with high-quality citations
    citations = [
        Citation(
            id="1",
            source="Nature",
            title="High Quality Study",
            year=2024,
            citation_type=CitationType.PEER_REVIEWED,
            evidence_level=EvidenceLevel.A,
            relevance_score=0.95,
            verified=True,
            citation_count=150,
            impact_factor=12.5
        ),
        Citation(
            id="2",
            source="Cochrane Library",
            title="Meta-Analysis",
            year=2023,
            citation_type=CitationType.META_ANALYSIS,
            evidence_level=EvidenceLevel.A,
            relevance_score=0.90,
            verified=True,
            citation_count=200,
            impact_factor=9.8
        )
    ]

    score = await scorer.calculate_confidence(
        "Climate change is accelerating global temperature rise.",
        citations
    )

    print(f"  ✓ Overall confidence: {score.overall:.2f}")
    print(f"  ✓ Statistical: {score.statistical:.2f}")
    print(f"  ✓ Citation strength: {score.citation_strength:.2f}")
    print(f"  ✓ Source agreement: {score.source_agreement:.2f}")
    print(f"  ✓ Expert consensus: {score.expert_consensus:.2f}")

    assert score.overall > 0.5, "High-quality citations should yield good confidence"
    assert len(score.contradictions) == 0, "No contradictions expected"

    # Test with no citations
    empty_score = await scorer.calculate_confidence("Unsupported claim", [])
    assert empty_score.overall < 0.3, "No citations should yield low confidence"
    print(f"  ✓ Empty citations confidence: {empty_score.overall:.2f}")

    # Test confidence level descriptions
    assert scorer.get_confidence_level(0.9) == "high"
    assert scorer.get_confidence_level(0.7) == "medium"
    assert scorer.get_confidence_level(0.5) == "low"
    assert scorer.get_confidence_level(0.3) == "very-low"
    print("  ✓ Confidence level descriptions correct")

    print("  ✅ ConfidenceScorer: PASSED")
    return True


async def test_contradiction_detection():
    """Test contradiction detection in citations."""
    print("\n=== Test: Contradiction Detection ===")

    from anti_hallucination import (
        ConfidenceScorer, Citation, CitationType, EvidenceLevel
    )

    scorer = ConfidenceScorer()

    # Create citations with contradictions
    contradictory_citations = [
        Citation(
            id="1",
            source="Study A",
            title="Recent High Quality Study",
            year=2024,
            evidence_level=EvidenceLevel.A,
            relevance_score=0.9,
            verified=True
        ),
        Citation(
            id="2",
            source="Study B",
            title="Old Low Quality Study",
            year=2010,  # Old study
            evidence_level=EvidenceLevel.D,  # Low quality
            relevance_score=0.5,
            verified=True
        ),
        Citation(
            id="3",
            source="Guidelines",
            title="Clinical Guideline",
            year=2023,
            citation_type=CitationType.GUIDELINE,
            evidence_level=EvidenceLevel.B,
            relevance_score=0.8,
            verified=True
        ),
        Citation(
            id="4",
            source="Expert",
            title="Expert Opinion",
            year=2024,
            citation_type=CitationType.EXPERT_OPINION,
            evidence_level=EvidenceLevel.C,
            relevance_score=0.7,
            verified=True
        )
    ]

    score = await scorer.calculate_confidence(
        "Medical treatment effectiveness",
        contradictory_citations
    )

    assert len(score.contradictions) > 0, "Should detect contradictions"
    print(f"  ✓ Detected {len(score.contradictions)} contradictions:")
    for c in score.contradictions:
        print(f"    - {c}")

    # Contradiction penalty should reduce score
    assert score.overall < 0.8, "Contradictions should reduce overall score"
    print(f"  ✓ Overall score with contradictions: {score.overall:.2f}")

    print("  ✅ Contradiction Detection: PASSED")
    return True


async def test_confidence_monitor():
    """Test ConfidenceMonitor functionality."""
    print("\n=== Test: ConfidenceMonitor ===")

    from anti_hallucination import ConfidenceMonitor, Severity

    monitor = ConfidenceMonitor(confidence_threshold=0.8, critical_threshold=0.6)
    print("  ✓ ConfidenceMonitor initialized")

    # Test high-confidence analysis
    high_conf_analysis = {
        "confidence": 0.85,
        "claims": [
            {"text": "Claim 1", "confidence": 0.9, "verified": True},
            {"text": "Claim 2", "confidence": 0.85, "verified": True}
        ],
        "citations": [
            {"source": "PubMed", "verified": True, "source_type": "peer_reviewed", "relevance_score": 0.9}
        ],
        "reasoning": "Detailed reasoning chain with multiple logical steps and evidence analysis."
    }

    metrics = monitor.monitor_confidence(high_conf_analysis)
    issues = monitor.validate_confidence(metrics)

    print(f"  ✓ Overall confidence: {metrics.overall:.2f}")
    print(f"  ✓ By component: {metrics.by_component}")
    print(f"  ✓ Data quality: {metrics.data_quality:.2f}")
    print(f"  ✓ Issues found: {len(issues)}")

    # Test low-confidence analysis
    low_conf_analysis = {
        "confidence": 0.4,
        "claims": [
            {"text": "Unverified claim", "confidence": 0.3, "verified": False}
        ],
        "citations": [],
        "reasoning": ""
    }

    low_metrics = monitor.monitor_confidence(low_conf_analysis)
    low_issues = monitor.validate_confidence(low_metrics)

    assert len(low_issues) > 0, "Should flag low confidence analysis"
    has_critical = any(i.severity == Severity.CRITICAL for i in low_issues)
    assert has_critical, "Should have critical issue for very low confidence"
    print(f"  ✓ Low confidence issues: {len(low_issues)}")
    print(f"  ✓ Has critical issue: {has_critical}")

    print("  ✅ ConfidenceMonitor: PASSED")
    return True


async def test_citation_validator():
    """Test CitationValidator functionality."""
    print("\n=== Test: CitationValidator ===")

    from anti_hallucination import CitationValidator, Citation, Severity

    validator = CitationValidator()
    print("  ✓ CitationValidator initialized")
    print(f"  ✓ Trusted sources count: {len(validator.trusted_sources)}")

    # Test valid citation
    valid_citation = Citation(
        id="1",
        source="Nature",
        title="Valid Study",
        year=2024,
        url="https://nature.com/article/12345",
        relevance_score=0.9,
        verified=True
    )

    result = validator.validate_citation(valid_citation)
    print(f"  ✓ Valid citation: is_valid={result.is_valid}, confidence={result.confidence:.2f}")

    # Test untrusted source
    untrusted_citation = Citation(
        id="2",
        source="Random Blog",
        title="Untrusted Source",
        year=2024,
        url="https://blog.example.com/post",
        relevance_score=0.5,
        verified=False
    )

    untrusted_result = validator.validate_citation(untrusted_citation)
    assert not untrusted_result.is_valid, "Untrusted unverified source should not be valid"
    print(f"  ✓ Untrusted citation: is_valid={untrusted_result.is_valid}")

    # Test multiple citations
    multiple_citations = [
        Citation(id="1", source="PubMed", title="Study 1", year=2024, verified=True, relevance_score=0.85),
        Citation(id="2", source="Cochrane", title="Study 2", year=2023, verified=True, relevance_score=0.9),
        Citation(id="3", source="JAMA", title="Study 3", year=2024, verified=True, relevance_score=0.88)
    ]

    multi_result = validator.validate_citations(multiple_citations)
    print(f"  ✓ Multiple citations: is_valid={multi_result.is_valid}, confidence={multi_result.confidence:.2f}")
    print(f"  ✓ Recommendations: {len(multi_result.recommendations)}")

    # Test adding trusted source
    validator.add_trusted_source("My Custom Source")
    assert "My Custom Source" in validator.trusted_sources
    print("  ✓ Custom trusted source added")

    print("  ✅ CitationValidator: PASSED")
    return True


async def test_hallucination_detection():
    """Test hallucination detection patterns."""
    print("\n=== Test: Hallucination Detection ===")

    from anti_hallucination import VerificationPipeline, HallucinationType, Severity

    pipeline = VerificationPipeline()
    print("  ✓ VerificationPipeline initialized")

    # Test overconfident language
    overconfident_text = "This always works and never fails. It's absolutely guaranteed to succeed."
    hallucinations = await pipeline.detect_hallucinations(overconfident_text)
    has_overconfident = any(
        h.type == HallucinationType.FACTUAL and "Overconfident" in h.description
        for h in hallucinations
    )
    print(f"  ✓ Overconfident text: {len(hallucinations)} hallucinations detected")

    # Test unsupported quantitative claims
    quantitative_text = "This treatment is 85% effective and works 10 times better than alternatives."
    quant_hallucinations = await pipeline.detect_hallucinations(quantitative_text)
    has_quant = any(h.type == HallucinationType.QUANTITATIVE for h in quant_hallucinations)
    assert has_quant, "Should detect quantitative hallucinations"
    print(f"  ✓ Quantitative claims: detected={has_quant}")

    # Test temporal vagueness
    temporal_text = "Recent studies have shown that modern research proves this works."
    temporal_hallucinations = await pipeline.detect_hallucinations(temporal_text)
    has_temporal = any(h.type == HallucinationType.TEMPORAL for h in temporal_hallucinations)
    assert has_temporal, "Should detect temporal vagueness"
    print(f"  ✓ Temporal vagueness: detected={has_temporal}")

    # Test absolute claims
    absolute_text = "This completely cures the disease and permanently fixes all issues."
    absolute_hallucinations = await pipeline.detect_hallucinations(absolute_text)
    has_critical = any(h.severity == Severity.CRITICAL for h in absolute_hallucinations)
    assert has_critical, "Absolute claims should be critical severity"
    print(f"  ✓ Absolute claims: critical={has_critical}")

    # Test fabricated authority
    fabricated_text = "According to experts and scientists agree that studies show this works."
    fab_hallucinations = await pipeline.detect_hallucinations(fabricated_text)
    has_citation = any(h.type == HallucinationType.CITATION for h in fab_hallucinations)
    assert has_citation, "Should detect vague authority references"
    print(f"  ✓ Fabricated authority: detected={has_citation}")

    # Test future date (temporal hallucination)
    future_text = f"According to a 2030 study, this will be common practice."
    future_hallucinations = await pipeline.detect_hallucinations(future_text)
    has_future = any(
        h.type == HallucinationType.TEMPORAL and "Future" in h.description
        for h in future_hallucinations
    )
    assert has_future, "Should detect future dates"
    print(f"  ✓ Future dates: detected={has_future}")

    # Test invalid percentage
    invalid_pct_text = "This has a 150% success rate."
    pct_hallucinations = await pipeline.detect_hallucinations(invalid_pct_text)
    has_invalid_pct = any(
        h.type == HallucinationType.QUANTITATIVE and h.severity == Severity.CRITICAL
        for h in pct_hallucinations
    )
    assert has_invalid_pct, "Should detect invalid percentages"
    print(f"  ✓ Invalid percentage: detected={has_invalid_pct}")

    # Test clean text (no hallucinations expected)
    clean_text = "Python is a programming language used for software development."
    clean_hallucinations = await pipeline.detect_hallucinations(clean_text)
    print(f"  ✓ Clean text: {len(clean_hallucinations)} hallucinations")

    print("  ✅ Hallucination Detection: PASSED")
    return True


async def test_verification_pipeline():
    """Test VerificationPipeline pre/post verification."""
    print("\n=== Test: VerificationPipeline ===")

    from anti_hallucination import (
        VerificationPipeline, Citation, CitationType, EvidenceLevel
    )

    pipeline = VerificationPipeline()

    # Test verification with good citations
    good_claim = "Python was created by Guido van Rossum and first released in 1991."
    good_citations = [
        Citation(
            id="1",
            source="Python Documentation",
            title="Python History",
            year=2024,
            url="https://docs.python.org/3/",
            citation_type=CitationType.OFFICIAL_DOC,
            evidence_level=EvidenceLevel.A,
            relevance_score=0.95,
            verified=True
        ),
        Citation(
            id="2",
            source="Wikipedia",
            title="Python Programming Language",
            year=2024,
            url="https://wikipedia.org/wiki/Python",
            relevance_score=0.85,
            verified=True
        )
    ]

    result = await pipeline.pre_output_verification(good_claim, good_citations)

    print(f"  ✓ Good claim: verified={result.verified}")
    print(f"  ✓ Confidence: {result.confidence.overall:.2f}")
    print(f"  ✓ Hallucinations: {len(result.hallucinations)}")
    print(f"  ✓ Requires review: {result.requires_review}")

    # Test verification without citations
    no_citation_claim = "This is a claim without any supporting evidence."
    no_citation_result = await pipeline.pre_output_verification(no_citation_claim, [])

    assert not no_citation_result.verified, "Unsupported claim should not be verified"
    assert len(no_citation_result.warnings) > 0, "Should have warnings"
    print(f"  ✓ No citations: verified={no_citation_result.verified}")
    print(f"  ✓ Warnings: {len(no_citation_result.warnings)}")

    # Test post-output validation
    original = "Python is a programming language."
    output = "Python is a programming language created by Guido van Rossum."
    post_result = await pipeline.post_output_validation(output, original, good_citations)

    print(f"  ✓ Post-output: verified={post_result.verified}")

    # Test provider review integration
    from anti_hallucination import ProviderReview
    import time

    review = ProviderReview(
        reviewer_id="human-reviewer-1",
        approved=True,
        corrections=[],
        feedback="Looks accurate",
        timestamp=int(time.time())
    )

    await pipeline.add_provider_review("claim-1", review)
    reviews = pipeline.get_provider_reviews("claim-1")
    assert len(reviews) == 1, "Should store provider review"
    print(f"  ✓ Provider reviews stored: {len(reviews)}")

    print("  ✅ VerificationPipeline: PASSED")
    return True


async def test_mcp_tools():
    """Test MCP tool registration."""
    print("\n=== Test: MCP Tool Registration ===")

    from anti_hallucination import register_anti_hallucination_tools

    class MockApp:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

    mock_app = MockApp()
    pipeline = register_anti_hallucination_tools(mock_app)

    expected_tools = [
        "verify_claim",
        "detect_hallucinations",
        "validate_citations",
        "monitor_confidence",
        "add_trusted_source",
        "anti_hallucination_status"
    ]

    for tool_name in expected_tools:
        assert tool_name in mock_app.tools, f"Missing tool: {tool_name}"
        print(f"  ✓ {tool_name} registered")

    # Test anti_hallucination_status
    status = await mock_app.tools["anti_hallucination_status"]()
    assert status["status"] == "active"
    assert status["components"]["verification_pipeline"] is True
    print(f"  ✓ Status: {status['status']}")
    print(f"  ✓ Components: {list(status['components'].keys())}")
    print(f"  ✓ Trusted sources: {status['trusted_sources_count']}")

    # Test verify_claim
    verify_result = await mock_app.tools["verify_claim"](
        claim="Test claim",
        citations=[
            {
                "id": "1",
                "source": "PubMed",
                "title": "Test Study",
                "year": 2024,
                "verified": True,
                "relevance_score": 0.9
            }
        ]
    )
    assert "verified" in verify_result
    assert "confidence" in verify_result
    print(f"  ✓ verify_claim: verified={verify_result['verified']}")

    # Test detect_hallucinations
    detect_result = await mock_app.tools["detect_hallucinations"](
        text="This always works 100% of the time and cures everything."
    )
    assert "hallucinations_found" in detect_result
    assert detect_result["hallucinations_found"] > 0
    print(f"  ✓ detect_hallucinations: found={detect_result['hallucinations_found']}")

    # Test validate_citations
    citation_result = await mock_app.tools["validate_citations"](
        citations=[
            {"id": "1", "source": "Nature", "title": "Study", "year": 2024, "verified": True, "relevance_score": 0.9}
        ]
    )
    assert "is_valid" in citation_result
    print(f"  ✓ validate_citations: is_valid={citation_result['is_valid']}")

    # Test monitor_confidence
    monitor_result = await mock_app.tools["monitor_confidence"](
        analysis={
            "confidence": 0.85,
            "claims": [{"text": "Test", "confidence": 0.8, "verified": True}],
            "citations": [{"verified": True, "source_type": "peer_reviewed"}],
            "reasoning": "Test reasoning"
        }
    )
    assert "overall_confidence" in monitor_result
    print(f"  ✓ monitor_confidence: overall={monitor_result['overall_confidence']:.2f}")

    # Test add_trusted_source
    source_result = await mock_app.tools["add_trusted_source"](source="Custom Research DB")
    assert source_result["success"] is True
    print(f"  ✓ add_trusted_source: sources={source_result['total_trusted_sources']}")

    print("  ✅ MCP Tools: PASSED")
    return True


async def test_convenience_functions():
    """Test convenience functions."""
    print("\n=== Test: Convenience Functions ===")

    from anti_hallucination import (
        get_pipeline, verify, detect, Citation, VerificationPipeline
    )

    # Test get_pipeline singleton
    pipeline1 = get_pipeline()
    pipeline2 = get_pipeline()
    assert pipeline1 is pipeline2, "Should return same instance"
    assert isinstance(pipeline1, VerificationPipeline)
    print("  ✓ get_pipeline() singleton working")

    # Test verify convenience function
    result = await verify("Test claim", [
        Citation(
            id="1",
            source="Test Source",
            title="Test",
            year=2024,
            relevance_score=0.8,
            verified=True
        )
    ])
    assert hasattr(result, "verified")
    assert hasattr(result, "confidence")
    print(f"  ✓ verify(): verified={result.verified}")

    # Test detect convenience function
    hallucinations = await detect("This always works and cures everything.")
    assert isinstance(hallucinations, list)
    print(f"  ✓ detect(): found {len(hallucinations)} hallucinations")

    print("  ✅ Convenience Functions: PASSED")
    return True


async def test_data_classes():
    """Test data class structures."""
    print("\n=== Test: Data Classes ===")

    from anti_hallucination import (
        Citation, CitationType, EvidenceLevel,
        ValidationIssue, IssueType, Severity,
        HallucinationDetection, HallucinationType,
        ConfidenceScore, ConfidenceMetrics, ConfidenceMetadata,
        ValidationResult, VerificationResult, ProviderReview
    )

    # Test Citation
    citation = Citation(
        id="test-1",
        source="Nature",
        title="Test Study",
        year=2024,
        url="https://example.com",
        citation_type=CitationType.PEER_REVIEWED,
        evidence_level=EvidenceLevel.A,
        relevance_score=0.95,
        verified=True,
        citation_count=100,
        impact_factor=10.5
    )
    assert citation.id == "test-1"
    assert citation.citation_type == CitationType.PEER_REVIEWED
    print("  ✓ Citation dataclass works")

    # Test ValidationIssue
    issue = ValidationIssue(
        type=IssueType.LOW_CONFIDENCE,
        severity=Severity.WARNING,
        description="Test issue",
        suggestion="Fix it"
    )
    assert issue.type == IssueType.LOW_CONFIDENCE
    print("  ✓ ValidationIssue dataclass works")

    # Test HallucinationDetection
    hallucination = HallucinationDetection(
        type=HallucinationType.FACTUAL,
        severity=Severity.HIGH,
        description="Factual error detected",
        suggestion="Verify facts"
    )
    assert hallucination.type == HallucinationType.FACTUAL
    print("  ✓ HallucinationDetection dataclass works")

    # Test ConfidenceScore
    score = ConfidenceScore(
        overall=0.85,
        statistical=0.9,
        citation_strength=0.8,
        source_agreement=0.85,
        expert_consensus=0.7,
        contradictions=[]
    )
    assert score.overall == 0.85
    print("  ✓ ConfidenceScore dataclass works")

    # Test ConfidenceMetrics
    metrics = ConfidenceMetrics(
        overall=0.8,
        by_component={"claims": 0.85, "evidence": 0.75},
        uncertainty_factors=["Limited data"],
        data_quality=0.7
    )
    assert metrics.overall == 0.8
    print("  ✓ ConfidenceMetrics dataclass works")

    # Test VerificationResult
    result = VerificationResult(
        verified=True,
        confidence=score,
        hallucinations=[],
        warnings=[],
        requires_review=False,
        suggestions=[]
    )
    assert result.verified is True
    print("  ✓ VerificationResult dataclass works")

    print("  ✅ Data Classes: PASSED")
    return True


async def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n=== Test: Edge Cases ===")

    from anti_hallucination import (
        ConfidenceScorer, CitationValidator, VerificationPipeline, Citation
    )

    scorer = ConfidenceScorer()
    validator = CitationValidator()
    pipeline = VerificationPipeline()

    # Empty claim
    empty_result = await pipeline.pre_output_verification("", [])
    assert empty_result is not None
    print("  ✓ Empty claim handled")

    # Very long claim
    long_claim = "This is a test claim. " * 100
    long_result = await pipeline.detect_hallucinations(long_claim)
    assert isinstance(long_result, list)
    print("  ✓ Long text handled")

    # Citation with missing fields
    minimal_citation = Citation(
        id="min",
        source="Unknown",
        title=""
    )
    min_result = validator.validate_citation(minimal_citation)
    assert min_result is not None
    print("  ✓ Minimal citation handled")

    # Unicode text
    unicode_text = "研究显示这个方法有效。 日本語のテキスト。 Émojis: 🔬📊"
    unicode_result = await pipeline.detect_hallucinations(unicode_text)
    assert isinstance(unicode_result, list)
    print("  ✓ Unicode text handled")

    # Special characters
    special_text = "Test with $100 and 50% & more <html> tags"
    special_result = await pipeline.detect_hallucinations(special_text)
    assert isinstance(special_result, list)
    print("  ✓ Special characters handled")

    # Numerical edge cases
    num_text = "This has 0% failure rate and 999999% improvement."
    num_result = await pipeline.detect_hallucinations(num_text)
    has_invalid = any(h.description and "percentage" in h.description.lower() for h in num_result)
    print(f"  ✓ Numerical edge cases: invalid_pct_detected={has_invalid}")

    print("  ✅ Edge Cases: PASSED")
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Anti-Hallucination System Integration Tests")
    print("=" * 60)

    tests = [
        ("ConfidenceScorer", test_confidence_scorer),
        ("Contradiction Detection", test_contradiction_detection),
        ("ConfidenceMonitor", test_confidence_monitor),
        ("CitationValidator", test_citation_validator),
        ("Hallucination Detection", test_hallucination_detection),
        ("VerificationPipeline", test_verification_pipeline),
        ("MCP Tools", test_mcp_tools),
        ("Convenience Functions", test_convenience_functions),
        ("Data Classes", test_data_classes),
        ("Edge Cases", test_edge_cases),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            print(f"  ❌ {name}: FAILED - {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
