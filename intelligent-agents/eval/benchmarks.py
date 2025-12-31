"""
Benchmarks for Skill Evaluation

Provides benchmark definitions, performance baselines, and comparison utilities.
Following Kai pattern: measurable, reproducible baselines.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import statistics


class BenchmarkCategory(Enum):
    """Categories of benchmarks."""
    SKILL_ACCURACY = "skill_accuracy"
    TASK_COMPLETION = "task_completion"
    RESPONSE_QUALITY = "response_quality"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    RESOURCE_USAGE = "resource_usage"
    SAFETY = "safety"
    CUSTOM = "custom"


class ComparisonResult(Enum):
    """Result of comparing to baseline."""
    EXCEEDS = "exceeds"      # Better than baseline
    MEETS = "meets"          # Within acceptable range
    BELOW = "below"          # Worse than baseline
    CRITICAL = "critical"    # Far below baseline


@dataclass
class PerformanceBaseline:
    """
    A performance baseline for comparison.

    Attributes:
        name: Baseline name
        metric_name: What metric this baseline measures
        target_value: Target/expected value
        minimum_value: Minimum acceptable value
        maximum_value: Maximum acceptable value (for metrics where lower is better)
        unit: Unit of measurement
        category: Benchmark category
        description: What this baseline measures
        established_date: When baseline was established
        source: How baseline was determined
    """
    name: str
    metric_name: str
    target_value: float
    minimum_value: Optional[float] = None
    maximum_value: Optional[float] = None
    unit: str = ""
    category: BenchmarkCategory = BenchmarkCategory.CUSTOM
    description: str = ""
    established_date: datetime = field(default_factory=datetime.now)
    source: str = "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compare(self, actual_value: float) -> ComparisonResult:
        """
        Compare an actual value against this baseline.

        Args:
            actual_value: The measured value to compare

        Returns:
            ComparisonResult indicating how value compares to baseline
        """
        # For latency/resource metrics, lower is better
        lower_is_better = self.category in (
            BenchmarkCategory.LATENCY,
            BenchmarkCategory.RESOURCE_USAGE
        )

        if lower_is_better:
            if self.maximum_value and actual_value > self.maximum_value:
                return ComparisonResult.CRITICAL
            if actual_value > self.target_value * 1.5:
                return ComparisonResult.CRITICAL
            if actual_value > self.target_value:
                return ComparisonResult.BELOW
            if actual_value <= self.target_value * 0.8:
                return ComparisonResult.EXCEEDS
            return ComparisonResult.MEETS
        else:
            # Higher is better (accuracy, throughput, etc.)
            if self.minimum_value and actual_value < self.minimum_value:
                return ComparisonResult.CRITICAL
            if actual_value < self.target_value * 0.5:
                return ComparisonResult.CRITICAL
            if actual_value < self.target_value:
                return ComparisonResult.BELOW
            if actual_value >= self.target_value * 1.1:
                return ComparisonResult.EXCEEDS
            return ComparisonResult.MEETS

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "metric_name": self.metric_name,
            "target_value": self.target_value,
            "minimum_value": self.minimum_value,
            "maximum_value": self.maximum_value,
            "unit": self.unit,
            "category": self.category.value,
            "description": self.description,
            "established_date": self.established_date.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    benchmark_name: str
    actual_value: float
    baseline: PerformanceBaseline
    comparison: ComparisonResult
    execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if benchmark passed (meets or exceeds)."""
        return self.comparison in (ComparisonResult.MEETS, ComparisonResult.EXCEEDS)

    @property
    def deviation(self) -> float:
        """Calculate deviation from target (as percentage)."""
        if self.baseline.target_value == 0:
            return 0.0
        return ((self.actual_value - self.baseline.target_value) /
                self.baseline.target_value) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "actual_value": self.actual_value,
            "target_value": self.baseline.target_value,
            "comparison": self.comparison.value,
            "passed": self.passed,
            "deviation_percent": self.deviation,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class Benchmark:
    """
    A benchmark definition for skill evaluation.

    Attributes:
        name: Benchmark name
        description: What this benchmark tests
        baseline: Performance baseline
        test_fn: Function to run the benchmark
        setup_fn: Optional setup function
        teardown_fn: Optional teardown function
        iterations: Number of iterations to run
        warmup_iterations: Warmup iterations (not counted)
        tags: Categories/labels
    """
    name: str
    description: str
    baseline: PerformanceBaseline
    test_fn: Optional[Callable[[], float]] = None
    setup_fn: Optional[Callable[[], None]] = None
    teardown_fn: Optional[Callable[[], None]] = None
    iterations: int = 1
    warmup_iterations: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def run(self, value: Optional[float] = None) -> BenchmarkResult:
        """
        Run the benchmark.

        Args:
            value: If provided, use this value instead of running test_fn

        Returns:
            BenchmarkResult with comparison to baseline
        """
        import time

        start_time = time.time()

        if value is not None:
            actual_value = value
        elif self.test_fn:
            # Setup
            if self.setup_fn:
                self.setup_fn()

            try:
                # Warmup
                for _ in range(self.warmup_iterations):
                    self.test_fn()

                # Actual runs
                values = []
                for _ in range(self.iterations):
                    values.append(self.test_fn())

                actual_value = statistics.mean(values) if values else 0.0
            finally:
                # Teardown
                if self.teardown_fn:
                    self.teardown_fn()
        else:
            raise ValueError("Must provide value or test_fn")

        execution_time = (time.time() - start_time) * 1000

        comparison = self.baseline.compare(actual_value)

        return BenchmarkResult(
            benchmark_name=self.name,
            actual_value=actual_value,
            baseline=self.baseline,
            comparison=comparison,
            execution_time_ms=execution_time,
            details={
                "iterations": self.iterations,
                "warmup_iterations": self.warmup_iterations,
            }
        )


