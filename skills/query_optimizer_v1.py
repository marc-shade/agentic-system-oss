"""Optimization: optimize query strings"""

def query_optimizer(query: str) -> str:
    """
    Optimize SQL-like query string.

    Args:
        query: Query string

    Returns:
        Optimized query
    """
    # Remove redundant whitespace
    optimized = " ".join(query.split())

    # Convert to uppercase for consistency
    keywords = ["SELECT", "FROM", "WHERE", "ORDER BY", "GROUP BY"]
    for keyword in keywords:
        optimized = optimized.replace(keyword.lower(), keyword)

    return optimized
