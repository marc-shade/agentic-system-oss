"""Error handling: retry logic decorator"""

def retry_handler(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator for retry logic.

    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")

                    if attempt < max_retries - 1:
                        time.sleep(delay)

            logger.error(f"All {max_retries} attempts failed")
            raise last_exception

        return wrapper
    return decorator