class BenchmarkSuite:
    """
    A collection of related benchmarks.

    Provides methods for running multiple benchmarks and aggregating results.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.tags = tags or []
        self.benchmarks: List[Benchmark] = []
        self.results: List[BenchmarkResult] = []
        self.created_at = datetime.now()

    def add_benchmark(self, benchmark: Benchmark) -> None:
        """Add a benchmark to the suite."""
        self.benchmarks.append(benchmark)

    def add_benchmarks(self, benchmarks: List[Benchmark]) -> None:
        """Add multiple benchmarks."""
        self.benchmarks.extend(benchmarks)

    def remove_benchmark(self, name: str) -> bool:
        """Remove a benchmark by name."""
        for i, b in enumerate(self.benchmarks):
            if b.name == name:
                del self.benchmarks[i]
                return True
        return False

    def get_benchmark(self, name: str) -> Optional[Benchmark]:
        """Get a benchmark by name."""
        for b in self.benchmarks:
            if b.name == name:
                return b
        return None

    def run_all(
        self,
        values: Optional[Dict[str, float]] = None,
        stop_on_critical: bool = False
    ) -> List[BenchmarkResult]:
        """
        Run all benchmarks in the suite.

        Args:
            values: Optional pre-computed values (benchmark_name -> value)
            stop_on_critical: If True, stop on first critical failure

        Returns:
            List of benchmark results
        """
        self.results = []

        for benchmark in self.benchmarks:
            value = values.get(benchmark.name) if values else None
            result = benchmark.run(value=value)
            self.results.append(result)

            if stop_on_critical and result.comparison == ComparisonResult.CRITICAL:
                break

        return self.results

    def run_by_tag(
        self,
        tag: str,
        values: Optional[Dict[str, float]] = None
    ) -> List[BenchmarkResult]:
        """Run benchmarks with a specific tag."""
        results = []

        for benchmark in self.benchmarks:
            if tag in benchmark.tags:
                value = values.get(benchmark.name) if values else None
                result = benchmark.run(value=value)
                results.append(result)

        return results

    def run_by_category(
        self,
        category: BenchmarkCategory,
        values: Optional[Dict[str, float]] = None
    ) -> List[BenchmarkResult]:
        """Run benchmarks in a specific category."""
        results = []

        for benchmark in self.benchmarks:
            if benchmark.baseline.category == category:
                value = values.get(benchmark.name) if values else None
                result = benchmark.run(value=value)
                results.append(result)

        return results

    @property
    def total_benchmarks(self) -> int:
        """Total number of benchmarks."""
        return len(self.benchmarks)

    @property
    def passed_count(self) -> int:
        """Number of passed benchmarks."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        """Number of failed benchmarks."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def critical_count(self) -> int:
        """Number of critical failures."""
        return sum(1 for r in self.results
                   if r.comparison == ComparisonResult.CRITICAL)

    @property
    def pass_rate(self) -> float:
        """Pass rate (0.0 to 1.0)."""
        if not self.results:
            return 0.0
        return self.passed_count / len(self.results)

    def summary(self) -> Dict[str, Any]:
        """Get summary of benchmark results."""
        if not self.results:
            return {
                "suite_name": self.name,
                "status": "not_run",
                "total_benchmarks": self.total_benchmarks,
            }

        by_comparison = {}
        for result in self.results:
            comp = result.comparison.value
            if comp not in by_comparison:
                by_comparison[comp] = []
            by_comparison[comp].append(result.benchmark_name)

        return {
            "suite_name": self.name,
            "status": "passed" if self.pass_rate >= 1.0 else "failed",
            "total_benchmarks": self.total_benchmarks,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "critical": self.critical_count,
            "pass_rate": self.pass_rate,
            "by_comparison": by_comparison,
            "total_execution_time_ms": sum(r.execution_time_ms for r in self.results),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert suite to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "total_benchmarks": self.total_benchmarks,
            "benchmarks": [
                {
                    "name": b.name,
                    "description": b.description,
                    "baseline": b.baseline.to_dict(),
                    "tags": b.tags,
                }
                for b in self.benchmarks
            ],
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary(),
            "created_at": self.created_at.isoformat(),
        }


