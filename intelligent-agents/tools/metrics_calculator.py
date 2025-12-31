"""
Deterministic Metrics Calculator

NO AI - Pure code for metrics and statistics.
Following Kai pattern: "If I can do it in code, I do it in code first."
"""

import math
from typing import List, Dict, Optional, Tuple, Union
from collections import Counter
from datetime import datetime, timedelta


class MetricsCalculator:
    """Deterministic metrics calculations - no AI required."""

    # Statistical Functions
    @staticmethod
    def mean(values: List[float]) -> float:
        """Calculate arithmetic mean."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def median(values: List[float]) -> float:
        """Calculate median value."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]

    @staticmethod
    def mode(values: List[float]) -> List[float]:
        """Calculate mode (most frequent values)."""
        if not values:
            return []
        counter = Counter(values)
        max_count = max(counter.values())
        return [val for val, count in counter.items() if count == max_count]

    @staticmethod
    def variance(values: List[float], sample: bool = True) -> float:
        """Calculate variance. Use sample=True for sample variance."""
        if len(values) < 2:
            return 0.0
        mean_val = MetricsCalculator.mean(values)
        squared_diffs = [(x - mean_val) ** 2 for x in values]
        divisor = len(values) - 1 if sample else len(values)
        return sum(squared_diffs) / divisor

    @staticmethod
    def std_dev(values: List[float], sample: bool = True) -> float:
        """Calculate standard deviation."""
        return math.sqrt(MetricsCalculator.variance(values, sample))

    @staticmethod
    def percentile(values: List[float], p: float) -> float:
        """Calculate p-th percentile (0-100)."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)

    @staticmethod
    def quartiles(values: List[float]) -> Tuple[float, float, float]:
        """Calculate Q1, Q2 (median), Q3."""
        return (
            MetricsCalculator.percentile(values, 25),
            MetricsCalculator.percentile(values, 50),
            MetricsCalculator.percentile(values, 75)
        )

    @staticmethod
    def iqr(values: List[float]) -> float:
        """Calculate interquartile range."""
        q1, _, q3 = MetricsCalculator.quartiles(values)
        return q3 - q1

    @staticmethod
    def min_max(values: List[float]) -> Tuple[float, float]:
        """Get min and max values."""
        if not values:
            return (0.0, 0.0)
        return (min(values), max(values))

    @staticmethod
    def range_val(values: List[float]) -> float:
        """Calculate range (max - min)."""
        if not values:
            return 0.0
        return max(values) - min(values)

    @staticmethod
    def sum_values(values: List[float]) -> float:
        """Calculate sum."""
        return sum(values)

    @staticmethod
    def count(values: List) -> int:
        """Count items."""
        return len(values)

    # Rate and Ratio Calculations
    @staticmethod
    def rate(numerator: float, denominator: float, per: float = 1.0) -> float:
        """Calculate rate per unit."""
        if denominator == 0:
            return 0.0
        return (numerator / denominator) * per

    @staticmethod
    def percentage(part: float, whole: float) -> float:
        """Calculate percentage."""
        if whole == 0:
            return 0.0
        return (part / whole) * 100

    @staticmethod
    def ratio(a: float, b: float) -> str:
        """Calculate ratio in a:b format."""
        if b == 0:
            return "inf:1" if a > 0 else "0:0"
        if a == 0:
            return "0:1"
        # Simplify using GCD
        from math import gcd
        g = gcd(int(a), int(b)) if a == int(a) and b == int(b) else 1
        return f"{int(a/g)}:{int(b/g)}"

    @staticmethod
    def change_rate(old: float, new: float) -> float:
        """Calculate percentage change."""
        if old == 0:
            return float('inf') if new > 0 else 0.0
        return ((new - old) / abs(old)) * 100

    @staticmethod
    def growth_rate(values: List[float]) -> float:
        """Calculate compound growth rate."""
        if len(values) < 2 or values[0] == 0:
            return 0.0
        return ((values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1) * 100

    # Time-Series Metrics
    @staticmethod
    def moving_average(values: List[float], window: int) -> List[float]:
        """Calculate simple moving average."""
        if window > len(values):
            return []
        result = []
        for i in range(len(values) - window + 1):
            result.append(sum(values[i:i+window]) / window)
        return result

    @staticmethod
    def exponential_moving_average(values: List[float], alpha: float = 0.3) -> List[float]:
        """Calculate exponential moving average."""
        if not values:
            return []
        result = [values[0]]
        for i in range(1, len(values)):
            ema = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(ema)
        return result

    @staticmethod
    def trend_direction(values: List[float]) -> str:
        """Determine trend direction: up, down, or stable."""
        if len(values) < 2:
            return "stable"
        first_half = MetricsCalculator.mean(values[:len(values)//2])
        second_half = MetricsCalculator.mean(values[len(values)//2:])
        diff = second_half - first_half
        threshold = MetricsCalculator.std_dev(values) * 0.1
        if diff > threshold:
            return "up"
        elif diff < -threshold:
            return "down"
        return "stable"

    # Performance Metrics
    @staticmethod
    def throughput(count: int, duration_seconds: float) -> float:
        """Calculate throughput (items per second)."""
        if duration_seconds == 0:
            return 0.0
        return count / duration_seconds

    @staticmethod
    def latency_stats(latencies: List[float]) -> Dict[str, float]:
        """Calculate latency statistics."""
        if not latencies:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0, "avg": 0, "max": 0}
        return {
            "p50": MetricsCalculator.percentile(latencies, 50),
            "p90": MetricsCalculator.percentile(latencies, 90),
            "p95": MetricsCalculator.percentile(latencies, 95),
            "p99": MetricsCalculator.percentile(latencies, 99),
            "avg": MetricsCalculator.mean(latencies),
            "max": max(latencies)
        }

    @staticmethod
    def error_rate(errors: int, total: int) -> float:
        """Calculate error rate as percentage."""
        return MetricsCalculator.percentage(errors, total)

    @staticmethod
    def success_rate(successes: int, total: int) -> float:
        """Calculate success rate as percentage."""
        return MetricsCalculator.percentage(successes, total)

    @staticmethod
    def availability(uptime_seconds: float, total_seconds: float) -> float:
        """Calculate availability as percentage."""
        return MetricsCalculator.percentage(uptime_seconds, total_seconds)

    # Score Calculations
    @staticmethod
    def normalize(value: float, min_val: float, max_val: float) -> float:
        """Normalize value to 0-1 range."""
        if max_val == min_val:
            return 0.5
        return (value - min_val) / (max_val - min_val)

    @staticmethod
    def z_score(value: float, mean: float, std_dev: float) -> float:
        """Calculate z-score (standard score)."""
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev

    @staticmethod
    def weighted_average(values: List[float], weights: List[float]) -> float:
        """Calculate weighted average."""
        if len(values) != len(weights) or not values:
            return 0.0
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / total_weight

    @staticmethod
    def geometric_mean(values: List[float]) -> float:
        """Calculate geometric mean."""
        if not values or any(v <= 0 for v in values):
            return 0.0
        product = 1.0
        for v in values:
            product *= v
        return product ** (1 / len(values))

    @staticmethod
    def harmonic_mean(values: List[float]) -> float:
        """Calculate harmonic mean."""
        if not values or any(v == 0 for v in values):
            return 0.0
        return len(values) / sum(1/v for v in values)

    # Time-Based Calculations
    @staticmethod
    def time_since(timestamp: datetime) -> timedelta:
        """Calculate time elapsed since timestamp."""
        return datetime.now() - timestamp

    @staticmethod
    def time_until(timestamp: datetime) -> timedelta:
        """Calculate time remaining until timestamp."""
        return timestamp - datetime.now()

    @staticmethod
    def duration_human(seconds: float) -> str:
        """Convert seconds to human-readable duration."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        elif seconds < 86400:
            return f"{seconds/3600:.1f}h"
        else:
            return f"{seconds/86400:.1f}d"

    @staticmethod
    def bytes_human(size: int) -> str:
        """Convert bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}PB"


if __name__ == '__main__':
    # Self-test
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    assert MetricsCalculator.mean(values) == 5.5
    assert MetricsCalculator.median(values) == 5.5
    assert MetricsCalculator.sum_values(values) == 55
    assert MetricsCalculator.count(values) == 10

    assert MetricsCalculator.percentage(25, 100) == 25.0
    assert MetricsCalculator.rate(100, 10) == 10.0
    assert MetricsCalculator.change_rate(100, 150) == 50.0

    ma = MetricsCalculator.moving_average(values, 3)
    assert len(ma) == 8
    assert ma[0] == 2.0  # (1+2+3)/3

    assert MetricsCalculator.normalize(5, 0, 10) == 0.5
    assert MetricsCalculator.success_rate(95, 100) == 95.0

    assert MetricsCalculator.duration_human(90) == "1.5m"
    assert MetricsCalculator.bytes_human(1536) == "1.5KB"

    print('All MetricsCalculator tests passed!')
