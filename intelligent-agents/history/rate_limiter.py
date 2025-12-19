"""
Rate Limiter

Provides rate limiting and request throttling for history operations.
Following Kai pattern: Protect system resources from abuse.

Implements two algorithms:
1. Sliding Window - For simple request counting
2. Token Bucket - For smooth rate limiting with burst allowance
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any
from functools import wraps

from .constants import (
    RATE_LIMIT_FILE_OPS,
    RATE_LIMIT_SEARCH_OPS,
    RATE_LIMIT_INDEX_OPS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_BURST_MULTIPLIER,
    RATE_LIMIT_COOLDOWN_SECONDS,
    TOKEN_BUCKET_REFILL_RATE,
    TOKEN_BUCKET_MAX_TOKENS,
)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, operation: str, retry_after: float):
        self.operation = operation
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for '{operation}'. "
            f"Retry after {retry_after:.1f} seconds."
        )


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""
    operation: str
    requests_in_window: int
    window_limit: int
    window_seconds: float
    requests_blocked: int
    last_request_time: Optional[float]
    tokens_available: Optional[float] = None


class SlidingWindowLimiter:
    """Sliding window rate limiter.

    Counts requests within a time window and blocks when limit exceeded.
    Simple and predictable but can allow bursts at window boundaries.
    """

    def __init__(
        self,
        limit: int = RATE_LIMIT_FILE_OPS,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        burst_multiplier: float = RATE_LIMIT_BURST_MULTIPLIER
    ):
        """Initialize sliding window limiter.

        Args:
            limit: Maximum requests per window
            window_seconds: Time window in seconds
            burst_multiplier: Allow bursts up to limit * multiplier
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.burst_limit = int(limit * burst_multiplier)
        self._requests: deque = deque()
        self._blocked_count = 0
        self._lock = threading.Lock()

    def _cleanup_old_requests(self) -> None:
        """Remove requests outside the current window."""
        cutoff = time.time() - self.window_seconds
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    def acquire(self, operation: str = "default") -> bool:
        """Attempt to acquire a rate limit slot.

        Args:
            operation: Name of operation for error messages

        Returns:
            True if request is allowed

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        with self._lock:
            self._cleanup_old_requests()

            current_count = len(self._requests)

            # Check against burst limit (hard limit)
            if current_count >= self.burst_limit:
                self._blocked_count += 1
                # Calculate retry time
                oldest = self._requests[0] if self._requests else time.time()
                retry_after = max(
                    RATE_LIMIT_COOLDOWN_SECONDS,
                    oldest + self.window_seconds - time.time()
                )
                raise RateLimitExceeded(operation, retry_after)

            # Record this request
            self._requests.append(time.time())
            return True

    def check(self) -> bool:
        """Check if a request would be allowed (without consuming a slot).

        Returns:
            True if request would be allowed
        """
        with self._lock:
            self._cleanup_old_requests()
            return len(self._requests) < self.burst_limit

    def get_stats(self, operation: str = "default") -> RateLimitStats:
        """Get current rate limit statistics."""
        with self._lock:
            self._cleanup_old_requests()
            return RateLimitStats(
                operation=operation,
                requests_in_window=len(self._requests),
                window_limit=self.limit,
                window_seconds=self.window_seconds,
                requests_blocked=self._blocked_count,
                last_request_time=self._requests[-1] if self._requests else None
            )

    def reset(self) -> None:
        """Reset the limiter (clear all request history)."""
        with self._lock:
            self._requests.clear()
            self._blocked_count = 0


class TokenBucketLimiter:
    """Token bucket rate limiter.

    Provides smoother rate limiting with natural burst handling.
    Tokens are added at a constant rate and consumed per request.
    """

    def __init__(
        self,
        max_tokens: int = TOKEN_BUCKET_MAX_TOKENS,
        refill_rate: float = TOKEN_BUCKET_REFILL_RATE
    ):
        """Initialize token bucket limiter.

        Args:
            max_tokens: Maximum bucket capacity
            refill_rate: Tokens added per second
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self._tokens = float(max_tokens)
        self._last_refill = time.time()
        self._blocked_count = 0
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.max_tokens,
            self._tokens + elapsed * self.refill_rate
        )
        self._last_refill = now

    def acquire(self, tokens: int = 1, operation: str = "default") -> bool:
        """Attempt to acquire tokens.

        Args:
            tokens: Number of tokens to consume
            operation: Name of operation for error messages

        Returns:
            True if tokens were acquired

        Raises:
            RateLimitExceeded: If not enough tokens available
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            self._blocked_count += 1
            # Calculate time until enough tokens available
            tokens_needed = tokens - self._tokens
            retry_after = max(
                RATE_LIMIT_COOLDOWN_SECONDS,
                tokens_needed / self.refill_rate
            )
            raise RateLimitExceeded(operation, retry_after)

    def check(self, tokens: int = 1) -> bool:
        """Check if tokens are available (without consuming).

        Returns:
            True if enough tokens are available
        """
        with self._lock:
            self._refill()
            return self._tokens >= tokens

    def get_stats(self, operation: str = "default") -> RateLimitStats:
        """Get current rate limit statistics."""
        with self._lock:
            self._refill()
            return RateLimitStats(
                operation=operation,
                requests_in_window=int(self.max_tokens - self._tokens),
                window_limit=self.max_tokens,
                window_seconds=self.max_tokens / self.refill_rate,
                requests_blocked=self._blocked_count,
                last_request_time=self._last_refill,
                tokens_available=self._tokens
            )

    def reset(self) -> None:
        """Reset the bucket to full capacity."""
        with self._lock:
            self._tokens = float(self.max_tokens)
            self._last_refill = time.time()
            self._blocked_count = 0


class RateLimiterRegistry:
    """Registry of rate limiters for different operations.

    Provides centralized management of rate limiters with defaults
    for common history system operations.
    """

    _instance: Optional['RateLimiterRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'RateLimiterRegistry':
        """Singleton pattern for global registry."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize registry with default limiters."""
        if self._initialized:
            return

        self._limiters: Dict[str, SlidingWindowLimiter] = {}
        self._token_limiters: Dict[str, TokenBucketLimiter] = {}

        # Register default limiters for history operations
        self.register("file_read", RATE_LIMIT_FILE_OPS)
        self.register("file_write", RATE_LIMIT_FILE_OPS)
        self.register("search", RATE_LIMIT_SEARCH_OPS)
        self.register("index_update", RATE_LIMIT_INDEX_OPS)
        self.register("session_load", RATE_LIMIT_FILE_OPS)
        self.register("pattern_extraction", RATE_LIMIT_SEARCH_OPS)

        self._initialized = True

    def register(
        self,
        operation: str,
        limit: int = RATE_LIMIT_FILE_OPS,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        use_token_bucket: bool = False
    ) -> None:
        """Register a rate limiter for an operation.

        Args:
            operation: Operation name
            limit: Requests per window (or max tokens)
            window_seconds: Window size (or bucket refill time)
            use_token_bucket: Use token bucket instead of sliding window
        """
        if use_token_bucket:
            refill_rate = limit / window_seconds
            self._token_limiters[operation] = TokenBucketLimiter(
                max_tokens=limit,
                refill_rate=refill_rate
            )
        else:
            self._limiters[operation] = SlidingWindowLimiter(
                limit=limit,
                window_seconds=window_seconds
            )

    def acquire(self, operation: str, tokens: int = 1) -> bool:
        """Acquire a rate limit slot for an operation.

        Args:
            operation: Operation name
            tokens: Tokens to consume (for token bucket)

        Returns:
            True if allowed

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        if operation in self._token_limiters:
            return self._token_limiters[operation].acquire(tokens, operation)
        elif operation in self._limiters:
            return self._limiters[operation].acquire(operation)
        else:
            # No limiter registered, allow by default
            return True

    def check(self, operation: str, tokens: int = 1) -> bool:
        """Check if operation would be allowed."""
        if operation in self._token_limiters:
            return self._token_limiters[operation].check(tokens)
        elif operation in self._limiters:
            return self._limiters[operation].check()
        return True

    def get_stats(self, operation: str) -> Optional[RateLimitStats]:
        """Get stats for an operation."""
        if operation in self._token_limiters:
            return self._token_limiters[operation].get_stats(operation)
        elif operation in self._limiters:
            return self._limiters[operation].get_stats(operation)
        return None

    def get_all_stats(self) -> Dict[str, RateLimitStats]:
        """Get stats for all registered operations."""
        stats = {}
        for op, limiter in self._limiters.items():
            stats[op] = limiter.get_stats(op)
        for op, limiter in self._token_limiters.items():
            stats[op] = limiter.get_stats(op)
        return stats

    def reset(self, operation: Optional[str] = None) -> None:
        """Reset limiter(s).

        Args:
            operation: Specific operation to reset, or None for all
        """
        if operation:
            if operation in self._limiters:
                self._limiters[operation].reset()
            if operation in self._token_limiters:
                self._token_limiters[operation].reset()
        else:
            for limiter in self._limiters.values():
                limiter.reset()
            for limiter in self._token_limiters.values():
                limiter.reset()


def rate_limited(
    operation: str,
    tokens: int = 1,
    on_exceeded: Optional[Callable[[RateLimitExceeded], Any]] = None
):
    """Decorator to apply rate limiting to a function.

    Args:
        operation: Operation name for the rate limiter
        tokens: Tokens to consume (for token bucket limiters)
        on_exceeded: Optional callback when rate limit exceeded.
                    If returns a value, that value is returned instead of raising.

    Example:
        @rate_limited("file_read")
        def read_session(self, session_id: str):
            ...

        @rate_limited("search", on_exceeded=lambda e: [])
        def search_sessions(self, query: str):
            ...  # Returns [] when rate limited
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            registry = RateLimiterRegistry()
            try:
                registry.acquire(operation, tokens)
                return func(*args, **kwargs)
            except RateLimitExceeded as e:
                if on_exceeded is not None:
                    return on_exceeded(e)
                raise
        return wrapper
    return decorator


