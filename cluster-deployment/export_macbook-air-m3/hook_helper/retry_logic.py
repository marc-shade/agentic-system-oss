#!/usr/bin/env python3
'''
Retry Logic with Exponential Backoff
Handles transient failures automatically
'''

import time
import functools
from typing import Callable, Tuple

def retry(max_attempts=3, backoff_factor=2, initial_delay=1,
          retry_on=(Exception,), no_retry_on=()):
    '''
    Retry decorator with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        retry_on: Tuple of exceptions to retry on
        no_retry_on: Tuple of exceptions to never retry
    '''
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except no_retry_on as e:
                    # Don't retry these exceptions
                    raise
                except retry_on as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        print(f"⚠️  Attempt {attempt + 1} failed: {e}")
                        print(f"   Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        print(f"❌ All {max_attempts} attempts failed")
                        raise

            raise last_exception

        return wrapper
    return decorator

# Specific retry configurations
retry_network = retry(
    max_attempts=3,
    backoff_factor=2,
    retry_on=(ConnectionError, TimeoutError),
    no_retry_on=(PermissionError, FileNotFoundError)
)

retry_file_operation = retry(
    max_attempts=2,
    backoff_factor=1.5,
    retry_on=(OSError, IOError),
    no_retry_on=(PermissionError, FileNotFoundError)
)
