"""
Pattern Matching Skills
=======================

Production-ready pattern detection utilities.
"""

import re
from typing import List, Dict, Any


def regex_matcher(text: str, pattern: str) -> List[str]:
    """
    Find all matches for a regex pattern.

    Args:
        text: Text to search
        pattern: Regex pattern

    Returns:
        List of matches
    """
    return re.findall(pattern, text)


def structural_pattern_finder(data: List[Dict], key_pattern: str) -> List[Dict]:
    """
    Find items matching a key pattern.

    Args:
        data: List of dicts
        key_pattern: Key to match

    Returns:
        Matching items
    """
    return [item for item in data if key_pattern in item]


def anomaly_detector(values: List[float], threshold: float = 2.0) -> List[int]:
    """
    Detect anomalies using standard deviation.

    Args:
        values: List of numeric values
        threshold: Standard deviation threshold

    Returns:
        Indices of anomalous values
    """
    if not values:
        return []

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5

    anomalies = []
    for i, value in enumerate(values):
        if abs(value - mean) > threshold * std_dev:
            anomalies.append(i)

    return anomalies
