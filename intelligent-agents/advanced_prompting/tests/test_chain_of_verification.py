#!/usr/bin/env python3
"""
Unit tests for Chain of Verification framework
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from advanced_prompting import (
    ChainOfVerification,
    VerificationStep,
    VerificationResult,
    VerificationPhase
)


class TestChainOfVerification:
    """Test suite for ChainOfVerification"""

    @pytest.fixture
    def verifier(self):
        """Create a ChainOfVerification instance"""
        return ChainOfVerification(
            cli_tool="gemini",
            adversarial_enabled=True,
            confidence_threshold=0.7
        )

    def test_initialization(self, verifier):
        """Test verifier initialization"""
        assert verifier.cli_tool == "gemini"
        assert verifier.adversarial_enabled is True
        assert verifier.confidence_threshold == 0.7
        assert len(verifier.verification_history) == 0

    @pytest.mark.asyncio
    async def test_verify_simple_decision(self, verifier):
        """Test verification of a simple decision"""
        decision = "Restart temporal service"
        context = {
            "cpu_percent": 95,
            "memory_percent": 92,
            "service_down": True
        }

        result = await verifier.verify_decision(decision, context)

        assert isinstance(result, VerificationResult)
        assert result.decision == decision
        assert result.context == context
        assert len(result.steps) > 0
        assert isinstance(result.passed, bool)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_verification_phases(self, verifier):
        """Test that all verification phases execute"""
        decision = "Deploy new feature to production"
        context = {"environment": "production", "tested": True}

        result = await verifier.verify_decision(decision, context)

        # Should have all phases
        phase_types = [step.phase for step in result.steps]

        assert VerificationPhase.ANALYZE in phase_types
        assert VerificationPhase.CRITIQUE in phase_types
        assert VerificationPhase.CITE_EVIDENCE in phase_types

        # Adversarial should be present if enabled
        if verifier.adversarial_enabled:
            assert VerificationPhase.ADVERSARIAL in phase_types

    @pytest.mark.asyncio
    async def test_issue_detection(self, verifier):
        """Test that verification detects issues"""
        # This decision should trigger issues
        decision = "Delete production database without backup"
        context = {"backup_exists": False, "critical_data": True}

        result = await verifier.verify_decision(decision, context)

        # Should detect issues
        assert len(result.failures) > 0 or result.confidence < 0.5

    def test_verification_stats(self, verifier):
        """Test verification statistics"""
        stats = verifier.get_verification_stats()

        assert "total" in stats
        assert stats["total"] == 0  # No verifications yet

    @pytest.mark.asyncio
    async def test_verification_history(self, verifier):
        """Test that verification history is recorded"""
        initial_count = len(verifier.verification_history)

        decision = "Update configuration file"
        context = {"config_valid": True}

        await verifier.verify_decision(decision, context)

        assert len(verifier.verification_history) == initial_count + 1

    def test_extract_confidence(self, verifier):
        """Test confidence extraction"""
        # Test various formats
        assert verifier._extract_confidence("confidence: 0.8") == 0.8
        assert verifier._extract_confidence("80% confident") == 0.8
        assert verifier._extract_confidence("confidence level: 0.95") == 0.95

    def test_extract_issues(self, verifier):
        """Test issue extraction"""
        response = """
        Analysis complete.
        ISSUE: Missing error handling
        ISSUE: No rollback mechanism
        Everything else looks good.
        """

        issues = verifier._extract_issues(response)
        assert len(issues) == 2
        assert "Missing error handling" in issues
        assert "No rollback mechanism" in issues


def test_verification_step_dataclass():
    """Test VerificationStep dataclass"""
    step = VerificationStep(
        phase=VerificationPhase.ANALYZE,
        prompt="Test prompt",
        response="Test response",
        passed=True,
        confidence=0.9
    )

    assert step.phase == VerificationPhase.ANALYZE
    assert step.prompt == "Test prompt"
    assert step.response == "Test response"
    assert step.passed is True
    assert step.confidence == 0.9
    assert len(step.issues_found) == 0


def test_verification_result_to_dict():
    """Test VerificationResult to_dict conversion"""
    step = VerificationStep(
        phase=VerificationPhase.ANALYZE,
        prompt="Test",
        response="Response",
        passed=True,
        confidence=0.8
    )

    result = VerificationResult(
        decision="Test decision",
        context={"test": True},
        steps=[step],
        passed=True,
        final_decision="Proceed",
        confidence=0.85,
        failures=[]
    )

    result_dict = result.to_dict()

    assert result_dict["decision"] == "Test decision"
    assert result_dict["passed"] is True
    assert result_dict["confidence"] == 0.85
    assert len(result_dict["steps"]) == 1
    assert "timestamp" in result_dict


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
