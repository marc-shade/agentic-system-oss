"""
Initial Skill Library
====================

Seed collection of skills for the Skill Evolution System.

Skills are organized by category:
- Data Processing: Data manipulation and transformation
- Code Analysis: Code inspection and quality checks
- Pattern Matching: Pattern detection and recognition
- Optimization: Performance and efficiency improvements
- Error Handling: Robust error management patterns
"""

from .data_processing import *
from .code_analysis import *
from .pattern_matching import *
from .optimization import *
from .error_handling import *

__all__ = [
    # Data Processing
    "filter_positive_numbers",
    "batch_processor",
    "data_transformer",

    # Code Analysis
    "complexity_analyzer",
    "import_detector",
    "function_counter",

    # Pattern Matching
    "regex_matcher",
    "structural_pattern_finder",
    "anomaly_detector",

    # Optimization
    "query_optimizer",
    "cache_manager",
    "batch_optimizer",

    # Error Handling
    "safe_executor",
    "retry_handler",
    "graceful_degrader",
]