# Module-level singleton for convenience
_registry: Optional[RateLimiterRegistry] = None


def get_rate_limiter() -> RateLimiterRegistry:
    """Get the global rate limiter registry."""
    global _registry
    if _registry is None:
        _registry = RateLimiterRegistry()
    return _registry


if __name__ == '__main__':
    import time

    # Self-test: Sliding Window Limiter
    print("Testing SlidingWindowLimiter...")
    limiter = SlidingWindowLimiter(limit=5, window_seconds=1.0)

    # Should allow 5 requests
    for i in range(5):
        assert limiter.acquire("test") == True

    # 6th request should fail (within burst limit of 7.5 -> 7)
    try:
        for i in range(5):  # Try to exceed burst
            limiter.acquire("test")
        print("  FAIL: Should have raised RateLimitExceeded")
    except RateLimitExceeded as e:
        assert "test" in str(e)
        print(f"  OK: Correctly blocked after burst ({e.retry_after:.1f}s retry)")

    # Wait for window to clear
    time.sleep(1.1)
    assert limiter.acquire("test") == True
    print("  OK: Allowed after window expired")

    # Self-test: Token Bucket Limiter
    print("\nTesting TokenBucketLimiter...")
    bucket = TokenBucketLimiter(max_tokens=10, refill_rate=5.0)

    # Should allow 10 tokens immediately
    for i in range(10):
        assert bucket.acquire(1, "test") == True

    # 11th should fail
    try:
        bucket.acquire(1, "test")
        print("  FAIL: Should have raised RateLimitExceeded")
    except RateLimitExceeded as e:
        print(f"  OK: Correctly blocked (retry in {e.retry_after:.1f}s)")

    # Wait for refill (0.5s = 2.5 tokens)
    time.sleep(0.5)
    assert bucket.check(2) == True
    print("  OK: Tokens refilled correctly")

    # Self-test: Registry
    print("\nTesting RateLimiterRegistry...")
    registry = get_rate_limiter()

    # Default limiters should exist
    assert registry.check("file_read") == True
    assert registry.check("search") == True

    # Stats should work
    stats = registry.get_stats("file_read")
    assert stats is not None
    assert stats.operation == "file_read"
    print(f"  OK: file_read stats: {stats.requests_in_window}/{stats.window_limit}")

    # Custom limiter
    registry.register("custom_op", limit=3, window_seconds=1.0)
    for i in range(3):
        registry.acquire("custom_op")

    try:
        for i in range(5):  # Exceed limit
            registry.acquire("custom_op")
        print("  FAIL: Should have blocked custom_op")
    except RateLimitExceeded:
        print("  OK: Custom limiter working")

    # Self-test: Decorator
    print("\nTesting @rate_limited decorator...")

    @rate_limited("test_decorated", on_exceeded=lambda e: "rate_limited")
    def test_func():
        return "success"

    # Should succeed initially
    registry.register("test_decorated", limit=2, window_seconds=1.0)
    assert test_func() == "success"
    assert test_func() == "success"

    # Should return fallback on rate limit
    for i in range(5):  # Exceed burst
        result = test_func()
    assert result == "rate_limited"
    print("  OK: Decorator with fallback working")

    print("\nAll rate limiter tests passed!")
