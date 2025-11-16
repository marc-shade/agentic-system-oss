#!/usr/bin/env python3
"""
Circuit Breaker Pattern for GitMQ Cluster
=========================================

Implements circuit breaker pattern to prevent cascading failures
and allow graceful degradation when services are unavailable.

Circuit Breaker States:
    CLOSED: Normal operation, requests pass through
    OPEN: Failures exceeded threshold, requests fail fast
    HALF_OPEN: Testing if service recovered, limited requests

Features:
- Automatic failure detection
- Configurable thresholds and timeouts
- Graceful degradation
- Health monitoring
- Integration with observability

Usage:
    breaker = CircuitBreaker(
        name="code_execution",
        failure_threshold=5,
        timeout_seconds=60,
        half_open_max_calls=3
    )

    # Protect operation
    @breaker.call
    def execute_code(code):
        return run_code(code)

    # Or use context manager
    with breaker:
        result = execute_code(code)
"""

import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Dict
from contextlib import contextmanager
from datetime import datetime, timedelta


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Blocking requests (fail fast)
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    # Failure detection
    failure_threshold: int = 5           # Failures before opening
    timeout_seconds: float = 60          # Seconds before half-open attempt
    success_threshold: int = 3           # Successes to close from half-open

    # Rate limiting in half-open state
    half_open_max_calls: int = 3         # Max concurrent calls in half-open

    # Monitoring window
    window_seconds: float = 300          # Rolling window for failure counting

    # Exception handling
    expected_exceptions: tuple = (Exception,)  # Exceptions that trigger opening


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    opened_at: Optional[float] = None
    half_opened_at: Optional[float] = None
    half_open_calls: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for protecting operations from cascading failures.

    Tracks failures and automatically opens circuit when threshold
    exceeded, preventing further calls until timeout expires.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique name for this circuit breaker
            config: CircuitBreakerConfig instance
            **kwargs: Config parameters (if config not provided)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig(**kwargs)
        self.stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        self._failure_times: list[float] = []

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with circuit breaker.

        Usage:
            @breaker.call
            def my_function():
                ...
        """
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper

    @contextmanager
    def __enter__(self):
        """Context manager entry - check if call allowed."""
        self._before_call()
        try:
            yield self
            self._on_success()
        except self.config.expected_exceptions as e:
            self._on_failure()
            raise
        except CircuitBreakerError:
            raise
        except Exception as e:
            # Unexpected exception - don't count as circuit failure
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function protected by circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        with self:
            return func(*args, **kwargs)

    def _before_call(self):
        """Check circuit state before allowing call."""
        with self._lock:
            self.stats.total_calls += 1

            # Check current state
            if self.stats.state == CircuitState.CLOSED:
                # Normal operation
                return

            elif self.stats.state == CircuitState.OPEN:
                # Check if timeout expired
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                    return
                else:
                    # Still open - fail fast
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN "
                        f"(timeout in {self._time_until_reset():.1f}s)"
                    )

            elif self.stats.state == CircuitState.HALF_OPEN:
                # Check if call allowed in half-open
                if self.stats.half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is HALF_OPEN "
                        f"(max concurrent calls reached)"
                    )
                self.stats.half_open_calls += 1
                return

    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self.stats.total_successes += 1

            if self.stats.state == CircuitState.HALF_OPEN:
                self.stats.success_count += 1
                self.stats.half_open_calls = max(0, self.stats.half_open_calls - 1)

                # Check if enough successes to close
                if self.stats.success_count >= self.config.success_threshold:
                    self._transition_to_closed()

    def _on_failure(self):
        """Handle failed call."""
        with self._lock:
            current_time = time.time()
            self.stats.total_failures += 1
            self.stats.failure_count += 1
            self.stats.last_failure_time = current_time
            self._failure_times.append(current_time)

            # Clean old failures outside window
            self._clean_old_failures()

            if self.stats.state == CircuitState.CLOSED:
                # Check if should open
                if self._should_open():
                    self._transition_to_open()

            elif self.stats.state == CircuitState.HALF_OPEN:
                # Immediate open on any failure in half-open
                self.stats.half_open_calls = max(0, self.stats.half_open_calls - 1)
                self._transition_to_open()

    def _should_open(self) -> bool:
        """Check if circuit should open based on failures."""
        return len(self._failure_times) >= self.config.failure_threshold

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset (transition to half-open)."""
        if self.stats.opened_at is None:
            return False

        elapsed = time.time() - self.stats.opened_at
        return elapsed >= self.config.timeout_seconds

    def _time_until_reset(self) -> float:
        """Calculate time until reset attempt."""
        if self.stats.opened_at is None:
            return 0.0

        elapsed = time.time() - self.stats.opened_at
        remaining = self.config.timeout_seconds - elapsed
        return max(0.0, remaining)

    def _clean_old_failures(self):
        """Remove failures outside monitoring window."""
        current_time = time.time()
        cutoff = current_time - self.config.window_seconds
        self._failure_times = [t for t in self._failure_times if t > cutoff]

    def _transition_to_open(self):
        """Transition to OPEN state."""
        self.stats.state = CircuitState.OPEN
        self.stats.opened_at = time.time()
        self.stats.last_state_change = time.time()
        self.stats.success_count = 0

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.half_opened_at = time.time()
        self.stats.last_state_change = time.time()
        self.stats.success_count = 0
        self.stats.half_open_calls = 0

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        self.stats.state = CircuitState.CLOSED
        self.stats.last_state_change = time.time()
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.stats.opened_at = None
        self.stats.half_opened_at = None
        self._failure_times.clear()

    def force_open(self):
        """Manually force circuit to OPEN state."""
        with self._lock:
            self._transition_to_open()

    def force_close(self):
        """Manually force circuit to CLOSED state."""
        with self._lock:
            self._transition_to_closed()

    def reset(self):
        """Reset circuit breaker to initial state."""
        with self._lock:
            self.stats = CircuitBreakerStats()
            self._failure_times.clear()

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.stats.state

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.stats.state.value,
                "failure_count": len(self._failure_times),
                "success_count": self.stats.success_count,
                "total_calls": self.stats.total_calls,
                "total_successes": self.stats.total_successes,
                "total_failures": self.stats.total_failures,
                "last_state_change": datetime.fromtimestamp(
                    self.stats.last_state_change
                ).isoformat(),
                "time_until_reset": self._time_until_reset() if self.stats.state == CircuitState.OPEN else None
            }


