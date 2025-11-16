"""Data processing: filter positive numbers"""

def filter_positive_numbers(data: List[float]) -> List[float]:
    """
    Filter positive numbers from a list.

    Args:
        data: List of numbers

    Returns:
        List of positive numbers only
    """
    return [x for x in data if x > 0]
