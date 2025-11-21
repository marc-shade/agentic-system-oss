#!/usr/bin/env python3
"""
Unit tests for Edge Case Learning framework
"""

import asyncio
import pytest
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from advanced_prompting import (
    EdgeCaseLearner,
    GraduatedExample,
    BoundaryDetector,
    EdgeCase,
    EdgeCaseSeverity,
    ExampleType
)


class TestBoundaryDetector:
    """Test suite for BoundaryDetector"""

    def test_detect_off_by_one(self):
        """Test off-by-one pattern detection"""
        input_text = "array index out of range at position length-1"
        boundaries = BoundaryDetector.detect_boundaries(input_text)

        assert "off_by_one" in boundaries

    def test_detect_null_vs_empty(self):
        """Test null vs empty pattern detection"""
        input_text = "expected empty string but got null"
        boundaries = BoundaryDetector.detect_boundaries(input_text)

        assert "null_vs_empty" in boundaries

    def test_detect_race_condition(self):
        """Test race condition pattern detection"""
        input_text = "concurrent access to shared resource caused timing issue"
        boundaries = BoundaryDetector.detect_boundaries(input_text)

        assert "race_condition" in boundaries

    def test_classify_failure_obvious(self):
        """Test obvious failure classification"""
        severity = BoundaryDetector.classify_failure(
            "syntax error",
            {"error_message": "missing semicolon"}
        )

        assert severity == EdgeCaseSeverity.OBVIOUS

    def test_classify_failure_adversarial(self):
        """Test adversarial failure classification"""
        severity = BoundaryDetector.classify_failure(
            "SQL injection attempt",
            {"error_message": "malicious input detected"}
        )

        assert severity == EdgeCaseSeverity.ADVERSARIAL

    def test_assess_correctness_gap(self):
        """Test correctness gap assessment"""
        has_gap, confidence, explanation = BoundaryDetector.assess_correctness_gap(
            "Hello", "hello"
        )

        assert has_gap is True
        assert confidence >= 0.8
        assert "case" in explanation.lower()