def compare_to_baseline(
    actual: float,
    baseline: Union[PerformanceBaseline, float],
    category: Optional[BenchmarkCategory] = None
) -> ComparisonResult:
    """
    Compare an actual value to a baseline.

    Args:
        actual: Measured value
        baseline: PerformanceBaseline or target value
        category: Category (required if baseline is float)

    Returns:
        ComparisonResult
    """
    if isinstance(baseline, PerformanceBaseline):
        return baseline.compare(actual)

    if category is None:
        category = BenchmarkCategory.CUSTOM

    temp_baseline = PerformanceBaseline(
        name="temp",
        metric_name="value",
        target_value=baseline,
        category=category,
    )
    return temp_baseline.compare(actual)


def create_accuracy_baseline(
    name: str,
    target: float = 0.95,
    minimum: float = 0.80,
    description: str = ""
) -> PerformanceBaseline:
    """Create a standard accuracy baseline."""
    return PerformanceBaseline(
        name=name,
        metric_name="accuracy",
        target_value=target,
        minimum_value=minimum,
        unit="%",
        category=BenchmarkCategory.SKILL_ACCURACY,
        description=description or f"Accuracy target: {target:.0%}",
    )


def create_latency_baseline(
    name: str,
    target_ms: float = 100.0,
    max_ms: float = 500.0,
    description: str = ""
) -> PerformanceBaseline:
    """Create a standard latency baseline."""
    return PerformanceBaseline(
        name=name,
        metric_name="latency_p95",
        target_value=target_ms,
        maximum_value=max_ms,
        unit="ms",
        category=BenchmarkCategory.LATENCY,
        description=description or f"P95 latency target: {target_ms}ms",
    )


def create_throughput_baseline(
    name: str,
    target_ops: float = 100.0,
    minimum_ops: float = 50.0,
    description: str = ""
) -> PerformanceBaseline:
    """Create a standard throughput baseline."""
    return PerformanceBaseline(
        name=name,
        metric_name="throughput",
        target_value=target_ops,
        minimum_value=minimum_ops,
        unit="ops/s",
        category=BenchmarkCategory.THROUGHPUT,
        description=description or f"Throughput target: {target_ops} ops/s",
    )


def create_success_rate_baseline(
    name: str,
    target: float = 0.99,
    minimum: float = 0.95,
    description: str = ""
) -> PerformanceBaseline:
    """Create a standard success rate baseline."""
    return PerformanceBaseline(
        name=name,
        metric_name="success_rate",
        target_value=target,
        minimum_value=minimum,
        unit="%",
        category=BenchmarkCategory.TASK_COMPLETION,
        description=description or f"Success rate target: {target:.0%}",
    )


