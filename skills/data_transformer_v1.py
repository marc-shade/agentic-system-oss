"""Data processing: apply transformations"""

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
