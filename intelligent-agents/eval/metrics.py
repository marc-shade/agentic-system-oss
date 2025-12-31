"""
Evaluation Metrics for Skill Testing

Provides comprehensive metrics calculation for agent skill evaluation.
Following Kai pattern: rigorous, deterministic measurement.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import statistics
import math


class MetricType(Enum):
    """Types of evaluation metrics."""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    COVERAGE = "coverage"
    CUSTOM = "custom"


@dataclass
class MetricValue:
    """A single metric measurement."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def formatted(self) -> str:
        """Format metric value for display."""
        if self.metric_type in (MetricType.ACCURACY, MetricType.PRECISION,
                                 MetricType.RECALL, MetricType.F1_SCORE,
                                 MetricType.SUCCESS_RATE, MetricType.ERROR_RATE,
                                 MetricType.COVERAGE):
            return f"{self.value:.2%}"
        elif self.metric_type == MetricType.LATENCY:
            return f"{self.value:.2f}ms"
        elif self.metric_type == MetricType.THROUGHPUT:
            return f"{self.value:.2f}/s"
        return f"{self.value:.4f}"


@dataclass
class MetricThreshold:
    """Threshold for metric evaluation."""
    metric_type: MetricType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    target_value: Optional[float] = None
    tolerance: float = 0.05

    def evaluate(self, value: float) -> Tuple[bool, str]:
        """
        Evaluate if value meets threshold.

        Returns:
            Tuple of (passed, reason)
        """
        if self.min_value is not None and value < self.min_value:
            return False, f"Below minimum ({value:.4f} < {self.min_value:.4f})"

        if self.max_value is not None and value > self.max_value:
            return False, f"Above maximum ({value:.4f} > {self.max_value:.4f})"

        if self.target_value is not None:
            diff = abs(value - self.target_value)
            if diff > self.tolerance:
                return False, f"Outside tolerance ({value:.4f} vs target {self.target_value:.4f})"

        return True, "Within acceptable range"


class EvalMetrics:
    """
    Comprehensive evaluation metrics calculator.

    Provides methods for calculating various performance metrics
    from evaluation results.
    """

    def __init__(self):
        self.measurements: List[MetricValue] = []
        self.thresholds: Dict[str, MetricThreshold] = {}

    def record(self, name: str, value: float, metric_type: MetricType,
               metadata: Optional[Dict] = None) -> MetricValue:
        """Record a metric measurement."""
        measurement = MetricValue(
            name=name,
            value=value,
            metric_type=metric_type,
            metadata=metadata or {}
        )
        self.measurements.append(measurement)
        return measurement

    def set_threshold(self, name: str, threshold: MetricThreshold) -> None:
        """Set a threshold for a metric."""
        self.thresholds[name] = threshold

    def get_measurements(self, name: Optional[str] = None,
                        metric_type: Optional[MetricType] = None) -> List[MetricValue]:
        """Get measurements, optionally filtered."""
        results = self.measurements

        if name:
            results = [m for m in results if m.name == name]
        if metric_type:
            results = [m for m in results if m.metric_type == metric_type]

        return results

    def evaluate_thresholds(self) -> Dict[str, Tuple[bool, str]]:
        """Evaluate all recorded metrics against thresholds."""
        results = {}

        for name, threshold in self.thresholds.items():
            measurements = self.get_measurements(name=name)
            if measurements:
                # Use latest measurement
                latest = max(measurements, key=lambda m: m.timestamp)
                results[name] = threshold.evaluate(latest.value)
            else:
                results[name] = (False, "No measurements recorded")

        return results

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics for all metrics."""
        summary = {}

        # Group by name
        by_name: Dict[str, List[float]] = {}
        for m in self.measurements:
            if m.name not in by_name:
                by_name[m.name] = []
            by_name[m.name].append(m.value)

        for name, values in by_name.items():
            if len(values) == 1:
                summary[name] = {"value": values[0]}
            else:
                summary[name] = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                }

        return summary

    def clear(self) -> None:
        """Clear all measurements."""
        self.measurements.clear()


def calculate_accuracy(
    predictions: List[Any],
    ground_truth: List[Any],
    strict: bool = True
) -> float:
    """
    Calculate accuracy score.

    Args:
        predictions: Predicted values
        ground_truth: True values
        strict: If True, require exact match; if False, allow partial

    Returns:
        Accuracy score (0.0 to 1.0)
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("Predictions and ground truth must have same length")

    if not predictions:
        return 0.0

    correct = 0
    for pred, truth in zip(predictions, ground_truth):
        if strict:
            if pred == truth:
                correct += 1
        else:
            # Partial matching for strings
            if isinstance(pred, str) and isinstance(truth, str):
                if truth.lower() in pred.lower() or pred.lower() in truth.lower():
                    correct += 1
            elif pred == truth:
                correct += 1

    return correct / len(predictions)


