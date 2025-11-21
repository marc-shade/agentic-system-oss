"""
Error Handling Skills
=====================

Production-ready error handling utilities.
"""

import time
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


def safe_executor(func: Callable, *args, default_value: Any = None, **kwargs) -> Any:
    """
    Execute function with exception handling.

    Args:
        func: Function to execute
        *args: Function arguments
        default_value: Value to return on error
        **kwargs: Function keyword arguments

    Returns:
        Function result or default_value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        return default_value


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
