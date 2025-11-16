"""Optimization: batch items optimally"""

def batch_optimizer(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """
    Optimize processing by batching items.

    Args:
        items: Items to batch
        batch_size: Optimal batch size

    Returns:
        Batched items
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