def calculate_precision(
    true_positives: int,
    false_positives: int
) -> float:
    """
    Calculate precision score.

    Precision = TP / (TP + FP)

    Args:
        true_positives: Number of true positives
        false_positives: Number of false positives

    Returns:
        Precision score (0.0 to 1.0)
    """
    total = true_positives + false_positives
    if total == 0:
        return 0.0
    return true_positives / total


def calculate_recall(
    true_positives: int,
    false_negatives: int
) -> float:
    """
    Calculate recall score.

    Recall = TP / (TP + FN)

    Args:
        true_positives: Number of true positives
        false_negatives: Number of false negatives

    Returns:
        Recall score (0.0 to 1.0)
    """
    total = true_positives + false_negatives
    if total == 0:
        return 0.0
    return true_positives / total


def calculate_f1_score(
    precision: Optional[float] = None,
    recall: Optional[float] = None,
    true_positives: Optional[int] = None,
    false_positives: Optional[int] = None,
    false_negatives: Optional[int] = None
) -> float:
    """
    Calculate F1 score.

    F1 = 2 * (precision * recall) / (precision + recall)

    Args:
        precision: Pre-calculated precision (optional)
        recall: Pre-calculated recall (optional)
        true_positives: TP count (used if precision/recall not provided)
        false_positives: FP count
        false_negatives: FN count

    Returns:
        F1 score (0.0 to 1.0)
    """
    if precision is None:
        if true_positives is None or false_positives is None:
            raise ValueError("Must provide precision or TP/FP counts")
        precision = calculate_precision(true_positives, false_positives)

    if recall is None:
        if true_positives is None or false_negatives is None:
            raise ValueError("Must provide recall or TP/FN counts")
        recall = calculate_recall(true_positives, false_negatives)

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def calculate_latency_percentile(
    latencies: List[float],
    percentile: float = 95.0
) -> float:
    """
    Calculate latency percentile.

    Args:
        latencies: List of latency measurements (ms)
        percentile: Percentile to calculate (0-100)

    Returns:
        Latency at given percentile
    """
    if not latencies:
        return 0.0

    if percentile < 0 or percentile > 100:
        raise ValueError("Percentile must be between 0 and 100")

    sorted_latencies = sorted(latencies)
    index = (percentile / 100) * (len(sorted_latencies) - 1)

    lower = int(math.floor(index))
    upper = int(math.ceil(index))

    if lower == upper:
        return sorted_latencies[lower]

    # Linear interpolation
    fraction = index - lower
    return sorted_latencies[lower] + fraction * (sorted_latencies[upper] - sorted_latencies[lower])


def calculate_latency_stats(latencies: List[float]) -> Dict[str, float]:
    """
    Calculate comprehensive latency statistics.

    Args:
        latencies: List of latency measurements (ms)

    Returns:
        Dictionary with mean, median, p50, p90, p95, p99, min, max
    """
    if not latencies:
        return {
            "mean": 0.0,
            "median": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "min": 0.0,
            "max": 0.0,
        }

    return {
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p50": calculate_latency_percentile(latencies, 50),
        "p90": calculate_latency_percentile(latencies, 90),
        "p95": calculate_latency_percentile(latencies, 95),
        "p99": calculate_latency_percentile(latencies, 99),
        "min": min(latencies),
        "max": max(latencies),
    }


def calculate_throughput(
    count: int,
    duration_seconds: float
) -> float:
    """
    Calculate throughput (operations per second).

    Args:
        count: Number of operations completed
        duration_seconds: Time taken in seconds

    Returns:
        Operations per second
    """
    if duration_seconds <= 0:
        return 0.0
    return count / duration_seconds


def calculate_error_rate(
    errors: int,
    total: int
) -> float:
    """
    Calculate error rate.

    Args:
        errors: Number of errors
        total: Total attempts

    Returns:
        Error rate (0.0 to 1.0)
    """
    if total == 0:
        return 0.0
    return errors / total


def calculate_success_rate(
    successes: int,
    total: int
) -> float:
    """
    Calculate success rate.

    Args:
        successes: Number of successes
        total: Total attempts

    Returns:
        Success rate (0.0 to 1.0)
    """
    if total == 0:
        return 0.0
    return successes / total