# ============================================================================
# Circuit Breaker Registry
# ============================================================================

class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides centralized access and monitoring of all circuit breakers
    in the system.
    """

    def __init__(self):
        """Initialize registry."""
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        **kwargs
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            config: Configuration (if creating new)
            **kwargs: Config parameters

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config, **kwargs)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }

    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global registry
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker from global registry."""
    return _registry.get_or_create(name, **kwargs)


# ============================================================================
# Example Usage
# ============================================================================

def example_circuit_breaker():
    """Example: Circuit breaker usage."""
    print("\n" + "=" * 70)
    print("Circuit Breaker Example")
    print("=" * 70)

    # Create circuit breaker
    breaker = CircuitBreaker(
        name="example_service",
        failure_threshold=3,
        timeout_seconds=5,
        success_threshold=2
    )

    print(f"\n1. Initial state: {breaker.get_state()}")

    # Simulate successful calls
    print("\n2. Successful calls:")
    for i in range(3):
        try:
            with breaker:
                print(f"   Call {i+1}: Success")
        except CircuitBreakerError as e:
            print(f"   Call {i+1}: {e}")

    # Simulate failures
    print("\n3. Failing calls (trigger circuit open):")
    for i in range(5):
        try:
            with breaker:
                if i < 3:
                    raise ValueError("Simulated failure")
                print(f"   Call {i+1}: Success")
        except ValueError:
            print(f"   Call {i+1}: Failed")
        except CircuitBreakerError as e:
            print(f"   Call {i+1}: Circuit OPEN - {e}")

    print(f"\n4. State after failures: {breaker.get_state()}")

    # Wait for timeout
    print("\n5. Waiting for timeout...")
    time.sleep(5.5)

    # Half-open state
    print(f"\n6. State after timeout: {breaker.get_state()} (should transition to HALF_OPEN)")

    # Recovery
    print("\n7. Recovery (successful calls in half-open):")
    for i in range(3):
        try:
            with breaker:
                print(f"   Call {i+1}: Success")
        except CircuitBreakerError as e:
            print(f"   Call {i+1}: {e}")

    print(f"\n8. Final state: {breaker.get_state()} (should be CLOSED)")

    # Statistics
    print("\n9. Statistics:")
    stats = breaker.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    example_circuit_breaker()
    print("\nCircuit breaker module loaded successfully ✓")
