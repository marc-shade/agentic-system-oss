"""
Eval Framework for Agent Skills

Following Kai pattern: rigorous, deterministic testing of agent capabilities.
Provides comprehensive evaluation of agent skills against defined benchmarks.

Components:
- SkillEvaluator: Core evaluation engine
- TestCase/TestSuite: Test case definitions
- EvalMetrics: Measurement and scoring
- Benchmarks: Performance baselines
- ReportGenerator: Evaluation reporting

Usage:
    from eval import SkillEvaluator, TestSuite, create_test_case

    suite = TestSuite(name="Code Agent Tests")
    suite.add_case(create_test_case(
        name="Read file test",
        skill="file_reading",
        input={"path": "test.py"},
        expected_behavior="Returns file content",
        success_criteria=["content_not_empty", "no_errors"]
    ))

    evaluator = SkillEvaluator()
    results = evaluator.run_suite(agent, suite)
    report = results.generate_report()
"""

from .test_cases import (
    TestCase,
    TestSuite,
    TestResult,
    create_test_case,
    ExpectedBehavior,
)
from .skill_evaluator import (
    SkillEvaluator,
    EvaluationConfig,
    EvaluationResult,
    SkillScore,
)
from .metrics import (
    EvalMetrics,
    MetricType,
    calculate_accuracy,
    calculate_f1_score,
    calculate_latency_percentile,
)
from .benchmarks import (
    Benchmark,
    BenchmarkSuite,
    PerformanceBaseline,
    compare_to_baseline,
)
from .report_generator import (
    ReportGenerator,
    ReportFormat,
    EvaluationReport,
)

__all__ = [
    # Test cases
    'TestCase',
    'TestSuite',
    'TestResult',
    'create_test_case',
    'ExpectedBehavior',
    # Evaluator
    'SkillEvaluator',
    'EvaluationConfig',
    'EvaluationResult',
    'SkillScore',
    # Metrics
    'EvalMetrics',
    'MetricType',
    'calculate_accuracy',
    'calculate_f1_score',
    'calculate_latency_percentile',
    # Benchmarks
    'Benchmark',
    'BenchmarkSuite',
    'PerformanceBaseline',
    'compare_to_baseline',
    # Reports
    'ReportGenerator',
    'ReportFormat',
    'EvaluationReport',
]