def calculate_coverage(
    covered: int,
    total: int
) -> float:
    """
    Calculate coverage percentage.

    Args:
        covered: Number of items covered
        total: Total items

    Returns:
        Coverage (0.0 to 1.0)
    """
    if total == 0:
        return 0.0
    return covered / total


def calculate_confusion_matrix(
    predictions: List[bool],
    ground_truth: List[bool]
) -> Dict[str, int]:
    """
    Calculate confusion matrix components.

    Args:
        predictions: Predicted boolean values
        ground_truth: True boolean values

    Returns:
        Dictionary with TP, TN, FP, FN counts
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("Predictions and ground truth must have same length")

    tp = tn = fp = fn = 0

    for pred, truth in zip(predictions, ground_truth):
        if pred and truth:
            tp += 1
        elif not pred and not truth:
            tn += 1
        elif pred and not truth:
            fp += 1
        else:  # not pred and truth
            fn += 1

    return {
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
    }


def calculate_all_classification_metrics(
    predictions: List[bool],
    ground_truth: List[bool]
) -> Dict[str, float]:
    """
    Calculate all classification metrics at once.

    Args:
        predictions: Predicted boolean values
        ground_truth: True boolean values

    Returns:
        Dictionary with accuracy, precision, recall, f1, specificity
    """
    cm = calculate_confusion_matrix(predictions, ground_truth)
    tp = cm["true_positives"]
    tn = cm["true_negatives"]
    fp = cm["false_positives"]
    fn = cm["false_negatives"]

    total = tp + tn + fp + fn

    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = calculate_precision(tp, fp)
    recall = calculate_recall(tp, fn)
    f1 = calculate_f1_score(precision=precision, recall=recall)
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "specificity": specificity,
        **cm
    }


def calculate_weighted_score(
    scores: Dict[str, float],
    weights: Dict[str, float]
) -> float:
    """
    Calculate weighted average score.

    Args:
        scores: Dictionary of metric names to scores
        weights: Dictionary of metric names to weights

    Returns:
        Weighted average score
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for name, score in scores.items():
        weight = weights.get(name, 1.0)
        weighted_sum += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight


if __name__ == '__main__':
    print("Metrics Module Self-Test")
    print("=" * 50)

    # Test accuracy
    preds = [True, True, False, True, False]
    truth = [True, False, False, True, True]
    acc = calculate_accuracy(preds, truth)
    assert acc == 0.6, f"Expected 0.6, got {acc}"
    print(f"Accuracy: {acc:.2%}")

    # Test precision/recall/F1
    metrics = calculate_all_classification_metrics(preds, truth)
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"F1 Score: {metrics['f1_score']:.2%}")

    # Test latency percentiles
    latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    p95 = calculate_latency_percentile(latencies, 95)
    print(f"\nP95 Latency: {p95:.1f}ms")

    stats = calculate_latency_stats(latencies)
    print(f"Mean Latency: {stats['mean']:.1f}ms")
    print(f"Median Latency: {stats['median']:.1f}ms")

    # Test throughput
    throughput = calculate_throughput(1000, 10)
    assert throughput == 100.0
    print(f"\nThroughput: {throughput:.0f} ops/s")

    # Test EvalMetrics class
    eval_metrics = EvalMetrics()
    eval_metrics.record("accuracy", 0.95, MetricType.ACCURACY)
    eval_metrics.record("latency_p95", 45.0, MetricType.LATENCY)
    eval_metrics.record("throughput", 500.0, MetricType.THROUGHPUT)

    eval_metrics.set_threshold("accuracy", MetricThreshold(
        metric_type=MetricType.ACCURACY,
        min_value=0.90
    ))
    eval_metrics.set_threshold("latency_p95", MetricThreshold(
        metric_type=MetricType.LATENCY,
        max_value=100.0
    ))

    threshold_results = eval_metrics.evaluate_thresholds()
    print(f"\nThreshold evaluation:")
    for name, (passed, reason) in threshold_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status} - {reason}")

    # Test weighted score
    scores = {"accuracy": 0.9, "recall": 0.8, "precision": 0.85}
    weights = {"accuracy": 2.0, "recall": 1.0, "precision": 1.5}
    weighted = calculate_weighted_score(scores, weights)
    print(f"\nWeighted Score: {weighted:.2%}")

    print("\nAll metrics tests passed!")
