"""Pattern matching: structural patterns in data"""

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
