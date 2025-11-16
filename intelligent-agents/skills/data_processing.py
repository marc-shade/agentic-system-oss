"""
Data Processing Skills
=====================

Production-ready data processing utilities.
"""

from typing import List, Any, Callable, Dict


def filter_positive_numbers(data: List[float]) -> List[float]:
    """
    Filter positive numbers from a list.

    Args:
        data: List of numbers

    Returns:
        List of positive numbers only
    """
    return [x for x in data if x > 0]


def batch_processor(data: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """
    Process data in batches.

    Args:
        data: List of items to batch
        batch_size: Size of each batch

    Returns:
        List of batches
    """
    return [data[i:i + batch_size] for i in range(0, len(data), batch_size)]


def data_transformer(data: List[Dict], transform_fn: Callable) -> List[Dict]:
    """
    Apply transformation function to each data item.

    Args:
        data: List of data dicts
        transform_fn: Function to apply to each item

    Returns:
        Transformed data list
    """
    return [transform_fn(item) for item in data]