class TestEdgeCaseLearner:
    """Test suite for EdgeCaseLearner"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield Path(path)
        # Cleanup
        if Path(path).exists():
            os.unlink(path)

    @pytest.fixture
    def learner(self, temp_db):
        """Create EdgeCaseLearner with temp database"""
        return EdgeCaseLearner(db_path=temp_db)

    def test_initialization(self, learner):
        """Test learner initialization"""
        assert learner.detector is not None
        assert isinstance(learner.edge_cases, dict)
        assert isinstance(learner.pattern_index, dict)

    def test_record_edge_case(self, learner):
        """Test recording an edge case"""
        edge_case = learner.record_edge_case(
            input_text="Payment amount: $0.00",
            expected_output={"status": "rejected"},
            actual_output={"status": "accepted"},
            category="payment_validation"
        )

        assert isinstance(edge_case, EdgeCase)
        assert edge_case.category == "payment_validation"
        assert edge_case.id in learner.edge_cases

    def test_edge_case_persistence(self, temp_db):
        """Test edge case persistence across instances"""
        # Create first learner and add case
        learner1 = EdgeCaseLearner(db_path=temp_db)
        edge_case = learner1.record_edge_case(
            input_text="Test input",
            expected_output="expected",
            actual_output="actual",
            category="test"
        )

        case_id = edge_case.id

        # Create second learner - should load from database
        learner2 = EdgeCaseLearner(db_path=temp_db)
        assert case_id in learner2.edge_cases

    def test_generate_few_shot_examples(self, learner):
        """Test few-shot example generation"""
        # Record some edge cases
        for i in range(3):
            learner.record_edge_case(
                input_text=f"Test input {i}",
                expected_output=f"expected {i}",
                actual_output=f"actual {i}",
                category="test_category"
            )

        examples = learner.generate_few_shot_examples(
            category="test_category",
            difficulty_progression=True,
            max_examples=5
        )

        assert isinstance(examples, list)
        assert len(examples) <= 5
        for example in examples:
            assert isinstance(example, GraduatedExample)

    def test_graduated_example_difficulty(self, learner):
        """Test graduated example difficulty progression"""
        # Create cases with different severities
        learner.record_edge_case(
            input_text="obvious error",
            expected_output="correct",
            actual_output="wrong",
            category="test",
            context={"error_message": "simple mistake"}
        )

        examples = learner.generate_few_shot_examples(
            category="test",
            difficulty_progression=True
        )

        if len(examples) > 0:
            assert 0.0 <= examples[0].difficulty_score <= 1.0

    def test_search_similar_cases(self, learner):
        """Test similar case search"""
        # Record cases
        learner.record_edge_case(
            input_text="database connection timeout",
            expected_output="retry",
            actual_output="crash",
            category="database"
        )

        similar = learner.search_similar_cases(
            input_text="database timeout error",
            category="database",
            limit=5
        )

        assert isinstance(similar, list)
        assert len(similar) <= 5

    def test_get_quality_metrics(self, learner):
        """Test quality metrics"""
        metrics = learner.get_quality_metrics()

        assert "total_edge_cases" in metrics
        assert "false_negative_rate" in metrics
        assert "boundary_detection_coverage" in metrics
        assert "patterns_detected" in metrics

    def test_create_graduated_example(self, learner):
        """Test manual example creation"""
        example = learner.create_graduated_example(
            example_type=ExampleType.POSITIVE_SUBTLE,
            input_text="Test input",
            correct_output="Correct output",
            explanation="This is a subtle positive example",
            difficulty_score=0.7,
            category="test_category"
        )

        assert isinstance(example, GraduatedExample)
        assert example.example_type == ExampleType.POSITIVE_SUBTLE
        assert example.difficulty_score == 0.7

    @pytest.mark.asyncio
    async def test_learn_from_failure_async(self, learner):
        """Test async failure learning"""
        edge_case = await learner.learn_from_failure_async(
            input_text="Async test",
            expected_output="expected",
            actual_output="actual",
            category="async_test"
        )

        assert isinstance(edge_case, EdgeCase)
        assert edge_case.id in learner.edge_cases


def test_edge_case_severity_enum():
    """Test EdgeCaseSeverity enum"""
    assert EdgeCaseSeverity.OBVIOUS.value == "obvious"
    assert EdgeCaseSeverity.SUBTLE.value == "subtle"
    assert EdgeCaseSeverity.BOUNDARY.value == "boundary"
    assert EdgeCaseSeverity.ADVERSARIAL.value == "adversarial"


def test_example_type_enum():
    """Test ExampleType enum"""
    assert ExampleType.NEGATIVE_OBVIOUS.value == "negative_obvious"
    assert ExampleType.POSITIVE_SUBTLE.value == "positive_subtle"
    assert ExampleType.BOUNDARY_CASE.value == "boundary_case"


def test_edge_case_to_dict():
    """Test EdgeCase to_dict conversion"""
    edge_case = EdgeCase(
        id="test123",
        input_text="Test",
        expected_output="expected",
        actual_output="actual",
        category="test",
        severity=EdgeCaseSeverity.SUBTLE,
        pattern="null_vs_empty"
    )

    data = edge_case.to_dict()

    assert data["id"] == "test123"
    assert data["category"] == "test"
    assert data["severity"] == "subtle"


def test_graduated_example_to_dict():
    """Test GraduatedExample to_dict conversion"""
    example = GraduatedExample(
        id="ex123",
        example_type=ExampleType.BOUNDARY_CASE,
        input_text="Test",
        correct_output="Output",
        explanation="Explanation",
        difficulty_score=0.8,
        category="test"
    )

    data = example.to_dict()

    assert data["id"] == "ex123"
    assert data["example_type"] == "boundary_case"
    assert data["difficulty_score"] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
