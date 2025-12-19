"""
History System Constants

Centralized configuration values for the Kai history module.
Following Kai pattern: Named constants prevent magic number confusion.
"""

# =============================================================================
# Session Tracker Constants
# =============================================================================

# Cache settings
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 100
CACHE_EVICTION_PERCENT = 10  # Remove 10% on overflow

# Index management
MAX_INDEX_ENTRIES = 1000
SESSION_ID_HASH_LENGTH = 8

# Default query limits
DEFAULT_RECENT_SESSIONS_LIMIT = 10
DEFAULT_SEARCH_LIMIT = 50
DEFAULT_ERROR_SUMMARY_DAYS = 7


# =============================================================================
# Action Summarizer Constants
# =============================================================================

# Output limits
MAX_KEY_ACTIONS = 10
MAX_FILES_TOUCHED = 20
MAX_FILES_MODIFIED = 50
MAX_ACTION_BREAKDOWN_ITEMS = 10
MAX_HIGHLIGHTS = 10
MAX_ACHIEVEMENTS = 10
MAX_CONCERNS = 10

# Text summary limits
TEXT_SUMMARY_TOP_ACTIONS = 3
TEXT_SUMMARY_MAX_ACHIEVEMENTS = 5
TEXT_SUMMARY_MAX_HIGHLIGHTS = 5
TEXT_SUMMARY_MAX_CONCERNS = 3

# Default time periods
DEFAULT_SUMMARY_DAYS = 1
DEFAULT_PRODUCTIVITY_DAYS = 7
DAYS_IN_WEEK = 7

# Thresholds
HIGH_ERROR_RATE_THRESHOLD = 0.3  # 30% error rate is concerning


# =============================================================================
# Failure Analyzer Constants
# =============================================================================

# Error message processing
ERROR_MESSAGE_MAX_LENGTH = 150
MAX_RESOLUTIONS_PER_PATTERN = 10

# Clustering thresholds
MIN_FAILURES_FOR_CLUSTER = 2
COMMON_CONTEXT_THRESHOLD_DIVISOR = 2  # threshold = len(failures) / 2

# Default query limits
DEFAULT_RECURRING_FAILURES_MIN = 3
DEFAULT_RECENT_FAILURES_DAYS = 7
DEFAULT_FAILURE_STATS_DAYS = 30

# Top-N limits
TOP_ACTION_TYPES_LIMIT = 10
MAX_SAMPLE_CONTEXTS = 5


# =============================================================================
# Learning Synthesizer Constants
# =============================================================================

# Pattern extraction
DEFAULT_PATTERN_DAYS = 30
TOP_SEQUENCES_LIMIT = 20
MIN_PATTERN_OCCURRENCES = 3
DEFAULT_SUCCESS_RATE = 0.5

# Error patterns
DEFAULT_ERROR_PATTERN_DAYS = 30
MIN_ERROR_OCCURRENCES = 2

# Learning synthesis
DEFAULT_LEARNING_DAYS = 30
TOP_KEYWORDS_FOR_GROUPING = 3
MIN_SIMILAR_LEARNINGS = 2
MIN_KEYWORD_LENGTH = 3
TOP_KEYWORDS_LIMIT = 10

# Confidence calculation
CONFIDENCE_BASE = 0.5
CONFIDENCE_INCREMENT_PER_OCCURRENCE = 0.1
CONFIDENCE_MAX = 0.95

# Success/failure thresholds
SUCCESS_PATTERN_THRESHOLD = 0.8  # >= 80% success rate
FAILURE_PATTERN_THRESHOLD = 0.3  # <= 30% success rate

# Recommendation limits
MAX_RECOMMENDATIONS = 10

# Default summary settings
DEFAULT_SUMMARY_DAYS_LEARNING = 30
MAX_TOP_ERROR_TYPES = 5


# =============================================================================
# Rate Limiting Constants
# =============================================================================

# Default rate limits (requests per time window)
RATE_LIMIT_FILE_OPS = 100  # File operations per window
RATE_LIMIT_SEARCH_OPS = 50  # Search operations per window
RATE_LIMIT_INDEX_OPS = 20  # Index update operations per window

# Time windows (seconds)
RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute sliding window

# Burst allowance (allow short bursts above normal rate)
RATE_LIMIT_BURST_MULTIPLIER = 1.5  # Allow 50% burst capacity

# Cooldown settings
RATE_LIMIT_COOLDOWN_SECONDS = 5  # Minimum wait when rate exceeded

# Token bucket settings
TOKEN_BUCKET_REFILL_RATE = 10  # Tokens per second
TOKEN_BUCKET_MAX_TOKENS = 100  # Maximum bucket capacity
