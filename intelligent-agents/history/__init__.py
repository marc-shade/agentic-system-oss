"""
History System Module

Following the Kai Design Pattern: Track actions, generate summaries, capture learnings.
This system builds institutional knowledge over time.

Components:
- SessionTracker: Track all actions in a session
- LearningSynthesizer: Extract patterns from past sessions
- FailureAnalyzer: Learn from mistakes to avoid repeating them
- ActionSummarizer: Generate concise summaries of work done
- RateLimiter: Protect system resources from abuse
"""

from .session_tracker import SessionTracker
from .learning_synthesizer import LearningSynthesizer
from .failure_analyzer import FailureAnalyzer
from .action_summarizer import ActionSummarizer
from .rate_limiter import (
    RateLimitExceeded,
    RateLimitStats,
    SlidingWindowLimiter,
    TokenBucketLimiter,
    RateLimiterRegistry,
    rate_limited,
    get_rate_limiter,
)

__all__ = [
    'SessionTracker',
    'LearningSynthesizer',
    'FailureAnalyzer',
    'ActionSummarizer',
    'RateLimitExceeded',
    'RateLimitStats',
    'SlidingWindowLimiter',
    'TokenBucketLimiter',
    'RateLimiterRegistry',
    'rate_limited',
    'get_rate_limiter',
]
