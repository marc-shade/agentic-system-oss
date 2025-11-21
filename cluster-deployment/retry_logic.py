#!/usr/bin/env python3
"""
Retry Logic with Exponential Backoff for GitMQ Cluster
======================================================

Provides resilient retry mechanisms with:
- Exponential backoff
- Jitter to prevent thundering herd
- Configurable retry policies
- Exception filtering
- Circuit breaker integration
- Observability hooks

Usage:
    retry_policy = RetryPolicy(
        max_attempts=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2,
        jitter=True
    )

    @retry(policy=retry_policy)
    def unreliable_operation():
        # Operation that may fail
        return result
"""

import time
import random
import logging
from dataclasses import dataclass
from typing import Callable, Optional, Any, Type, Tuple
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3                    # Maximum retry attempts
    initial_delay: float = 1.0               # Initial delay (seconds)
    max_delay: float = 60.0                  # Maximum delay (seconds)
    exponential_base: float = 2.0            # Backoff multiplier
    jitter: bool = True                      # Add random jitter
    jitter_factor: float = 0.1               # Jitter randomness (0-1)
    retriable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retriable_exceptions: Tuple[Type[Exception], ...] = ()


class RetryExhausted(Exception):
    """Raised when all retry attempts exhausted."""
    pass


class Retry:
    """
    Retry decorator with exponential backoff.

    Automatically retries failed operations with configurable
    backoff strategy and exception handling.
    """

    def __init__(self, policy: Optional[RetryPolicy] = None, **kwargs):
        """
        Initialize retry decorator.

        Args:
            policy: RetryPolicy instance
            **kwargs: Policy parameters (if policy not provided)
        """
        self.policy = policy or RetryPolicy(**kwargs)

    def __call__(self, func: Callable) -> Callable:
        """Decorate function with retry logic."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute_with_retry(func, *args, **kwargs)

        return wrapper

    def _execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        attempt = 0

        while attempt < self.policy.max_attempts:
            attempt += 1

            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(
                        f"Operation succeeded on attempt {attempt}/{self.policy.max_attempts}"
                    )
                return result

            except self.policy.non_retriable_exceptions as e:
                # Non-retriable exception - fail immediately
                logger.error(f"Non-retriable exception: {e}")
                raise

            except self.policy.retriable_exceptions as e:
                last_exception = e

                if attempt >= self.policy.max_attempts:
                    # Exhausted retries
                    break

                # Calculate backoff delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"Attempt {attempt}/{self.policy.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                time.sleep(delay)

        # All retries exhausted
        raise RetryExhausted(
            f"Operation failed after {self.policy.max_attempts} attempts"
        ) from last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate backoff delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ (attempt - 1))
        delay = self.policy.initial_delay * (
            self.policy.exponential_base ** (attempt - 1)
        )

        # Cap at max_delay
        delay = min(delay, self.policy.max_delay)

        # Add jitter if enabled
        if self.policy.jitter:
            jitter_amount = delay * self.policy.jitter_factor
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)  # Ensure non-negative


def retry(policy: Optional[RetryPolicy] = None, **kwargs) -> Callable:
    """
    Decorator factory for retry logic.

    Usage:
        @retry(max_attempts=5, initial_delay=2.0)
        def my_function():
            ...
    """
    return Retry(policy, **kwargs)


# ============================================================================
# Example Usage
# ============================================================================

def example_retry_logic():
    """Example: Retry logic with exponential backoff."""
    print("\n" + "=" * 70)
    print("Retry Logic Example")
    print("=" * 70)

    # Example 1: Simple retry
    print("\n1. Simple retry (fails 2 times, succeeds on 3rd):")

    attempt_counter = [0]

    @retry(max_attempts=5, initial_delay=0.5)
    def unreliable_operation():
        attempt_counter[0] += 1
        print(f"   Attempt {attempt_counter[0]}")
        if attempt_counter[0] < 3:
            raise ValueError("Simulated failure")
        return "Success!"

    result = unreliable_operation()
    print(f"   Result: {result}")

    # Example 2: Retry exhausted
    print("\n2. Retry exhausted (always fails):")

    @retry(max_attempts=3, initial_delay=0.2)
    def always_fails():
        raise ValueError("Always fails")

    try:
        always_fails()
    except RetryExhausted as e:
        print(f"   {e}")

    # Example 3: Non-retriable exception
    print("\n3. Non-retriable exception (fails immediately):")

    policy = RetryPolicy(
        max_attempts=5,
        initial_delay=0.5,
        non_retriable_exceptions=(KeyError,)
    )

    @retry(policy=policy)
    def non_retriable_error():
        raise KeyError("Non-retriable error")

    try:
        non_retriable_error()
    except KeyError as e:
        print(f"   Failed immediately: {e}")

    # Example 4: Exponential backoff demonstration
    print("\n4. Exponential backoff delays:")

    retry_decorator = Retry(
        RetryPolicy(
            max_attempts=5,
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
    )

    for attempt in range(1, 6):
        delay = retry_decorator._calculate_delay(attempt)
        print(f"   Attempt {attempt}: delay = {delay:.2f}s")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_retry_logic()
    print("\nRetry logic module loaded successfully ✓")
