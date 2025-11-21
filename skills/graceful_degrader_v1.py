"""Error handling: graceful degradation"""

def graceful_degrader(primary_func: Callable, fallback_func: Callable) -> Callable:
    """
    Create function with graceful degradation.

    Args:
        primary_func: Primary function to try
        fallback_func: Fallback function if primary fails

    Returns:
        Function that tries primary, falls back on error
    """
    def wrapper(*args, **kwargs):
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed: {e}, using fallback")
            return fallback_func(*args, **kwargs)

    return wrapper
