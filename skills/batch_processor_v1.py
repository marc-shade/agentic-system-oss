"""Data processing: batch items for efficiency"""

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