# Standard benchmarks for common skill evaluations
STANDARD_BASELINES = {
    "code_reading_accuracy": create_accuracy_baseline(
        "code_reading_accuracy",
        target=0.95,
        minimum=0.85,
        description="Accuracy of code understanding and analysis"
    ),
    "code_generation_quality": create_accuracy_baseline(
        "code_generation_quality",
        target=0.90,
        minimum=0.75,
        description="Quality of generated code (syntax, logic, style)"
    ),
    "task_completion_rate": create_success_rate_baseline(
        "task_completion_rate",
        target=0.95,
        minimum=0.85,
        description="Rate of successfully completed tasks"
    ),
    "response_latency": create_latency_baseline(
        "response_latency",
        target_ms=500.0,
        max_ms=2000.0,
        description="Response time for standard queries"
    ),
    "tool_selection_accuracy": create_accuracy_baseline(
        "tool_selection_accuracy",
        target=0.98,
        minimum=0.90,
        description="Accuracy of selecting correct tools for tasks"
    ),
    "safety_compliance": create_success_rate_baseline(
        "safety_compliance",
        target=1.0,
        minimum=0.99,
        description="Compliance with safety constraints"
    ),
}


if __name__ == '__main__':
    print("Benchmarks Module Self-Test")
    print("=" * 50)

    # Test PerformanceBaseline
    baseline = create_accuracy_baseline(
        "test_accuracy",
        target=0.90,
        minimum=0.75
    )
    print(f"Baseline: {baseline.name}")
    print(f"  Target: {baseline.target_value}")
    print(f"  Minimum: {baseline.minimum_value}")

    # Test comparisons
    assert baseline.compare(0.95) == ComparisonResult.EXCEEDS
    assert baseline.compare(0.90) == ComparisonResult.MEETS
    assert baseline.compare(0.85) == ComparisonResult.MEETS
    assert baseline.compare(0.70) == ComparisonResult.BELOW
    assert baseline.compare(0.40) == ComparisonResult.CRITICAL
    print(f"  Comparisons validated")

    # Test latency baseline (lower is better)
    latency_baseline = create_latency_baseline(
        "test_latency",
        target_ms=100.0,
        max_ms=500.0
    )
    assert latency_baseline.compare(50.0) == ComparisonResult.EXCEEDS
    assert latency_baseline.compare(100.0) == ComparisonResult.MEETS
    assert latency_baseline.compare(120.0) == ComparisonResult.BELOW
    assert latency_baseline.compare(600.0) == ComparisonResult.CRITICAL
    print(f"  Latency comparisons validated")

    # Test Benchmark
    benchmark = Benchmark(
        name="accuracy_test",
        description="Test accuracy benchmark",
        baseline=baseline,
        iterations=1
    )
    result = benchmark.run(value=0.92)
    assert result.passed
    assert result.comparison == ComparisonResult.EXCEEDS
    print(f"\nBenchmark result: {result.comparison.value}")
    print(f"  Deviation: {result.deviation:.1f}%")

    # Test BenchmarkSuite
    suite = BenchmarkSuite(
        name="Agent Skill Benchmarks",
        description="Test suite for agent capabilities"
    )

    for name, bl in STANDARD_BASELINES.items():
        suite.add_benchmark(Benchmark(
            name=name,
            description=bl.description,
            baseline=bl,
        ))

    print(f"\nSuite: {suite.name}")
    print(f"  Total benchmarks: {suite.total_benchmarks}")

    # Run with sample values
    test_values = {
        "code_reading_accuracy": 0.96,
        "code_generation_quality": 0.88,
        "task_completion_rate": 0.97,
        "response_latency": 350.0,
        "tool_selection_accuracy": 0.99,
        "safety_compliance": 1.0,
    }

    results = suite.run_all(values=test_values)
    summary = suite.summary()

    print(f"\nResults:")
    print(f"  Passed: {summary['passed']}/{summary['total_benchmarks']}")
    print(f"  Pass rate: {summary['pass_rate']:.0%}")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"  {result.benchmark_name}: {status} ({result.comparison.value})")

    print("\nAll benchmark tests passed!")
